# Harness Engineering

Harness Engineering is the standard for building and changing the ai-engineering framework itself. It treats the agent experience as a governed runtime: deterministic controls prove safety, probabilistic agents propose and explain work, and every lasting state change is traceable.

## Rules

1. Spec and work-plane state are authoritative. Implementation traces to an approved spec, plan, task ledger entry, current summary, and verification evidence.
2. Deterministic gates own enforcement. LLM judgment can advise, but policy, validation, tests, and scans decide whether a claim is proven.
3. Mirrors are generated projections. Canonical skill and agent sources are edited once, and IDE mirrors are regenerated rather than hand-edited.
4. Runtime surfaces keep explicit owners. Control-plane, mirror, kernel, state, capability, context, eval, and adapter contracts are consumed by later slices rather than reopened.
5. Replacement comes before deletion. Legacy surfaces retire family by family only after parity proof and rollback criteria exist.
6. User-facing docs trail runtime truth. README-style docs explain implemented commands and artifacts, not planned contracts.

## Review Focus

Harness changes should be reviewed for ownership drift, deterministic proof, rollback path, mirror provenance, and state authority. Style concerns are secondary unless they affect maintainability or future proof.

## Verify Focus

Harness verification should prove the relevant command, validator, state, mirror, or context behavior with fresh evidence. A passing narrative is not a substitute for a command result, structural validation, or focused regression test.