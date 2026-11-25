# v0.2.0 release checklist

Prepared checklist. Do not tag or publish until Joel authorises release.

## Pre-release

- [x] Manifest version is exactly `0.2.0`
- [x] `iot_class` is `local_push`
- [x] `requirements` pin `paho-mqtt>=2.1.0,<3`
- [x] CHANGELOG has a `0.2.0` entry mapping findings to tickets
- [x] COMPATIBILITY.md lists Hub `v1.1.1197` and HA `2026.11.1`
- [x] Unit suite passes network-free (`python3 -m unittest discover -s tests`)
- [ ] HACS validation passed
- [ ] Hassfest validation passed
- [ ] Working tree clean at the final release commit
- [ ] Final release commit selected and verified

## Publish (requires explicit authorisation)

- [ ] `v0.2.0` tag pushed to the configured origin
- [ ] GitHub release `v0.2.0` created
- [ ] Post-release HACS Custom Repository install/update verified
- [ ] Final corrective issue closeout completed
