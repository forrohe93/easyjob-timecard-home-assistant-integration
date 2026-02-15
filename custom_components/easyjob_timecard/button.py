from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RuntimeData
from .const import DOMAIN
from .entity import EasyjobBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([EasyjobStartButton(hass, entry), EasyjobStopButton(hass, entry)])


class _BaseEasyjobButton(EasyjobBaseEntity, ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._entry = entry
        self._username = entry.data.get("username", "user")

    @property
    def _runtime(self) -> RuntimeData:
        return self.hass.data[DOMAIN][self.entry.entry_id]

    @property
    def _client(self):
        return self._runtime.client

    @property
    def _coordinator(self):
        return self._runtime.coordinator


class EasyjobStartButton(_BaseEasyjobButton):
    _attr_translation_key = "start"
    _attr_icon = "mdi:play"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry)
        self._attr_unique_id = f"{entry.entry_id}_start"

    async def async_press(self) -> None:
        _LOGGER.debug("Start pressed for entry_id=%s", self.entry.entry_id)
        await self._client.async_start()
        await self._coordinator.async_request_refresh()


class EasyjobStopButton(_BaseEasyjobButton):
    _attr_translation_key = "stop"
    _attr_icon = "mdi:stop"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry)
        self._attr_unique_id = f"{entry.entry_id}_stop"

    async def async_press(self) -> None:
        _LOGGER.debug("Stop pressed for entry_id=%s", self.entry.entry_id)
        await self._client.async_stop()
        await self._coordinator.async_request_refresh()
