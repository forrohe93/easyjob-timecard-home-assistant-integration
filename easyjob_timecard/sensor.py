from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EasyjobCoordinator

SENSORS = [
    ("date", "Date", None, lambda d: d.date),
    ("holidays", "Holidays", None, lambda d: d.holidays),
    ("total_work_minutes", "Total work minutes", "min", lambda d: d.total_work_minutes),
    ("work_minutes", "Work minutes", "min", lambda d: d.work_minutes),
    ("work_minutes_planed", "Work minutes planed", "min", lambda d: d.work_minutes_planed),
    ("work_time", "Work time", None, lambda d: d.work_time),
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EasyjobCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    username = entry.data.get("username", "user")

    entities = [
        EasyjobSensor(coordinator, entry, username, key, name, unit, getter)
        for (key, name, unit, getter) in SENSORS
    ]
    async_add_entities(entities)

class EasyjobSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EasyjobCoordinator,
        entry: ConfigEntry,
        username: str,
        key: str,
        name: str,
        unit: str | None,
        getter,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._getter = getter
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = f"{username} {name}"
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        data = self.coordinator.data
        return None if data is None else self._getter(data)

    @property
    def device_info(self):
        # sorgt dafür, dass die Sensoren im gleichen Gerät wie die Buttons auftauchen
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": f"Easyjob ({self._entry.data.get('username','user')})",
            "manufacturer": "protonic",
            "model": "easyjob Timecard",
        }
