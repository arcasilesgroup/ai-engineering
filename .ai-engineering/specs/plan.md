---
total: 4
completed: 4
---

# Plan: spec-084 Agentic Operations Program

## Plan

- [x] Phase 1: Finalize the autopilot decomposition, deep-plan each child spec, and lock the dependency DAG in `.ai-engineering/specs/autopilot/`.
- [x] Phase 2: Implement independent runtime streams in parallel: portable runbooks, shared-context promotion, verify refresh, and review refresh.
- [x] Phase 3: Land dependent follow-ons: update tree UX after ownership migration, then README refresh after all runtime surfaces settle.
- [x] Phase 4: Run convergence gates, create the pull request with auto-merge enabled, and keep repairing CI until the PR is merged.

## Notes

- Umbrella execution is delegated through `.ai-engineering/specs/autopilot/manifest.md` and the per-sub-spec `spec.md` / `plan.md` files.
- Child-spec execution order:
  - Wave 1: `sub-001`, `sub-003`, `sub-005`, `sub-006`
  - Wave 2: `sub-002`
  - Wave 3: `sub-004`
- Convergence evidence before PR:
  - `uv run python scripts/sync_command_mirrors.py --check`
  - `uv run pytest tests/unit/test_sync_mirrors.py tests/unit/test_template_skill_parity.py tests/unit/test_agent_schema_validation.py tests/unit/test_validator.py tests/unit/test_runbook_contracts.py tests/unit/test_verify_service.py tests/unit/test_verify_scoring.py tests/unit/test_cli_ui.py tests/integration/test_cli_command_modules.py tests/unit/test_state.py tests/unit/installer/test_phases.py tests/integration/test_updater.py tests/unit/test_framework_context_loads.py -q`
