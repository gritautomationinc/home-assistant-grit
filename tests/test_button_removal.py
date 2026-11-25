"""Tests for v0.2.0 removal of Restart/Reboot buttons (F11 / T10)."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from tests import test_runtime_mqtt as runtime_tests


COMPONENT_ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "grit_hub"
RUNTIME_MODULE = runtime_tests.RUNTIME_MODULE


class ButtonRemovalTests(unittest.TestCase):
    def test_removed_unique_ids_are_exact(self) -> None:
        self.assertEqual(
            RUNTIME_MODULE._REMOVED_BUTTON_UNIQUE_IDS,
            frozenset({"grit_hub_restart_service", "grit_hub_reboot"}),
        )

    def test_remove_retired_button_entities_deletes_only_retired_ids(self) -> None:
        removed: list[str] = []
        keep = SimpleNamespace(
            entity_id="button.keep",
            unique_id="grit_hub_refresh_all",
        )
        restart = SimpleNamespace(
            entity_id="button.restart",
            unique_id="grit_hub_restart_service",
        )
        reboot = SimpleNamespace(
            entity_id="button.reboot",
            unique_id="grit_hub_reboot",
        )
        registry = mock.Mock()
        registry.async_remove.side_effect = removed.append

        with (
            mock.patch.object(
                RUNTIME_MODULE.er,
                "async_get",
                return_value=registry,
            ),
            mock.patch.object(
                RUNTIME_MODULE.er,
                "async_entries_for_config_entry",
                return_value=[keep, restart, reboot],
            ),
        ):
            RUNTIME_MODULE._remove_retired_button_entities(
                object(),
                SimpleNamespace(entry_id="entry"),
            )

        self.assertEqual(
            sorted(removed),
            ["button.reboot", "button.restart"],
        )

    def test_source_no_longer_exposes_restart_or_reboot_api(self) -> None:
        button_source = (COMPONENT_ROOT / "button.py").read_text(encoding="utf-8")
        api_source = (COMPONENT_ROOT / "api.py").read_text(encoding="utf-8")
        self.assertNotIn("grit_hub_restart_service", button_source)
        self.assertNotIn("grit_hub_reboot", button_source)
        self.assertNotIn("async def restart_service", api_source)
        self.assertNotIn("async def reboot_hub", api_source)
        entities = (
            Path(__file__).resolve().parents[1] / "docs" / "ENTITIES.md"
        ).read_text(encoding="utf-8")
        self.assertIn("were removed in v0.2.0", entities)
        self.assertNotIn(
            "| Restart GRIT Service |",
            entities,
        )
        self.assertNotIn("| Reboot Hub |", entities)


if __name__ == "__main__":
    unittest.main()
