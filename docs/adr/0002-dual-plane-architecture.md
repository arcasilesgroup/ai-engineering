# ADR-0002 — Dual-Plane Architecture (Probabilistic + Deterministic)

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decider**: ai-engineering core team
- **Source**: NotebookLM deep research, BONUS missed-trend analysis

## Context

The original v1 plan treated agents as monolithic entities. The 2026
state-of-the-art separates the **Probabilistic Plane** (the LLM "brain"
doing reasoning, planning, content generation) from the **Deterministic
Plane** (sandbox + policy engine + audit log + identity broker).

Without this separation, frameworks expose users to:

- **Excessive Agency** — agents acquire scopes they don't need.
- **Prompt Injection** — third-party content steers the agent into
  unintended actions.
- **Cognitive Debt** — the organizational cost of maintaining opaque,
  non-deterministic systems grows without bound.

## Decision

Every action proposed by the LLM **MUST** pass through the Deterministic
Plane before execution. The framework provides four invariants:

1. **Input Guard** — regex + lightweight model scan for PII and known
   exploitation patterns BEFORE the prompt reaches the LLM.
2. **Identity Broker** — issues short-lived "On-Behalf-Of" tokens with
   minimum scopes bound to a specific spec/plan execution.
3. **Policy Engine (OPA)** — evaluates every proposed action ("execute
   bash", "edit file", "delete branch") against declarative rules.
4. **Audit Log (immutable)** — append-only, hash-chained log of every
   prompt, thought, and tool execution. SOC2 CC7.2 / HIPAA 164.312(b) /
   DORA Art 11-13 ready.

```
LLM -> proposes action -> [Input Guard] -> [Policy Engine] --+--> EXEC
                              |                  |           |
                              v                  v           v
                         [Audit Log]       [Audit Log]   [Audit Log]
                              ^
                       [Identity Token w/ min scopes]
```

## Consequences

- **Pro**: catastrophic failures (rm -rf prod, leaked creds) are stopped
  by the deterministic gate, not by the LLM "remembering" to be careful.
- **Pro**: regulated industries (banking/healthcare) have a paper trail
  out-of-the-box.
- **Pro**: same architecture handles BYOK (regulated profile pins the
  policy engine to remote attestation).
- **Con**: every action pays a small policy-evaluation cost. OPA hot path
  is < 1ms; acceptable.
- **Con**: more moving parts to test. Mitigated by treating the
  Deterministic Plane as first-class domain entities (Phase 1 includes them).

## Alternatives considered

- **LLM-only with prompt rules ("always check before deleting")** —
  documented as antipattern in NotebookLM research; LLMs comply
  inconsistently.
- **Sandbox-only (no policy engine)** — works for blast-radius but not
  for compliance / audit.

## Implementation references

- `packages/runtime/src/shared/ports/policy.ts` — `PolicyPort`
- `packages/runtime/src/shared/ports/identity.ts` — `IdentityPort`
- `packages/runtime/src/shared/ports/audit.ts` — `AuditLogPort`
