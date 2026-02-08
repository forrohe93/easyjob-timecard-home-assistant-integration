from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
    client = hass.data[DOMAIN][entry.entry_id]["client"]
    async_add_entities([EasyjobResourceStateTypeSelect(hass, coordinator, entry, client)])


class EasyjobResourceStateTypeSelect(CoordinatorEntity[EasyjobCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Ressourcenstatus"
    _attr_icon = "mdi:clipboard-text-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: EasyjobCoordinator,
        entry: ConfigEntry,
        client,
    ) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self._entry = entry
        self._client = client

        self._attr_unique_id = f"{entry.entry_id}_resource_state_type"

        self._caption_to_id: dict[str, int] = {}
        self._options: list[str] = []
        self._current: str | None = None

        # WICHTIG: options muss beim Add bereits existieren
        self._attr_options = []

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": f"Easyjob ({self._entry.data.get('username','user')})",
            "manufacturer": "protonic",
            "model": "easyjob Timecard",
        }

    @property
    def options(self) -> list[str]:
        # SelectEntity erwartet zwingend options
        return self._options

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._refresh_options()
        self.async_write_ha_state()

    async def _refresh_options(self) -> None:
        items = await self._client.async_get_resource_state_types()

        self._caption_to_id = {
            i["Caption"]: int(i["IdResourceStateType"])
            for i in items
            if i.get("Caption") and i.get("IdResourceStateType") is not None
        }

        self._options = list(self._caption_to_id.keys())

        # Zusätzlich _attr_options aktualisieren (HA nutzt je nach Version beides)
        self._attr_options = self._options

        if self._options and self._current not in self._options:
            self._current = self._options[0]
        elif not self._options:
            self._current = None

    async def async_select_option(self, option: str) -> None:
        if option not in self._caption_to_id:
            return
        self._current = option
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        return {
            "id_resource_state_type": self._caption_to_id.get(self._current) if self._current else None
        }
