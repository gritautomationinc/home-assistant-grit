## ADR 0001: Device-state authority

### Status
Accepted for v0.2.0.

### Context
The GRIT Hub publishes both commands and observations on MQTT. Some command topics share similar payload shapes with device-originated topics. Treating command echoes as observations can make Home Assistant show a state that was never confirmed by the device.

This integration controls physical access equipment. Reporting an optimistic or incorrect state is a safety and trust problem.

### Decision
Home Assistant state for GRIT devices is confirmed only by device-originated evidence.

- **Device-originated topics are observations**: for example `gl-d` (GRITLock completion), `mv-d` (gate movement completion), `st` and `sts` (device status and reports).
- **Hub-originated topics are commands, not observations**: for example `gl`, `mv`, `s`. These frames must never update entity state and must never satisfy confirmation waits.
- **Participation is explicit**: GRITLock participation is derived from the Hub REST `gritLockEnabled` and MQTT `gle` (gritLockEnabled). It is not derived from `gte` (gateTriggerEnabled).
- **Participation settles against the latest Hub REST inventory**: the set of participating triggers is evaluated at settle time, using the most recent REST inventory. If the inventory changes during a confirmation window, the latest inventory wins. REST inventory never mutates stored burst observations; it only selects which of those observations count.
- **Hub REST may seed state, with attribution**: when a successful Hub REST trigger inventory provides persisted per-trigger `gritLockState` for every participant and those values agree, it may seed the integration's GRITLock display state. This seed is labeled `rest_seed` (Hub-rest-derived), not device-confirmed, and cannot satisfy a lock or unlock confirmation wait.
- **Availability fails open; confirmation fails closed**: when Hub REST polling is succeeding, the GRITLock entity stays available even if state is unknown, so lock and unlock can still reach the Hub. Confirmation still requires device-originated evidence.

### Consequences
- Confirmations can take longer because device evidence may arrive after a Hub restart or MQTT reconnect. The integration must keep entities available while state is unknown, so commands can still reach the Hub.
- After an MQTT reconnect the displayed state becomes unknown until a successful REST seed or later device evidence arrives. Late `/sts` and `/gl-d` frames after the startup window still update display state. Live `/gl-d` authority is not overwritten by later status-only frames.
- The integration must topic-gate before parsing payloads, to avoid interpreting non-device traffic as device state.
- Tests and fixtures must distinguish command topics from device-originated topics, and must cover settle-time participation against a mid-burst inventory change.

