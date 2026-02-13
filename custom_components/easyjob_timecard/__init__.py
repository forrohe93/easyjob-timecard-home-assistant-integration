from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.components import persistent_notification, websocket_api
from homeassistant.util import dt as dt_util

from .api import EasyjobClient
from .coordinator import EasyjobCoordinator
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_BASE_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_VERIFY_SSL,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_RESOURCE_STATE = "set_resource_state"

SERVICE_SET_RESOURCE_STATE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("start"): cv.datetime,
        vol.Required("end"): cv.datetime,
    }
)

_WS_REGISTERED_KEY = "ws_registered"


@dataclass
class RuntimeData:
    client: EasyjobClient
    coordinator: EasyjobCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    client = EasyjobClient(
        session=session,
        base_url=entry.data[CONF_BASE_URL],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, True),
    )

    coordinator = EasyjobCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = RuntimeData(client=client, coordinator=coordinator)

    # Reload entry when options change (important for dynamic entities / filters)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Service/Action nur einmal global registrieren
    if not hass.services.has_service(DOMAIN, SERVICE_SET_RESOURCE_STATE):

        async def _service_handler(call: ServiceCall) -> None:
            await _handle_set_resource_state(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_RESOURCE_STATE,
            _service_handler,
            schema=SERVICE_SET_RESOURCE_STATE_SCHEMA,
        )

    # WebSocket command nur einmal global registrieren
    domain_state: dict[str, Any] = hass.data[DOMAIN]
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
                start_dt = dt_util.parse_datetime(msg["start"])
                end_dt = dt_util.parse_datetime(msg["end"])
                result = await _perform_set_resource_state(
                    hass, msg["device_id"], start_dt, end_dt
                )
                connection.send_result(msg["id"], {"result": result})
            except Exception as err:
                _LOGGER.exception("WebSocket set_resource failed: %s", err)
                connection.send_error(msg["id"], "error", str(err))

        websocket_api.async_register_command(hass, ws_set_resource)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _perform_set_resource_state(
    hass: HomeAssistant, device_id: str, start_dt, end_dt
) -> Any:
    """Kernfunktion, die den Ressourcenstatus setzt und das API-Result zurückgibt."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    device = dev_reg.async_get(device_id)
    if device is None:
        raise ValueError("device_id nicht gefunden.")

    # Device -> Config Entry(s)
    config_entry_ids = list(device.config_entries)
    if not config_entry_ids:
        raise ValueError("Kein Config Entry für dieses Gerät gefunden.")

    entry_id = config_entry_ids[0]

    if DOMAIN not in hass.data or entry_id not in hass.data[DOMAIN]:
        raise ValueError("Config Entry der Integration nicht geladen (hass.data).")

    runtime: RuntimeData = hass.data[DOMAIN][entry_id]
    client = runtime.client
    coordinator = runtime.coordinator

    # Select-Entity auf diesem Device finden (domain=select, platform=easyjob_timecard)
    select_entity_id: str | None = None
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

    # Caption -> IdResourceStateType auflösen (robust)
    types = await client.async_get_resource_state_types()
    caption_to_id = {
        t.get("Caption"): int(t.get("IdResourceStateType"))
        for t in types
        if t.get("Caption") and t.get("IdResourceStateType") is not None
    }

    type_id = caption_to_id.get(caption)
    if not type_id:
        raise ValueError(f"Ressourcenstatus '{caption}' nicht in der API-Liste gefunden.")

    # API erwartet: "YYYY-MM-DDTHH:MM:SS"
    start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    result = await client.async_save_resource_state(
        id_resource_state_type=int(type_id),
        start_iso=start_iso,
        end_iso=end_iso,
    )

    # Fire event and persistent notification for backward compatibility
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
