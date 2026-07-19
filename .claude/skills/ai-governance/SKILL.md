---
name: ai-governance
description: "Validates framework compliance, ownership boundaries, risk acceptance lifecycle, and manifest integrity for regulated environments. Trigger for 'are quality gates enforced', 'who owns this file', 'formally accept a known risk', 'pre-release compliance check', 'governance report for auditors'. Not for code quality; use /ai-verify instead. Not for security scanning; use /ai-security instead — this validates governance process, not code content."
effort: high
argument-hint: "all|compliance|ownership|risk|integrity|--report"
tags: [governance, compliance, ownership, risk, integrity, enterprise]
---

# Governance

Validates framework compliance, ownership boundaries, risk-acceptance lifecycle, and manifest integrity for regulated environments. Use it between phases or before releases to confirm quality gates are enforced, formally accept a known risk, or produce a scored compliance report for auditors.

## Quick start

```
/ai-governance              # compliance mode (default)
/ai-governance all          # all four modes
/ai-governance risk accept  # accept a new risk (TTL by severity)
/ai-governance integrity    # framework consistency check
/ai-governance --report     # formal report (score + verdict)
```

## Workflow

Principles applied: §10.4 DRY (the manifest and decision-store are the single canonical stores this validates — governance confirms every datum has one authoritative home).

Compliance validation for regulated industries. Default mode is `compliance`. Pick a mode, run the checks, surface findings; with `--report`, generate a scored audit document.

0. **Load contexts** — read `.ai-engineering/manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` per stack + `_shared/conventions.md`; load `.ai-engineering/team/*.md`.
1. **compliance** — verify quality-gate enforcement (hooks, CI workflows, non-negotiables, security contract).
2. **ownership** — map files to ownership zones (framework / team / project / system); verify modification history.
3. **risk** — record / resolve / renew risk acceptances in `decision-store.json` with severity-based TTL.
4. **integrity** — manifest counters vs disk reality; agent-skill cross-refs; state-file schemas.

Detail: [the four modes](references/modes.md), [OPA policy-engine integration](references/policy-engine.md), [`--report` format and scoring](references/formal-report.md).

## Common Mistakes

- Running governance mid-implementation — best between phases or before releases.
- Accepting risk without `follow_up_action` — mandatory field.
- Exceeding 2 renewals — remediation becomes mandatory.

## Examples

### Example — pre-release compliance report

User: "generate a formal compliance report I can hand to auditors"

```
/ai-governance --report
```

Walks the compliance checks, scores against the rubric, emits a Markdown report with findings table, gate status, and verdict (PASS / WARN / FAIL). (`/ai-governance risk accept` instead records a risk-acceptance entry in `decision-store.json` with severity-based TTL, a mandatory `follow_up_action`, and a pre-push-consumed audit trail.)

## Integration

Called by: `/ai-verify` (governance-mode delegation); release gate `/ai-verify --release` checks governance status. CLI equivalents (non-interactive; the LLM performs checks directly): `ai-eng validate --category <mode>`, `ai-eng doctor`, `ai-eng maintenance risk-status`. Risk acceptances block pre-push when expired. Boundary: `/ai-pipeline` generates workflow files; `/ai-governance` validates the governance gates in them are enforced.

## Key Files

- `.ai-engineering/manifest.yml` — governance non-negotiables and quality thresholds.
- `state/decision-store.json` — risk acceptance records (decision records).
- `.ai-engineering/reference/risk-acceptance-flow.md` — DEC lineage and risk-acceptance lifecycle.

$ARGUMENTS
