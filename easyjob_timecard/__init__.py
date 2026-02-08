from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EasyjobClient
from .coordinator import EasyjobCoordinator
from .const import DOMAIN, PLATFORMS, CONF_BASE_URL, CONF_USERNAME, CONF_PASSWORD, CONF_VERIFY_SSL

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
    hass.data[DOMAIN][entry.entry_id] = {"client": client, "coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, "start"):

        async def handle_start(call: ServiceCall) -> None:
            await _handle_start(hass, call)

        async def handle_stop(call: ServiceCall) -> None:
            await _handle_stop(hass, call)

        hass.services.async_register(DOMAIN, "start", handle_start)
        hass.services.async_register(DOMAIN, "stop", handle_stop)


    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok

def _entry_id(call: ServiceCall) -> str:
    eid = call.data.get("entry_id")
    if not eid:
        raise ValueError("entry_id fehlt")
    return eid

async def _handle_start(hass: HomeAssistant, call: ServiceCall) -> None:
    entry_id = _entry_id(call)
    client = hass.data[DOMAIN][entry_id]["client"]
    coordinator = hass.data[DOMAIN][entry_id]["coordinator"]
    await client.async_start()
    await coordinator.async_request_refresh()

async def _handle_stop(hass: HomeAssistant, call: ServiceCall) -> None:
    entry_id = _entry_id(call)
    client = hass.data[DOMAIN][entry_id]["client"]
    coordinator = hass.data[DOMAIN][entry_id]["coordinator"]
    await client.async_stop()
    await coordinator.async_request_refresh()
