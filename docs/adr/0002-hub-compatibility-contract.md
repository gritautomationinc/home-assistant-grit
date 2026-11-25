## ADR 0002: Hub compatibility contract

### Status
Accepted for v0.2.0.

### Context
The integration depends on GRIT Hub REST and MQTT contracts. A Hub update can change payload shapes, topic behavior, or endpoint semantics. Without an explicit compatibility contract, regressions can ship unnoticed.

### Decision
The integration declares one Hub version it is verified against, and it warns when the Hub version differs.

- **Verified Hub version**: v0.2.0 is verified against GRIT-hub v1.1.1197.
- **Contract fixtures**: the repository includes hand-built fixtures derived from GRIT-hub v1.1.1197 source. Each fixture cites file and line ranges from that tag.
- **Version check**: at setup, the integration reads the Hub software version. If the version is below v1.1.1197 or cannot be parsed, the integration continues to run but raises a Home Assistant repair issue stating that the Hub version is not verified with this integration release.
- **Forward updates**: when verifying against a new Hub release, the process is to update fixtures first, then update parsing and behavior, then update the compatibility documentation.

### Consequences
- Reviewers can independently confirm contract assumptions against fixtures and cited Hub sources.
- Users get a clear warning on Hub version skew without a hard failure, which avoids breaking existing installs due to updates outside Home Assistant.

