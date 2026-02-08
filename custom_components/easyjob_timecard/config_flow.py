from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EasyjobClient, EasyjobAuthError
from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                client = EasyjobClient(
                    session=session,
                    base_url=user_input[CONF_BASE_URL],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    verify_ssl=user_input[CONF_VERIFY_SSL],
                )
                await client.async_test_auth()
            except EasyjobAuthError:
                errors["base"] = "auth_failed"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data={
                        CONF_BASE_URL: user_input[CONF_BASE_URL],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        # NICHT self.config_entry = ... (read-only property)!
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                client = EasyjobClient(
                    session=session,
                    base_url=user_input[CONF_BASE_URL],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    verify_ssl=user_input[CONF_VERIFY_SSL],
                )
                await client.async_test_auth()
            except EasyjobAuthError:
                errors["base"] = "auth_failed"
            except Exception:
                errors["base"] = "unknown"
            else:
                # Update Entry Daten
                new_data = dict(self._config_entry.data)
                new_data.update(
                    {
                        CONF_BASE_URL: user_input[CONF_BASE_URL],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                    }
                )
                self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

                # Entry neu laden, damit neuer Client mit neuen Credentials/SSL gebaut wird
                await self.hass.config_entries.async_reload(self._config_entry.entry_id)

                return self.async_create_entry(title="", data={})

        data = self._config_entry.data
        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=data.get(CONF_BASE_URL, "")): str,
                vol.Required(CONF_USERNAME, default=data.get(CONF_USERNAME, "")): str,
                vol.Required(CONF_PASSWORD, default=data.get(CONF_PASSWORD, "")): str,
                vol.Required(CONF_VERIFY_SSL, default=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
