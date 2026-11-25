"""Network-free tests for Hub software-version parsing and verification."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = REPOSITORY_ROOT / "custom_components" / "grit_hub"


def _load_hub():
    package_name = "_grit_hub_version_tests"
    package = types.ModuleType(package_name)
    package.__path__ = [str(COMPONENT_ROOT)]
    stubs = {package_name: package}
    loaded = {}
    with mock.patch.dict(sys.modules, stubs):
        for module_name in ("const", "hub"):
            spec = importlib.util.spec_from_file_location(
                f"{package_name}.{module_name}",
                COMPONENT_ROOT / f"{module_name}.py",
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            loaded[module_name] = module
    sys.modules.update(
        {f"{package_name}.{name}": module for name, module in loaded.items()}
    )
    return loaded["hub"]


HUB = _load_hub()


class HubVersionTests(unittest.TestCase):
    def test_verified_version_and_below(self):
        self.assertTrue(
            HUB.hub_version_is_verified({"softwareVersion": "1.1.1197"})
        )
        self.assertTrue(
            HUB.hub_version_is_verified({"hubVersion": "1.2.0"})
        )
        self.assertFalse(
            HUB.hub_version_is_verified({"softwareVersion": "1.1.1196"})
        )
        self.assertFalse(
            HUB.hub_version_is_verified({"softwareVersion": "not-a-version"})
        )
        self.assertFalse(HUB.hub_version_is_verified({}))
        self.assertFalse(HUB.hub_version_is_verified(None))

    def test_sanitize_prefers_software_version(self):
        sanitized = HUB.sanitize_hub_data(
            {
                "id": "0123456789abcdef0123456789abcdef",
                "softwareVersion": "1.1.1197",
            }
        )
        self.assertEqual(sanitized["softwareVersion"], "1.1.1197")
        self.assertEqual(sanitized["hubVersion"], "1.1.1197")


if __name__ == "__main__":
    unittest.main()
