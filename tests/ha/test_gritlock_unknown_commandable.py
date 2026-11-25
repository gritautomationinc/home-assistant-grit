"""GRITLock remains commandable while unknown (CI-only).

This module must be import-safe for `python3 -m unittest discover -s tests`.
The real test content activates only when GRIT_HUB_HA_SMOKE=1 is set.
"""

from __future__ import annotations

import os


if os.environ.get("GRIT_HUB_HA_SMOKE") == "1":
    from aiohttp import web
    import pytest
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from unittest.mock import patch

    from homeassistant.helpers import entity_registry as er

    from custom_components.grit_hub.const import (
        CONF_BASE_URL,
        CONF_MQTT_HOST,
        CONF_MQTT_HUB_ID,
        CONF_MQTT_PASSWORD,
        CONF_MQTT_PORT,
        CONF_MQTT_USERNAME,
        CONF_TOKEN,
        CONF_VERIFY_SSL,
        DEFAULT_MQTT_PORT,
        DEVICE_TYPES,
        DOMAIN,
    )

    _HUB_ID = "0123456789abcdef0123456789abcdef"


    @pytest.fixture(name="hub_server")
    async def hub_server_fixture(aiohttp_server):
        received: list[dict] = []

        async def _health_check(_request: web.Request) -> web.Response:
            return web.json_response({"ok": True})

        async def _hub(_request: web.Request) -> web.Response:
            return web.json_response(
                {
                    "id": _HUB_ID,
                    "displayName": "Test Hub",
                    "hubVersion": "1.1.1197",
                }
            )

        async def _trigger_collection(_request: web.Request) -> web.Response:
            return web.json_response(
                [
                    {
                        "id": "trigger-one",
                        "displayName": "Trigger One",
                        "gritLockEnabled": True,
                    }
                ]
            )

        async def _empty_collection(_request: web.Request) -> web.Response:
            return web.json_response([])

        async def _lockout(request: web.Request) -> web.Response:
            received.append(await request.json())
            return web.json_response({"ok": True})

        app = web.Application()
        app["received_lockout"] = received
        app.router.add_get("/health-check", _health_check)
        app.router.add_get("/api/hub", _hub)
        app.router.add_get("/api/trigger", _trigger_collection)
        for device_type in DEVICE_TYPES:
            if device_type == "trigger":
                continue
            app.router.add_get(f"/api/{device_type}", _empty_collection)
        app.router.add_put("/api/hub/lockout", _lockout)
        return await aiohttp_server(app)


    def _mqtt_start_disconnected(self) -> bool:  # noqa: ANN001
        return True


    def _mqtt_stop_smoke(self) -> None:  # noqa: ANN001
        if getattr(self, "_connection_state_callback", None) is not None:
            self._connection_state_callback(False)


    @pytest.mark.asyncio
    async def test_gritlock_lock_service_calls_hub_while_unknown(hass, hub_server):
        base_url = str(hub_server.make_url("")).rstrip("/")
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_BASE_URL: base_url,
                CONF_TOKEN: "test-token",
                CONF_VERIFY_SSL: True,
                CONF_MQTT_HOST: "mqtt.example",
                CONF_MQTT_PORT: DEFAULT_MQTT_PORT,
                CONF_MQTT_HUB_ID: _HUB_ID,
                CONF_MQTT_USERNAME: "user",
                CONF_MQTT_PASSWORD: "pass",
            },
        )
        entry.add_to_hass(hass)

        with patch(
            "custom_components.grit_hub.mqtt_live.MqttLiveClient.start",
            new=_mqtt_start_disconnected,
        ), patch(
            "custom_components.grit_hub.mqtt_live.MqttLiveClient.stop",
            new=_mqtt_stop_smoke,
        ):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        registry = er.async_get(hass)
        entity_entry = registry.async_get_entity_id(
            "lock",
            DOMAIN,
            "grit_hub_system_gritlock",
        )
        assert entity_entry is not None
        await hass.services.async_call(
            "lock",
            "lock",
            {"entity_id": entity_entry},
            blocking=True,
        )

        received = hub_server.app["received_lockout"]
        assert received == [{"state": True}]

