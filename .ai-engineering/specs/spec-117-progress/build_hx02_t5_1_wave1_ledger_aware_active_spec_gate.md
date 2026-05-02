# Build Packet - HX-02 / T-5.1 / wave1-ledger-aware-active-spec-gate

## Task ID

HX-02-T-5.1-wave1-ledger-aware-active-spec-gate

## Objective

Cut Wave 1 over from placeholder-only spec readiness to resolved-work-plane
ledger readiness. When `project_root` is explicit, the same root must control
readiness detection, fixer subprocess `cwd`, and relative staged-file
convergence checks.

## Write Scope

- `src/ai_engineering/policy/orchestrator.py`
- `tests/unit/test_orchestrator_wave1.py`
- No edits outside those files.

## Failing Tests First

- Add `test_wave1_runs_spec_verify_for_placeholder_spec_with_active_resolved_ledger`
  and expect Wave 1 to skip `spec-verify` before the fix.
- Keep the existing placeholder idle regression green.
- After review, add pointer-aware idle and relative-path convergence regressions
  to close the remaining project-root gaps.

## Minimum Production Change

- Keep the cutover local to `run_wave1()` and `_has_active_spec()`.
- Treat placeholder `spec.md` as active when `read_task_ledger(project_root)`
  returns any non-`DONE` task from the resolved work plane.
- Forward explicit `project_root` into the Wave 1 readiness gate and every
  fixer subprocess `cwd`.
- Normalize relative staged paths against `project_root` before mtime snapshots
  and ruff argv construction so convergence reruns still trigger correctly.
- Do not widen into validator code, CLI wrappers, resolver internals, or
  work-item services.

## Verification

- `uv run pytest tests/unit/test_orchestrator_wave1.py -k placeholder_spec_with_active_resolved_ledger -q`
- `uv run pytest tests/unit/test_orchestrator_wave1.py -k "resolved_ledger or relative_staged_file_changes" -q`
- `uv run pytest tests/unit/test_orchestrator_wave1.py -q`

## Done Condition

- Placeholder `spec.md` plus readable resolved ledger with live tasks runs
  `spec-verify`.
- Placeholder plus fully `done` resolved ledger stays idle even when fallback
  surfaces look active.
- Explicit `project_root` controls readiness and fixer subprocess `cwd`.
- Relative staged paths under explicit `project_root` still trigger the
  convergence rerun and modified-file accounting.
- Focused and full Wave 1 pytest slices pass.

## Execution Evidence

### Change Summary

- Made `_has_active_spec(project_root)` ledger-aware for placeholder specs.
- Forwarded `project_root` into `run_wave1()` readiness checks and into every
  fixer subprocess `cwd`.
- Normalized relative staged paths against `project_root` before snapshotting
  mtimes or building ruff argv.
- Added resolved-ledger active, resolved-ledger idle, and relative-path
  convergence regressions in `test_orchestrator_wave1.py`.

### Failing Test Executed First

- `uv run pytest tests/unit/test_orchestrator_wave1.py -k placeholder_spec_with_active_resolved_ledger -q`
- Result before implementation: `FAIL` because Wave 1 skipped `spec-verify`
  for a placeholder spec even when the resolved ledger still had live work.

### Follow-up Repairs

- Correctness review found that `spec-verify` inherited the caller's working
  directory instead of `project_root`; fixed `_run_pass(..., cwd=project_root)`
  and asserted `cwd` in the active regression.
- Testing review found the idle branch was not discriminating and that
  relative staged files under explicit `project_root` could miss convergence
  reruns. Tightened the idle regression with contradictory fallback surfaces
  and added a relative-path rerun regression.
- Final correctness and testing reviews returned no findings.

### Passing Checks Executed

- `uv run pytest tests/unit/test_orchestrator_wave1.py -k placeholder_spec_with_active_resolved_ledger -q` -> `1 passed`
- `uv run pytest tests/unit/test_orchestrator_wave1.py -k "resolved_ledger or relative_staged_file_changes" -q` -> `3 passed`
- `uv run pytest tests/unit/test_orchestrator_wave1.py -q` -> `13 passed`

### Result

- Wave 1 no longer treats placeholder prose alone as the authoritative idle
  state when the resolved ledger still carries live work.
- Explicit `project_root` now governs both subprocess execution and relative
  staged-file convergence tracking.
- The cutover stayed inside `policy/orchestrator.py` and
  `test_orchestrator_wave1.py`.

### Residual Concerns

- `T-5.1` still has remaining runtime and CLI cutover work outside Wave 1.
- `T-5.2` deferred-cleanup documentation remains blocked on normalizing the
  next slice into the task ledger.