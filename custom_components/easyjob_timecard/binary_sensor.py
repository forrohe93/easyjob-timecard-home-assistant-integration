from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er
from homeassistant.const import EntityCategory
from homeassistant.util import dt as dt_util

from . import RuntimeData
from .const import DOMAIN, CONF_STATUS_BINARY_SENSORS, DEFAULT_STATUS_BINARY_SENSORS
from .entity import EasyjobCoordinatorEntity
from .util import parse_datetime


def _get_selected_status_ids(entry: ConfigEntry) -> list[int]:
    raw = entry.options.get(
        CONF_STATUS_BINARY_SENSORS,
        entry.data.get(CONF_STATUS_BINARY_SENSORS, DEFAULT_STATUS_BINARY_SENSORS),
    ) or []
    ids: set[int] = set()
    for v in raw:
        try:
            ids.add(int(v))
        except Exception:
            continue
    return sorted(ids)


def _norm_text(v: Any) -> str:
    return str(v).strip().casefold() if v is not None else ""


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]

    selected_ids = _get_selected_status_ids(entry)

    # --- CLEANUP: remove deselected dynamic entities from entity registry ---
    ent_reg = er.async_get(hass)

    # We delete only our dynamic status sensors. Unique_id pattern:
    # f"{entry.entry_id}_status_active_{status_id}"
    prefix = f"{entry.entry_id}_status_active_"

    to_remove: list[er.RegistryEntry] = []
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if reg_entry.domain != "binary_sensor":
            continue
        if reg_entry.platform != DOMAIN:
            continue
        if not reg_entry.unique_id:
            continue
        if not reg_entry.unique_id.startswith(prefix):
            continue

        # parse status_id from unique_id
        status_part = reg_entry.unique_id[len(prefix) :]
        try:
            status_id = int(status_part)
        except Exception:
            continue

        if status_id not in selected_ids:
            to_remove.append(reg_entry)

    for reg_entry in to_remove:
        ent_reg.async_remove(reg_entry.entity_id)
    # --- END CLEANUP ---

    entities: list[BinarySensorEntity] = [
        EasyjobConnectedBinarySensor(runtime, entry),
        EasyjobWorktimeActiveBinarySensor(runtime, entry),
    ]

    # Resolve nice names via API (Caption for IdResourceStateType)
    id_to_caption: dict[int, str] = {}
    if selected_ids:
        try:
            types = await runtime.client.async_get_resource_state_types()
            for t in types or []:
                cap = t.get("Caption")
                _id = t.get("IdResourceStateType")
                if cap and _id is not None:
                    try:
                        id_to_caption[int(_id)] = str(cap)
                    except Exception:
                        continue
        except Exception:
            id_to_caption = {}

    for status_id in selected_ids:
        entities.append(
            EasyjobResourceStatusActiveBinarySensor(
                runtime=runtime,
                entry=entry,
                status_id=status_id,
                status_caption=id_to_caption.get(status_id),
            )
        )

    async_add_entities(entities, update_before_add=True)


class _BaseEasyjobBinarySensor(EasyjobCoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, runtime: RuntimeData, entry: ConfigEntry) -> None:
        EasyjobCoordinatorEntity.__init__(self, runtime.coordinator, entry)
        self._runtime = runtime


class EasyjobConnectedBinarySensor(_BaseEasyjobBinarySensor):
    _attr_name = "Verbunden"
    _attr_device_class = "connectivity"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:cloud-check-outline"

    def __init__(self, runtime: RuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_connected"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.last_update_success)


class EasyjobWorktimeActiveBinarySensor(_BaseEasyjobBinarySensor):
    _attr_name = "Zeiterfassung aktiv"

    def __init__(self, runtime: RuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.entry_id}_worktime_active"

    def _work_time_raw(self) -> Any:
        data = self.coordinator.data
        if data is None:
            return None

        if isinstance(data, dict):
            return data.get("work_time") or data.get("CurrentWorkTime")

        return getattr(data, "work_time", None)

    @property
    def is_on(self) -> bool:
        return self._work_time_raw() is not None

    @property
    def icon(self) -> str:
        return "mdi:clock-check" if self.is_on else "mdi:clock-outline"


class EasyjobResourceStatusActiveBinarySensor(_BaseEasyjobBinarySensor):
    _attr_icon = "mdi:calendar-check"

    def __init__(
        self,
        runtime: RuntimeData,
        entry: ConfigEntry,
        status_id: int,
        status_caption: str | None = None,
    ) -> None:
        super().__init__(runtime, entry)

        self._status_id = int(status_id)
        self._status_caption = status_caption or None
        self._status_caption_norm = _norm_text(self._status_caption)

        self._attr_name = (
            f"Status aktiv: {self._status_caption}"
            if self._status_caption
            else f"Status aktiv: {self._status_id}"
        )
        self._attr_unique_id = f"{entry.entry_id}_status_active_{self._status_id}"

        self._active_item: dict[str, Any] | None = None
        self._next_item: dict[str, Any] | None = None
        self._matching_count: int = 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "status_id": self._status_id,
            "status_caption": self._status_caption,
            "matching_items_in_cache": self._matching_count,
            "calendar_last_updated": getattr(self.coordinator, "calendar_last_updated", None),
            "calendar_last_error": getattr(self.coordinator, "calendar_last_error", None),
        }
        if self._active_item:
            attrs.update(
                {
                    "active_event_id": self._active_item.get("Id"),
                    "active_caption": self._active_item.get("Caption"),
                    "active_idt": self._active_item.get("IdT"),
                    "active_start": self._active_item.get("StartDate"),
                    "active_end": self._active_item.get("EndDate"),
                    "active_color": self._active_item.get("Color"),
                }
            )
        if self._next_item:
            attrs.update(
                {
                    "next_event_id": self._next_item.get("Id"),
                    "next_caption": self._next_item.get("Caption"),
                    "next_idt": self._next_item.get("IdT"),
                    "next_start": self._next_item.get("StartDate"),
                    "next_end": self._next_item.get("EndDate"),
                    "next_color": self._next_item.get("Color"),
                }
            )
        return attrs

    def _event_matches_status(self, it: dict[str, Any]) -> bool:
        try:
            if int(it.get("IdT")) == self._status_id:
                return True
        except Exception:
            pass

        if not self._status_caption_norm:
            return False

        ev_cap_norm = _norm_text(it.get("Caption"))
        if not ev_cap_norm:
            return False

        return ev_cap_norm == self._status_caption_norm or self._status_caption_norm in ev_cap_norm

    def _iter_matching_items(self) -> list[dict[str, Any]]:
        items = list(getattr(self._runtime.coordinator, "calendar_items", []) or [])
        out: list[dict[str, Any]] = []
        for it in items:
            if self._event_matches_status(it):
                out.append(it)
        self._matching_count = len(out)
        return out

    def _to_local_dt(self, value: Any):
        dt = parse_datetime(value)
        if dt is None:
            return None

        if dt.tzinfo is None:
            tz_name = getattr(self.coordinator.hass.config, "time_zone", None)
            tz = dt_util.get_time_zone(tz_name) if tz_name else dt_util.DEFAULT_TIME_ZONE
            return dt.replace(tzinfo=tz)

        return dt_util.as_local(dt)

    def _compute_state(self) -> bool:
        now = dt_util.now()
        matches = self._iter_matching_items()

        active: list[tuple[Any, dict[str, Any]]] = []
        upcoming: list[tuple[Any, dict[str, Any]]] = []

        for it in matches:
            start = self._to_local_dt(it.get("StartDate"))
            end = self._to_local_dt(it.get("EndDate"))
            if start is None or end is None:
                continue

            if start <= now < end:
                active.append((start, it))
            elif start >= now:
                upcoming.append((start, it))

        active.sort(key=lambda t: t[0])
        upcoming.sort(key=lambda t: t[0])

        self._active_item = active[0][1] if active else None
        self._next_item = upcoming[0][1] if upcoming else None

        return self._active_item is not None

    @property
    def is_on(self) -> bool:
        return self._compute_state()

    @property
    def icon(self) -> str:
        return "mdi:calendar-check" if self.is_on else "mdi:calendar-blank"
