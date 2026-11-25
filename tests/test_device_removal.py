"""Network-free tests for manual stale-device removal (T11)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = REPOSITORY_ROOT / "custom_components" / "grit_hub"


class ConfigEntryError(Exception):
    pass


class ConfigEntryNotReady(Exception):
    pass


class HomeAssistantError(Exception):
    pass


class FakeDeviceEntry:
    def __init__(self, identifiers):
        self.identifiers = identifiers


class FakeCoordinator:
    def __init__(self, inventory):
        self.last_complete_inventory = inventory
        self.hub_data = {"hubVersion": "1.1.1197"}


class FakeRuntime:
    def __init__(self, coordinator):
        self.coordinator = coordinator


class FakeEntry:
    def __init__(self, runtime):
        self.runtime_data = runtime
        self.entry_id = "entry-fabricated"


class FakeHass:
    def __init__(self):
        self.data = {}


def _load_runtime():
    package_name = "_grit_device_removal_tests"
    voluptuous = types.ModuleType("voluptuous")
    voluptuous.Schema = lambda schema: schema
    voluptuous.Required = lambda key, **kwargs: key
    voluptuous.Optional = lambda key, **kwargs: key
    voluptuous.Any = lambda *args: object()

    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    exceptions = types.ModuleType("homeassistant.exceptions")
    helpers = types.ModuleType("homeassistant.helpers")
    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    issue_registry = types.ModuleType("homeassistant.helpers.issue_registry")

    class IssueSeverity:
        WARNING = "warning"

    issue_registry.IssueSeverity = IssueSeverity
    issue_registry.async_create_issue = lambda *a, **k: None
    issue_registry.async_delete_issue = lambda *a, **k: None
    device_registry.DeviceEntry = FakeDeviceEntry
    entity_registry.async_get = lambda hass: object()
    entity_registry.async_entries_for_config_entry = lambda *a, **k: []
    exceptions.ConfigEntryError = ConfigEntryError
    exceptions.ConfigEntryNotReady = ConfigEntryNotReady
    exceptions.HomeAssistantError = HomeAssistantError
    config_entries.ConfigEntry = object
    core.HomeAssistant = object
    core.ServiceCall = object
    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.exceptions = exceptions
    homeassistant.helpers = helpers
    helpers.entity_registry = entity_registry
    helpers.device_registry = device_registry
    helpers.issue_registry = issue_registry

    package = types.ModuleType(package_name)
    package.__path__ = [str(COMPONENT_ROOT)]
    stubs = {
        "voluptuous": voluptuous,
        "homeassistant": homeassistant,
        "homeassistant.config_entries": config_entries,
        "homeassistant.core": core,
        "homeassistant.exceptions": exceptions,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.entity_registry": entity_registry,
        "homeassistant.helpers.device_registry": device_registry,
        "homeassistant.helpers.issue_registry": issue_registry,
        package_name: package,
    }
    with mock.patch.dict(sys.modules, stubs):
        for name in ("const", "hub"):
            spec = importlib.util.spec_from_file_location(
                f"{package_name}.{name}", COMPONENT_ROOT / f"{name}.py"
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

        api = types.ModuleType(f"{package_name}.api")

        class GritHubApiClient:
            pass

        class GritHubApiError(Exception):
            pass

        api.GritHubApiClient = GritHubApiClient
        api.GritHubApiError = GritHubApiError
        sys.modules[api.__name__] = api

        coordinator = types.ModuleType(f"{package_name}.coordinator")
        coordinator.GritHubCoordinator = FakeCoordinator
        sys.modules[coordinator.__name__] = coordinator

        mqtt = types.ModuleType(f"{package_name}.mqtt_live")

        class GritLiveMqtt:
            pass

        mqtt.GritLiveMqtt = GritLiveMqtt
        sys.modules[mqtt.__name__] = mqtt

        spec = importlib.util.spec_from_file_location(
            package_name, COMPONENT_ROOT / "__init__.py"
        )
        runtime = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = runtime
        spec.loader.exec_module(runtime)
        return runtime


RUNTIME = _load_runtime()


class DeviceRemovalTests(unittest.IsolatedAsyncioTestCase):
    async def test_present_device_cannot_be_removed(self):
        coordinator = FakeCoordinator(frozenset({("gate", "gate-1")}))
        entry = FakeEntry(FakeRuntime(coordinator))
        device = FakeDeviceEntry(
            {("grit_hub", "gate", "gate-1")}
        )
        allowed = await RUNTIME.async_remove_config_entry_device(
            FakeHass(), entry, device
        )
        self.assertFalse(allowed)

    async def test_absent_device_can_be_removed(self):
        coordinator = FakeCoordinator(frozenset({("gate", "gate-1")}))
        entry = FakeEntry(FakeRuntime(coordinator))
        device = FakeDeviceEntry(
            {("grit_hub", "gate", "gate-old")}
        )
        allowed = await RUNTIME.async_remove_config_entry_device(
            FakeHass(), entry, device
        )
        self.assertTrue(allowed)

    async def test_unknown_inventory_blocks_removal(self):
        coordinator = FakeCoordinator(None)
        entry = FakeEntry(FakeRuntime(coordinator))
        device = FakeDeviceEntry(
            {("grit_hub", "gate", "gate-old")}
        )
        allowed = await RUNTIME.async_remove_config_entry_device(
            FakeHass(), entry, device
        )
        self.assertFalse(allowed)

    async def test_hub_device_cannot_be_removed(self):
        coordinator = FakeCoordinator(frozenset())
        entry = FakeEntry(FakeRuntime(coordinator))
        device = FakeDeviceEntry({("grit_hub", "hub")})
        allowed = await RUNTIME.async_remove_config_entry_device(
            FakeHass(), entry, device
        )
        self.assertFalse(allowed)


if __name__ == "__main__":
    unittest.main()
