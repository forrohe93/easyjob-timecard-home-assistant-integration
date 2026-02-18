from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EasyjobClient
from .const import (
    CONF_BASE_URL,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import EasyjobCoordinator
from .runtime import RuntimeData
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)


def _make_stable_unique_id(base_url: str, username: str) -> str:
    """Create a stable unique_id for the config entry (legacy-safe)."""
    base = (base_url or "").strip().rstrip("/").lower()
    user = (username or "").strip().lower()
    return f"{base}|{user}"


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry from entry_id-based identifiers/unique_ids to stable unique_id.

    Version 1 -> 2:
      - Ensure entry.unique_id is set to a stable value (base_url|username)
      - Migrate Entity Registry unique_ids from "<entry_id>_..." -> "<entry.unique_id>_..."
      - Migrate Device Registry identifiers from (DOMAIN, entry_id) -> (DOMAIN, entry.unique_id)
    """
    if entry.version >= 2:
        return True

    old_entry_id = entry.entry_id
    base_url = str(entry.data.get(CONF_BASE_URL, ""))
    username = str(entry.data.get(CONF_USERNAME, ""))
    computed_uid = _make_stable_unique_id(base_url, username)

    _LOGGER.info(
        "Migrating %s entry %s from version %s to 2 (unique_id=%s)",
        DOMAIN,
        old_entry_id,
        entry.version,
        computed_uid,
    )

    # 1) Ensure ConfigEntry.unique_id is set
    if not entry.unique_id:
        hass.config_entries.async_update_entry(entry, unique_id=computed_uid)
        new_uid = computed_uid
    else:
        new_uid = entry.unique_id

    # 2) Migrate Entity Registry unique_id prefixes
    ent_reg = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(ent_reg, old_entry_id):
        if ent.unique_id and ent.unique_id.startswith(f"{old_entry_id}_"):
            migrated_unique_id = ent.unique_id.replace(old_entry_id, new_uid, 1)
            _LOGGER.debug(
                "Migrating entity unique_id %s: %s -> %s",
                ent.entity_id,
                ent.unique_id,
                migrated_unique_id,
            )
            ent_reg.async_update_entity(ent.entity_id, new_unique_id=migrated_unique_id)

    # 3) Migrate Device Registry identifiers (and avoid double devices)
    dev_reg = dr.async_get(hass)
    for dev in dr.async_entries_for_config_entry(dev_reg, old_entry_id):
        if (DOMAIN, old_entry_id) in dev.identifiers:
            new_identifiers = set(dev.identifiers)
            new_identifiers.discard((DOMAIN, old_entry_id))
            new_identifiers.add((DOMAIN, new_uid))

            _LOGGER.debug(
                "Migrating device identifiers for %s -> %s",
                dev.id,
                new_identifiers,
            )
            dev_reg.async_update_device(dev.id, new_identifiers=new_identifiers)

    # 4) Bump entry version
    hass.config_entries.async_update_entry(entry, version=2)

    _LOGGER.info("Migration completed for %s entry %s", DOMAIN, old_entry_id)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ---- Ensure stable entry.unique_id for legacy installs (defensive) ----
    # (The real migration happens in async_migrate_entry, but this also covers edge cases
    #  where entries existed without version bump / migration for some reason.)
    if not entry.unique_id:
        new_uid = _make_stable_unique_id(entry.data[CONF_BASE_URL], entry.data[CONF_USERNAME])
        hass.config_entries.async_update_entry(entry, unique_id=new_uid)

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

    domain_data = hass.data.setdefault(DOMAIN, {"entries": {}, "services": {}})
    domain_data["entries"][entry.entry_id] = RuntimeData(client=client, coordinator=coordinator)

    # Reload entry when options change (important for dynamic entities / filters)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Services / WebSocket Commands global einmalig registrieren
    await async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].get("entries", {}).pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
