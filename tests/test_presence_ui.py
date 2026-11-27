"""Network-free contract checks for the Presence card's Hub write paths."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

from tests.test_api_discovery import API


ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "grit_hub"
PACKAGE = "_grit_presence_ui_tests"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
http = types.ModuleType("homeassistant.components.http")
http.HomeAssistantView = type("HomeAssistantView", (), {})
http.StaticPathConfig = lambda *args: args
web = types.ModuleType("aiohttp.web")
web.Request = object
web.Response = object
web.json_response = lambda body, status=200: (status, body)
aiohttp = types.ModuleType("aiohttp")
aiohttp.web = web
homeassistant = types.ModuleType("homeassistant")
components = types.ModuleType("homeassistant.components")
components.http = http
homeassistant.components = components
const = types.ModuleType(f"{PACKAGE}.const")
const.DOMAIN = "grit_hub"
coordinator_module = types.ModuleType(f"{PACKAGE}.coordinator")
coordinator_module.MQTT_STATE_KEY = "_grit_mqtt"
with mock.patch.dict(sys.modules, {
    PACKAGE: package,
    f"{PACKAGE}.api": API,
    f"{PACKAGE}.const": const,
    f"{PACKAGE}.coordinator": coordinator_module,
    "aiohttp": aiohttp,
    "aiohttp.web": web,
    "homeassistant": homeassistant,
    "homeassistant.components": components,
    "homeassistant.components.http": http,
}):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.presence_ui", ROOT / "presence_ui.py")
    PRESENCE_UI = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(PRESENCE_UI)


class FakeApi:
    def __init__(self):
        self.calls = []

    async def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        if path == "/api/update/status":
            return {"presence": {"count": 2, "updateIsRunning": False}}
        return {"ok": True}


class FakeRequest(dict):
    def __init__(self, hass, *, admin=False, body=None):
        super().__init__(hass_user=types.SimpleNamespace(is_admin=admin))
        self.app = {"hass": hass}
        self.body = body

    async def json(self):
        return self.body


class PresenceUiTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi()
        self.coordinator = types.SimpleNamespace(
            data={"devices": {"presence": [{
                "id": "presence-test", "name": "Test Presence",
                "zones": [{"x1": -500, "y1": 0, "x2": 500, "y2": 1000}],
                "_grit_mqtt": {"occupied": True, "online": True},
            }]}},
            mqtt_connected=True,
            async_request_refresh=self._refresh,
        )
        self.runtime = types.SimpleNamespace(
            active=True, unloading=False, api=self.api,
            coordinator=self.coordinator, presence_frames={},
        )
        self.hass = types.SimpleNamespace(data={"grit_hub": {"entry-test": {
            "runtime": self.runtime, "coordinator": self.coordinator,
        }}})
        self.refreshes = 0

    async def _refresh(self):
        self.refreshes += 1

    def request(self, *, admin=False, body=None):
        return FakeRequest(self.hass, admin=admin, body=body)

    def test_read_only_snapshot_does_not_return_raw_device(self):
        status, body = asyncio.run(PRESENCE_UI.PresenceView().get(
            self.request(), "entry-test", "presence-test"))
        self.assertEqual(status, 200)
        self.assertTrue(body["occupied"])
        self.assertEqual(body["zones"][0]["x1"], -500)
        self.assertNotIn("_grit_mqtt", body)

    def test_zone_edit_requires_admin_and_uses_presence_route(self):
        zones = [{"x1": -500, "y1": 0, "x2": 500, "y2": 1000}]
        view = PRESENCE_UI.PresenceActionView()
        status, _ = asyncio.run(view.put(self.request(body={"zones": zones}), "entry-test", "presence-test", "zones"))
        self.assertEqual(status, 403)
        self.assertEqual(self.api.calls, [])
        status, _ = asyncio.run(view.put(self.request(admin=True, body={"zones": zones}), "entry-test", "presence-test", "zones"))
        self.assertEqual(status, 200)
        self.assertEqual(self.api.calls, [("PUT", "/api/presence/presence-test", {"json": {"zones": zones}})])
        self.assertEqual(self.refreshes, 1)

    def test_firmware_action_is_explicitly_fleet_wide(self):
        view = PRESENCE_UI.PresenceActionView()
        status, body = asyncio.run(view.get(self.request(), "entry-test", "presence-test", "updates"))
        self.assertEqual((status, body["count"]), (200, 2))
        status, _ = asyncio.run(view.post(self.request(admin=True), "entry-test", "presence-test", "install-update"))
        self.assertEqual(status, 200)
        self.assertEqual(self.api.calls[-1], ("POST", "/api/update/presence", {}))


if __name__ == "__main__":
    unittest.main()
