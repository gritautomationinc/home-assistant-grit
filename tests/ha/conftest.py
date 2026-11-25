"""Pytest-only Home Assistant smoke tests.

This directory is intentionally import-safe for the stdlib unittest runner.
The real tests only activate when GRIT_HUB_HA_SMOKE=1 is set (CI job only).
"""

from __future__ import annotations

import os

if os.environ.get("GRIT_HUB_HA_SMOKE") == "1":
    # Official HA test package (replaces broken pytest-homeassistant-custom-component
    # against Core 2026.11.1). Import Home Assistant first so httpx2 can alias
    # before any residual respx import paths.
    import homeassistant  # noqa: F401
