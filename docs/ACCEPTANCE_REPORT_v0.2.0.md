# v0.2.0 acceptance report

Prepared report for integration release `0.2.0`. **Not published.** No
`v0.2.0` tag or GitHub release exists yet.

## Scope

Safe state authority, MQTT hardening, Hub v1.1.1197 compatibility, and the
Wave 1 + Wave 2 tickets listed in `docs/work-packages/v0.2.0.md`.

## Automated evidence (this preparation)

- Network-free unit suite: see the tip-branch CI / local
  `python3 -m unittest discover -s tests` run recorded with the release prep
  commits.
- Fake REST/MQTT clients only; no live Hub or physical equipment.
- manifest is prepared at version `0.2.0`.

## Decisions locked for this release

- T11: manual stale-device removal only (no auto-prune).
- T17: warn on unverified Hub versions; do not refuse setup.
- T20: stop shipping `DEFAULT_MQTT_PASSWORD`; legacy entries keep working with a
  repair issue; discovery never probes with a built-in password.
- T6: leave command-echo `return {}` as implemented.

## Remaining gates

- Owner authorisation to tag and publish.
- HACS and Hassfest workflow green on the final release commit.
- Separate production-acceptance gate for installing on a live Home Assistant.
