from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTime

from . import RuntimeData
from .const import DOMAIN
from .entity import EasyjobCoordinatorEntity


# (key, native_unit_of_measurement, getter)
SENSORS = [
    ("holidays", UnitOfTime.DAYS, lambda d: d.holidays),
    ("total_work_minutes", UnitOfTime.MINUTES, lambda d: d.total_work_minutes),
    ("work_minutes", UnitOfTime.MINUTES, lambda d: d.work_minutes),
    ("work_minutes_planed", UnitOfTime.MINUTES, lambda d: d.work_minutes_planed),
    ("work_time", None, lambda d: d.work_time),
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
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]

    entities = [
        EasyjobSensor(runtime, entry, key, unit, getter)
        for (key, unit, getter) in SENSORS
    ]

    async_add_entities(entities, update_before_add=True)


class EasyjobSensor(EasyjobCoordinatorEntity, SensorEntity):
    def __init__(
        self,
        runtime: RuntimeData,
        entry: ConfigEntry,
        key: str,
        unit: str | None,
        getter,
    ) -> None:
        EasyjobCoordinatorEntity.__init__(self, runtime.coordinator, entry)

        self._getter = getter
        self._key = key

        self._attr_unique_id = f"{entry.entry_id}_{key}"

        # Übersetzbarer Entity-Name über translations/strings.json + de.json/en.json
        # Erwartet: entity.sensor.<translation_key>.name
        self._attr_translation_key = key

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
