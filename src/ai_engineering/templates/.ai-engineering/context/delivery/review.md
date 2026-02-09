# Review and Quality Gates

## Document Metadata

- Doc ID: DEL-REVIEW
- Owner: project-managed (delivery)
- Status: active
- Last reviewed: 2026-02-09
- Source of truth: `.ai-engineering/context/delivery/review.md`

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

## Backlog and Delivery Docs Pre-Merge Checklist

- lifecycle alignment present: Discovery -> Architecture -> Planning -> Implementation -> Review -> Verification -> Testing -> Iteration.
- ownership model respected: no contradiction with framework/team/project/system boundaries.
- traceability complete: epic -> feature -> story -> task -> implementation/verif/testing evidence links.
- active-vs-history separation respected: no phase execution logs added to active backlog catalogs.
- stale snapshot handling respected: historical snapshots are archived or explicitly marked deprecated.
- required quality/security gate statement present for code-affecting work: `unit`, `integration`, `e2e`, `ruff`, `ty`, `gitleaks`, `semgrep`, `pip-audit`.
- missing mandatory tooling was auto-remediated and checks re-run, or operation stayed blocked with explicit manual remediation steps.
- references updated: `backlog/index.md`, `delivery/index.md`, and `backlog/status.md` reflect current state.
