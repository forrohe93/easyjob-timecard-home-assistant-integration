from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, MANUFACTURER


class EasyjobBaseEntity:
    """Mixin providing common device_info (and defaults) for all entities."""

    _entry = None  # type: ignore[assignment]
    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo | None:
        entry = getattr(self, "_entry", None)
        if entry is None:
            return None

        username = entry.data.get("username", "user")
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Easyjob ({username})",
            manufacturer=MANUFACTURER,
            model=NAME,
        )


class EasyjobCoordinatorEntity(EasyjobBaseEntity, CoordinatorEntity):
    """Base for all coordinator-backed entities."""

    def __init__(self, coordinator, entry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        self._entry = entry
