from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from datetime import date
from .const import DEFAULT_FILTERED_IDT

import aiohttp


class EasyjobAuthError(Exception):
    """Raised when authentication/token retrieval fails."""

class EasyjobNotTimecardUserError(Exception):
    """User is not a Timecard user (IsTimeCardUser is false)."""


@dataclass
class EasyjobData:
    # Values for your sensors
    date: str | None
    holidays: int | None
    total_work_minutes: int | None
    work_minutes: int | None
    work_minutes_planed: int | None
    work_time: str | None  # "work_time" isn't directly in Details; we derive it from CurrentWorkTime


class EasyjobClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl

        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    # -------- Token --------

    async def async_get_token(self, force: bool = False) -> str:
        """Get and cache Bearer token from /token (x-www-form-urlencoded)."""
        if not force and self._access_token and self._token_expires_at:
            # 60s safety buffer
            if datetime.now(timezone.utc) < (self._token_expires_at - timedelta(seconds=60)):
                return self._access_token

        token_url = f"{self._base_url}/token"

        form = {
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            async with self._session.post(
                token_url,
                data=form,
                headers=headers,
                timeout=20,
                ssl=self._verify_ssl,  #  verify_ssl berücksichtigt
            ) as resp:
                if resp.status in (401, 403):
                    raise EasyjobAuthError("Token-Login fehlgeschlagen (401/403).")
                resp.raise_for_status()
                payload = await resp.json()
        except aiohttp.ClientConnectorCertificateError as err:
            raise EasyjobAuthError(f"SSL-Zertifikatsfehler beim Token-Login: {err}") from err
        except aiohttp.ClientSSLError as err:
            raise EasyjobAuthError(f"SSL-Fehler beim Token-Login: {err}") from err
        except aiohttp.ClientError as err:
            raise EasyjobAuthError(f"Netzwerkfehler beim Token-Login: {err}") from err

        token = payload.get("access_token")
        if not token:
            raise EasyjobAuthError("Kein access_token im /token Response gefunden.")

        expires_in = payload.get("expires_in", 600)
        self._access_token = token
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        return token

    async def _request(self, method: str, url: str, **kwargs) -> Any:
        """Perform a request with Bearer auth; retry once on 401 with fresh token.

        Extra keyword arguments (e.g. `json`, `params`) are forwarded to
        `aiohttp.ClientSession.request`.
        """
        token = await self.async_get_token()
        headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                timeout=20,
                ssl=self._verify_ssl,
                **kwargs,
            ) as resp:
                if resp.status == 401:
                    token = await self.async_get_token(force=True)
                    headers["Authorization"] = f"Bearer {token}"
                    async with self._session.request(
                        method,
                        url,
                        headers=headers,
                        timeout=20,
                        ssl=self._verify_ssl,
                        **kwargs,
                    ) as resp2:
                        resp2.raise_for_status()
                        if resp2.content_type == "application/json":
                            return await resp2.json()
                        return await resp2.text()

                resp.raise_for_status()
                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.text()

        except aiohttp.ClientConnectorCertificateError as err:
            raise EasyjobAuthError(f"SSL-Zertifikatsfehler: {err}") from err
        except aiohttp.ClientSSLError as err:
            raise EasyjobAuthError(f"SSL-Fehler: {err}") from err
        except aiohttp.ClientError as err:
            raise err

    # -------- Public API --------

    async def async_test_auth(self) -> None:
        """Used by config_flow to validate credentials."""
        await self.async_fetch_details()

    async def async_fetch_details(self, d: str | None = None) -> EasyjobData:
        """GET /api.json/Timecard/Details?d (param 'd' optional)."""
        if d:
            url = f"{self._base_url}/api.json/Timecard/Details?d={d}"
        else:
            # You provided it like this; keep exact behaviour.
            url = f"{self._base_url}/api.json/Timecard/Details?d"

        payload = await self._request("GET", url)

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
        url = f"{self._base_url}/api.json/Timecard/StartWorkTime"
        await self._request("POST", url)

    async def async_stop(self) -> None:
        """POST /api.json/Timecard/CloseWorkTime"""
        url = f"{self._base_url}/api.json/Timecard/CloseWorkTime"
        await self._request("POST", url)
    
    async def async_fetch_calendar(
        self,
        start: date,
        end: date,
        filtered_idt: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch calendar items from easyjob resource plan."""
        days = max(1, (end - start).days)
        startdate = start.strftime("%Y-%m-%d")
        url = f"{self._base_url}/api.json/dashboard/calendar/?days={days}&startdate={startdate}"
        payload = await self._request("GET", url)
        items: list[dict[str, Any]] = payload or []

        # Wenn None übergeben wird, nutzen wir Default-Liste (zukunftssicher)
        deny = DEFAULT_FILTERED_IDT if filtered_idt is None else filtered_idt
        if not deny:
            return items

        return [it for it in items if it.get("IdT") not in deny]

    _idaddress: int | None = None

    async def async_get_idaddress(self, force: bool = False) -> int:
        """GET /api.json/Common/GetWebSettings -> IdAddress"""
        if self._idaddress is not None and not force:
            return self._idaddress

        url = f"{self._base_url}/api.json/Common/GetWebSettings"
        payload = await self._request("GET", url)

        # je nach API kann das Feld anders heißen  passe ggf. an:
        # häufig: payload["IdAddress"] oder payload["IdAddressDefault"] o.ä.
        idaddress = payload.get("IdAddress") or payload.get("IdAddressDefault") or payload.get("idaddress")
        if not idaddress:
            raise ValueError("Konnte IdAddress nicht aus GetWebSettings lesen.")
        self._idaddress = int(idaddress)
        return self._idaddress

    async def async_get_resource_state_types(self) -> list[dict[str, Any]]:
        """GET /api.json/ResourceStates/GetFormData?id=0&idaddress=..."""
        idaddress = await self.async_get_idaddress()
        url = f"{self._base_url}/api.json/ResourceStates/GetFormData?id=0&idaddress={idaddress}"
        payload = await self._request("GET", url)
        return payload.get("ResourceStateTypeSelection", []) or []

    async def async_save_resource_state(
        self,
        id_resource_state_type: int,
        start_iso: str,
        end_iso: str,
    ) -> Any:
        """POST /api.json/ResourceStates/Save"""
        idaddress = await self.async_get_idaddress()
        url = f"{self._base_url}/api.json/ResourceStates/Save"
        body = {
            "IdResourceState": 0,
            "Address": {"IdAddress": idaddress},
            "IdResourceStateType": int(id_resource_state_type),
            "StartDate": start_iso,
            "EndDate": end_iso,
        }
        payload = await self._request("POST", url, json=body)
        return payload

    async def async_get_web_settings(self) -> dict:
        """GET /api.json/Common/GetWebSettings"""
        url = f"{self._base_url}/api.json/Common/GetWebSettings"
        payload = await self._request("GET", url)
        if not isinstance(payload, dict):
            raise ValueError("GetWebSettings returned unexpected response.")
        return payload

    async def async_validate_timecard_user(self) -> None:
        """Raise if user is not a Timecard user."""
        ws = await self.async_get_web_settings()
        is_tc = ws.get("IsTimeCardUser")
        if is_tc is not True:
            raise EasyjobNotTimecardUserError("User is not Timecard user")
