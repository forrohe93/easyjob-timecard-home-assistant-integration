from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import EntityCategory

from .const import DOMAIN
from .coordinator import EasyjobCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EasyjobCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        [
            EasyjobConnectedBinarySensor(coordinator, entry),
            EasyjobWorktimeActiveBinarySensor(coordinator, entry),
        ]
    )


class _BaseEasyjobBinarySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: EasyjobCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": f"Easyjob ({self._entry.data.get('username','user')})",
            "manufacturer": "protonic",
            "model": "easyjob Timecard",
        }


class EasyjobConnectedBinarySensor(_BaseEasyjobBinarySensor):
    _attr_name = "Verbunden"
    _attr_device_class = "connectivity"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:cloud-check-outline"

    def __init__(self, coordinator: EasyjobCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_connected"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.last_update_success)


class EasyjobWorktimeActiveBinarySensor(_BaseEasyjobBinarySensor):
    _attr_name = "Zeiterfassung aktiv"

    def __init__(self, coordinator: EasyjobCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_worktime_active"

    def _work_time_raw(self) -> Any:
        data = self.coordinator.data
        if data is None:
            return None
        # Falls mal dict statt EasyjobData
        if isinstance(data, dict):
            return data.get("work_time") or data.get("CurrentWorkTime")
        return getattr(data, "work_time", None)

    @property
    def is_on(self) -> bool:
        return self._work_time_raw() is not None

    @property
    def icon(self) -> str:
        # on = läuft, off = nicht aktiv
        return "mdi:clock-check" if self.is_on else "mdi:clock-outline"
