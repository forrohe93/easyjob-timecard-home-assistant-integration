from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import RuntimeData
from .const import (
    DOMAIN,
    CONF_FILTERED_IDT,
    DEFAULT_FILTERED_IDT,
    DEFAULT_LOOKAHEAD_DAYS,
)
from .entity import EasyjobBaseEntity
from .util import parse_datetime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EasyjobResourcePlanCalendar(hass, runtime, entry)])


class EasyjobResourcePlanCalendar(EasyjobBaseEntity, CalendarEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar"

    def __init__(
        self,
        hass: HomeAssistant,
        runtime: RuntimeData,
        entry: ConfigEntry,
    ) -> None:
        self.hass = hass
        self._runtime = runtime
        self._client = runtime.client
        self._entry = entry

        self._attr_name = "Ressourcenplan"
        self._attr_unique_id = f"{entry.entry_id}_resourceplan"

        self._event: CalendarEvent | None = None
        self._event_color: str | None = None

        self._filtered_idt: list[int] = list(
            entry.options.get(CONF_FILTERED_IDT, DEFAULT_FILTERED_IDT)
        )

    @property
    def available(self) -> bool:
        return bool(self._runtime.coordinator.last_update_success)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"event_color": self._event_color}

    @property
    def event(self) -> CalendarEvent | None:
        return self._event

    def _tz(self):
        return dt_util.get_time_zone(self.hass.config.time_zone)

    def _build_description(self, item: dict[str, Any]) -> str | None:
        pre = item.get("PreCaption")
        post = item.get("PostCaption")

        parts: list[str] = []
        if pre:
            parts.append(str(pre))
        if post:
            parts.append(str(post))

        return "\n".join(parts) if parts else None

    def _parse_item(
        self, item: dict[str, Any], tz
    ) -> tuple[CalendarEvent, str | None] | None:
        start_dt = parse_datetime(item.get("StartDate"))
        end_dt = parse_datetime(item.get("EndDate"))
        if start_dt is None or end_dt is None:
            return None

        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=tz)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=tz)

        uid = str(item.get("Id")) if item.get("Id") is not None else None
        caption = item.get("Caption") or ""

        ev = CalendarEvent(
            summary=caption,
            start=start_dt,
            end=end_dt,
            description=self._build_description(item),
            uid=uid,
        )

        return ev, item.get("Color")

    def _parse_items(
        self, items: list[dict[str, Any]] | None
    ) -> list[tuple[CalendarEvent, str | None]]:
        tz = self._tz()
        parsed: list[tuple[CalendarEvent, str | None]] = []

        for it in items or []:
            res = self._parse_item(it, tz)
            if res is not None:
                parsed.append(res)

        return parsed

    async def async_update(self) -> None:
        """Aktualisiert den Kalender-State (nächstes Event) + dessen Farbe."""
        now = dt_util.now()
        start = now.date()
        end = (now + timedelta(days=DEFAULT_LOOKAHEAD_DAYS)).date()

        items = await self._client.async_fetch_calendar(
            start, end, self._filtered_idt
        )
        parsed = self._parse_items(items)

        upcoming = [(ev, color) for (ev, color) in parsed if ev.end >= now]
        upcoming.sort(key=lambda t: t[0].start)

        if upcoming:
            self._event, self._event_color = upcoming[0]
        else:
            self._event, self._event_color = None, None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        items = await self._client.async_fetch_calendar(
            start_date.date(),
            end_date.date(),
            self._filtered_idt,
        )

        parsed = self._parse_items(items)
        return [ev for (ev, _color) in parsed]
