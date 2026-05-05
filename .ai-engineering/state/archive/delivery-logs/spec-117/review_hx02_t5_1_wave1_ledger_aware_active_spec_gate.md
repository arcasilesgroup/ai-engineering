# HX-02 T-5.1 Wave 1 Ledger-Aware Active Spec Gate - Review Handoff

## Scope

- `src/ai_engineering/policy/orchestrator.py`
- `tests/unit/test_orchestrator_wave1.py`

## Review Agents

- `code-reviewer-correctness`
- `code-reviewer-testing`

## Findings

- Initial correctness review found that `spec-verify` was invoked without
  `cwd=project_root`; fixed locally by forwarding `project_root` through
  `_run_pass(...)` and rerunning the focused plus full Wave 1 tests.
- Initial testing review found that the idle resolved-ledger regression was
  not discriminating and that relative staged files under explicit
  `project_root` were not covered for convergence reruns. Tightened the idle
  regression with contradictory fallback surfaces and added the relative-path
  rerun regression, then reran the focused and full Wave 1 tests.
- Final correctness review: No findings.
- Final testing review: No findings.

## Status

- `DONE`

## Residual Scope

- Remaining `T-5.1` work is outside `run_wave1()` and still concerns any other
  runtime or CLI readiness gates that may treat placeholder buffers as
  authoritative.