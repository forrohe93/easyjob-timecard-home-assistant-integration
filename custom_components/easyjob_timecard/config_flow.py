from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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


def _build_schema(defaults: dict | None = None) -> vol.Schema:
    """Build config/options schema with optional defaults."""
    defaults = defaults or {}

    return vol.Schema(
        {
            vol.Required(CONF_BASE_URL, default=defaults.get(CONF_BASE_URL, "")): str,
            vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): str,
            vol.Required(
                CONF_VERIFY_SSL,
                default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            ): bool,
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _build_client(self, user_input: dict) -> EasyjobClient:
        """Create Easyjob client from user input."""
        session = async_get_clientsession(self.hass)
        return EasyjobClient(
            session=session,
            base_url=user_input[CONF_BASE_URL],
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
            verify_ssl=user_input[CONF_VERIFY_SSL],
        )

    async def _validate_input(self, user_input: dict, log_prefix: str) -> dict[str, str]:
        """Validate credentials and return HA-style error dict."""
        errors: dict[str, str] = {}

        try:
            client = await self._build_client(user_input)
            await client.async_test_auth()
            await client.async_validate_timecard_user()

        except EasyjobNotTimecardUserError:
            errors["base"] = "not_timecard_user"

        except EasyjobAuthError:
            errors["base"] = "invalid_auth"

        except Exception as err:
            _LOGGER.exception("Unhandled error during %s: %s", log_prefix, err)
            errors["base"] = "unknown"

        return errors

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._validate_input(user_input, "config flow")

            if not errors:
                base_url = user_input[CONF_BASE_URL].rstrip("/")
                title = f"{base_url} - {user_input[CONF_USERNAME]}"

                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(),
            errors=errors,
        )

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
            flow = ConfigFlow()
            flow.hass = self.hass  # reuse validation logic

            errors = await flow._validate_input(user_input, "options flow")

            if not errors:
                new_data = dict(self._config_entry.data)
                new_data.update(user_input)

                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data=new_data,
                )

                await self.hass.config_entries.async_reload(
                    self._config_entry.entry_id
                )

                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(self._config_entry.data),
            errors=errors,
        )
