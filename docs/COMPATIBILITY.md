# Compatibility

| Integration | Verified GRIT Hub | Home Assistant |
| --- | --- | --- |
| `0.3.0` | `v1.1.1197` routes inspected for environmental and Presence features; live validation pending | `2026.11.1` smoke tested (minimum `2026.3.0` per `hacs.json`) |
| `0.2.0` | `v1.1.1197` | `2026.11.1` (minimum `2026.3.0` per `hacs.json`) |

At setup the integration reads the Hub `softwareVersion` (falling back to
`hubVersion`). If the version is below `1.1.1197` or cannot be parsed, setup
continues and Home Assistant raises a non-fatal repair issue: **Hub version not
verified with this integration**.

MQTT uses `paho-mqtt` `>=2.1.0,<3`. The integration declares `iot_class`
`local_push`.
