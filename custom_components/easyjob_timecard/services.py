from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.components import persistent_notification, websocket_api

from .const import DOMAIN
from .runtime import RuntimeData
from .util import parse_ws_datetime

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_RESOURCE_STATE = "set_resource_state"

SERVICE_SET_RESOURCE_STATE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("start"): cv.datetime,
        vol.Required("end"): cv.datetime,
    }
)

_SERVICES_REGISTERED_KEY = "services_registered"
_WS_REGISTERED_KEY = "ws_registered"


async def async_register_services(hass: HomeAssistant) -> None:
    """Registriert Services (und optional WS) genau einmal global."""

    domain_data: dict[str, Any] = hass.data.setdefault(DOMAIN, {"entries": {}, "services": {}})
    domain_state: dict[str, Any] = domain_data["services"]


    # --- Service nur einmal global registrieren ---
    if not domain_state.get(_SERVICES_REGISTERED_KEY):
        domain_state[_SERVICES_REGISTERED_KEY] = True

        async def _service_handler(call: ServiceCall) -> None:
            await _handle_set_resource_state(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_RESOURCE_STATE,
            _service_handler,
            schema=SERVICE_SET_RESOURCE_STATE_SCHEMA,
        )

    # --- WebSocket command nur einmal global registrieren (optional, aber passt hier gut dazu) ---
    if not domain_state.get(_WS_REGISTERED_KEY):
        domain_state[_WS_REGISTERED_KEY] = True

        @websocket_api.async_response
        @websocket_api.require_admin
        @websocket_api.websocket_command(
            {
                "type": "easyjob_timecard/set_resource",
                "device_id": str,
                "start": str,
                "end": str,
            }
        )
        async def ws_set_resource(hass, connection, msg):
            try:
                start_dt = parse_ws_datetime(msg, "start")
                end_dt = parse_ws_datetime(msg, "end")

                if end_dt <= start_dt:
                    raise websocket_api.WebSocketError(
                        "invalid_range",
                        "'end' muss nach 'start' liegen."
                    )

                result = await _perform_set_resource_state(
                    hass, msg["device_id"], start_dt, end_dt
                )
                connection.send_result(msg["id"], {"result": result})

            except websocket_api.WebSocketError as err:
                connection.send_error(msg["id"], err.code, err.message)

        websocket_api.async_register_command(hass, ws_set_resource)


async def _perform_set_resource_state(
    hass: HomeAssistant, device_id: str, start_dt, end_dt
) -> Any:
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    device = dev_reg.async_get(device_id)
    if device is None:
        raise ValueError("device_id nicht gefunden.")

    config_entry_ids = list(device.config_entries)
    if not config_entry_ids:
        raise ValueError("Kein Config Entry für dieses Gerät gefunden.")

    entry_id = config_entry_ids[0]

    domain_data = hass.data.get(DOMAIN)
    if not domain_data or entry_id not in domain_data.get("entries", {}):
        raise ValueError("Config Entry der Integration nicht geladen (hass.data).")

    runtime: RuntimeData = domain_data["entries"][entry_id]

    client = runtime.client
    coordinator = runtime.coordinator

    # Select-Entity bevorzugt aus Runtime (wird in select.py gesetzt),
    # fallback: Entity Registry Scan (z.B. direkt nach Migration/Restore)
    select_entity_id: str | None = runtime.resource_state_select_entity_id

    if not select_entity_id:
        for e in er.async_entries_for_device(ent_reg, device_id):
            if e.domain == "select" and e.platform == DOMAIN:
                select_entity_id = e.entity_id
                break

    if not select_entity_id:
        raise ValueError("Keine Ressourcenstatus-Select-Entity auf dem Gerät gefunden.")


    sel_state = hass.states.get(select_entity_id)
    if sel_state is None:
        raise ValueError("Select-Entity State nicht gefunden.")

    caption = sel_state.state
    if not caption or caption in ("unknown", "unavailable"):
        raise ValueError("Ressourcenstatus ist nicht ausgewählt oder nicht verfügbar.")

    caption_to_id = runtime.resource_state_caption_to_id

    # Cache leer? -> einmalig von API holen und in Runtime cachen
    if not caption_to_id:
        types = await client.async_get_resource_state_types()
        caption_to_id = {
            t.get("Caption"): int(t.get("IdResourceStateType"))
            for t in types
            if t.get("Caption") and t.get("IdResourceStateType") is not None
        }
        runtime.resource_state_caption_to_id = dict(caption_to_id)

    type_id = caption_to_id.get(caption)

    if not type_id:
        raise ValueError(f"Ressourcenstatus '{caption}' nicht in der API-Liste gefunden.")

    start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    result = await client.async_save_resource_state(
        id_resource_state_type=int(type_id),
        start_iso=start_iso,
        end_iso=end_iso,
    )

    hass.bus.async_fire(
        "easyjob_timecard_set_resource_result",
        {"device_id": device_id, "result": result},
    )

    try:
        persistent_notification.async_create(
            hass,
            f"Ressourcenstatus gesetzt. API-Antwort: {result}",
            "easyjob_timecard",
        )
    except Exception:
        _LOGGER.debug("Konnte persistent notification nicht erstellen.")

    await coordinator.async_request_refresh()
    return result


async def _handle_set_resource_state(hass: HomeAssistant, call: ServiceCall) -> None:
    device_id: str = call.data["device_id"]
    start_dt = call.data["start"]
    end_dt = call.data["end"]

    try:
        result = await _perform_set_resource_state(hass, device_id, start_dt, end_dt)
        _LOGGER.info("Ressourcenstatus gesetzt, API-Antwort: %s", result)
    except Exception as err:
        _LOGGER.exception("Fehler beim Setzen des Ressourcenstatus: %s", err)
        raise
