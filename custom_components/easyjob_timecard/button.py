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
    # RuntimeData wird einmal pro Entry geholt und in die Entities injected.
    # Wenn du später hass.data strukturiert (entries/ws_registered) umbaust,
    # änderst du nur diese Zeile.
    runtime: RuntimeData = hass.data[DOMAIN]["entries"][entry.entry_id]

    async_add_entities(
        [
            EasyjobStartButton(runtime, entry),
            EasyjobStopButton(runtime, entry),
        ]
    )


class _BaseEasyjobButton(EasyjobBaseEntity, ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, runtime: RuntimeData, entry: ConfigEntry) -> None:
        self._runtime = runtime
        self.entry = entry
        self._entry = entry
        self._username = entry.data.get("username", "user")

    @property
    def _client(self):
        return self._runtime.client

    @property
    def _coordinator(self):
        return self._runtime.coordinator


class EasyjobStartButton(_BaseEasyjobButton):
    _attr_translation_key = "start"
    _attr_icon = "mdi:play"

    def __init__(self, runtime: RuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.unique_id}_start"

    async def async_press(self) -> None:
        _LOGGER.debug("Start pressed for entry_id=%s", self.entry.entry_id)
        await self._client.async_start()
        await self._coordinator.async_request_refresh()


class EasyjobStopButton(_BaseEasyjobButton):
    _attr_translation_key = "stop"
    _attr_icon = "mdi:stop"

    def __init__(self, runtime: RuntimeData, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.unique_id}_stop"

    async def async_press(self) -> None:
        _LOGGER.debug("Stop pressed for entry_id=%s", self.entry.entry_id)
        await self._client.async_stop()
        await self._coordinator.async_request_refresh()
