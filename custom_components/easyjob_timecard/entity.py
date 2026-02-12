from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, NAME, MANUFACTURER


class EasyjobBaseEntity:

    _entry = None  # type: ignore[assignment]

    @property
    def device_info(self) -> DeviceInfo:
        username = self._entry.data.get("username", "user")
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"Easyjob ({username})",
            manufacturer=f"{MANUFACTURER}",
            model=f"{NAME}",
        )

class EasyjobCoordinatorEntity(EasyjobBaseEntity, CoordinatorEntity):
    """Base for all coordinator-backed entities."""

    def __init__(self, coordinator, entry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        self._entry = entry