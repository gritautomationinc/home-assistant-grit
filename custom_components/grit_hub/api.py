"""Async client for the GRIT Hub API."""
from __future__ import annotations

import asyncio
import math
from typing import Any
from urllib.parse import quote

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auth import bearer_authorization_value, validate_bearer_token
from .const import DEVICE_TYPES, REMOTE_TYPES, REST_DISCOVERY_TIMEOUT
from .hub import normalize_hub_id, sanitize_hub_data


class GritHubApiError(Exception):
    """Raised when the GRIT Hub API returns a safe, bounded error."""

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status


class GritHubValidationError(GritHubApiError):
    """Invalid caller input rejected before any HTTP request."""


class GritHubApiClient:
    """Small, defensive async API client for GRIT Hub."""

    def __init__(self, hass, base_url: str, token: str, verify_ssl: bool = True) -> None:
        self.hass = hass
        self.base_url = base_url.rstrip("/")
        self.token = validate_bearer_token(token)
        self.verify_ssl = verify_ssl
        self.session = async_get_clientsession(hass, verify_ssl=verify_ssl)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": bearer_authorization_value(self.token),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        timeout: int = 20,
    ) -> Any:
        if not path.startswith("/"):
            path = f"/{path}"
        url = f"{self.base_url}{path}"
        endpoint = endpoint_identifier(path)
        try:
            async with self.session.request(
                method.upper(),
                url,
                headers=self.headers,
                json=json,
                params=params,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=False,
            ) as resp:
                if resp.status >= 300:
                    raise GritHubApiError(
                        f"{method.upper()} {endpoint} failed: HTTP {resp.status}",
                        http_status=resp.status,
                    )
                text = await resp.text()
                if not text:
                    return None
                ctype = resp.headers.get("Content-Type", "")
                if "json" in ctype.lower():
                    return await resp.json(content_type=None)
                return text
        except asyncio.TimeoutError as err:
            raise GritHubApiError(f"{method.upper()} {endpoint} timed out") from err
        except aiohttp.ClientError as err:
            raise GritHubApiError(
                f"{method.upper()} {endpoint} failed due to a client error"
            ) from err

    async def health_check(self) -> Any:
        """Prefer `/health-check`; fall back to `/` only on HTTP 404."""
        try:
            return await self.request("GET", "/health-check", timeout=10)
        except GritHubApiError as err:
            if err.http_status == 404:
                return await self.request("GET", "/", timeout=10)
            if err.http_status == 503:
                raise GritHubApiError(
                    "Hub health check: identity unavailable (503)",
                    http_status=503,
                ) from err
            raise

    async def get_hub(self) -> dict[str, Any] | None:
        """Read the documented current-hub response and sanitize it."""
        data = await self.request(
            "GET",
            "/api/hub",
            timeout=REST_DISCOVERY_TIMEOUT,
        )
        return sanitize_hub_data(data)

    async def set_gritlock(self, locked: bool) -> Any:
        """Set system-wide GRITLock through the bounded lockout route."""
        if not isinstance(locked, bool):
            raise GritHubApiError("GRITLock state is invalid")
        try:
            return await self.request(
                "PUT",
                "/api/hub/lockout",
                json={"state": locked},
                timeout=REST_DISCOVERY_TIMEOUT,
            )
        except GritHubApiError as err:
            if err.http_status == 502:
                raise GritHubApiError(
                    "GRITLock was partially applied",
                    http_status=502,
                ) from err
            if err.http_status == 409:
                raise GritHubApiError(
                    "GRITLock request was superseded by a newer request",
                    http_status=409,
                ) from err
            raise

    async def set_system_led_brightness(
        self,
        hub_id: str,
        brightness: int,
    ) -> Any:
        """Update only the documented system LED brightness setting."""
        normalized_hub_id = normalize_hub_id(hub_id)
        if normalized_hub_id is None:
            raise GritHubApiError("Hub identifier is invalid")
        if (
            isinstance(brightness, bool)
            or not isinstance(brightness, int)
            or not 0 <= brightness <= 100
        ):
            raise GritHubApiError("System LED brightness is invalid")
        return await self.request(
            "PUT",
            f"/api/hub/{quote(normalized_hub_id)}/settings",
            json={"systemLedBrightness": brightness},
            timeout=REST_DISCOVERY_TIMEOUT,
        )

    async def get_collection(self, device_type: str) -> list[dict[str, Any]]:
        normalized_type = _normalize_path_component(
            device_type, label="Device type"
        )
        if normalized_type not in DEVICE_TYPES:
            raise GritHubValidationError("Device type is invalid")
        data = await self.request(
            "GET",
            f"/api/{quote(normalized_type, safe='')}",
        )
        items = normalise_list(data)
        sanitized = [
            sanitize_device_data(item, device_type=normalized_type)
            for item in items
        ]
        return [item for item in sanitized if item]

    async def get_rfid_device(self, device_id: str) -> dict[str, Any]:
        """Read and strictly sanitize one RFID reader detail response."""
        if not isinstance(device_id, str):
            raise GritHubValidationError("RFID device identifier is invalid")
        normalized_id = _normalize_path_component(
            device_id, label="RFID device identifier"
        )
        data = await self.request(
            "GET",
            f"/api/rfid/{quote(normalized_id, safe='')}",
            timeout=REST_DISCOVERY_TIMEOUT,
        )
        return sanitize_rfid_device_data(data)

    async def get_collector_device(self, device_id: str) -> dict[str, Any]:
        """Read and strictly sanitize one collector detail response."""
        if not isinstance(device_id, str):
            raise GritHubValidationError("Collector device identifier is invalid")
        normalized_id = _normalize_path_component(
            device_id, label="Collector device identifier"
        )
        data = await self.request(
            "GET",
            f"/api/collector/{quote(normalized_id, safe='')}",
            timeout=REST_DISCOVERY_TIMEOUT,
        )
        return sanitize_collector_device_data(data)

    async def request_device_telemetry(
        self,
        device_type: str,
        device_id: str,
    ) -> None:
        """Request current telemetry for one supported mesh device."""
        if not isinstance(device_type, str) or device_type not in {
            "gate",
            "rfid",
            "trigger",
        }:
            raise GritHubValidationError("Telemetry device type is invalid")
        if not isinstance(device_id, str):
            raise GritHubValidationError("Telemetry device identifier is invalid")
        normalized_type = _normalize_path_component(
            device_type, label="Telemetry device type"
        )
        normalized_id = _normalize_path_component(
            device_id, label="Telemetry device identifier"
        )
        response = await self.request(
            "POST",
            "/api/device/mesh-telemetry/refresh/"
            f"{quote(normalized_type, safe='')}/{quote(normalized_id, safe='')}",
            timeout=REST_DISCOVERY_TIMEOUT,
        )
        if not isinstance(response, dict) or response.get("success") is not True:
            raise GritHubApiError("Telemetry refresh request failed")

    async def set_device_state(
        self, device_type: str, device_id: str | int, on: bool
    ) -> Any:
        normalized_type = _normalize_path_component(device_type, label="Device type")
        if normalized_type not in DEVICE_TYPES:
            raise GritHubValidationError("Device type is invalid")
        normalized_id = _normalize_path_component(
            device_id, label="Device identifier"
        )
        value = "true" if on else "false"
        # Most controllable GRIT devices use state/{onOff}. Some endpoints use
        # a semantic open boolean; the caller maps that for covers.
        return await self.request(
            "PUT",
            f"/api/{quote(normalized_type, safe='')}/{quote(normalized_id, safe='')}/state/{value}",
        )

    async def set_air_filter(self, device_id: str | int, on: bool, minutes: int) -> Any:
        """Use the Hub's timed manual air-filter override."""
        normalized_id = _normalize_path_component(device_id, label="Device identifier")
        if (
            not isinstance(on, bool)
            or isinstance(minutes, bool)
            or not isinstance(minutes, int)
            or not 1 <= minutes <= 1440
        ):
            raise GritHubValidationError("Air filter run time is invalid")
        body = {"manual": True}
        if on:
            body["minutes"] = minutes
        return await self.request(
            "POST",
            f"/api/airquality/{quote(normalized_id, safe='')}/override/{str(on).lower()}",
            json=body,
        )

    async def call_command(
        self,
        device_type: str,
        device_id: str | int,
        command_name: str,
        action: str,
        remote_type: str = "api",
    ) -> Any:
        normalized_type = _normalize_path_component(device_type, label="Device type")
        if normalized_type not in DEVICE_TYPES:
            raise GritHubValidationError("Device type is invalid")
        normalized_id = _normalize_path_component(device_id, label="Device identifier")
        normalized_command = _normalize_path_component(
            command_name, label="Command name"
        )
        normalized_action = _normalize_path_component(action, label="Action")
        normalized_remote = _normalize_path_component(
            remote_type, label="Remote type"
        )
        if normalized_remote not in REMOTE_TYPES:
            raise GritHubValidationError("Remote type is invalid")
        return await self.request(
            "POST",
            "/api/command/"
            f"{quote(normalized_type, safe='')}/"
            f"{quote(normalized_id, safe='')}/"
            f"{quote(normalized_command, safe='')}/"
            f"{quote(normalized_action, safe='')}/"
            f"{quote(normalized_remote, safe='')}",
            json={},
        )

    async def refresh_device(self, device_type: str, device_id: str | int) -> Any:
        normalized_type = _normalize_path_component(device_type, label="Device type")
        if normalized_type not in DEVICE_TYPES:
            raise GritHubValidationError("Device type is invalid")
        normalized_id = _normalize_path_component(device_id, label="Device identifier")
        return await self.request(
            "GET",
            f"/api/device/refresh/{quote(normalized_type, safe='')}/{quote(normalized_id, safe='')}",
        )

    async def locate_device(self, device_type: str, device_id: str | int) -> Any:
        normalized_type = _normalize_path_component(device_type, label="Device type")
        if normalized_type not in DEVICE_TYPES:
            raise GritHubValidationError("Device type is invalid")
        normalized_id = _normalize_path_component(device_id, label="Device identifier")
        return await self.request(
            "GET",
            f"/api/device/locate/{quote(normalized_type, safe='')}/{quote(normalized_id, safe='')}",
        )


def _normalize_path_component(
    value: str | int,
    *,
    label: str,
) -> str:
    """Reject path traversal and encoded separators before any HTTP call (AC5)."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise GritHubValidationError(f"{label} is invalid")
    normalized = str(value).strip()
    lowered = normalized.lower()
    if (
        not normalized
        or normalized in {".", ".."}
        or len(normalized) > 128
        or not normalized.isprintable()
        or any(ord(char) < 32 for char in normalized)
        or "/" in normalized
        or "\\" in normalized
        or "%2f" in lowered
        or "%2e%2e" in lowered
        or "%5c" in lowered
    ):
        raise GritHubValidationError(f"{label} is invalid")
    return normalized


def endpoint_identifier(path: str) -> str:
    """Return a bounded endpoint label without query values or object IDs."""
    segments = [segment for segment in path.split("?", 1)[0].split("/") if segment]
    if not segments:
        return "/"
    visible_count = 2 if segments[0].lower() == "api" else 1
    visible = segments[:visible_count]
    suffix = "/*" if len(segments) > len(visible) else ""
    return f"/{'/'.join(visible)}{suffix}"


_DEVICE_IDENTIFIER_FIELDS = (
    "id",
    "deviceId",
    "deviceID",
    "_id",
    "uuid",
    "key",
    "serialNumber",
    "serial",
    "deviceIdentifier",
)
_DEVICE_NAME_FIELDS = ("name", "displayName", "label", "description", "deviceName")
_DEVICE_STATE_FIELDS = (
    "status",
    "state",
    "mode",
    "on",
    "onOff",
    "enabled",
    "active",
    "open",
    "locked",
    "isOn",
)
_DEVICE_BOOLEAN_FIELDS = ("gritLockEnabled", "gritLockState")
_MAX_DEVICE_TEXT_LENGTH = 128


def _bounded_device_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if (
        not value
        or len(value) > _MAX_DEVICE_TEXT_LENGTH
        or not value.isprintable()
    ):
        return None
    return value


def sanitize_device_data(
    value: Any,
    *,
    device_type: str | None = None,
) -> dict[str, Any]:
    """Retain only bounded fields required by existing entities and commands."""
    if not isinstance(value, dict):
        return {}

    sanitized: dict[str, Any] = {}
    for field in _DEVICE_IDENTIFIER_FIELDS:
        raw = value.get(field)
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int):
            sanitized[field] = raw
            continue
        text = _bounded_device_text(raw)
        if text is not None:
            sanitized[field] = text

    for field in _DEVICE_NAME_FIELDS:
        text = _bounded_device_text(value.get(field))
        if text is not None:
            sanitized[field] = text

    for field in _DEVICE_STATE_FIELDS:
        if device_type in {"rfid", "collector"} and field == "state":
            continue
        raw = value.get(field)
        if isinstance(raw, bool) or isinstance(raw, int):
            sanitized[field] = raw
        elif isinstance(raw, float) and math.isfinite(raw):
            sanitized[field] = raw
        else:
            text = _bounded_device_text(raw)
            if text is not None:
                sanitized[field] = text

    for field in _DEVICE_BOOLEAN_FIELDS:
        raw = value.get(field)
        if isinstance(raw, bool):
            sanitized[field] = raw

    if device_type == "airquality":
        version = _bounded_device_text(value.get("version"))
        if version is not None:
            sanitized["version"] = version
        control_type = value.get("controlType")
        if control_type in {"inline", "ir", "rf"}:
            sanitized["controlType"] = control_type
        minutes = value.get("overrideOnTimer")
        if (
            isinstance(minutes, int)
            and not isinstance(minutes, bool)
            and 1 <= minutes <= 1440
        ):
            sanitized["overrideOnTimer"] = minutes

    return sanitized


def sanitize_rfid_device_data(value: Any) -> dict[str, Any]:
    """Retain only fields required from one RFID detail response."""
    if not isinstance(value, dict):
        return {}

    sanitized: dict[str, Any] = {}
    identifier = value.get("id")
    if isinstance(identifier, int) and not isinstance(identifier, bool):
        sanitized["id"] = identifier
    else:
        text_id = _bounded_device_text(identifier)
        if text_id is not None:
            sanitized["id"] = text_id

    state = value.get("state")
    if isinstance(state, bool):
        sanitized["state"] = state

    online = value.get("onlineStatus")
    if isinstance(online, bool):
        sanitized["onlineStatus"] = online

    for field in ("name", "displayName", "version"):
        text = _bounded_device_text(value.get(field))
        if text is not None:
            sanitized[field] = text

    return sanitized


def sanitize_collector_device_data(value: Any) -> dict[str, Any]:
    """Retain only strict fields required from one collector detail response."""
    if not isinstance(value, dict):
        return {}

    sanitized: dict[str, Any] = {}
    identifier = value.get("id")
    if isinstance(identifier, int) and not isinstance(identifier, bool):
        sanitized["id"] = identifier
    else:
        text_id = _bounded_device_text(identifier)
        if text_id is not None:
            sanitized["id"] = text_id

    for field in (
        "state",
        "stateChanging",
        "stateChangingTo",
        "onlineStatus",
        "isOnline",
    ):
        field_value = value.get(field)
        if isinstance(field_value, bool):
            sanitized[field] = field_value

    for field in ("name", "displayName", "version"):
        text = _bounded_device_text(value.get(field))
        if text is not None:
            sanitized[field] = text

    return sanitized


def normalise_list(data: Any) -> list[dict[str, Any]]:
    """Convert common API list shapes into a list of dictionaries."""
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("items", "data", "results", "devices", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def obj_id(obj: dict[str, Any]) -> str | int | None:
    for key in ("id", "deviceId", "deviceID", "_id", "uuid", "key"):
        if obj.get(key) not in (None, ""):
            return obj[key]
    return None


def obj_name(obj: dict[str, Any], fallback: str) -> str:
    for key in ("name", "displayName", "label", "description", "serialNumber", "deviceName"):
        if obj.get(key):
            return str(obj[key])
    ident = obj_id(obj)
    return f"{fallback} {ident}" if ident is not None else fallback


_BOOL_STATE_KEYS = (
    "on",
    "onOff",
    "enabled",
    "active",
    "open",
    "locked",
    "state",
    "status",
    "isOn",
)
_BOOL_STATE_TRUE = frozenset(
    {"on", "open", "enabled", "active", "true", "1", "unlocked", "online"}
)
_BOOL_STATE_FALSE = frozenset(
    {"off", "closed", "disabled", "inactive", "false", "0", "locked", "offline"}
)


def _coerce_bool_state_value(value: Any, *, allow_nested: bool) -> bool | None:
    """Coerce one Hub state value; nested dicts are expanded at most once."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _BOOL_STATE_TRUE:
            return True
        if lowered in _BOOL_STATE_FALSE:
            return False
        return None
    if allow_nested and isinstance(value, dict):
        return bool_state(value, _allow_nested=False)
    return None


def bool_state(obj: dict[str, Any], *, _allow_nested: bool = True) -> bool | None:
    """Return a strict boolean from Hub device state shapes.

    Precedence (first present key wins):
    ``on``, ``onOff``, ``enabled``, ``active``, ``open``, ``locked``,
    ``state``, ``status``, ``isOn``.

    Accepted value shapes for each key:
    - ``bool`` — returned as-is
    - ``int`` / ``float`` — ``bool(value)`` (``0``/``0.0`` → False)
    - ``str`` — case-insensitive vocabulary shared by dict and string forms
      (``on``/``off``, ``true``/``false``, ``1``/``0``, and related aliases)
    - ``dict`` — one nested pass with the same key precedence (so
      ``{"state": {"on": true}}`` matches ``{"on": true}`` / ``{"state": "on"}``)

    Unknown keys or unrecognized shapes return ``None``.
    """
    if not isinstance(obj, dict):
        return None
    for key in _BOOL_STATE_KEYS:
        if key not in obj:
            continue
        coerced = _coerce_bool_state_value(
            obj[key],
            allow_nested=_allow_nested,
        )
        if coerced is not None:
            return coerced
    return None
