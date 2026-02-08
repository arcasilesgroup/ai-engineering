# Planning

## Update Metadata

- Rationale: convert architecture decisions into executable workstreams.
- Expected gain: clearer build order and measurable DoD.
- Potential impact: current backlog priorities are reordered around enforcement and ownership.

## MVP Workstreams (Priority Order)

1. Ownership + state model (`install-manifest.json`, `ownership-map.json`, `sources.lock.json`, `decision-store.json`, `audit-log.ndjson`).
2. Standards layering engine for framework/team precedence.
3. Command flows for `/commit`, `/pr`, `/acho`.
4. Hook enforcement engine with mandatory checks.
5. Readiness checks for `gh`, `az`, hooks, `uv`, `ruff`, `ty`, `pip-audit`.
6. Remote skills lock/cache/integrity behavior.
7. Maintenance and compaction reporting.

## MVP Backlog

| Priority | Item | Dependencies | DoD |
|---|---|---|---|
| P0 | Ownership-safe installer and updater | none | updater changes framework/system paths only |
| P0 | Policy engine with non-negotiables | standards resolver | weakening attempt triggers warning + remediation + explicit risk acceptance |
| P0 | Command runner for `/commit`, `/pr`, `/acho` | policy + hooks | behavior matrix passes |
| P0 | Mandatory hook checks | policy engine | `gitleaks`, `semgrep`, dep and stack checks enforced |
| P0 | Readiness validator | installer | machine-readable readiness output |
| P0 | Sources lock and cache | state layer | deterministic lock replay and offline fallback |
| P1 | Maintenance agent local reports | state + context | weekly report with compaction recommendations |
| P1 | Telemetry pipeline | policy engine | strict opt-in only |

## /pr --only Decision Flow

If branch is not pushed:

- show warning.
- propose auto-push.
- if accepted, push and continue.
- if declined, continue with one mode: `defer-pr`, `attempt-pr-anyway`, or `export-pr-payload`.
- persist chosen behavior in decision store and audit log.

## Definition of Done (MVP)

- command contract implemented and tested.
- non-bypassable local enforcement active.
- state files present with schema validation.
- updater ownership rules proven by contract tests.
- E2E validation passes on Windows, macOS, Linux.

## Phase Execution Plan

| Phase | Scope | Status |
|---|---|---|
| Phase A | Contract alignment: `AGENTS.md`, `CLAUDE.md`, root docs, local permissions, tooling baseline metadata | Completed |
| Phase B | App bootstrap: module scaffolding, state schemas, install/doctor base | Completed |
| Phase C | Governance enforcement: hooks, mandatory checks, protected-branch blocking | Completed |
| Phase D | Command runtime: `/commit`, `/pr`, `/acho`, `/pr --only` continuation modes | Completed |
| Phase E | Remote skills lock/cache and maintenance-agent workflow | Pending |

## Phase B Progress Notes

- Rationale: establish executable framework baseline before high-impact governance enforcement.
- Expected gain: install/doctor and state validation become deterministic and testable.
- Potential impact: command surface and module layout are now fixed for downstream phases.

- Completed in this block: module scaffolding, state schemas, default state generators, minimal `install` and `doctor`, and initial tests.
- Remaining in Phase B: richer doctor reporting, stronger install idempotency signals, and updater ownership enforcement implementation.

## Phase C Progress Notes

- Rationale: enforce governance locally before implementing high-impact command automation.
- Expected gain: immediate policy protection through hooks and gate execution.
- Potential impact: commit/push flows now fail closed when mandatory checks fail.

- Completed in this block: managed hook scripts, hook integrity checks, protected-branch blocking, and mandatory pre-commit/pre-push gate execution wiring.
- Completed in Phase C closeout: branch-protection discovery from GitHub remote (with fallback), gate remediation guidance, and gate requirements listing.

## Phase D Progress Notes

- Rationale: implement governed command workflows used by engineers daily.
- Expected gain: deterministic stage/commit/push/PR behavior with decision-store aware PR-only paths.
- Potential impact: command flows become stricter and rely on local gate outcomes.

- Completed in this block: command workflow service, CLI `commit`/`pr`/`acho` commands, and PR-only continuation handling (`auto-push`, `defer-pr`, `attempt-pr-anyway`, `export-pr-payload`).
- Completed in Phase D closeout: workflow coverage for real git scenarios (feature-branch commit path and PR-only defer decision persistence).
