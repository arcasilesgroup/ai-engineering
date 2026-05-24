## spec-105 — Unified Gate + Generalized Risk Acceptance

**Branch**: `feat/spec-101-installer-robustness` (umbrella; PR re-point to `feat/specs-101-104-105-adoption` deferred to post-spec-106).
**Phases**: 8. **Tasks closed**: 147 (122 build + 25 verify). **Cycle pattern**: each commit shipped GREEN code for the current phase plus RED tests (`@pytest.mark.spec_105_red`) for the next phase, mirroring spec-104.

**Phase commit SHAs**:
- P1 `f6fb46cc` — schema additions (Decision finding_id/batch_id), 4 RED test scaffolds.
- P2 `a060427a` — `apply_risk_acceptances` + GateFindingsDocument v1.1 + AcceptedFinding model.
- P3 `4d16b7ba` — `ai-eng risk *` CLI surface (7 subcommands).
- P4 `d352998b` — orchestrator wiring + dual-emit v1/v1.1 + compact CLI output.
- P5 `73497a73` — `gates.mode` + escalation + tier allocation.
- P6 `5a8ae82f` — `policy/auto_stage.py` + Wave 1 hook integration.
- P7 `8dbb461f` — prompt-injection-guard whitelist + skill/doc/mirror updates.
- P8 (this commit) — RED sweep + new-module coverage push + history update.

**Key metrics**:
- New modules + coverage: `risk_cmd.py` 86%, `_accept_lookup.py` 100%, `auto_stage.py` 85%, `mode_dispatch.py` 99% (89% aggregate across the 4).
- `pytest -m 'not spec_105_red' --no-cov`: 4626 passed (vs 4586 in P7 baseline). 26 failed + 10 errors are pre-existing isolation flakes in `test_doctor_remaining_branches`, `test_python_env_mode_install`, `test_safe_run_env_scrub`, `test_setup_cli`, `test_update_orphan_detection`, `test_update_provider_filtering`.
- `pytest -m 'spec_105_red' --collect-only`: 1 selected (perf test only — intentional nightly opt-in).
- New tests added across phases: 102+ (decision-model, lookup, schema v1.1, CLI per-command, validation edge cases, orchestrator integration, mode escalation, tier allocation, auto-stage parity, skill mirror parity, plus Phase 8 filter/format/banner coverage).

**Lessons learned**:
1. **Marker pattern is effective**: `@pytest.mark.spec_105_red` excluded by default keeps CI green throughout; markers removed only after the targeted GREEN code lands. Iron Law preserved — no test was weakened to fit implementation.
2. **Pre-existing isolation flakes**: 6 test files (env-scrub, setup CLI, updater orphan/filter, doctor branches, python-env install) fail in suite ordering but PASS in isolation. Verified on every parent commit; none introduced by spec-105.
3. **Fixture invariants matter**: `GateFinding` rejects `auto_fixable=True` paired with `auto_fix_command=None` per `_enforce_auto_fix_command_when_fixable`. Phase 1 RED scaffolds pre-dated this validator; Phase 8 GREEN bodies set `auto_fixable=False` to satisfy it without coupling assertions to fixer wiring.
4. **Coverage padding rule honored**: Phase 8 added two test files (`test_risk_cli_filters_and_formats.py`, `test_mode_dispatch_banners_and_globs.py`) targeting *real* uncovered branches (markdown formatter, severity/expires-within filter, error paths, banner_for_mode, `release/*` glob, manifest-load failure fallback) rather than no-ops to satisfy the ≥80% bar.
5. **Cross-IDE parity**: `test_risk_cross_ide.py` pivoted from subprocess `python -m ai_engineering` (no `__main__.py`) to CliRunner+`monkeypatch.setenv`; same parity contract, faster execution.

**Branch consolidation status**: Tasks T-8.15–T-8.18 (rename to `feat/specs-101-104-105-adoption`, push, PR re-point, conditional stale-branch deletion) deferred to post-spec-106. Default per CLAUDE.md Don't #5 + spec D-105-13: leave the existing branch in place; never push --force or delete origin branches without explicit approval.
