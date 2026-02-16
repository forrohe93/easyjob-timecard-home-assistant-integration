from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from typing import Any, Final

import aiohttp


from .const import DEFAULT_FILTERED_IDT


# ---- Exceptions ----

class EasyjobApiError(Exception):
    """Base error for easyjob WebApi failures."""


class EasyjobAuthError(EasyjobApiError):
    """Raised when authentication/token retrieval fails."""


class EasyjobNotTimecardUserError(EasyjobApiError):
    """User is not a Timecard user (IsTimeCardUser is false)."""


class EasyjobRequestError(EasyjobApiError):
    """Raised for non-auth request failures (HTTP/Network/Parse)."""


# ---- Models ----

@dataclass
class EasyjobData:
    date: str | None
    holidays: int | None
    total_work_minutes: int | None
    work_minutes: int | None
    work_minutes_planed: int | None
    work_time: str | None  # derived from CurrentWorkTime


# ---- Client ----

class EasyjobClient:

    _TOKEN_SAFETY_BUFFER_SECONDS: Final[int] = 60
    _DEFAULT_TIMEOUT_SECONDS: Final[int] = 20

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
        timeout: int = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl
        self._timeout = aiohttp.ClientTimeout(total=timeout)

        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

        self._idaddress: int | None = None

    # ---------- Common helpers ----------

    def _common_headers(self) -> dict[str, str]:
        # Required by easyjob WebApi docs for full feature access.
        return {
            "Accept": "application/json",
            "ej-webapi-client": "ThirdParty",
        }

    def _auth_headers(self, token: str) -> dict[str, str]:
        h = self._common_headers()
        h["Authorization"] = f"Bearer {token}"
        return h

    @staticmethod
    def _is_json_response(resp: aiohttp.ClientResponse) -> bool:
        # Robust to "application/json; charset=utf-8"
        ctype = resp.headers.get("Content-Type", "")
        return ctype.lower().startswith("application/json")

    @staticmethod
    async def _read_response(resp: aiohttp.ClientResponse) -> Any:
        if EasyjobClient._is_json_response(resp):
            return await resp.json()
        return await resp.text()

    def _raise_ssl_as_auth(self, err: Exception, prefix: str) -> None:
        # SSL/Cert errors are effectively auth/connectivity errors in UI.
        raise EasyjobAuthError(f"{prefix}: {err}") from err

    async def _request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Perform a request against base_url.

        - Adds required protonic header `ej-webapi-client: ThirdParty`
        - Adds Bearer token if auth=True
        - Retries once on 401 by forcing a new token
        - Normalizes errors into Easyjob* exceptions
        """
        url = f"{self._base_url}{path}"

        base_headers = self._common_headers()
        if headers:
            base_headers.update(headers)

        token: str | None = None
        if auth:
            token = await self.async_get_token()
            base_headers = self._auth_headers(token) | (headers or {})

        try:
            async with self._session.request(
                method,
                url,
                headers=base_headers,
                ssl=self._verify_ssl,
                timeout=self._timeout,
                **kwargs,
            ) as resp:
                if auth and resp.status == 401:
                    # refresh token once and retry
                    token = await self.async_get_token(force=True)
                    retry_headers = self._auth_headers(token) | (headers or {})
                    async with self._session.request(
                        method,
                        url,
                        headers=retry_headers,
                        ssl=self._verify_ssl,
                        timeout=self._timeout,
                        **kwargs,
                    ) as resp2:
                        if resp2.status in (401, 403):
                            raise EasyjobAuthError("Unauthorized (401/403).")
                        resp2.raise_for_status()
                        return await self._read_response(resp2)

                if resp.status in (401, 403) and auth:
                    raise EasyjobAuthError("Unauthorized (401/403).")

                # Optional: rate limiting could happen; treat as request error
                # (you can add backoff later if needed)
                resp.raise_for_status()
                return await self._read_response(resp)

        except aiohttp.ClientConnectorCertificateError as err:
            self._raise_ssl_as_auth(err, "SSL certificate error")
        except aiohttp.ClientSSLError as err:
            self._raise_ssl_as_auth(err, "SSL error")
        except aiohttp.ClientResponseError as err:
            # HTTP error with status already in err.status
            raise EasyjobRequestError(f"HTTP error {err.status}: {err.message}") from err
        except aiohttp.ClientError as err:
            raise EasyjobRequestError(f"Network error: {err}") from err

    # ---------- Token ----------

    async def async_get_token(self, force: bool = False) -> str:
        """Get and cache Bearer token from /token (x-www-form-urlencoded)."""
        if not force and self._access_token and self._token_expires_at:
            if datetime.now(timezone.utc) < (
                self._token_expires_at - timedelta(seconds=self._TOKEN_SAFETY_BUFFER_SECONDS)
            ):
                return self._access_token

        form = {
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
        }

        headers = self._common_headers() | {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            async with self._session.post(
                f"{self._base_url}/token",
                data=form,
                headers=headers,
                ssl=self._verify_ssl,
                timeout=self._timeout,
            ) as resp:
                if resp.status in (401, 403):
                    raise EasyjobAuthError("Token login failed (401/403).")
                resp.raise_for_status()
                payload = await resp.json()

        except aiohttp.ClientConnectorCertificateError as err:
            self._raise_ssl_as_auth(err, "SSL certificate error during token login")
        except aiohttp.ClientSSLError as err:
            self._raise_ssl_as_auth(err, "SSL error during token login")
        except aiohttp.ClientResponseError as err:
            raise EasyjobAuthError(f"HTTP error during token login ({err.status}).") from err
        except aiohttp.ClientError as err:
            raise EasyjobAuthError(f"Network error during token login: {err}") from err

        token = payload.get("access_token")
        if not token:
            raise EasyjobAuthError("Missing access_token in /token response.")

        expires_in = int(payload.get("expires_in", 600))
        self._access_token = str(token)
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return self._access_token

    # ---------- Public API ----------

    async def async_test_auth(self) -> None:
        await self.async_fetch_details()

    async def async_fetch_details(self, d: str | None = None) -> EasyjobData:
        """GET /api.json/Timecard/Details?d (param 'd' optional)."""
        # Keep your existing behavior exactly:
        path = f"/api.json/Timecard/Details?d={d}" if d else "/api.json/Timecard/Details?d"
        payload = await self._request("GET", path, auth=True)

        current_work_time = payload.get("CurrentWorkTime")
        work_time = None if current_work_time is None else str(current_work_time)

        return EasyjobData(
            date=payload.get("Date"),
            holidays=payload.get("Holidays"),
            total_work_minutes=payload.get("TotalWorkMinutes"),
            work_minutes=payload.get("WorkMinutes"),
            work_minutes_planed=payload.get("WorkMinutesPlaned"),
            work_time=work_time,
        )

    async def async_start(self) -> None:
        """POST /api.json/Timecard/StartWorkTime"""
        await self._request("POST", "/api.json/Timecard/StartWorkTime", auth=True)

    async def async_stop(self) -> None:
        """POST /api.json/Timecard/CloseWorkTime"""
        await self._request("POST", "/api.json/Timecard/CloseWorkTime", auth=True)

    async def async_fetch_calendar(
        self,
        start: date,
        end: date,
        filtered_idt: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch calendar items from easyjob resource plan."""
        days = max(1, (end - start).days)
        startdate = start.strftime("%Y-%m-%d")
        path = f"/api.json/dashboard/calendar/?days={days}&startdate={startdate}"

        payload = await self._request("GET", path, auth=True)
        items: list[dict[str, Any]] = payload or []

        deny = DEFAULT_FILTERED_IDT if filtered_idt is None else filtered_idt
        if not deny:
            return items

        return [it for it in items if it.get("IdT") not in deny]

    async def async_get_idaddress(self, force: bool = False) -> int:
        """GET /api.json/Common/GetWebSettings -> IdAddress (cached)."""
        if self._idaddress is not None and not force:
            return self._idaddress

        payload = await self._request("GET", "/api.json/Common/GetWebSettings", auth=True)
        if not isinstance(payload, dict):
            raise EasyjobRequestError("GetWebSettings returned unexpected response.")

        idaddress = payload.get("IdAddress") or payload.get("IdAddressDefault") or payload.get("idaddress")
        if not idaddress:
            raise EasyjobRequestError("Could not read IdAddress from GetWebSettings response.")
        self._idaddress = int(idaddress)
        return self._idaddress

    async def async_get_resource_state_types(self) -> list[dict[str, Any]]:
        """GET /api.json/ResourceStates/GetFormData?id=0&idaddress=..."""
        idaddress = await self.async_get_idaddress()
        path = f"/api.json/ResourceStates/GetFormData?id=0&idaddress={idaddress}"
        payload = await self._request("GET", path, auth=True)
        if not isinstance(payload, dict):
            raise EasyjobRequestError("GetFormData returned unexpected response.")
        return payload.get("ResourceStateTypeSelection", []) or []

    async def async_save_resource_state(
        self,
        id_resource_state_type: int,
        start_iso: str,
        end_iso: str,
    ) -> Any:
        """POST /api.json/ResourceStates/Save"""
        idaddress = await self.async_get_idaddress()
        body = {
            "IdResourceState": 0,
            "Address": {"IdAddress": idaddress},
            "IdResourceStateType": int(id_resource_state_type),
            "StartDate": start_iso,
            "EndDate": end_iso,
        }
        return await self._request("POST", "/api.json/ResourceStates/Save", auth=True, json=body)

    async def async_get_web_settings(self) -> dict:
        """GET /api.json/Common/GetWebSettings"""
        payload = await self._request("GET", "/api.json/Common/GetWebSettings", auth=True)
        if not isinstance(payload, dict):
            raise EasyjobRequestError("GetWebSettings returned unexpected response.")
        return payload

    async def async_validate_timecard_user(self) -> None:
        """Raise if user is not a Timecard user."""
        ws = await self.async_get_web_settings()
        is_tc = ws.get("IsTimeCardUser")
        if is_tc is not True:
            raise EasyjobNotTimecardUserError("User is not Timecard user")

    async def async_get_global_web_settings(self) -> dict[str, Any]:
        """GET /api.json/Common/GetGlobalWebSettings"""
        payload = await self._request("GET", "/api.json/Common/GetGlobalWebSettings", auth=True)
        if not isinstance(payload, dict):
            raise EasyjobRequestError("GetGlobalWebSettings returned unexpected response.")
        return payload
