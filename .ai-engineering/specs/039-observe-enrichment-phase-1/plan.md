---
spec: "039"
approach: "serial-phases"
---

# Plan — Observe Enrichment Phase 1

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/vcs/repo_context.py` | RepoContext dataclass — URL parsing (GitHub SSH/HTTPS, ADO modern/user-prefix/legacy/SSH), module-level cache, fail-open |
| `src/ai_engineering/git/context.py` | GitContext dataclass — branch + commit_sha (short 8), module-level cache |
| `src/ai_engineering/cli_commands/workflow.py` | CLI wrappers: `workflow commit`, `workflow pr`, `workflow pr-only` |
| `tests/unit/test_repo_context.py` | URL parsing for GitHub/ADO variants |
| `tests/unit/test_git_context.py` | Branch/commit extraction with mocked run_git |
| `tests/unit/test_spec_helpers.py` | `_next_spec_number()` and `_slugify()` in lib/parsing.py |
| `tests/unit/test_signal_aggregators.py` | 8 new aggregator functions |
| `tests/unit/test_workflow_cmd.py` | CLI invocation tests |
| `tests/unit/test_observe_dashboards.py` | 5 expanded dashboards |
| `tests/unit/test_deploy_event_wiring.py` | Release orchestrator → emit_deploy_event |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/state/models.py` | +7 optional fields on AuditEntry |
| `src/ai_engineering/state/audit.py` | Import + inject VCS/git context in `_emit()` |
| `src/ai_engineering/installer/service.py` | `_log_install_event()` — add VCS fields |
| `src/ai_engineering/installer/operations.py` | `_save_manifest_and_log()` — add VCS fields |
| `src/ai_engineering/commands/workflows.py` | `_log_audit()` — add VCS fields |
| `src/ai_engineering/release/orchestrator.py` | Replace `_log_audit_event()` with `emit_deploy_event()` |
| `src/ai_engineering/updater/service.py` | `_log_update_event()` — add VCS fields |
| `src/ai_engineering/cli_commands/signals_cmd.py` | `signals_emit()` — add VCS fields |
| `src/ai_engineering/cli_factory.py` | Register `workflow_app`, remove `spec save` |
| `src/ai_engineering/lib/signals.py` | +8 aggregator/reader functions |
| `src/ai_engineering/lib/parsing.py` | +`_next_spec_number()`, +`_slugify()` from spec_save.py |
| `src/ai_engineering/cli_commands/observe.py` | 5 dashboard expansions |
| `.gitignore` | Remove `state/*` + exceptions |
| `.ai-engineering/state/audit-log.ndjson` | Reset (empty) |
| `.ai-engineering/agents/plan.md` | New Spec-as-Gate Pattern (LLM-driven) |
| `.ai-engineering/skills/spec/SKILL.md` | Remove CLI-Driven Path section |
| `.ai-engineering/skills/plan/SKILL.md` | Remove `ai-eng spec save` reference |

### Deleted Files

| File | Reason |
|------|--------|
| `src/ai_engineering/cli_commands/spec_save.py` | Replaced by LLM-driven spec creation |
| `tests/unit/test_spec_save.py` | Tests for removed command |

## Session Map

### Phase 0: LLM-Driven Spec Creation [M]

Remove `ai-eng spec save`, move helpers to lib, update governance docs.

- Agent: `build`
- Files: 8 (2 delete, 3 edit, 1 edit+move, 2 create)
- Gate: `ai-eng spec --help` shows no `save` subcommand

### Phase 1: VCS Context [S]

Create `repo_context.py` and `git/context.py` with tests. No dependencies on other phases.

- Agent: `build`
- Files: 4 (2 create, 2 test)
- Gate: Unit tests pass for URL parsing + git context

### Phase 2: AuditEntry Extension [S]

Add 7 optional fields to AuditEntry. Inject in `_emit()`.

- Agent: `build`
- Files: 2 (edit)
- Gate: Existing tests still pass, new fields serialized correctly

### Phase 3: Update Write Sites [M]

Update 6 modules that write audit entries outside `_emit()`. Standardize release orchestrator.

- Agent: `build`
- Files: 7 (6 edit, 1 test)
- Gate: Deploy events use `emit_deploy_event()`

### Phase 4: Workflow CLI Wiring [S]

Create workflow CLI commands. Register in cli_factory.

- Agent: `build`
- Files: 3 (2 create, 1 edit)
- Gate: `ai-eng workflow commit --help` works

### Phase 5: Signal Aggregators [M]

Add 8 new helper functions to signals.py with tests.

- Agent: `build`
- Files: 2 (1 edit, 1 test)
- Gate: All aggregator tests pass

### Phase 6: Dashboard Expansion [L]

Expand 5 observe dashboards with new sections. Preserve existing `_sonar_metrics()`.

- Agent: `build`
- Files: 2 (1 edit, 1 test)
- Gate: `ai-eng observe <mode>` shows expanded output

### Phase 7: Git Tracking [S]

Simplify .gitignore. Reset audit-log.

- Agent: `build`
- Files: 2 (edit)
- Gate: `git status` shows state/ tracked

### Phase 8: Verification [S]

Run all quality gates.

- Agent: `build`
- Gate: ruff + ty + pytest + ai-eng gate pre-commit

## Patterns

### Fail-Open

All VCS context resolution and signal aggregation is fail-open. If git is not available or data sources are missing, functions return empty/default values. No operation should fail because of missing observability data.

### Module-Level Cache

`get_repo_context()` and `get_git_context()` use module-level variables to cache results. VCS remote URL and repo context don't change within a session. Branch and commit SHA are stable within a single CLI invocation.

### Single Event Store

All events flow through `_emit()` → `audit-log.ndjson`. No dual-write. Aggregators read from this single source. Dashboards compose aggregator outputs.

### Backward Compatibility

All 7 new AuditEntry fields are optional with `None` default. Existing events without these fields continue to deserialize correctly. Aggregators handle missing fields gracefully.

## Execution Plan

| Phase | Agent | Tasks | Depends On | Gate |
|-------|-------|-------|------------|------|
| 0 | `build` | 0.1–0.8 | — | `ai-eng spec --help` no `save` |
| 1 | `build` | 1.1–1.4 | — | Unit tests pass |
| 2 | `build` | 2.1–2.2 | Phase 1 | Serialization OK |
| 3 | `build` | 3.1–3.7 | Phase 2 | Deploy events emitted |
| 4 | `build` | 4.1–4.3 | — | `workflow --help` works |
| 5 | `build` | 5.1–5.9 | — | Aggregator tests pass |
| 6 | `build` | 6.1–6.6 | Phase 5 | Dashboards show new sections |
| 7 | `build` | 7.1–7.2 | Phase 2 | state/ tracked |
| 8 | `build` | 8.1–8.5 | All | All gates green |

**Parallelizable**: Phases 0, 1, 4, 5 have no cross-dependencies.
**Serial chain**: Phase 1 → 2 → 3 → 7. Phase 5 → 6.

## Observability Roadmap (continuity to 100%)

| Phase | Spec | Coverage | Key Deliverables |
|-------|------|----------|-----------------|
| **1** (this) | 039 | ~65% | VCS enrichment, wiring, dashboard expansion |
| **2** | TBD | ~85% | Wire scan/build/session emitters to agents |
| **3** | TBD | ~92% | Skill/agent tracking (new event types) |
| **4** | TBD | ~98% | External integrations (MTTR, drift) |
| **5** | TBD | 100% | Trend analysis, self-optimization hints |
