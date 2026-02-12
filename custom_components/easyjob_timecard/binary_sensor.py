from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import EntityCategory

from . import RuntimeData
from .const import DOMAIN
from .entity import EasyjobCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            EasyjobConnectedBinarySensor(runtime, entry),
            EasyjobWorktimeActiveBinarySensor(runtime, entry),
        ],
        update_before_add=True,
    )


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

        # Falls mal dict statt EasyjobData
        if isinstance(data, dict):
            return data.get("work_time") or data.get("CurrentWorkTime")

        return getattr(data, "work_time", None)

    @property
    def is_on(self) -> bool:
        return self._work_time_raw() is not None

    @property
    def icon(self) -> str:
        return "mdi:clock-check" if self.is_on else "mdi:clock-outline"
