---
spec: "004"
approach: "serial-phases"
---

# Plan — Hygiene & Risk Governance

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/git/__init__.py` | Git helpers package init |
| `src/ai_engineering/git/operations.py` | Shared git operations: current_branch, is_branch_pushed, PROTECTED_BRANCHES |
| `src/ai_engineering/maintenance/branch_cleanup.py` | Branch scanning, cleanup, and reporting |
| `src/ai_engineering/pipeline/__init__.py` | Pipeline compliance package init |
| `src/ai_engineering/pipeline/compliance.py` | Pipeline scanning and compliance checking |
| `src/ai_engineering/pipeline/injector.py` | Risk gate injection into pipelines |
| `src/ai_engineering/templates/pipeline/github-risk-gate-step.yml` | GitHub Actions step template |
| `src/ai_engineering/templates/pipeline/azure-risk-gate-task.yml` | Azure DevOps task template |
| `.ai-engineering/skills/workflows/pre-implementation.md` | Pre-implementation hygiene skill |
| `.ai-engineering/skills/govern/accept-risk.md` | Risk acceptance skill |
| `.ai-engineering/skills/govern/resolve-risk.md` | Risk resolution skill |
| `.ai-engineering/skills/govern/renew-risk.md` | Risk renewal skill |
| `tests/unit/test_git_operations.py` | Git helpers tests |
| `tests/unit/test_branch_cleanup.py` | Branch cleanup tests |
| `tests/unit/test_risk_lifecycle.py` | Risk lifecycle tests |
| `tests/unit/test_pipeline_compliance.py` | Pipeline compliance tests |

### Modified Files

| File | Changes |
|------|---------|
| `src/ai_engineering/state/models.py` | Evolve `Decision` with risk fields, add enums |
| `src/ai_engineering/state/decision_logic.py` | Add risk lifecycle functions |
| `src/ai_engineering/state/defaults.py` | Update `default_decision_store()` to schema 1.1 |
| `src/ai_engineering/policy/gates.py` | Add risk acceptance checks, import from git helpers |
| `src/ai_engineering/commands/workflows.py` | Import from git helpers, remove duplicates |
| `src/ai_engineering/maintenance/report.py` | Extend `MaintenanceReport` with risk/branch data |
| `src/ai_engineering/cli_factory.py` | Register new CLI commands |
| `src/ai_engineering/cli_commands/gate.py` | Add `risk-check` command |
| `src/ai_engineering/cli_commands/maintenance.py` | Add `branch-cleanup`, `risk-status`, `pipeline-compliance` |
| `tests/unit/test_state.py` | Add tests for new Decision fields, backward compat |
| `tests/unit/test_gates.py` | Add tests for risk gate checks |
| `AGENTS.md` | Register new skills, add pre-implementation directive |
| `.github/copilot-instructions.md` | Register new skills |
| `CLAUDE.md` | Register new skills |
| `CHANGELOG.md` | Add entries under `[Unreleased]` |

### Mirror Copies

| Source | Mirror |
|--------|--------|
| `.ai-engineering/skills/workflows/pre-implementation.md` | `src/ai_engineering/templates/.ai-engineering/skills/workflows/pre-implementation.md` |
| `.ai-engineering/skills/govern/accept-risk.md` | `src/ai_engineering/templates/.ai-engineering/skills/govern/accept-risk.md` |
| `.ai-engineering/skills/govern/resolve-risk.md` | `src/ai_engineering/templates/.ai-engineering/skills/govern/resolve-risk.md` |
| `.ai-engineering/skills/govern/renew-risk.md` | `src/ai_engineering/templates/.ai-engineering/skills/govern/renew-risk.md` |

## File Structure

```
src/ai_engineering/
├── git/
│   ├── __init__.py
│   └── operations.py                  # Shared git helpers
├── maintenance/
│   ├── branch_cleanup.py              # Branch scan + cleanup
│   └── report.py                      # Extended with risk/branch
├── pipeline/
│   ├── __init__.py
│   ├── compliance.py                  # Pipeline scanning
│   └── injector.py                    # Risk gate injection
├── state/
│   ├── models.py                      # Evolved Decision model
│   └── decision_logic.py              # Extended risk functions
├── policy/
│   └── gates.py                       # Extended with risk checks
├── cli_commands/
│   ├── gate.py                        # + risk-check
│   └── maintenance.py                 # + branch-cleanup, risk-status, pipeline-compliance
└── templates/
    └── pipeline/
        ├── github-risk-gate-step.yml
        └── azure-risk-gate-task.yml
```

## Session Map

| Phase | Description | Size | Key Deliverables |
|-------|-------------|------|-----------------|
| 0 | Scaffold | S | spec.md, plan.md, tasks.md, _active.md |
| 1 | Git helpers refactor + schema evolution | M | `git/operations.py`, evolved `Decision` model, manifest config |
| 2 | Decision logic enhancement | M | Risk lifecycle functions in `decision_logic.py` |
| 3 | Risk lifecycle skills | M | 4 skill markdown files + mirrors + registration |
| 4 | Branch cleanup module | M | `branch_cleanup.py` + `pre-implementation.md` skill |
| 5 | Gate enforcement | M | Risk checks in `gates.py` + `risk-check` CLI command |
| 6 | Pipeline compliance | L | `pipeline/compliance.py`, `injector.py`, templates |
| 7 | CLI & reporting | M | `branch-cleanup`, `risk-status`, `pipeline-compliance` commands, extended report |
| 8 | Audit & governance docs | S | Audit events, AGENTS.md, copilot-instructions, CHANGELOG |
| 9 | Testing | L | All new test files + extended existing tests |

## Patterns

- **Backward compatibility**: all new `Decision` fields are `Optional` with defaults. Schema version bumped but 1.0 data validates.
- **Layer discipline**: CLI → service → state → I/O. No layer skipping.
- **Pydantic models**: all data structures use `BaseModel`, not dataclasses (except `GateCheckResult`/`GateResult` which are pre-existing).
- **Git subprocess**: all git operations go through `subprocess.run` with timeout and error handling.
- **Audit trail**: every risk lifecycle transition logs to `audit-log.ndjson`.
- **Configurable defaults**: severity expiry, max renewals, warn-before days — all in `manifest.yml`.
