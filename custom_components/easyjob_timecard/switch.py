from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RuntimeData
from .const import DOMAIN
from .entity import EasyjobCoordinatorEntity
from .util import minutes_to_human


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [EasyjobWorktimeSwitch(runtime, entry)],
        update_before_add=True,
    )


class EasyjobWorktimeSwitch(EasyjobCoordinatorEntity, SwitchEntity):
    _attr_translation_key = "worktime"

    def __init__(
        self,
        runtime: RuntimeData,
        entry: ConfigEntry,
    ) -> None:
        EasyjobCoordinatorEntity.__init__(self, runtime.coordinator, entry)

        self._runtime = runtime
        self._client = runtime.client

        self._attr_unique_id = f"{entry.entry_id}_worktime_switch"

    @property
    def available(self) -> bool:
        return bool(self.coordinator.last_update_success)

    @property
    def icon(self) -> str:
        return "mdi:clock-check" if self.is_on else "mdi:clock-outline"

    @property
    def is_on(self) -> bool:
        """
        Echter Status aus der API:
        - work_time == None -> aus
        - work_time != None -> an
        """
        data = self.coordinator.data
        if data is None:
            return False

        return getattr(data, "work_time", None) is not None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        minutes = getattr(data, "work_minutes", None) if data is not None else None

        if isinstance(minutes, float):
            minutes = int(minutes)

        return {
            "work_minutes": minutes,
            "work_minutes_human": minutes_to_human(minutes),
        }

    async def async_turn_on(self, **kwargs) -> None:
        if self.is_on:
            return

        await self._client.async_start()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        if not self.is_on:
            return

        await self._client.async_stop()
        await self.coordinator.async_request_refresh()
