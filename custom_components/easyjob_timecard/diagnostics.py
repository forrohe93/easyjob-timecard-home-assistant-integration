from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import DOMAIN, CONF_PASSWORD
from .runtime import RuntimeData

TO_REDACT = {CONF_PASSWORD, "Authorization", "access_token", "refresh_token"}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    domain_data = hass.data.get(DOMAIN, {})
    runtime: RuntimeData | None = domain_data.get("entries", {}).get(entry.entry_id)

    coordinator = runtime.coordinator if runtime else None

    data: dict[str, Any] = {
        "entry": {
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
            "version": entry.version,
        },
        "coordinator": {
            "last_update_success": getattr(coordinator, "last_update_success", None),
            "last_exception": str(getattr(coordinator, "last_exception", "") or ""),
            "calendar_last_error": getattr(coordinator, "calendar_last_error", None),
            "calendar_last_updated": str(getattr(coordinator, "calendar_last_updated", None)),
            "web_api_version": getattr(coordinator, "web_api_version", None),
            "web_api_version_last_error": getattr(coordinator, "web_api_version_last_error", None),
        },
        # optional: ein kleiner Snapshot der letzten Daten (aber nicht zu groß)
        "data_snapshot": _safe_data_snapshot(getattr(coordinator, "data", None)),
    }

    return async_redact_data(data, TO_REDACT)

def _safe_data_snapshot(details) -> dict[str, Any] | None:
    if details is None:
        return None
    # EasyjobData ist bei dir ein Dataclass → super dafür
    try:
        return {
            "date": getattr(details, "date", None),
            "holidays": getattr(details, "holidays", None),
            "total_work_minutes": getattr(details, "total_work_minutes", None),
            "work_minutes": getattr(details, "work_minutes", None),
            "work_minutes_planed": getattr(details, "work_minutes_planed", None),
            "work_time": getattr(details, "work_time", None),
        }
    except Exception:
        return None
