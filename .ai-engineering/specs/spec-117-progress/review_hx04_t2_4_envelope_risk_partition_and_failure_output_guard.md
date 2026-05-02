# Guard Review: HX-04 T-2.4 Envelope, Risk Partition, And Failure Output

## Verdict

- `PASS-WITH-NOTES`

## Findings

- The shared `KernelContract` now centralizes registration, resolved mode, findings model, residual sibling, publish owner, retry ceiling, loop caps, and blocked disposition output for the owned orchestrator/gate path.
- Risk-accept partitioning already runs on the owned kernel path and stays scoped to blocking versus accepted findings plus additive expiration arrays rather than mutating task state or eval taxonomy.
- The failure-output contract is now explicit and still HX-04-scoped: retry ceiling `3`, active cap `30 min`, passive cap `4h`, blocked status `blocked`, residual output `watch-residuals.json`, and exit code `90`.
- Carry-forward: adapter convergence must treat the full `GateFindingsDocument` family, including additive accepted/expiring arrays, as the authoritative result-envelope family rather than keying only on the base `v1` schema literal.
- Carry-forward: publish ownership should remain explicit on the adapter side for the first cut.
- The HX-05 and HX-11 boundary remains intact; no durable task-state mutation, event-vocabulary ownership, or eval taxonomy ownership moved into HX-04.

## Outcome

- `HX-04` can proceed to `T-3.1`.
- Adapter convergence can stay narrow: parity tests and adapter rewiring over the now-explicit kernel contract, without reopening absorbed baseline or widening into state/eval ownership.

## Next Queue

- Record `HX-04` `T-2.4` as complete in the work-plane.
- Continue with `HX-04` `T-3.1`.