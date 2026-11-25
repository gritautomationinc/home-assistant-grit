from __future__ import annotations

import json
import pathlib
import re
import unittest


_FIXTURES_DIR = (
    pathlib.Path(__file__).resolve().parent / "fixtures" / "hub_v1_1_1197"
)


class TestHubV1_1_1197ContractFixtures(unittest.TestCase):
    def test_fixtures_directory_exists(self) -> None:
        self.assertTrue(_FIXTURES_DIR.exists(), f"Missing {_FIXTURES_DIR}")

    def test_each_fixture_is_valid_json_with_source_citation(self) -> None:
        fixture_paths = sorted(_FIXTURES_DIR.glob("*.json"))
        self.assertGreater(len(fixture_paths), 0, "No fixtures found")

        for path in fixture_paths:
            with self.subTest(path=path.name):
                raw = path.read_text(encoding="utf-8")
                data = json.loads(raw)
                self.assertIsInstance(data, dict)

                meta = data.get("__meta__")
                self.assertIsInstance(meta, dict, "Missing __meta__ object")

                hub_ref = meta.get("hub_ref")
                self.assertEqual(hub_ref, "danowitz/GRIT-hub@v1.1.1197")

                source = meta.get("source")
                self.assertIsInstance(source, str, "Missing __meta__.source")
                self.assertRegex(
                    source,
                    re.compile(r"^[^:]+:[0-9]+-[0-9]+$"),
                    "Expected __meta__.source in the form path/to/file:lineStart-lineEnd",
                )
