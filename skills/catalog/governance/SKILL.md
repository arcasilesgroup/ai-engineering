---
name: governance
description: Use when verifying compliance posture, ownership boundaries, manifest integrity, or risk acceptance lifecycle — audit-ready evidence, OPA policy checks, decision-store TTL freshness. Trigger for "is this compliant", "audit our governance", "expire this risk acceptance", "verify ownership".
effort: max
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: true
---

# /ai-governance

Living compliance. Validates manifest integrity, ownership boundaries,
and risk acceptance lifecycle. Produces audit-ready evidence for SOC2,
HIPAA, DORA, and EU AI Act regulators.

> **OPA gatekeeper** (ADR-0002) — declarative policies in Rego evaluate
> every proposed action. Hot path < 1ms.

## When to use

- Pre-merge governance gate (PR uses `/ai-verify` which calls this)
- Quarterly audit prep — produce evidence pack
- New skill / agent / plugin onboarding — boundary check
- TTL-expired risk acceptance follow-up
- "Is this change in scope for this spec?"

## Process

1. **Manifest integrity** — verify `.ai-engineering/manifest.toml`
   schema, no orphan references, hash-chain on `decision-store.json`.
2. **Ownership boundaries** — every changed file is within an active
   spec's declared write scope; flag drift outside boundaries.
3. **Spec → plan → impl traceability** — every commit references a
   spec; every spec has a plan; every plan has gate criteria.
4. **Risk acceptance lifecycle** — find expired entries, prompt for
   renewal or remediation; emit `risk.expired` events.
5. **Policy evaluation (OPA)** — run `opa eval` on declarative rules
   covering: write boundaries, plugin trust tiers, branch protection,
   secret allowlists, hook integrity hashes.
6. **Evidence emission** — append to immutable audit log; export
   regulator-friendly bundle (`.ai-engineering/audit/<date>.tar.gz`).

## Outputs

- **Compliance report** — pass/fail per control with evidence references
- **Boundary violations** — files outside declared write scope
- **Stale risk acceptances** — entries past TTL needing action
- **Audit bundle** — immutable hash-chained NDJSON + manifest snapshot

## Hard rules

- NEVER weaken a gate, severity, or threshold without the full protocol:
  warn user, generate remediation patch, persist risk acceptance with
  owner + spec-ref + TTL, emit outcome event.
- NEVER edit `decision-store.json` outside the `risk-accept` flow —
  the hash chain breaks and audit trail invalidates.
- NEVER expand a spec's write scope mid-implementation; revise the spec.
- Manifest changes require ADR for Articles I–VI of the constitution.

## Common mistakes

- Allowing implicit scope creep ("just one more file outside the spec")
- Treating risk acceptance as suppression rather than logged-acceptance
- Skipping audit bundle export — regulators ask later, not now
- Letting TTL expire silently rather than escalating
- Ignoring OPA policy denials by routing around the gatekeeper
