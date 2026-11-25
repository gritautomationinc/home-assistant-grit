<p align="center">
  <img src="docs/assets/grit-home-assistant-icon.png" alt="GRIT Hub for Home Assistant integration artwork" width="112">
</p>

<h1 align="center">GRIT Hub for Home Assistant</h1>

Bring GRIT Hub gates, RFiD readers, GRITLock, and connected equipment into Home Assistant.

**[Install with HACS](#install-with-hacs) · [Supported entities](#what-you-get) · [Compatibility](docs/COMPATIBILITY.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)**

`v0.2.0` is the current release ([release notes](https://github.com/gritautomationinc/home-assistant-grit/releases/tag/v0.2.0)). This project remains a HACS Custom Repository; it is not listed in the default HACS catalogue.

## Install with HACS

Before you start, have Home Assistant `2026.3.0` or newer, your GRIT API URL and token, and access to the Hub's MQTT broker.

1. In HACS, open **Custom repositories**.
2. Add `https://github.com/gritautomationinc/home-assistant-grit` as an **Integration**.
3. Install **GRIT Hub** and restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and select **GRIT Hub**.
5. Enter your GRIT API URL, raw bearer token, and the Hub's per-hub read-only MQTT credentials when prompted.

See the [installation guide](docs/INSTALLATION.md) for manual installation, configuration, verification, and removal.

## What you get

| Equipment or function | Home Assistant entities |
| --- | --- |
| Gates | Covers with position and open/closed state |
| RFiD readers | Individual lock entities |
| GRITLock | One system-wide lock entity |
| Collectors, solenoids, latches, powerbanks | Switches |
| GRIT Hub | LED brightness, refresh and locate controls, connectivity and device diagnostics |

The [entity reference](docs/ENTITIES.md) lists the full set and explains where each state comes from. Some controls can operate physical equipment; check the target and site conditions before using them.

## Compatibility and behavior

The current release was verified with GRIT Hub `v1.1.1197` and Home Assistant `2026.11.1`; the declared minimum Home Assistant version is `2026.3.0`. See [Compatibility](docs/COMPATIBILITY.md) for the tested scope.

The integration requires both REST and direct MQTT; HACS does not install a broker, and the Home Assistant MQTT integration is not required. REST provides authenticated discovery, reconciliation, and commands. MQTT supplies live device observations; the integration never publishes to MQTT. Gate and GRITLock command confirmation depends on fresh device state. See [Architecture](docs/ARCHITECTURE.md) for the state and confirmation rules, and [Known limitations](#known-limitations) before relying on a particular entity.

<details>
<summary>Startup state and command confirmation</summary>

After the exact runtime subscription is ready, the integration makes bounded authenticated telemetry requests. Gates use a per-request MQTT status response; `/req-tel` is never state. GRITLock instead opens one bounded current-connection snapshot as soon as MQTT is ready. Trigger status with `gls` can hydrate state during that window; messages without `gls` are ignored. Startup status and settled live `/gl-d` bursts use the same displayed-state field, but only fresh live evidence can confirm a Lock or Unlock command. The integration does not publish MQTT or operate equipment during startup hydration.

</details>

> [!CAUTION]
> GRIT equipment can operate gates and physical access-control devices. This integration must not be relied upon as the sole security or access-control mechanism. Maintain independent safety devices, physical controls, and manual access procedures. It is not a safety, security, or life-safety system.

## Documentation

### Guides

- [Installation and removal](docs/INSTALLATION.md)
- [Compatibility](docs/COMPATIBILITY.md)
- [Entity reference](docs/ENTITIES.md)
- [Architecture and state authority](docs/ARCHITECTURE.md)
- [Troubleshooting and safe log redaction](docs/TROUBLESHOOTING.md)

### Project and release

- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [v0.2.0 acceptance report](docs/ACCEPTANCE_REPORT_v0.2.0.md) and [release checklist](docs/RELEASE_CHECKLIST_v0.2.0.md)

## Known limitations

This is an experimental custom integration. Direct MQTT is required; REST-only operation is unsupported. MQTT uses QoS 0 and has no per-device staleness timer. New devices need an integration reload, stale devices require manual removal, and multi-hub use has not been broadly validated. A Hub-level GRITLock change may fail to propagate to an individual trigger. See [Compatibility](docs/COMPATIBILITY.md) and [Architecture](docs/ARCHITECTURE.md) for the detailed boundaries.

## Privacy and security

Configuration and backups may contain API and MQTT secrets. Share only redacted logs; do not post credentials, raw payloads, private addresses, or customer data. The integration does not expose raw REST or MQTT objects as entity attributes and does not provide a Home Assistant diagnostics download. See the [security policy](SECURITY.md) for vulnerability reporting.

## Notice

This is a community-maintained, unofficial Home Assistant integration for GRIT Hub. It is published by GRIT Automation, Inc. as a convenience.

It is provided AS IS, without warranty of any kind. GRIT Automation, Inc. does not provide support for it and does not guarantee updates, fixes, compatibility with any Home Assistant or GRIT Hub version, or continued availability. Use at your own risk.

Issues and pull requests are welcome, but may not be answered.

See the [MIT License](LICENSE) for the full warranty disclaimer.
