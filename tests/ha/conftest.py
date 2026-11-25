"""Pytest-only Home Assistant smoke tests.

This directory is intentionally import-safe for the stdlib unittest runner.
The real tests only activate when GRIT_HUB_HA_SMOKE=1 is set (CI job only).
"""

from __future__ import annotations

import os

if os.environ.get("GRIT_HUB_HA_SMOKE") == "1":
    # Provide the Home Assistant test fixtures when the smoke suite is enabled.
    pytest_plugins = ("pytest_homeassistant_custom_component.plugins",)

