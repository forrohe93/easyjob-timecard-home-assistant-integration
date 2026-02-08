from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EasyjobCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EasyjobCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([EasyjobWorktimeSwitch(hass, coordinator, entry)])


class EasyjobWorktimeSwitch(CoordinatorEntity[EasyjobCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Zeiterfassung"
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, hass: HomeAssistant, coordinator: EasyjobCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._entry = entry
        self._client = hass.data[DOMAIN][entry.entry_id]["client"]
        self._attr_unique_id = f"{entry.entry_id}_worktime_switch"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": f"Easyjob ({self._entry.data.get('username','user')})",
            "manufacturer": "protonic",
            "model": "easyjob Timecard",
        }

    @property
    def available(self) -> bool:
        # gleiches Verhalten wie deine anderen Coordinator-Entities
        return bool(self.coordinator.last_update_success)
    
    @property
    def icon(self) -> str:
        return "mdi:clock-check" if self.is_on else "mdi:clock-outline"


    @property
    def is_on(self) -> bool:
        """
        ECHTER Status aus der API:
        - work_time == None -> aus
        - work_time != None (JSON Array) -> an
        """
        data = self.coordinator.data
        if data is None:
            return False
        # robust: falls work_time mal als Attribut fehlt
        work_time = getattr(data, "work_time", None)
        return work_time is not None
    
    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data

        minutes = None
        if data is not None:
            minutes = getattr(data, "work_minutes", None)

            # robust: falls float kommt
            if isinstance(minutes, float):
                minutes = int(minutes)

        return {
            "work_minutes": minutes,
            "work_minutes_human": _minutes_to_human(minutes),
        }


    async def async_turn_on(self, **kwargs) -> None:
        # Wenn schon an, nichts tun (verhindert Doppelklick-Fehler)
        if self.is_on:
            return
        await self._client.async_start()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        # Wenn schon aus, nichts tun
        if not self.is_on:
            return
        await self._client.async_stop()
        await self.coordinator.async_request_refresh()

def _minutes_to_human(minutes: int | None) -> str | None:
    if minutes is None:
        return None
    if minutes < 0:
        return None

    h = minutes // 60
    m = minutes % 60

    parts: list[str] = []
    if h:
        parts.append(f"{h} h")
    # Minuten immer anzeigen (auch bei 0), damit z.B. "6 h 0 m" möglich ist
    parts.append(f"{m} m")

    return " ".join(parts)