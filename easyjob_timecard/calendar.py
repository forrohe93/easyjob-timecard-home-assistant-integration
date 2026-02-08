from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import EasyjobCoordinator


DEFAULT_LOOKAHEAD_DAYS = 30


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    coordinator: EasyjobCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([EasyjobResourcePlanCalendar(hass, coordinator, entry)])


class EasyjobResourcePlanCalendar(CalendarEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar"

    def __init__(self, hass: HomeAssistant, coordinator: EasyjobCoordinator, entry: ConfigEntry) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self._entry = entry
        self._client = hass.data[DOMAIN][entry.entry_id]["client"]

        username = entry.data.get("username", "user")
        self._attr_name = f"{username} Ressourcenplan"
        self._attr_unique_id = f"{entry.entry_id}_resourceplan"

        self._event: CalendarEvent | None = None
        self._event_color: str | None = None  # <- nur ein HEX Wert

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": f"Easyjob ({self._entry.data.get('username','user')})",
            "manufacturer": "protonic",
            "model": "easyjob Resourcenplan",
        }

    @property
    def available(self) -> bool:
        return bool(self._coordinator.last_update_success)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Nur der HEX-Wert (oder None)
        return {
            "event_color": self._event_color,
        }

    @property
    def event(self) -> CalendarEvent | None:
        return self._event

    async def async_update(self) -> None:
        """
        Aktualisiert den Kalender-State (nächstes Event) + dessen Farbe.
        """
        now = dt_util.now()
        start = now.date()
        end = (now + timedelta(days=DEFAULT_LOOKAHEAD_DAYS)).date()

        items = await self._client.async_fetch_calendar(start, end)

        tz = dt_util.get_time_zone(self.hass.config.time_zone)
        parsed: list[tuple[CalendarEvent, str | None]] = []

        for it in items or []:
            start_dt = dt_util.parse_datetime(it.get("StartDate"))
            end_dt = dt_util.parse_datetime(it.get("EndDate"))
            if start_dt is None or end_dt is None:
                continue

            # API liefert ohne TZ -> als lokale TZ interpretieren
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=tz)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=tz)

            uid = str(it.get("Id")) if it.get("Id") is not None else None
            caption = it.get("Caption") or ""

            pre = it.get("PreCaption")
            post = it.get("PostCaption")
            desc_parts = []
            if pre:
                desc_parts.append(str(pre))
            if post:
                desc_parts.append(str(post))
            description = "\n".join(desc_parts) if desc_parts else None

            ev = CalendarEvent(
                summary=caption,
                start=start_dt,
                end=end_dt,
                description=description,
                uid=uid,
            )

            color = it.get("Color")
            parsed.append((ev, color))

        # nächstes Event bestimmen (noch nicht komplett vorbei)
        upcoming = [(ev, color) for (ev, color) in parsed if ev.end >= now]
        upcoming.sort(key=lambda t: t[0].start)

        if upcoming:
            self._event, self._event_color = upcoming[0][0], upcoming[0][1]
        else:
            self._event, self._event_color = None, None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """
        Wird von HA für die Kalender-Ansicht aufgerufen.
        (Hier liefern wir Events zurück; Farbe wird NICHT als Mapping gespeichert,
        sondern nur für das aktuelle 'event' in async_update.)
        """
        items = await self._client.async_fetch_calendar(start_date.date(), end_date.date())

        tz = dt_util.get_time_zone(hass.config.time_zone)
        events: list[CalendarEvent] = []

        for it in items or []:
            start_dt = dt_util.parse_datetime(it.get("StartDate"))
            end_dt = dt_util.parse_datetime(it.get("EndDate"))
            if start_dt is None or end_dt is None:
                continue

            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=tz)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=tz)

            uid = str(it.get("Id")) if it.get("Id") is not None else None
            caption = it.get("Caption") or ""

            pre = it.get("PreCaption")
            post = it.get("PostCaption")
            desc_parts = []
            if pre:
                desc_parts.append(str(pre))
            if post:
                desc_parts.append(str(post))
            description = "\n".join(desc_parts) if desc_parts else None

            events.append(
                CalendarEvent(
                    summary=caption,
                    start=start_dt,
                    end=end_dt,
                    description=description,
                    uid=uid,
                )
            )

        return events
