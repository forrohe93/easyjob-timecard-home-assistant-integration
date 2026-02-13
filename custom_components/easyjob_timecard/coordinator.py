from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import EasyjobClient
from .const import DEFAULT_LOOKAHEAD_DAYS, DEFAULT_SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class EasyjobCoordinator(DataUpdateCoordinator):
    """Coordinator for easyjob timecard details + resource plan calendar cache.

    Notes:
    - `coordinator.data` stays the *details* object (backwards compatible for existing entities).
    - Calendar items are cached on the coordinator as `self.calendar_items`.
    - Calendar fetch failures are NON-FATAL (details still update), so entities don't go unavailable
      just because the calendar endpoint had a hiccup.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: EasyjobClient,
        *,
        lookahead_days: int = DEFAULT_LOOKAHEAD_DAYS,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="easyjob_timecard",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self.lookahead_days = lookahead_days

        # Cached calendar items (resource plan)
        self.calendar_items: list[dict] = []
        self.calendar_last_updated = None
        self.calendar_last_error: str | None = None

    async def _async_update_data(self):
        """Fetch timecard details and refresh cached calendar items.

        Details fetch is REQUIRED. Calendar fetch is BEST-EFFORT.
        """
        # Always fetch details (core data for existing entities)
        details_task = self.client.async_fetch_details()

        # Fetch calendar for a lookahead window; keep unfiltered here so other features can use it.
        start = dt_util.now().date()
        end = start + timedelta(days=self.lookahead_days)
        calendar_task = self.client.async_fetch_calendar(
            start=start,
            end=end,
            filtered_idt=[],  # do NOT apply filtering in the coordinator cache
        )

        try:
            details_result, calendar_result = await asyncio.gather(
                details_task, calendar_task, return_exceptions=True
            )

            # Details failures are fatal (integration data is stale/unreliable)
            if isinstance(details_result, Exception):
                raise details_result

            # Calendar failures are non-fatal; keep last known cache and expose error
            if isinstance(calendar_result, Exception):
                self.calendar_last_error = str(calendar_result)
                _LOGGER.debug("Calendar update failed (non-fatal): %s", calendar_result)
            else:
                self.calendar_items = calendar_result or []
                self.calendar_last_updated = dt_util.utcnow()
                self.calendar_last_error = None

            return details_result

        except Exception as err:
            # If details failed (or something unexpected), mark update failed.
            raise UpdateFailed(str(err)) from err
