---
name: ai-governance
description: Validates framework compliance, ownership boundaries, risk acceptance lifecycle, and manifest integrity for regulated environments. Trigger for 'are quality gates enforced', 'who owns this file', 'formally accept a known risk', 'pre-release compliance check', 'governance report for auditors'. Not for code quality; use /ai-verify instead. Not for security scanning; use /ai-security instead — this validates governance process, not code content.
effort: max
argument-hint: "all|compliance|ownership|risk|integrity|--report"
tags: [governance, compliance, ownership, risk, integrity, enterprise]
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-governance/SKILL.md
edit_policy: generated-do-not-edit
---


# Governance

## Quick start

```
/ai-governance              # compliance mode (default)
/ai-governance all          # all four modes
/ai-governance risk accept  # accept a new risk (TTL by severity)
/ai-governance integrity    # framework consistency check
/ai-governance --report     # formal report (score + verdict)
```

## Workflow

Compliance validation for regulated industries. Default mode is `compliance`. Pick a mode, run the checks, surface findings; with `--report`, generate a scored audit document.

1. **compliance** — verify quality-gate enforcement (hooks, CI workflows, non-negotiables, security contract).
2. **ownership** — map files to ownership zones (framework / team / project / system); verify modification history.
3. **risk** — record / resolve / renew risk acceptances in `state.db.decisions` with severity-based TTL.
4. **integrity** — manifest counters vs disk reality; agent-skill cross-refs; state-file schemas.

> Detail: see [the four modes (compliance/ownership/risk/integrity)](references/modes.md), [OPA policy-engine integration](references/policy-engine.md), [`--report` format and scoring](references/formal-report.md).

## When to Use

- Governance audit, pre-release check, post-install verification.
- NOT for code quality — use `/ai-verify quality`.
- NOT for security scanning — use `/ai-security`.

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Common Mistakes

- Running governance mid-implementation — best between phases or before releases.
- Accepting risk without `follow_up_action` — mandatory field.
- Exceeding 2 renewals — remediation becomes mandatory.

## Examples

### Example 1 — pre-release compliance report

User: "generate a formal compliance report I can hand to auditors"

```
/ai-governance --report
```

Walks the compliance checks, scores against the rubric, emits a Markdown report with findings table, gate status, and verdict (PASS / WARN / FAIL).

### Example 2 — accept a known risk

User: "we've reviewed the gitleaks finding and want to accept it for 30 days"

```
/ai-governance risk accept
```

Records a risk-acceptance entry in `state.db.decisions` with severity-based TTL, mandatory `follow_up_action`, and an audit trail consumed by pre-push.

## Integration

- **Called by**: `/ai-verify` (governance mode delegation).
- CLI layer: `ai-eng validate --category <mode>`, `ai-eng doctor`, `ai-eng maintenance risk-status`. The LLM performs checks directly by reading files and running tools; `ai-eng validate` and `ai-eng doctor` are CLI equivalents for non-interactive use.
- Risk acceptances block pre-push when expired.
- Release gate (`/ai-verify --release`) checks governance status.
- **Boundary**: `/ai-pipeline` generates workflow files; `/ai-governance` validates that governance gates are enforced in them.

## Key Files

- `.ai-engineering/manifest.yml` — governance non-negotiables and quality thresholds.
- `state/state.db` — risk acceptance records in `decisions` table (spec-124 D-124-12).
- `.ai-engineering/contexts/risk-acceptance-flow.md` — DEC lineage and risk-acceptance lifecycle.

$ARGUMENTS
