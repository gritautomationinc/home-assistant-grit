"""Authenticated Home Assistant API for the GRIT Presence dashboard card."""
from __future__ import annotations

from pathlib import Path
import time
from typing import Any
from urllib.parse import quote

from aiohttp import web
from homeassistant.components.http import HomeAssistantView, StaticPathConfig

from .api import GritHubApiError, sanitize_device_data
from .const import DOMAIN
from .coordinator import MQTT_STATE_KEY


CARD_URL = "/grit-presence/presence-card.js"
_REGISTRATION_KEY = "grit_hub_presence_ui_registered"


def _response_error(message: str, status: int) -> web.Response:
    return web.json_response({"error": message}, status=status)


def _get_presence(request: web.Request, entry_id: str, device_id: str):
    stored = request.app["hass"].data.get(DOMAIN, {}).get(entry_id)
    if not isinstance(stored, dict):
        return None
    runtime = stored.get("runtime")
    if runtime is None or not runtime.active or runtime.unloading:
        return None
    devices = stored["coordinator"].data.get("devices", {}).get("presence", [])
    matches = [
        device for device in devices
        if isinstance(device, dict) and str(device.get("id")) == device_id
    ]
    if len(matches) != 1:
        return None
    return runtime, matches[0]


def _require_admin(request: web.Request) -> web.Response | None:
    user = request.get("hass_user")
    if user is None or not user.is_admin:
        return _response_error("Home Assistant administrator access is required", 403)
    return None


class PresenceView(HomeAssistantView):
    """Read a known Presence sensor and its transient radar frame."""

    url = "/api/grit_hub/presence/{entry_id}/{device_id}"
    name = "api:grit_hub:presence"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, device_id: str) -> web.Response:
        found = _get_presence(request, entry_id, device_id)
        if found is None:
            return _response_error("Presence sensor not found", 404)
        runtime, device = found
        state = device.get(MQTT_STATE_KEY, {})
        if not isinstance(state, dict):
            state = {}
        frame = runtime.presence_frames.get(device_id, {})
        targets = frame.get("targets", []) if time.monotonic() - frame.get("target_at", 0) < 2 else []
        occupied = state.get("occupied")
        online = state.get("online") if runtime.coordinator.mqtt_connected else False
        if online is not True:
            targets = []
        return web.json_response({
            "name": device.get("displayName") or device.get("name") or f"Presence {device_id}",
            "online": online if isinstance(online, bool) else None,
            "occupied": occupied if isinstance(occupied, bool) and online is not False else None,
            "zones": device.get("zones", []),
            "presenceBehavior": device.get("presenceBehavior"),
            "triggerOnDebounceMs": device.get("triggerOnDebounceMs"),
            "triggerOffDebounceMs": device.get("triggerOffDebounceMs"),
            "sensorMask": device.get("sensorMask"),
            "version": device.get("version"),
            "targets": targets,
            "zoneOccupied": frame.get("zones", {}) if occupied is True and online is not False else {},
        })


class PresenceActionView(HomeAssistantView):
    """Use only the Hub's documented Presence and firmware routes."""

    url = "/api/grit_hub/presence/{entry_id}/{device_id}/{action}"
    name = "api:grit_hub:presence:action"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, device_id: str, action: str) -> web.Response:
        found = _get_presence(request, entry_id, device_id)
        if found is None or action != "updates":
            return _response_error("Presence action not found", 404)
        runtime, _ = found
        try:
            response = await runtime.api.request("GET", "/api/update/status")
        except GritHubApiError as err:
            return _response_error(str(err), err.http_status or 502)
        status = response.get("presence", {}) if isinstance(response, dict) else {}
        if not isinstance(status, dict):
            status = {}
        count = status.get("count")
        progress = status.get("percentComplete")
        return web.json_response({
            "count": count if type(count) is int and 0 <= count <= 10_000 else 0,
            "running": status.get("updateIsRunning") is True,
            "percentComplete": progress if type(progress) in (int, float) and 0 <= progress <= 100 else None,
        })

    async def put(self, request: web.Request, entry_id: str, device_id: str, action: str) -> web.Response:
        found = _get_presence(request, entry_id, device_id)
        if found is None or action not in {"zones", "settings"}:
            return _response_error("Presence action not found", 404)
        if (denied := _require_admin(request)) is not None:
            return denied
        try:
            body = await request.json()
        except (ValueError, TypeError):
            return _response_error("Invalid JSON body", 400)
        if not isinstance(body, dict):
            return _response_error("Expected a settings object", 400)
        if action == "zones":
            if set(body) != {"zones"}:
                return _response_error("Expected zones only", 400)
            payload = sanitize_device_data(body, device_type="presence")
            if "zones" not in payload:
                return _response_error("Invalid radar zones", 400)
            payload = {"zones": payload["zones"]}
        else:
            allowed = {"presenceBehavior", "triggerOnDebounceMs", "triggerOffDebounceMs"}
            if not body or not set(body) <= allowed:
                return _response_error("Invalid Presence settings", 400)
            sanitized = sanitize_device_data(body, device_type="presence")
            if set(sanitized) != set(body):
                return _response_error("Invalid Presence settings", 400)
            payload = sanitized
        runtime, _ = found
        try:
            await runtime.api.request("PUT", f"/api/presence/{quote(device_id, safe='')}", json=payload)
            await runtime.coordinator.async_request_refresh()
        except GritHubApiError as err:
            return _response_error(str(err), err.http_status or 502)
        return web.json_response({"ok": True})

    async def post(self, request: web.Request, entry_id: str, device_id: str, action: str) -> web.Response:
        found = _get_presence(request, entry_id, device_id)
        if found is None or action not in {"radar-stream", "install-update"}:
            return _response_error("Presence action not found", 404)
        if (denied := _require_admin(request)) is not None:
            return denied
        runtime, _ = found
        try:
            if action == "radar-stream":
                body = await request.json()
                if not isinstance(body, dict) or type(body.get("active")) is not bool:
                    return _response_error("Expected active boolean", 400)
                await runtime.api.request(
                    "POST", f"/api/presence/{quote(device_id, safe='')}/radar-stream",
                    json={"active": body["active"]},
                )
            else:
                await runtime.api.request("POST", "/api/update/presence")
        except (ValueError, TypeError):
            return _response_error("Invalid JSON body", 400)
        except GritHubApiError as err:
            return _response_error(str(err), err.http_status or 502)
        return web.json_response({"ok": True})


async def async_register_presence_ui(hass) -> None:
    """Serve the bundled card and its authenticated endpoints once per HA instance."""
    if hass.data.get(_REGISTRATION_KEY):
        return
    await hass.http.async_register_static_paths([
        StaticPathConfig(CARD_URL, str(Path(__file__).parent / "frontend" / "presence-card.js"), False)
    ])
    hass.http.register_view(PresenceView())
    hass.http.register_view(PresenceActionView())
    hass.data[_REGISTRATION_KEY] = True
