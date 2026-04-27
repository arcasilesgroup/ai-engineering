---
name: incident-respond
description: Use when an ICT-related incident is detected under a regulated profile and DORA timeframes apply — critical < 4h major < 24h regulator notification. Trigger for "we have an incident", "page on-call", "notify the regulator", "DORA major", "contain and remediate". Drives Detect → Triage → Notify → Contain → Remediate → Postmortem and hands off to `/ai-postmortem` for the DERP write-up.
effort: high
tier: regulated
capabilities: [tool_use]
governance:
  blocking: true
---

# /ai-incident-respond

Regulated-tier incident response orchestrator. Enforces DORA Art 17-18
notification windows, drives a six-phase response loop, and produces the
audit evidence regulators require. Hands the resolved incident to
`/ai-postmortem` for the DERP write-up.

## Activation

This skill is only loaded under regulated profiles:
`ai-eng install --profile banking|healthcare|fintech|airgapped`

## When to use

- A telemetry alert crossed a Sev-1 / Sev-2 threshold
- A customer reported a regulated-data exposure (PII / PHI / PCI)
- A control failure was detected by `/ai-governance` (e.g., ownership drift on cardholder data)
- A near-miss that *would* have been DORA major if it had reached production
- A supply-chain compromise was confirmed (paired with `/ai-security`)

## Process

1. **Detect** — confirm the alert, capture the trigger (telemetry event id,
   customer ticket, SOC dispatch). Open `/ai-engineering/incidents/<id>.md`
   and start the live timeline.
2. **Triage** — classify severity AND regulatory impact:
   - DORA **critical**: regulator notification window **< 4h** from awareness.
   - DORA **major**: regulator notification window **< 24h** from awareness.
   - HIPAA breach: HHS notification within 60 days; > 500 records → media.
   - PCI-DSS: card brand notification per acquirer SLA (typically 24h).
3. **Notify** regulators and stakeholders before the deadline. Templates
   under `.ai-engineering/templates/regulators/` (DORA, HHS, ICO, FCA, OCC).
   Every notification is itself an audit-trail entry.
4. **Contain** — invoke `/ai-hotfix` for code-level mitigation, rotate
   credentials via the Identity Broker (ADR-0002), revoke OPA policies
   that are part of the blast radius.
5. **Remediate** — validate the fix, re-open production traffic in stages,
   monitor regression metrics for the configured cool-down window.
6. **Postmortem** — within 48h call `/ai-postmortem` with the incident id;
   it consumes the audit-trail timeline as the source of truth.

## Standards mapping

| Control / Article | Requirement | How this skill satisfies it |
|---|---|---|
| **DORA Art 17** | Major incident classification within 4h | Triage step encodes thresholds; gate refuses to proceed without classification |
| **DORA Art 18** | Initial / intermediate / final notifications | Templated notifications + audit-trail entries per notification |
| **HIPAA 164.404** | Breach notification of affected individuals | HHS templates + 60-day countdown timer |
| **PCI-DSS 12.10** | Incident response plan + 24/7 readiness | Six-phase loop + on-call roster integration |
| **SOC2 CC7.3** | Identify, classify, and respond to incidents | Full timeline persisted via `/ai-audit-trail` |
| **GDPR Art 33** | 72h notification of personal data breach | Triage step adds GDPR clock alongside DORA |

## Hard rules

- **NEVER** skip regulator notification on a DORA *major* incident, even
  if remediation completed before the window closed. The notification IS
  the regulatory artifact.
- **NEVER** edit the live timeline retroactively — corrections are new
  entries marked `correction` referencing the original.
- **NEVER** rotate credentials outside the Identity Broker; manual
  rotation breaks the audit chain and re-introduces excessive agency.
- **NEVER** declare an incident resolved without a green `/ai-test`
  pass on the affected paths and a confirmed regression-window watch.
- **NEVER** skip the postmortem within 48h; it is mandatory for any
  DORA major or HIPAA reportable event.
- A DORA *critical* page MUST acknowledge within 15 minutes; missing the
  ack escalates automatically to backup on-call.

## Common mistakes

- Confusing severity (operational) with classification (regulatory) — they
  are independent decisions
- Treating "we fixed it fast" as a reason to skip notification
- Containment without rotating identities — same compromise resurfaces
- Reconstructing the timeline from chat scrollback instead of the audit log
- Letting comms and remediation block on each other; they run in parallel
- Forgetting the 48h postmortem deadline because the page is closed
