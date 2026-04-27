---
name: audit-trail
description: Use when recording any agent action into the immutable, hash-chained audit log required by regulated profiles — DORA Art 11-13, HIPAA 164.312(b), SOC2 CC7.2. Trigger for "log this for audit", "is this DORA-evidentiary", "verify the audit chain", "export evidence for the auditor". Every action passes through this skill before the Deterministic Plane records it.
effort: high
tier: regulated
capabilities: [tool_use]
governance:
  blocking: true
---

# /ai-audit-trail

Hash-chained, append-only evidence log for regulated tiers. Every action
proposed by the Probabilistic Plane lands here **before** execution so
banking, healthcare, fintech, and air-gapped deployments inherit a
tamper-evident paper trail by default. Implements the Audit Log invariant
of the Dual-Plane Architecture (ADR-0002).

## Activation

This skill is only loaded under regulated profiles:
`ai-eng install --profile banking|healthcare|fintech|airgapped`

## When to use

- Before executing any tool action under a regulated profile
- Reconstructing an incident timeline from telemetry (paired with `/ai-incident-respond`)
- Producing the evidence bundle requested by `/ai-compliance-report`
- Verifying the hash chain after a suspected tamper event
- Onboarding a new storage adapter (chain re-anchor, not rewrite)

## Process

1. **Capture** the actor (user / agent / spec-ref), the proposed action,
   and the input payload (PII-redacted via the LiteLLM/TrueFoundry
   bridge — ADR-0008).
2. **Policy decision** — submit to the OPA Policy Engine; record the
   decision (allow/deny/risk-accept) as part of the entry.
3. **Hash-link** to the prior entry: `entry.hash = sha256(prev.hash || canonical(entry.body))`.
   Anchor periodically to the configured storage adapter.
4. **Persist** through the storage adapter chosen at install time:
   - **AWS**: S3 Object Lock (compliance mode) + DynamoDB hash index.
   - **AWS regulated/legal-hold**: Amazon QLDB (cryptographically verifiable).
   - **Air-gapped**: in-process append-only NDJSON with periodic notarization to an internal HSM.
5. **Execute** the action only after the entry is durably persisted.
6. **Emit** a `audit.entry.persisted` event so observability and
   `/ai-governance` see fresh evidence.

## Standards mapping

| Control / Article | Requirement | How this skill satisfies it |
|---|---|---|
| **SOC2 CC7.2** | Detect and respond to anomalies via complete activity logs | Append-only entries with actor, action, decision, outcome |
| **HIPAA 164.312(b)** | Audit controls for ePHI access | PHI-tagged actions captured pre-execution; hash chain prevents post-hoc edits |
| **DORA Art 11** | ICT-related incident detection and management | Every tool execution logged with timestamp ≤ 1ms skew |
| **DORA Art 12** | Major incident reporting evidence | Bundle export feeds regulator template |
| **DORA Art 13** | Resilience testing traceability | Test runs recorded with same chain |
| **PCI-DSS 10.2** | Logged events for cardholder data access | PCI-tagged classifications integrated via `/ai-data-classification` |
| **GDPR Art 30** | Records of processing activities | Actor + lawful basis recorded per entry |

## Hard rules

- **NEVER** execute an action before its audit entry is durably persisted —
  the storage write is the gate, not best-effort.
- **NEVER** mutate or delete an existing entry; corrections are *new*
  entries that reference the prior `entry_id`.
- **NEVER** bypass the OPA Policy Engine for "small" actions — every
  proposed action records its decision, even allow-by-default.
- **NEVER** ship plaintext PII/PHI/PCI in entry payloads; redact at the
  Input Guard before hashing.
- The chain head MUST be co-signed (cosign keyless OIDC) before export
  to a regulator or external auditor.
- Storage adapter swaps are ADR-required and create a *new* chain root
  with a notarized handoff entry — never silently re-key.

## Common mistakes

- Writing the audit entry **after** execution ("we'll log it on success")
- Treating the in-process fallback as a long-term store under banking profiles
- Forgetting to include the policy decision when the action was allowed
- Using mutable timestamps (server local time) instead of monotonic + UTC
- Embedding raw PII in entry bodies because "the storage is encrypted"
- Re-using a single hash chain across tenants — chains MUST be tenant-scoped
- Skipping cosign signing of the chain head before regulator export
