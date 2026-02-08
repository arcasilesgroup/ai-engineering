# Review and Quality Gates

## Update Metadata

- Rationale: enforce non-negotiables at review and merge boundaries.
- Expected gain: fewer policy regressions and clearer blocking criteria.
- Potential impact: stricter review outcomes for governance-sensitive changes.

## Mandatory Review Criteria

- change aligns with ownership boundaries and layering precedence.
- non-negotiables are not weakened.
- security-sensitive code paths include tests and audit events.
- docs stay concise and avoid policy duplication.

## Mandatory Local Checks

- `gitleaks`.
- `semgrep`.
- dependency vulnerability checks (`pip-audit` in Python baseline).
- stack checks (`uv`, `ruff`, `ty`, tests).

## Blocking Policies

- no direct commits to `main` or `master`.
- no protected branch direct push for governed commit commands.
- no hook bypass in framework-managed flows.

## Risk Acceptance Review

When policy weakening is requested:

- emit warning and remediation suggestion.
- never auto-apply remediation.
- require explicit risk acceptance to keep weakened state.
- persist result in `state/decision-store.json` and `state/audit-log.ndjson`.

## Cross-OS and Provider Review

- MVP PRs must validate behavior on Windows, macOS, Linux.
- manifest/provider changes must preserve provider-agnostic schema and ADO extension points.
