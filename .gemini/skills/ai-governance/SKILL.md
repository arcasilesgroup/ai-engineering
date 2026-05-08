---
name: ai-governance
description: Validates framework compliance, ownership boundaries, risk acceptance lifecycle, and manifest integrity for regulated environments. Trigger for 'are quality gates enforced', 'who owns this file', 'formally accept a known risk', 'pre-release compliance check', 'governance report for auditors'. Not for code quality; use /ai-verify instead. Not for security scanning; use /ai-security instead — this validates governance process, not code content.
effort: max
argument-hint: "all|compliance|ownership|risk|integrity|--report"
tags: [governance, compliance, ownership, risk, integrity, enterprise]
mirror_family: gemini-skills
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

Compliance validation for regulated industries. Modes: `compliance` (quality gates), `ownership` (boundary verification), `risk` (decision-store lifecycle), `integrity` (framework consistency).

## When to Use

- Governance audit, pre-release check, post-install verification.
- NOT for code quality -- use `/ai-verify quality`.
- NOT for security scanning -- use `/ai-security`.

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Modes

### compliance -- Quality Gate Validation

Validate that rules in `CLAUDE.md`, `manifest.yml`, and boundaries in `CONSTITUTION.md` are enforced.

1. **Hook enforcement** -- verify required hooks exist in `.git/hooks/`, are executable, contain no `--no-verify` escapes.
2. **Check coverage** -- for each stack in `enforcement.checks`, confirm tool is configured and callable.
3. **Non-negotiables** -- walk `standards.non_negotiables`, trace enforcement chain: manifest -> hook -> CLAUDE.md.
4. **CI workflows** -- verify `enforcement.ci.required_workflows` exist under `.github/workflows/`.
5. **Security contract** -- gitleaks in pre-commit, semgrep in pre-push, dependency audit per stack.

### ownership -- Boundary Validation

Verify files live in correct ownership zones.

1. **Zone mapping** -- load `ownership.model` from manifest. Build zones: framework-managed, team-managed, project-managed, system-managed.
2. **File placement** -- scan `.ai-engineering/`, verify each file maps to exactly one zone.
3. **Modification history** -- `git log` framework-managed files, confirm only framework commits touched them.
4. **Update rule compliance** -- team/project paths never overwritten by automation.

### risk -- Risk Acceptance Lifecycle

Sub-modes: `accept`, `resolve`, `renew`.

**Accept**: record time-limited risk in `state.db` `decisions` table (spec-124 D-124-12).

- Classify finding, determine severity, register with mandatory `follow_up_action`.
- Auto-expiry: Critical 15d, High 30d, Medium 60d, Low 90d.

**Resolve**: close after remediation.

- Validate fix committed, scan clean, no regression.
- Mark `remediated` (preserved for audit trail, not deleted).

**Renew**: extend before expiry (max 2 renewals).

- Check eligibility (`renewal_count < 2`). Require justification.
- Create new decision with `renewed_from` reference.

### integrity -- Framework Consistency

Validate manifest claims match disk reality.

1. **Manifest counters** -- compare `governance_surface.agents.total` and `skills.total` against actual file counts.
2. **Agent-skill references** -- verify every path in agent `references.skills` resolves to an existing SKILL.md.
3. **State file schemas** -- confirm `state/` files are valid JSON/NDJSON with required keys.
4. **Command file existence** -- verify each SKILL.md has valid YAML frontmatter.

## Policy Engine Integration

Use OPA `.rego` policies under `.ai-engineering/policies/` over ad-hoc procedural checks. Spec-122 Phase C swapped the in-tree mini-Rego interpreter for upstream OPA; spec-123 wired it into pre-commit, pre-push, and `risk accept`.

- Prefer existing policy files over re-implementing the same gate.
- The evaluator (`src/ai_engineering/governance/opa_runner.py`) is owned by governance code, not by this skill.
- If a rule exceeds OPA's grammar, STOP and escalate to spec/implementation work.

Every OPA evaluation is recorded in the state.db audit projection. Inspect via `ai-eng audit query "SELECT created_at, source, policy, decision, deny_messages FROM events WHERE kind = 'policy_decision' ORDER BY created_at DESC LIMIT 10"`.

`ai-eng doctor` runs four advisory OPA probes (binary, version, bundle-load, bundle-signature). Failures surface as WARN (non-blocking).

### `--report` -- Formal Report

The `--report` flag can combine with any mode (e.g., `/ai-governance integrity --report`). Without a mode, it defaults to `compliance`.

Generate structured compliance report suitable for audit:

```markdown
# Governance Report: [mode]

## Score: N/100

## Verdict: PASS (>=90) | WARN (>=70) | FAIL (<70)

## Findings

| # | Severity | Category | Description | Location | Remediation |

## Gate Check

- Blocker: N (threshold: 0)
- Critical: N (threshold: 0)
```

Scoring: start at 100. Deduct: blocker -25, critical -15, major -5, minor -1. Floor at 0.

## Quick Reference

```
/ai-governance              # compliance mode (default)
/ai-governance all          # all modes
/ai-governance risk accept  # accept a new risk
/ai-governance risk resolve # close a remediated risk
/ai-governance integrity    # framework consistency check
/ai-governance --report     # generate formal report
```

## Common Mistakes

- Running governance mid-implementation -- best between phases or before releases.
- Accepting risk without `follow_up_action` -- mandatory field.
- Exceeding 2 renewals -- remediation becomes mandatory.

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

- **Called by**: `/ai-verify` (governance mode delegation)

- CLI layer: `ai-eng validate --category <mode>`, `ai-eng doctor`, `ai-eng maintenance risk-status`. The LLM performs checks directly by reading files and running tools. `ai-eng validate` and `ai-eng doctor` are CLI equivalents for non-interactive use.
- Risk acceptances block pre-push when expired.
- Release gate (`/ai-release-gate`) checks governance status.
- **Boundary**: `/ai-pipeline` generates workflow files; `/ai-governance` validates that governance gates are enforced in them

## References

- `.ai-engineering/manifest.yml` -- governance non-negotiables and quality thresholds.
- `state/state.db` -- risk acceptance records in `decisions` table (spec-124 D-124-12).
- `.ai-engineering/policies/branch_protection.rego` -- branch-push policy (spec-122 Phase C).
- `.ai-engineering/policies/commit_conventional.rego` -- conventional-commits policy.
- `.ai-engineering/policies/risk_acceptance_ttl.rego` -- risk-acceptance TTL policy.
- `src/ai_engineering/governance/opa_runner.py` -- OPA subprocess wrapper.
- `src/ai_engineering/governance/decision_log.py` -- emits `kind='policy_decision'` events.
- `src/ai_engineering/policy/checks/opa_gate.py` -- shared deny-rule adapter.
- `src/ai_engineering/doctor/runtime/opa_health.py` -- advisory health probes.
- `.ai-engineering/contexts/risk-acceptance-flow.md` -- DEC lineage and risk-acceptance lifecycle.
  $ARGUMENTS
