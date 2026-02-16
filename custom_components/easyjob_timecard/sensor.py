from __future__ import annotations

import ast
import json
from typing import Any

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
        self._attr_translation_key = key
        self._attr_native_unit_of_measurement = unit

    def _parse_work_time(self, value: Any) -> dict[str, Any] | None:
        """work_time kann dict sein oder als String ankommen -> robust parsen."""
        if value is None:
            return None

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None

            # 1) echtes JSON
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

            # 2) Python-dict-String wie "{'ID': 1, ...}"
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return None

        return None

    @property
    def native_value(self):
        data = self.coordinator.data
        if data is None:
            return None

        value = self._getter(data)
        if value is None:
            return None

        # work_time: State soll nur die ID sein (oder unknown via None)
        if self._key == "work_time":
            wt = self._parse_work_time(value)
            if not wt:
                return None

            work_id = wt.get("ID")
            if isinstance(work_id, (int, float)):
                return int(work_id)
            # Wenn ID fehlt/None/komisch -> unknown
            return None

        # Minuten-Sensoren immer als Ganzzahl
        if isinstance(value, (int, float)):
            return int(value)

        return value

    @property
    def extra_state_attributes(self) -> dict | None:
        data = self.coordinator.data
        if data is None:
            return None

        value = self._getter(data)
        if value is None:
            return None

        if self._key == "work_time":
            wt = self._parse_work_time(value)
            if not wt:
                return None
            # Alles außer "ID" als Attribute
            return {k: v for k, v in wt.items() if k != "ID"}

        return None

    @property
    def icon(self) -> str | None:
        return ICONS.get(self._key)
