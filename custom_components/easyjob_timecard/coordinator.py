from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EasyjobClient

_LOGGER = logging.getLogger(__name__)

class EasyjobCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: EasyjobClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="easyjob_timecard",
            update_interval=timedelta(seconds=60),
        )
        self.client = client

    async def _async_update_data(self):
        try:
            return await self.client.async_fetch_details()
        except Exception as err:
            raise UpdateFailed(str(err)) from err
