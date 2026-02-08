# User Stories

## Update Metadata

- Rationale: recast stories around the final command and governance model.
- Expected gain: clearer testable outcomes for implementation.
- Potential impact: legacy session-centric stories are retired.

## US-1 Commanded Commit Flow (P0)

As a developer, I want `/commit` and `/commit --only` to be deterministic so I can deliver quickly with governance.

Acceptance criteria:

- `/commit` stages, commits, and pushes current branch.
- `/commit --only` stages and commits only.
- operation is blocked on protected branch or mandatory check failure.

## US-2 Commanded PR Flow (P0)

As a developer, I want `/pr` and `/pr --only` to cover normal and PR-only workflows.

Acceptance criteria:

- `/pr` stages, commits, pushes current branch, and creates PR.
- `/pr --only` warns when branch is not pushed and proposes auto-push.
- if auto-push is declined, user can continue via `defer-pr`, `attempt-pr-anyway`, or `export-pr-payload`.

## US-3 Ownership-Safe Updates (P0)

As a platform engineer, I want framework updates to never overwrite team/project content.

Acceptance criteria:

- updater only modifies framework-managed and system-managed paths.
- team and project paths remain unchanged after update.

## US-4 Risk Decision Reuse (P0)

As a team lead, I want accepted risk decisions to be remembered so users are not repeatedly prompted.

Acceptance criteria:

- decision is persisted with scope, policy, severity, context hash, and expiry.
- prompting is skipped when valid decision exists.
- prompt appears again only on expiry or material context change.

## US-5 Readiness Assurance (P0)

As a developer, I want install/doctor to confirm tools are operational, not only installed.

Acceptance criteria:

- `gh`, `az`, hooks, `uv`, `ruff`, `ty`, and `pip-audit` readiness states are reported.
- failures include actionable remediation.
