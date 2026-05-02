# Guard Review: HX-04 T-1.2 Deterministic Vs Advisory Kernel Behavior

## Verdict

- `PASS-WITH-NOTES`

## Findings

- The runtime work-plane truth is now `HX-04` `T-1.2`; the earlier spec-wide Phase 1 admission readout remains a program gate, not a substitute for this slice-local guard review.
- Deterministic kernel behavior is currently concentrated in the modern orchestrated path; prototyping stays advisory and escalates through resolver logic when stronger conditions apply.
- Local blocking authority is still split because generated hooks and the gate CLI continue to route through the legacy `policy.gates` path.
- Serialized findings are already unified at the model-family level, but publish responsibility is still split between orchestrator emission and gate CLI persistence.
- The ownership boundary with `HX-05` and `HX-11` remains intact: validator and verify keep their own report families, the audit/state plane stays outside `HX-04`, and CI remains downstream fan-in.
- No repository-state evidence requires reopening `HX-01`, `HX-02`, or `HX-03`.

## Outcome

- `HX-04` can proceed to `T-1.3`.
- `T-1.3` should carry forward only the already-declared compatibility work: legacy hook gate behavior, findings publication, residual output compatibility, and CI-facing semantics.
- `T-1.3` must not widen into `HX-05` state-plane ownership or `HX-11` eval ownership.

## Next Queue

- Record `HX-04` `T-1.2` as complete in the work-plane.
- Continue with `HX-04` `T-1.3`.