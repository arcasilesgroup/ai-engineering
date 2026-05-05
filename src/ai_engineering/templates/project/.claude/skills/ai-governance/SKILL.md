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

Use the policy engine when a governance gate already exists, or can be expressed cleanly, as a `.rego` policy under `.ai-engineering/policies/` rather than ad-hoc procedural checks. Spec-122 Phase C swapped the in-tree mini-Rego interpreter for the upstream OPA binary; spec-123 finished wiring it into all three governance touchpoints (pre-commit, pre-push, `risk accept`).

Operational contract for this skill:

- Prefer existing policy files over re-implementing the same gate in skill prose.
- Treat the evaluator (`src/ai_engineering/governance/opa_runner.py`) as an implementation detail owned by the governance code, not by this skill.
- If a needed rule appears to require grammar or engine capabilities beyond what OPA supports, STOP and escalate to spec/implementation work instead of extending policy behavior inline from the skill.

For OPA invocation semantics, use `src/ai_engineering/governance/opa_runner.py`. For DEC lineage and risk-acceptance lifecycle details, use `.ai-engineering/contexts/risk-acceptance-flow.md`.

### Policy Decision Audit (spec-122/123)

Every OPA evaluation (allow or block) is recorded in the canonical state.db audit projection. Inspect recent decisions when investigating a blocked commit, push, or risk acceptance:

```bash
# Last 10 policy decisions, newest first
ai-eng audit query "
  SELECT created_at, source, policy, decision, deny_messages
  FROM events
  WHERE kind = 'policy_decision'
  ORDER BY created_at DESC
  LIMIT 10
"

# Filter to a single policy package
ai-eng audit query "
  SELECT created_at, source, decision, deny_messages
  FROM events
  WHERE kind = 'policy_decision' AND policy = 'risk_acceptance_ttl'
  ORDER BY created_at DESC
  LIMIT 20
"
```

The `events.kind = 'policy_decision'` rows are emitted by `src/ai_engineering/governance/decision_log.py::emit_policy_decision`. The `source` column carries one of `pre-commit`, `pre-push`, `risk-cmd` so you can scope the query to a single touchpoint.

### OPA Health (`ai-eng doctor`)

`ai-eng doctor` runs four advisory probes under the runtime stage:

- `opa-binary` — `shutil.which('opa')` returns a real path.
- `opa-version` — installed OPA is at or above 0.70.0 (the floor exercised in CI).
- `opa-bundle-load` — `opa eval --bundle` parses the three policies cleanly.
- `opa-bundle-signature` — `.signatures.json` accompanies `.manifest`.

Failures surface as `WARN` (advisory, non-blocking) so a missing OPA does not break diagnose runs in environments where governance is not yet bootstrapped.

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
- `.ai-engineering/policies/branch_protection.rego` -- branch-push policy (spec-122 Phase C).
- `.ai-engineering/policies/commit_conventional.rego` -- conventional-commits policy.
- `.ai-engineering/policies/risk_acceptance_ttl.rego` -- risk-acceptance TTL policy.
- `src/ai_engineering/governance/opa_runner.py` -- OPA subprocess wrapper.
- `src/ai_engineering/governance/decision_log.py` -- emits `kind='policy_decision'` events.
- `src/ai_engineering/policy/checks/opa_gate.py` -- shared deny-rule adapter.
- `src/ai_engineering/doctor/runtime/opa_health.py` -- advisory health probes.
- `.ai-engineering/contexts/risk-acceptance-flow.md` -- DEC lineage and risk-acceptance lifecycle.
  $ARGUMENTS
