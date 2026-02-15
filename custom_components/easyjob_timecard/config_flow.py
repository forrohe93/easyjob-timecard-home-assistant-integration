from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EasyjobClient, EasyjobAuthError, EasyjobNotTimecardUserError
from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
    CONF_STATUS_BINARY_SENSORS,
    DEFAULT_STATUS_BINARY_SENSORS,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_multi_select_to_int_list(value) -> list[int]:
    """Convert HA multi_select output to a sorted list[int]."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw = value
    else:
        raw = [value]

    out: set[int] = set()
    for v in raw:
        try:
            out.add(int(v))
        except Exception:
            continue
    return sorted(out)


def _to_str_list(value) -> list[str]:
    """Convert list-ish of ids to list[str] for multi_select defaults."""
    if not value:
        return []
    out: list[str] = []
    for v in value:
        try:
            out.append(str(int(v)))
        except Exception:
            continue
    return out


def _normalize_base_url(base_url: str) -> str:
    """Normalize base url for consistent comparisons / unique_id."""
    return (base_url or "").strip().rstrip("/")


def _normalize_username(username: str) -> str:
    """Normalize username for consistent comparisons / unique_id."""
    return (username or "").strip()


def _make_unique_id(base_url: str, username: str) -> str:
    """Build a stable unique_id from base_url + username."""
    return f"{_normalize_base_url(base_url).lower()}|{_normalize_username(username).lower()}"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._base_input: dict | None = None
        self._types_map: dict[str, str] = {}

    def _is_duplicate_entry(self, base_url: str, username: str) -> bool:
        """Detect duplicates even if older entries have no unique_id."""
        wanted_uid = _make_unique_id(base_url, username)

        for entry in self.hass.config_entries.async_entries(DOMAIN):
            # Prefer unique_id when present
            if entry.unique_id and entry.unique_id == wanted_uid:
                return True

            # Fallback for legacy entries without unique_id
            other_url = _normalize_base_url(str(entry.data.get(CONF_BASE_URL, "")))
            other_user = _normalize_username(str(entry.data.get(CONF_USERNAME, "")))
            if _make_unique_id(other_url, other_user) == wanted_uid:
                return True

        return False

    async def _build_client(self, user_input: dict) -> EasyjobClient:
        session = async_get_clientsession(self.hass)
        return EasyjobClient(
            session=session,
            base_url=user_input[CONF_BASE_URL],
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
            verify_ssl=user_input[CONF_VERIFY_SSL],
        )

    async def _validate_input(self, user_input: dict, log_prefix: str) -> dict[str, str]:
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

    async def _fetch_resource_state_types_map(self, user_input: dict) -> dict[str, str]:
        client = await self._build_client(user_input)
        types = await client.async_get_resource_state_types()

        out: dict[str, str] = {}
        for t in types or []:
            cap = t.get("Caption")
            _id = t.get("IdResourceStateType")
            if not cap or _id is None:
                continue
            try:
                out[str(int(_id))] = str(cap)
            except Exception:
                continue

        return dict(sorted(out.items(), key=lambda kv: kv[1].lower()))

    def _schema_credentials(self, defaults: dict | None = None) -> vol.Schema:
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

    def _schema_status_selection(self, default_ids: list[int]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Optional(
                    CONF_STATUS_BINARY_SENSORS,
                    default=_to_str_list(default_ids),
                ): cv.multi_select(self._types_map),
            }
        )

    async def async_step_user(self, user_input=None):
        """Step 1: credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input = dict(user_input)
            user_input[CONF_BASE_URL] = _normalize_base_url(user_input[CONF_BASE_URL])
            user_input[CONF_USERNAME] = _normalize_username(user_input[CONF_USERNAME])

            # ---- Duplicate detection (URL + Username) ----
            # Check via unique_id AND legacy data fallback -> shows form error (not abort)
            if self._is_duplicate_entry(user_input[CONF_BASE_URL], user_input[CONF_USERNAME]):
                errors["base"] = "already_configured"
            else:
                # Keep unique_id for good measure (new entries will store it)
                await self.async_set_unique_id(
                    _make_unique_id(user_input[CONF_BASE_URL], user_input[CONF_USERNAME])
                )

                # ---- Validate credentials against backend ----
                errors = await self._validate_input(user_input, "config flow")
                if not errors:
                    self._base_input = user_input
                    try:
                        self._types_map = await self._fetch_resource_state_types_map(user_input)
                    except Exception as err:
                        _LOGGER.exception("Failed to fetch resource state types: %s", err)
                        errors["base"] = "unknown"

                    if not errors:
                        return await self.async_step_status()

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema_credentials(),
            errors=errors,
        )

    async def async_step_status(self, user_input=None):
        """Step 2: choose which resource statuses should become binary sensors."""
        if self._base_input is None:
            return await self.async_step_user()

        if user_input is not None:
            status_ids = _normalize_multi_select_to_int_list(
                user_input.get(CONF_STATUS_BINARY_SENSORS)
            )

            base_url = self._base_input[CONF_BASE_URL]
            title = f"{base_url} - {self._base_input[CONF_USERNAME]}"

            data = dict(self._base_input)
            options = {CONF_STATUS_BINARY_SENSORS: status_ids}

            # Prefer storing in options; fallback for older HA versions
            try:
                return self.async_create_entry(title=title, data=data, options=options)
            except TypeError:
                data.update(options)
                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="status",
            data_schema=self._schema_status_selection(DEFAULT_STATUS_BINARY_SENSORS),
            errors={},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._types_map: dict[str, str] = {}

    async def _build_client(self, user_input: dict) -> EasyjobClient:
        session = async_get_clientsession(self.hass)
        return EasyjobClient(
            session=session,
            base_url=user_input[CONF_BASE_URL],
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
            verify_ssl=user_input[CONF_VERIFY_SSL],
        )

    async def _validate_input(self, user_input: dict, log_prefix: str) -> dict[str, str]:
        errors: dict[str, str] = {}
        try:
            client = await self._build_client(user_input)
            await client.async_test_auth()
            await client.async_validate_timecard_user()
        except EasyjobNotTimecardUserError:
            errors["base"] = "not_timecard_user"
        except EasyjobAuthError:
            error
