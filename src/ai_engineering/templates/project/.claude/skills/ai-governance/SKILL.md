---
name: ai-governance
description: "Use for framework compliance validation, ownership boundary checks, risk acceptance lifecycle, and manifest integrity verification. Trigger for 'are quality gates enforced?', 'who owns this?', 'formally accept a known risk', 'is the framework consistent?', 'pre-release compliance check', 'governance report for auditors'. Complements /ai-security (scanning) — this validates governance process, not code content."
effort: max
argument-hint: "all|compliance|ownership|risk|integrity|--report"
tags: [governance, compliance, ownership, risk, integrity, enterprise]
---


# Governance

Compliance validation for regulated industries. Modes: `compliance` (quality gates), `ownership` (boundary verification), `risk` (decision-store lifecycle), `integrity` (framework consistency). Default: compliance.

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

**Accept**: record time-limited risk in `decision-store.json`.
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

Spec-110 Phase 3 ships a Rego-subset evaluator at
`src/ai_engineering/governance/policy_engine.py`. Use it whenever a gate
can be expressed as a `.rego` rule under `.ai-engineering/policies/` rather
than ad-hoc Python.

### Active Policies

| Policy file | Input shape | Purpose |
|-------------|-------------|---------|
| `branch_protection.rego` | `{"branch": str, "action": str}` | Deny pushes to `main`/`master`. |
| `commit_conventional.rego` | `{"subject": str}` | Require Conventional Commits subject. |
| `risk_acceptance_ttl.rego` | `{"now": RFC-3339, "ttl_expires_at": RFC-3339}` | Allow only while not expired. |

### Invocation

```python
from pathlib import Path
from ai_engineering.governance.policy_engine import evaluate, Decision

policy = Path(".ai-engineering/policies/branch_protection.rego")
decision: Decision = evaluate(policy, {"branch": "main", "action": "push"})
if not decision.allow:
    raise SystemExit(f"governance gate failed: {decision.reason}")
```

The first firing `allow if` wins; otherwise the first firing `deny if`
wins (its message becomes `reason`); otherwise `default allow := <bool>`
applies.

### Engine Scope (per D-110-04)

The evaluator is a *subset* of OPA Rego, not a full OPA daemon -- this
avoids a Go runtime in CI and Claude hooks. New policies must stay in
grammar: `package`/`default allow`, `allow if`/`deny[<msg>] if`/`deny if`,
`input.<dotted.path>`, literals (numbers, bools, `null`, strings),
comparisons (`==`/`!=`/`<`/`<=`/`>`/`>=`), boolean ops (`and`/`or`/`not`)
with parentheses, and built-ins `regex.match` and `time.parse_rfc3339_ns`.
Anything outside raises `PolicyError`; escalate per spec-110 R-4 instead
of extending silently. Cover new policies with `tests/unit/governance/`
and update the Active Policies table.

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

## Integration

- **Called by**: `/ai-verify` (governance mode delegation)

- CLI layer: `ai-eng validate --category <mode>`, `ai-eng doctor`, `ai-eng maintenance risk-status`. The LLM performs checks directly by reading files and running tools. `ai-eng validate` and `ai-eng doctor` are CLI equivalents for non-interactive use.
- Risk acceptances block pre-push when expired.
- Release gate (`/ai-release-gate`) checks governance status.
- **Boundary**: `/ai-pipeline` generates workflow files; `/ai-governance` validates that governance gates are enforced in them

## References

- `.ai-engineering/manifest.yml` -- governance non-negotiables and quality thresholds.
- `state/decision-store.json` -- risk acceptance records.
- `.ai-engineering/policies/branch_protection.rego` -- branch-push policy (spec-110 Phase 3).
- `.ai-engineering/policies/commit_conventional.rego` -- conventional-commits policy.
- `.ai-engineering/policies/risk_acceptance_ttl.rego` -- risk-acceptance TTL policy.
- `src/ai_engineering/governance/policy_engine.py` -- Rego-subset evaluator (spec-110 T-3.8..T-3.10).
- `.ai-engineering/specs/spec-110-governance-v3-harvest.md` -- lineage and D-110-04.
$ARGUMENTS
