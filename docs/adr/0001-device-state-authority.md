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
- **Hub REST may seed state, with attribution**: when the Hub REST inventory provides persisted per-trigger `gritLockState`, it may be used to seed the integration's GRITLock state. This seed is labeled as Hub-rest-derived, not device-confirmed.

### Consequences
- Confirmations can take longer because device evidence may arrive after a Hub restart or MQTT reconnect. The integration must keep entities available while state is unknown, so commands can still reach the Hub.
- The integration must topic-gate before parsing payloads, to avoid interpreting non-device traffic as device state.
- Tests and fixtures must distinguish command topics from device-originated topics.

