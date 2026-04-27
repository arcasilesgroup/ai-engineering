---
name: compliance-report
description: Use when assembling the cross-framework compliance report for a regulated tier — one finding mapped to SOC2, ISO 27001, HIPAA Safeguards, PCI-DSS, and DORA Articles. Trigger for "generate the audit report", "sync to Vanta", "push to Drata", "produce the board pack", "sign the audit CSV". Outputs PDF (board), JSON (Vanta/Drata), and SHA256-hashed cosign-signed CSV (audit firm).
effort: high
tier: regulated
capabilities: [tool_use, structured_output]
governance:
  blocking: true
---

# /ai-compliance-report

Cross-mapping engine that turns the audit-trail evidence + governance
posture into the artifacts external auditors and GRC platforms expect.
Single source of truth: every finding maps to a SOC2 control id, ISO
27001 control id, HIPAA Safeguard, PCI-DSS requirement, and DORA Article
in one entry.

## Activation

This skill is only loaded under regulated profiles:
`ai-eng install --profile banking|healthcare|fintech|airgapped`

## When to use

- Quarterly audit prep — produce the evidence pack across frameworks
- Vanta / Drata sync windows (read tokens from `manifest.toml`)
- Board reporting cadence (PDF for the audit committee)
- External auditor field request — signed CSV with traceable controls
- Pre-listing readiness check (SOC2 Type II + ISO 27001 dual scope)

## Process

1. **Aggregate** evidence from `/ai-audit-trail`, `/ai-governance`,
   `/ai-security`, and `/ai-data-classification`. Time-window per the
   audit period.
2. **Cross-map** each finding via the framework matrix
   (`shared/data/compliance-matrix.json`) so one root finding emits all
   linked control references.
3. **Render** outputs:
   - **PDF** for the board (executive summary + heatmap).
   - **JSON** for Vanta and Drata APIs (one document per platform schema).
   - **CSV** for the audit firm (one row per (control × evidence)).
4. **Hash** every artifact with SHA-256; record the hash in the
   audit-trail chain.
5. **Sign** every artifact with **cosign keyless OIDC**; attach the
   signature next to the artifact and a link to the Rekor transparency
   log entry.
6. **Sync** to Vanta / Drata using existing tokens from `manifest.toml`
   (read-only handler — never write secrets back).
7. **Emit** `compliance.report.signed` and `compliance.report.synced`
   events for observability.

## Standards mapping

| Control / Article | Requirement | How this skill satisfies it |
|---|---|---|
| **SOC2 CC6 / CC7 / CC8** | Logical access, monitoring, change mgmt evidence | Aggregated from audit-trail, security, governance lanes |
| **ISO 27001 Annex A** | 93 controls with evidence references | Matrix maps each finding to applicable A.x control id |
| **HIPAA Safeguards** | Administrative / Physical / Technical | Tagged at evidence ingestion via `/ai-data-classification` |
| **PCI-DSS v4.0** | 12 requirements + sub-controls | Cardholder data scope inherited from classification |
| **DORA Art 11-13** | Operational resilience + testing evidence | Incident + test telemetry flowed via audit-trail |
| **GDPR Art 30** | Records of processing activities | RoPA dataset emitted as a JSON sidecar |

## Hard rules

- **NEVER** ship a report without SHA-256 hashing AND cosign signing —
  unsigned artifacts are non-evidentiary.
- **NEVER** embed Vanta or Drata tokens in the report payload; tokens
  stay in `manifest.toml` and are read at sync time only.
- **NEVER** flatten the cross-mapping — auditors require the full
  framework set, not just the primary one.
- **NEVER** alter historical reports; new periods produce new
  signed artifacts that reference (do not overwrite) prior ones.
- The Rekor transparency log entry MUST be included alongside the
  artifact; bare cosign signatures are insufficient for some auditors.
- Every report run is itself an audit-trail entry — the meta-evidence
  matters as much as the report.

## Common mistakes

- Choosing one framework and assuming auditors accept "equivalent" mapping
- Forgetting Rekor transparency log links — cosign signature alone is weaker
- Re-using the same export filename across periods (overwrites evidence)
- Pushing to Vanta/Drata without checking the sync was idempotent
- Putting board PDF assets behind links that expire before the next meeting
- Hand-editing the matrix instead of versioning it via spec + ADR
