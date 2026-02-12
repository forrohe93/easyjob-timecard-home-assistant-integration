from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EasyjobCoordinator
from .entity import EasyjobBaseEntity

SENSORS = [
    ("holidays", "Holidays", "days", lambda d: d.holidays),
    ("total_work_minutes", "Total work minutes", "min", lambda d: d.total_work_minutes),
    ("work_minutes", "Work minutes", "min", lambda d: d.work_minutes),
    ("work_minutes_planed", "Work minutes planed", "min", lambda d: d.work_minutes_planed),
    ("work_time", "Work time", None, lambda d: d.work_time),
]

ICONS: dict[str, str] = {
    "holidays": "mdi:beach",
    "total_work_minutes": "mdi:counter",
    "work_minutes": "mdi:timer-outline",
    "work_minutes_planed": "mdi:calendar-clock",
    "work_time": "mdi:clock-outline",
}

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

class EasyjobSensor(EasyjobBaseEntity, CoordinatorEntity, SensorEntity):
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
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = f"{username} {name}"
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        data = self.coordinator.data
        if data is None:
            return None

        value = self._getter(data)

        if value is None:
            return None

        # Minuten-Sensoren immer als Ganzzahl
        if isinstance(value, (int, float)):
            return int(value)

        return value


    @property
    def icon(self) -> str | None:
        return ICONS.get(self._key)
