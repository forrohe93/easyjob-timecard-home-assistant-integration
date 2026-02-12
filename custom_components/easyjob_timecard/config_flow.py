from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .api import EasyjobClient, EasyjobAuthError, EasyjobNotTimecardUserError
from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

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
                await client.async_validate_timecard_user()

            except EasyjobNotTimecardUserError:
                errors["base"] = "not_timecard_user"

            except EasyjobAuthError:
                # HA Standard-Key ist "invalid_auth"
                errors["base"] = "invalid_auth"

            except Exception as err:
                _LOGGER.exception("Unhandled error during config flow: %s", err)
                errors["base"] = "unknown"

            else:
                base_url = user_input[CONF_BASE_URL].rstrip("/")

                title = f"{base_url} - {user_input[CONF_USERNAME]}"
                return self.async_create_entry(
                    title=title,
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
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors: dict[str, str] = {}

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
                await client.async_validate_timecard_user()

            except EasyjobNotTimecardUserError:
                errors["base"] = "not_timecard_user"

            except EasyjobAuthError:
                errors["base"] = "invalid_auth"

            except Exception as err:
                _LOGGER.exception("Unhandled error during options flow: %s", err)
                errors["base"] = "unknown"

            else:
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
