"""Minimal Home Assistant smoke test (CI-only).

This module must be import-safe for `python3 -m unittest discover -s tests`.
The real test content activates only when GRIT_HUB_HA_SMOKE=1 is set.
"""

from __future__ import annotations

import os


if os.environ.get("GRIT_HUB_HA_SMOKE") == "1":
    from aiohttp import web
    import pytest
    from pytest_homeassistant.common import MockConfigEntry
    from unittest.mock import patch

    from homeassistant.config_entries import ConfigEntryState

    from custom_components.grit_hub.const import (
        CONF_BASE_URL,
        CONF_MQTT_HOST,
        CONF_MQTT_HUB_ID,
        CONF_MQTT_KEEPALIVE,
        CONF_MQTT_PASSWORD,
        CONF_MQTT_PORT,
        CONF_MQTT_USE_TLS,
        CONF_MQTT_USERNAME,
        CONF_MQTT_VERIFY_TLS,
        CONF_TOKEN,
        CONF_VERIFY_SSL,
        DEFAULT_MQTT_KEEPALIVE,
        DEFAULT_MQTT_PORT,
        DEVICE_TYPES,
        DOMAIN,
    )

    _HUB_ID = "0123456789abcdef0123456789abcdef"


    @pytest.fixture(name="hub_server")
    async def hub_server_fixture(aiohttp_server, socket_enabled):
        """Fake Hub API server for first refresh."""

        async def _health_check(_request: web.Request) -> web.Response:
            return web.json_response({"ok": True})

        async def _hub(_request: web.Request) -> web.Response:
            # Minimal fields required by `sanitize_hub_data`.
            return web.json_response(
                {
                    "id": _HUB_ID,
                    "displayName": "Test Hub",
                    "hubVersion": "1.1.1197",
                }
            )

        async def _empty_collection(_request: web.Request) -> web.Response:
            return web.json_response([])

        app = web.Application()
        app.router.add_get("/health-check", _health_check)
        app.router.add_get("/api/hub", _hub)
        for device_type in DEVICE_TYPES:
            app.router.add_get(f"/api/{device_type}", _empty_collection)
        return await aiohttp_server(app)


    def _mqtt_start_smoke(self) -> bool:  # noqa: ANN001
        """Pretend the MQTT client connected, without importing paho-mqtt."""
        if getattr(self, "_connection_state_callback", None) is not None:
            self._connection_state_callback(True)
        return True


    def _mqtt_stop_smoke(self) -> None:  # noqa: ANN001
        if getattr(self, "_connection_state_callback", None) is not None:
            self._connection_state_callback(False)


    @pytest.mark.asyncio
    async def test_setup_entry_smoke(hass, hub_server):
        base_url = str(hub_server.make_url("")).rstrip("/")

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="GRIT Hub",
            data={
                CONF_BASE_URL: base_url,
                CONF_TOKEN: "test-token",
                CONF_VERIFY_SSL: False,
                CONF_MQTT_HOST: "mqtt.invalid",
                CONF_MQTT_PORT: DEFAULT_MQTT_PORT,
                CONF_MQTT_HUB_ID: _HUB_ID,
                CONF_MQTT_USERNAME: "smoke-user",
                CONF_MQTT_PASSWORD: "smoke-pass",
                CONF_MQTT_KEEPALIVE: DEFAULT_MQTT_KEEPALIVE,
                CONF_MQTT_USE_TLS: False,
                CONF_MQTT_VERIFY_TLS: True,
            },
        )
        entry.add_to_hass(hass)

        with (
            patch(
                "custom_components.grit_hub.mqtt_live.GritLiveMqtt.start",
                _mqtt_start_smoke,
            ),
            patch(
                "custom_components.grit_hub.mqtt_live.GritLiveMqtt.stop",
                _mqtt_stop_smoke,
            ),
        ):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED

            assert await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()

