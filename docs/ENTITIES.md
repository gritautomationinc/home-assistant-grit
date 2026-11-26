# Entity reference

This document inventories the entity platforms implemented by the `grit_hub`
custom integration. Entity creation depends on the devices and fields returned
by the configured GRIT system.

Forwarded platforms are `sensor`, `binary_sensor`, `switch`, `cover`, `button`,
`lock`, and `number`.

## State-authority summary

| Device or control | Home Assistant platform | Displayed-state authority | Command confirmation |
| --- | --- | --- | --- |
| Gate | `cover` | MQTT live state, including fresh requested `/sts` or `/tel` startup telemetry | Newer matching MQTT observation after the pre-command boundary |
| RFID reader | `lock` | Individual `GET /api/rfid/{id}` strict `state` | Newer matching individual REST generation |
| GRITLock | `lock` | Latest immutable observation from REST seed, startup status, device status, settled live `/gl-d`, or disagreement | Matching fresh settled `live_gl_d` observation newer than the pre-command connection/sequence boundary |
| Collector | `switch` | Individual collector detail, with proven MQTT supplementation | Newer online, settled matching individual REST detail |
| Solenoid, latch, powerbank | `switch` | Existing collection/reconciliation implementation | Bounded full coordinator refresh; no collector contract is claimed |
| Air filter on controllable air-quality units | `switch` | Device `st` or `sts` state | Newer matching MQTT state observation after the manual override command |
| System LED brightness | `number` | Sanitized hub REST field | Newer full hub refresh with matching value |

Unknown or incomplete authoritative evidence remains Unknown. HTTP success alone
does not confirm a state-changing command, and no entity publishes optimistic
state.

## Covers

### Gate

One `CoverEntity` with device class `gate` is created per discovered gate.
After exact MQTT readiness, a bounded authenticated per-gate telemetry request
waits for a fresh `/sts` or `/tel` response. Its compact `p` field may be a
bounded number or numeric text and hydrates position/open state. `/req-tel` is a
request marker, not gate state. Hub command `/mv` is ignored as state and never
updates the gate. Later device-originated `/mv-d`, `/p`, and `/st` observations
continue to update immediately. Gate `/s` currently still updates open state
through the same sanitized path when it carries a valid open, state, or `s`
field or a usable position; that behaviour is unchanged here pending an owner
decision relative to ADR 0001. Open and close use the bounded REST
state route, capture the MQTT sequence before the command, and require a newer
matching MQTT observation. There is no unproven REST gate-state fallback and no
assumption that a retained MQTT status exists. A missing response leaves that
gate Unknown without erasing valid state accepted for another gate.
Availability requires a successful REST update, an active MQTT subscription,
and no explicit offline report. Attributes are restricted to bounded
allowlisted diagnostics.

## Locks

### GRITLock

One system-wide `LockEntity` is created. `PUT /api/hub/lockout` receives
`{"state": true}` for Lock and `{"state": false}` for Unlock. The entity is
never toggle-driven or optimistic. It stays available whenever Hub REST polling
is succeeding, even when state is unknown. A successful REST trigger inventory
may seed display state from agreeing `gritLockState` values (`rest_seed`); that
seed cannot confirm Lock or Unlock.

Displayed state derives from one latest immutable coordinator observation.
Strict current-connection trigger `/sts` or `/tel` `gls` may hydrate that field
at startup; `/tel` without `gls` does not count. Nonempty complete REST
`gritLockEnabled` metadata selects startup participants only when the complete
nonempty set is fully represented by current strict `gls`. Empty, invalid, or
not-fully-represented metadata falls back to the bounded observed reporters.
Messages without `gls` are ignored. After 250 ms quiet, unanimous one is Locked,
unanimous zero is Unlocked, and disagreement is Unknown; valid evidence need not
wait for the full five-second window. Startup status is displayed-state
authority only and cannot confirm Lock or Unlock.

Exact `trigger/<id>/gl-d` messages provide continuous live authority. Each
bounded quiet-settled burst keeps only the latest valid observation per trigger.
If REST inventory provides a usable `gritLockEnabled=true` set, participation is
that set, evaluated at settle time against the latest inventory (latest wins).
Otherwise, if any fresh observation has `gle=1`, exactly the fresh `gle=1`
subset participates. If all fresh observations have `gle=0` or omit `gle`, every
fresh observed trigger participates, including a sparse one-frame burst. Every
selected observation must agree: `gls=1` is locked (`True`), `gls=0` is unlocked
(`False`), and exact `False` is authority, not missing state. Complete
disagreement publishes Unknown. Malformed, incomplete, overflowing, or unsettled
evidence preserves the last valid state. REST inventory never mutates stored
burst observations; it only selects which observations participate at settle.

A command captures MQTT connection generation and receive sequence before the
explicit REST desired-state request. It then waits against the same latest
observation channel for a naturally settled `live_gl_d` observation supported
entirely by sequences newer than the boundary. This accepts a matching frame
that arrives while REST is still awaiting and avoids lost wakeups by checking
before and after waiter registration. HTTP success, current displayed state,
startup status, REST seed, stale evidence, an opposite state, disagreement,
timeout, disconnect, or reconnect cannot confirm. There are no command
generation IDs or retained command-result map. When MQTT is disconnected the
REST lockout request still reaches the Hub; confirmation simply cannot complete.

No-op requests still send REST and require fresh matching live evidence.
Confirmation failure preserves the last valid displayed state unless explicit
disagreement or disconnect invalidates authority. A valid live observation
notifies the entity once, so Locked exposes Unlock and Unlocked exposes Lock
without waiting for REST polling. Unknown remains available while Hub REST
polling is succeeding. Gate and RFID entity semantics are unchanged by this
GRITLock refactor.

### RFID reader

One `LockEntity` is created per uniquely identified RFID reader. The lock state
is the Hub's in-memory observation exposed through the strict boolean `state`
from `GET /api/rfid/{id}`:

- `true` means enabled/unlocked;
- `false` means disabled/locked.

Unknown means the Hub has not observed that reader's state since the Hub process
started. Lock sends REST state `false`; Unlock sends REST state `true`.
Confirmation requires a newer matching individual detail read. Collection
`state` and `lockout` are not used as lock state. Exact MQTT `s`, `st`, and
`sts` types invalidate the cached state and schedule a bounded, debounced
individual REST refresh; their payload values do not determine the lock state.

An explicitly offline reader is unavailable. A temporary failed read preserves
the last valid state internally without inventing a new one. No signed-in user,
cardholder, card number, or other personal data is ingested into entity state or
attributes.

## Switches

One `SwitchEntity` may be created for each discovered collector, solenoid,
latch, and powerbank.

### Collector

Collector state comes from strict individual `GET /api/collector/{id}` fields,
including `state`, transition fields, and online status. A command captures the
individual-detail generation before sending REST state `true` or `false`, then
performs bounded detail reads. It waits through a legitimate transition and
succeeds only for a newer, online, settled matching state. This accommodates the
proven delayed collector shutdown without claiming success too early.

### Other switch types

Solenoid, latch, and powerbank retain the existing generic REST collection
refresh confirmation. The integration does not claim collector transition
semantics for them. Their availability also depends on successful REST and MQTT
connectivity and no explicit offline observation.

## Numbers

### System LED Brightness

A configuration-category `NumberEntity` provides a 0–100 percent slider in
whole-number steps. It writes only the documented hub setting and confirms it
with a newer full hub refresh. No matching refreshed value means failure rather
than an assumed state.

## Buttons

| Entity | Category | Behavior and limitations |
| --- | --- | --- |
| Refresh All | Configuration | Requests an immediate coordinator refresh; no device command |
| Device Refresh | Configuration, per device | Calls the bounded device refresh route, then refreshes coordinator state |
| Device Locate | Configuration, per device | Calls the bounded locate route and may cause physical device activity |

Restart GRIT Service and Reboot Hub buttons were removed in v0.2.0. Those Hub
routes require a human admin session and always return 403 for API tokens. On
upgrade, their entity registry entries are deleted during setup.

## Binary sensors

All are diagnostic entities:

- **Online** — Home Assistant coordinator REST update success.
- **Internet Connectivity** — strict sanitized hub
  `connectedToInternet` value.
- **Physical Hub Buttons Disabled** — strict sanitized hub
  `disableHubButtons` value.
- **MQTT Connection** — dedicated client connection/subscription state; always
  available so broker loss remains visible.
- **MQTT Online** — per-device bounded MQTT online observation, available only
  after a supported value has been observed.

## Sensors

Hub diagnostic sensors are **Status**, **Device Count**, **Hub IP Address**,
**Hub Software Version**, and **Software Branch**. Generic status sensors may be
created for air-quality, presence, pressure, dustbin, magswipe, scanner,
trigger, and extender devices.

Air-quality devices also expose measurement sensors for PM1, PM2.5, PM4, PM10
(µg/m³), temperature (°C), humidity (%), carbon dioxide (ppm), VOC index, and
NOx index when their firmware reports those readings on MQTT `q`. Pressure
devices expose pressure (mbar) and temperature (°C) from MQTT `pt` or `st`.
These numeric sensors use Home Assistant's measurement state class, so the
recorder can graph them from the time observations begin. Unsupported or
unreported readings remain unavailable; Hub historical readings are not
imported.

Controllable air-quality devices with a supported control type receive an **Air Filter**
switch. Turning it on requests a timed manual override using the Hub's
configured `overrideOnTimer` value, or 30 minutes if absent. Turning it off
requests manual off. A fresh device `st` or `sts` state report confirms either
command; HTTP success alone does not change the displayed switch state.
Sensor-only AirGuard 4.1 and 5.1 units have no filter switch.

Every uniquely discovered device may also receive these diagnostics when a
supported value exists:

- **MQTT RSSI** — signal strength in dBm;
- **MQTT Firmware** — bounded firmware text;
- **MQTT Last Received** — UTC timestamp of the last accepted device MQTT
  message for that device. Every accepted device message updates it. While MQTT
  is connected the entity stays available; a missing value means never seen
  this session (unknown), not unavailable.

Entity attributes are limited to the integration's small scalar allowlist; raw
REST objects, raw MQTT payloads, complete topics, and error responses are not
exposed.

## Device removal

Stale devices that are absent from the last successful complete Hub inventory
may be removed manually in Home Assistant. Devices still present in that
inventory cannot be removed. There is no automatic prune option.

## Services

`grit_hub.device_command`, `grit_hub.refresh_device`, and
`grit_hub.locate_device` are registered. They accept bounded path components,
not arbitrary HTTP methods or arbitrary endpoint paths. They can still cause
physical activity and should be called only with a verified target and an
explicitly authorized site procedure.

No MQTT publishing service or general arbitrary-endpoint service exists.

See [Architecture](ARCHITECTURE.md), [Troubleshooting](TROUBLESHOOTING.md), or
return to the [README](../README.md).
