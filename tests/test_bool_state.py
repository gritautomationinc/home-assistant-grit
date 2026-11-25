"""Network-free tests for api.bool_state precedence and Hub shape parity."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = REPOSITORY_ROOT / "custom_components" / "grit_hub"
FIXTURE_PATH = (
    REPOSITORY_ROOT / "tests" / "fixtures" / "bool_state_shapes.json"
)


def _load_api():
    package_name = "_grit_bool_state_tests"
    package = types.ModuleType(package_name)
    package.__path__ = [str(COMPONENT_ROOT)]

    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientTimeout = lambda **kwargs: kwargs
    aiohttp.ClientError = OSError
    homeassistant = types.ModuleType("homeassistant")
    helpers = types.ModuleType("homeassistant.helpers")
    aiohttp_client = types.ModuleType(
        "homeassistant.helpers.aiohttp_client"
    )
    aiohttp_client.async_get_clientsession = lambda *_args, **_kwargs: object()
    helpers.aiohttp_client = aiohttp_client
    homeassistant.helpers = helpers
    stubs = {
        package_name: package,
        "aiohttp": aiohttp,
        "homeassistant": homeassistant,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.aiohttp_client": aiohttp_client,
    }
    loaded = {}
    with mock.patch.dict(sys.modules, stubs):
        for module_name in ("const", "hub", "api"):
            spec = importlib.util.spec_from_file_location(
                f"{package_name}.{module_name}",
                COMPONENT_ROOT / f"{module_name}.py",
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            loaded[spec.name] = module
    sys.modules.update(loaded)
    return loaded[f"{package_name}.api"]


API = _load_api()


class BoolStateTests(unittest.TestCase):
    def test_fixture_shapes_agree_on_expected_result(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        for case in payload["cases"]:
            with self.subTest(case=case["id"]):
                for shape in case["shapes"]:
                    self.assertEqual(
                        API.bool_state(shape),
                        case["expected"],
                        msg=repr(shape),
                    )

    def test_dict_and_string_shapes_are_equivalent(self):
        pairs = (
            ({"state": True}, {"state": "true"}),
            ({"state": False}, {"state": "false"}),
            ({"on": True}, {"state": {"on": "on"}}),
            ({"on": False}, {"state": {"on": "off"}}),
            ({"enabled": True}, {"enabled": "enabled"}),
            ({"status": "online"}, {"status": True}),
        )
        for left, right in pairs:
            with self.subTest(left=left, right=right):
                self.assertEqual(API.bool_state(left), API.bool_state(right))
                self.assertIsNotNone(API.bool_state(left))

    def test_unknown_shapes_return_none(self):
        for shape in (
            "on",
            ["on"],
            None,
            {"state": object()},
            {"state": {"nested": {"on": True}}},
        ):
            with self.subTest(shape=repr(shape)):
                self.assertIsNone(API.bool_state(shape))


if __name__ == "__main__":
    unittest.main()
