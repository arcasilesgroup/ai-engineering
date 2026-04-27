---
name: data-classification
description: Use when classifying data, defining residency boundaries, or maintaining the GDPR Art 30 inventory under a regulated profile. Trigger for "is this PII", "classify this dataset", "where can this data live", "build the data inventory", "scope cardholder data". Tiers data as PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED with PII / PHI / PCI flags and emits an audit event for every classification change.
effort: high
tier: regulated
capabilities: [tool_use, structured_output]
governance:
  blocking: true
---

# /ai-data-classification

Single classification authority for regulated tiers. Tags datasets,
fields, and message payloads with a confidentiality tier and regulatory
flags, then enforces residency boundaries (e.g., EU-only routing for
banking tenants). Pairs with `/ai-audit-trail` so every classification
change is itself an evidence-grade event.

## Activation

This skill is only loaded under regulated profiles:
`ai-eng install --profile banking|healthcare|fintech|airgapped`

## When to use

- Onboarding a new dataset, table, queue, or LLM context window
- Building / refreshing the GDPR Art 30 RoPA (records of processing)
- Defining PCI cardholder data scope (CDE) before a v4.0 assessment
- Mapping HIPAA designated record sets and PHI flows
- Setting per-tenant residency rules (e.g., `--profile=banking --tenant=eu-bank`)
- Responding to a CCPA / GDPR data subject request (DSAR)

## Process

1. **Discover** — scan the asset (schema, code path, prompt template)
   for known patterns: emails, national ids, PAN, MRN, IBAN, biometrics,
   geolocation; reuse `/ai-security` regex packs for first pass.
2. **Tier** — assign one of:
   - **PUBLIC** — disclosure has no impact (marketing copy).
   - **INTERNAL** — disclosure causes minor harm (org charts).
   - **CONFIDENTIAL** — disclosure causes material harm (financials).
   - **RESTRICTED** — disclosure triggers regulatory action (PII / PHI / PCI).
3. **Flag** regulatory categories: `pii`, `phi`, `pci`, `biometric`,
   `child` (COPPA), `union-data` (sensitive employment), `genetic`.
4. **Bind residency** — record the allowed regions per tenant (e.g., a
   banking EU tenant locks to `eu-west-1`, `eu-central-1`); LiteLLM /
   TrueFoundry routing reads this binding (ADR-0008).
5. **Persist** the classification through `/ai-audit-trail` so the change
   is hash-chained alongside actor + lawful basis.
6. **Refresh inventories** — RoPA (GDPR Art 30), CCPA consumer-rights
   map, PCI CDE diagram, HIPAA designated record set.
7. **Emit** `data.classified` and `residency.bound` events; downstream
   skills (security, compliance-report, llm-bridge) subscribe.

## Standards mapping

| Control / Article | Requirement | How this skill satisfies it |
|---|---|---|
| **GDPR Art 30** | Records of processing activities (RoPA) | RoPA built from RESTRICTED + flagged datasets with lawful basis |
| **GDPR Art 28** | Processor obligations + sub-processor list | Residency bindings captured per tenant |
| **CCPA § 1798.100** | Consumer rights map (access / delete / opt-out) | DSAR-ready inventory keyed by data subject id |
| **HIPAA 164.514** | De-identification + minimum necessary | PHI flag drives redaction at LiteLLM/TrueFoundry bridge |
| **PCI-DSS 1.1.3** | Cardholder data scope diagram | PCI flag maintains the CDE asset map |
| **DORA Art 8** | ICT risk inventory | Tier + flag combination feeds the risk register |
| **EU AI Act Art 10** | Training / input data quality + bias controls | Classification carries dataset provenance metadata |

## Hard rules

- **NEVER** route RESTRICTED data outside its bound residency, even for
  "fast" inference paths — the bridge MUST refuse.
- **NEVER** treat aggregated or hashed PII as exempt unless a privacy
  engineer signed off; pseudonymization is not anonymization.
- **NEVER** mutate a classification in place; always emit a new
  audit-trail entry referencing the prior `classification_id`.
- **NEVER** allow LLM context windows to ingest RESTRICTED data without
  the Input Guard redaction (Dual-Plane ADR-0002) firing first.
- **NEVER** rely on the developer "remembering" residency — the binding
  is enforced by the deterministic plane, not by guidance.
- Cross-tenant RESTRICTED reads require an explicit OPA policy carve-out
  with risk acceptance (TTL ≤ 30d).

## Common mistakes

- Using INTERNAL for "things only employees see" when it is actually PII
- Forgetting biometric / genetic flags on health datasets — they raise
  the tier under GDPR Art 9
- Treating tokenized PAN as out of scope for PCI without segmentation evidence
- Letting residency live in a wiki rather than as a machine-enforced binding
- Skipping the audit event on classification changes ("trivial edit")
- Conflating de-identification with anonymization in HIPAA reporting
