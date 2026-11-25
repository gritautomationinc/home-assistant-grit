"""Sanitized hub data and system-wide GRITLock state helpers."""
from __future__ import annotations

from ipaddress import ip_address
import re
from typing import Any

from .const import VERIFIED_HUB_VERSION

_HUB_ID_PATTERN = re.compile(r"^[0-9A-Fa-f]{32}$")
_VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_MAX_HUB_TEXT_LENGTH = 128


def normalize_hub_id(value: Any) -> str | None:
    """Return a documented 32-character hexadecimal hub identifier."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if _HUB_ID_PATTERN.fullmatch(value) else None


def normalize_ethernet_ip(value: Any) -> str | None:
    """Return a canonical IP address without accepting hostnames."""
    if not isinstance(value, str):
        return None
    try:
        return str(ip_address(value.strip()))
    except ValueError:
        return None


def _bounded_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if (
        not value
        or len(value) > _MAX_HUB_TEXT_LENGTH
        or not value.isprintable()
    ):
        return None
    return value


def sanitize_hub_data(value: Any) -> dict[str, Any] | None:
    """Retain only the documented v0.1.0 hub fields."""
    if not isinstance(value, dict):
        return None

    sanitized: dict[str, Any] = {}
    hub_id = normalize_hub_id(value.get("id"))
    if hub_id is not None:
        sanitized["id"] = hub_id

    for field in ("displayName", "name", "hubVersion", "branch"):
        text = _bounded_text(value.get(field))
        if text is not None:
            sanitized[field] = text

    software_version = _bounded_text(value.get("softwareVersion"))
    if software_version is not None:
        sanitized["softwareVersion"] = software_version
        # Prefer the Hub's softwareVersion for display when hubVersion is absent.
        sanitized.setdefault("hubVersion", software_version)

    ethernet_ip = normalize_ethernet_ip(value.get("ipAddressEthernet"))
    if ethernet_ip is not None:
        sanitized["ipAddressEthernet"] = ethernet_ip

    for field in ("connectedToInternet", "disableHubButtons"):
        field_value = value.get(field)
        if isinstance(field_value, bool):
            sanitized[field] = field_value

    brightness = value.get("systemLedBrightness")
    if (
        not isinstance(brightness, bool)
        and isinstance(brightness, int)
        and 0 <= brightness <= 100
    ):
        sanitized["systemLedBrightness"] = brightness

    if "automaticGritLockTime" in value:
        lock_time = value.get("automaticGritLockTime")
        if lock_time is None:
            sanitized["automaticGritLockTime"] = None
        else:
            text = _bounded_text(lock_time)
            if text is not None:
                sanitized["automaticGritLockTime"] = text

    return sanitized


def parse_hub_software_version(value: Any) -> tuple[int, int, int] | None:
    """Parse a Hub software version string into a comparable triple."""
    if not isinstance(value, str):
        return None
    match = _VERSION_PATTERN.search(value.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def hub_version_is_verified(hub_data: dict[str, Any] | None) -> bool:
    """Return True when Hub software version is at least the verified release."""
    if not isinstance(hub_data, dict):
        return False
    raw = hub_data.get("softwareVersion")
    if raw is None:
        raw = hub_data.get("hubVersion")
    parsed = parse_hub_software_version(raw)
    if parsed is None:
        return False
    return parsed >= VERIFIED_HUB_VERSION


def hub_version_label(hub_data: dict[str, Any] | None) -> str | None:
    """Return a bounded display label for the Hub software version."""
    if not isinstance(hub_data, dict):
        return None
    raw = hub_data.get("softwareVersion")
    if raw is None:
        raw = hub_data.get("hubVersion")
    return raw if isinstance(raw, str) else None
