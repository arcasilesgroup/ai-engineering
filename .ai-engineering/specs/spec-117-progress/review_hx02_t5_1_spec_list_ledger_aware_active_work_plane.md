# Review - HX-02 / T-5.1 / spec-list-ledger-aware-active-work-plane

## Scope

- `src/ai_engineering/cli_commands/spec_cmd.py`
- `tests/unit/test_spec_cmd.py`

## Review Focus

- placeholder `spec.md` must not force a false `No active spec.` result when the resolved spec-local work plane still has live ledger tasks
- fully-done resolved ledgers must remain idle for compatibility
- keep the cutover local to `spec_list()` and matching unit coverage

## Findings

- No correctness findings after the final local review.
- The production change reuses the same placeholder-to-ledger activity rule already landed in Wave 1 and the work-items service.
- The tests cover both the live-ledger activation path and the done-ledger idle guardrail for a spec-local work plane.

## Residual Risk

- Identifier-driven readers still need an explicit fallback policy when the compatibility `spec.md` buffer stays placeholder text.
