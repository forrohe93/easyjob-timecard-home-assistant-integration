from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity

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
        [EasyjobResourceStateTypeSelect(runtime, entry)],
        update_before_add=True,
    )


class EasyjobResourceStateTypeSelect(EasyjobCoordinatorEntity, RestoreEntity, SelectEntity):
    _attr_translation_key = "resource_state_type"
    _attr_icon = "mdi:clipboard-text-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        runtime: RuntimeData,
        entry: ConfigEntry,
    ) -> None:
        EasyjobCoordinatorEntity.__init__(self, runtime.coordinator, entry)

        self._runtime = runtime
        self._client = runtime.client

        self._attr_unique_id = f"{entry.entry_id}_resource_state_type"

        self._caption_to_id: dict[str, int] = {}
        self._options: list[str] = []
        self._current: str | None = None

        # HA erwartet options beim Hinzufügen
        self._attr_options = []

    @property
    def options(self) -> list[str]:
        return self._options

    @property
    def current_option(self) -> str | None:
        return self._current

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # 1) Letzten Zustand wiederherstellen
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            self._current = last_state.state

        # 2) Optionen laden und nur fallbacken, wenn restored Wert nicht mehr existiert
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
        self._attr_options = self._options

        if not self._options:
            self._current = None
            return

        # Wenn kein current gesetzt ist oder current nicht mehr existiert -> fallback
        if self._current not in self._options:
            self._current = self._options[0]

    async def async_select_option(self, option: str) -> None:
        if option not in self._caption_to_id:
            return

        self._current = option
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        return {
            "id_resource_state_type": self._caption_to_id.get(self._current)
            if self._current
            else None
        }
