# Planning

## Document Metadata

- Doc ID: DEL-PLANNING
- Owner: project-managed (delivery)
- Status: active
- Last reviewed: 2026-02-09
- Source of truth: `.ai-engineering/context/delivery/planning.md`

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
| Phase E | Remote skills lock/cache and maintenance-agent workflow | Completed |
| Phase F | Product contract consolidation and rollout charter alignment | Completed |
| Phase G | Legacy content adoption pack with content-first constraints | Completed |
| Phase H | Ownership-safe updater (dry-run/apply, ownership rule evaluation) | Completed (advanced merge hooks pending) |
| Phase I | Canonical/template governance alignment and cleanup | Completed |
| Phase J | PR auto-complete and git cleanup slice | Archived/Superseded |
| Phase K | Command contract closure and stack/IDE management commands | Completed (cross-OS hook launcher hardening pending) |
| Phase L | Runtime simplification and removal of non-contractual cleanup command | Completed |
| Phase M | CLI modularization and audit-log timestamp hardening | Completed |
| Phase N | Workflow runtime simplification and internal path cleanup | Completed |
| Phase O | Backlog-delivery traceability hardening quick wins | Completed |
| Phase P | Structure reorganization (indexes, status board, active-vs-history split) | Completed |
| Phase Q | Documentation hardening (metadata normalization and pre-merge checklist) | Completed |
| Phase R | Automated docs contract enforcement (gate + CLI + tests) | Completed |

## Phase Status Alignment Notes

- Phase J records are historical only and are no longer normative for active planning.
- Active backlog and execution sources are:
  - `.ai-engineering/context/backlog/tasks.md`
  - `.ai-engineering/context/delivery/implementation.md`
- Open carry-over items from prior phases remain tracked in active backlog queue:
  - B-007 richer doctor/install ownership-safe extensions.
  - F-007 charter workstreams W1-W5 full implementation.
  - H-005 advanced merge strategy and migration hooks.
  - K-006 Windows-safe hook launcher hardening.

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

## Phase E Progress Notes

- Rationale: activate remote skills cache/lock behavior and context-maintenance loops for long-term governance health.
- Expected gain: deterministic skill sourcing with offline fallback and regular context quality reports.
- Potential impact: `.ai-engineering/state/` now includes maintenance and skills sync artifacts.

- Completed in this block: skills sync/list services with cache and lock updates, maintenance report generation, and CLI entrypoints.
- Completed in Phase E closeout: hard-fail trust enforcement (allowlist + checksum pinning validation) and approved maintenance payload PR command flow.
