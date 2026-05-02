# Guard Review: HX-05 T-3.4 Task-Trace Governance

## Verdict

- `PASS-WITH-NOTES`

## Findings

- Task traces now append from authoritative task-ledger mutations through `state.work_plane.write_task_ledger(...)` and the canonical `emit_task_trace(...)` helper, so derived summaries and chat heuristics are not part of the source of truth.
- Runtime plus live and template hook writers still converge on the single append-only `framework-events.ndjson` stream; `T-3.2` did not create a second audit log or alternate chain field.
- The absence of a kernel-outcome `task_trace` callsite is acceptable in the current repo state because no existing kernel surface carries authoritative task identity; wiring one now would require heuristics, which the contract explicitly forbids.
- Carry-forward risk: `write_task_ledger(...)` persists the authoritative ledger before appending `task_trace`, so an append failure would leave task state correct while the audit view is incomplete.

## Outcome

- `HX-05` can proceed to `T-4.1`.
- `T-4.1` and `T-4.2` should keep scorecards and reporting strictly downstream of task-ledger plus framework-event inputs and should not infer task identity from generic kernel outcomes.
- If a future kernel API starts carrying authoritative task identity, wire `task_trace` there directly instead of synthesizing task lineage across records.

## Reopen Check

- No earlier slice must reopen; the remaining note is sequencing and failure semantics inside `HX-05`, not evidence that `HX-01`, `HX-02`, `HX-03`, or `HX-04` landed the wrong contract.