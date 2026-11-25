# Changelog

All notable project changes are recorded here. This project uses semantic
versioning for public releases.

## 0.2.0 — 2026-11-25

Release for GRIT Hub v1.1.1197 compatibility and safe state authority.

### Finding → ticket map

| Finding | Ticket | Change |
| --- | --- | --- |
| F1 | T4 | GRITLock confirms only on device-originated `gl-d` |
| F2 | T6 | Gate `mv` and switch `s` command echoes ignored (`return {}`) |
| F3 | T5 | GRITLock stays available when unknown; REST seed; late `sts` |
| F4 | T8 | `device_command` uses POST execute |
| F5 | T7 | Path-segment hardening rejects traversal before HTTP |
| F6 | T9 | Options flow no longer assigns read-only `config_entry` |
| F7 | T11 | Manual stale-device removal; no auto-prune; no MQTT re-append |
| F9 | T12 | MQTT topic gate (structure, hub id, device type) before JSON parse |
| F10 | T13 | RFID `sts` refresh; `last_received` on every accepted message |
| F11 | T10 | Restart/Reboot buttons removed |
| F12 | T14 | Lockout 502/409 semantics |
| F13 | T15 | Health-check 503 vs 404 fallback |
| F14 | T16 | Primary entity naming without doubled object ids |
| F15 | T16 | Consistent `bool_state` for dict/string shapes |
| F16 | T17 | Hub version repair (warn); `iot_class` local_push; paho pin |
| F18 | T20 | Stop shipping default MQTT password; legacy repair issue |

### Added

- Home Assistant repair issues for legacy shared MQTT credentials and unverified
  Hub software versions.
- Manual device removal via `async_remove_config_entry_device` when absent from
  the last complete Hub inventory.
- Compatibility documentation for Hub `v1.1.1197` and HA `2026.11.1`.

### Changed

- Manifest version `0.2.0`, `iot_class` `local_push`,
  `requirements` `paho-mqtt>=2.1.0,<3`.
- New installs require explicit per-hub MQTT username and password.
- RFID exact `s` / `st` / `sts` schedule coalesced REST refresh.
- MQTT Last Received stays available while connected (never-seen is unknown).

## 0.1.2 — 2026-08-06

### Fixed

- Consolidated GRITLock startup status and quiet-settled live `/gl` evidence into
  one continuous immutable observed-state channel.
- Kept Lock and Unlock as explicit `PUT /api/hub/lockout` desired-state commands
  and require a fresh matching post-command `/gl` observation on that same
  channel for confirmation.
- Added compatibility for Dion's mixed `gte=1` Lock and sparse/all-`gte=0`
  Unlock patterns, plus Jeff's all-`gte=0` Lock and Unlock pattern.
- Corrected bounded startup hydration for both Dion-style and Jeff-style trigger
  status reporting while ignoring messages without strict binary `gls`.
- Preserved prior valid state when evidence is incomplete or a command times out;
  complete disagreement and MQTT disconnect continue to invalidate authority.
- Preserved gate startup hydration and RFID startup/detail authority.

## 0.1.1 — 2026-08-05

### Fixed

- Made GRITLock compatible with trigger `/gl` messages that report `gte=0`:
  `gls` remains the authoritative live state and `gte` is advisory only. Valid
  REST participant metadata takes precedence; otherwise the exact bounded set
  observed in the fresh quiet-settled `/gl` generation defines participants.
  Empty, incomplete, contradictory, stale, overflowing, timed-out, or unsettled
  generations continue to fail closed.

Released as [GRIT Hub for Home Assistant v0.1.1](https://github.com/gritautomationinc/home-assistant-grit/releases/tag/v0.1.1)
on 2026-08-05. The release passed the all-`gte=0` installation but exposed a
mixed-installation regression and is superseded by v0.1.2.

## 0.1.0 — 2026-08-04

### Changed

- Recorded final transferred-repository live acceptance and verified repository
  security settings.
- Prepared publication documentation, security guidance, repository metadata,
  and offline documentation validation.
- Reduced benign unsupported MQTT-object logging from warning to debug while
  retaining warnings for malformed input.
- Made authenticated REST requests fail closed on HTTP redirects.

### Added

- HACS custom-integration packaging and config-flow localization.
- Authenticated current-hub discovery using `GET /api/hub`, with broker-only
  fallback when the API omits a usable LAN address.
- Direct subscribe-only MQTT v3.1.1 client with bounded lifecycle, input
  validation, exact successful SUBACK readiness, and no publish path.
- Gate covers with MQTT startup hydration, immediate external updates, and
  post-command MQTT confirmation.
- Per-reader RFID locks using authoritative individual REST detail and bounded
  MQTT-triggered invalidation refresh.
- System GRITLock using bounded MQTT trigger consensus with provisional strict
  REST startup state.
- Collector switches using individual REST detail and transition-aware command
  confirmation.
- Hub controls and diagnostics, including LED brightness, connectivity,
  software information, refresh, restart, and disabled-by-default reboot.
- Reconfiguration for API token rotation and MQTT settings while preserving
  config-entry, device, and entity identity.
- Deterministic network-free tests and HACS, Hassfest, and unit-test workflows.

### Security and privacy

- Opaque bounded bearer-token handling shared by production and diagnostic code.
- Sanitized REST and MQTT data retention, bounded generic logging, and no raw
  response/payload entity attributes.
- Redirect refusal for bearer-authenticated requests and diagnostics.
- No arbitrary HTTP endpoint service and no MQTT publishing.

Released as [GRIT Hub for Home Assistant v0.1.0](https://github.com/gritautomationinc/home-assistant-grit/releases/tag/v0.1.0)
on 2026-08-04.
