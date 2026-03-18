---
name: integrity
version: 1.0.0
description: 'Comprehensive framework self-verification: sync, validate, doctor, governance,
  drift. Modes: full | quick | sync.'
argument-hint: full|quick|sync
tags: [integrity, verification, sync, validate, doctor, governance, drift]
---

# Integrity

## Purpose

Single entry point for framework self-verification. Orchestrates mirror sync, content validation, doctor diagnostics, governance scoring, and decision drift detection into one unified report with a GO/NO-GO verdict.

The framework has multiple verification tools (`ai-eng sync`, `ai-eng validate`, `ai-eng doctor`, `/ai-governance`). This skill runs them in sequence and produces a consolidated scorecard -- no need to remember which tool checks what.

## Trigger

- Command: `/ai-integrity [full|quick|sync]`
- Context: pre-release verification, post-install validation, periodic health audit, post-structural-change check.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"integrity"}'` at skill start. Fail-open -- skip if ai-eng unavailable.

> For a scored assessment with verdict as part of a broader verification, use `/ai-verify governance` instead.

## Modes

### full (default) -- Complete framework verification

Runs all 5 dimensions. Use before releases, after structural changes (new skills/agents), or for periodic audits.

### quick -- Fast structural check

Runs dimensions 1-2 only (sync + validate). No external tool invocation. Safe for CI and minimal environments.

### sync -- Mirror-only verification

Runs dimension 1 only. Use after editing canonical skill/agent definitions to verify mirrors are in sync.

## Procedure

### Step 1: Emit telemetry start

```
ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"integrity","mode":"<MODE>"}'
```

Fail-open -- skip if ai-eng unavailable.

### Step 2: Mirror Sync Check (all modes)

```
ai-eng sync --check
```

- Exit 0 = PASS (score: 100)
- Exit 1 = FAIL (score: 0) -- mirrors have drifted from canonical sources
- **Remediation**: `ai-eng sync` (run without --check to apply)

### Step 3: Content Validation (all modes except sync)

```
ai-eng validate --json
```

Parse JSON output for 7 category results: file-existence, mirror-sync, counter-accuracy, cross-reference, instruction-consistency, manifest-coherence, skill-frontmatter.

- Score: start at 100, deduct per FAIL (blocker -25, critical -15, major -5)
- **Remediation**: per-category specific (e.g., "Update manifest.yml skill count", "Fix cross-reference in agent definition")

### Step 4: Doctor Diagnostics (full mode only)

```
ai-eng doctor
```

Checks: layout, state files, hooks, venv, tools, branch policy, readiness.

- Score: start at 100, deduct per FAIL (-15) and WARN (-3)
- **Remediation**: `ai-eng doctor --fix-hooks`, `ai-eng doctor --fix-tools`

### Step 5: Governance Score (full mode only)

Reuse the validate output from Step 3. Do NOT re-run `ai-eng validate`.

Interpret the results using the governance scoring model: start at 100, deduct per finding by severity.

### Step 6: Drift Check (full mode only)

1. Read `state/decision-store.json`
2. Filter decisions with status `active` and category containing `architectural` or `risk-acceptance`
3. For each active decision, verify the code location still aligns with the decision's intent
4. Classify drift: none, minor (cosmetic), major (behavioral), critical (contradicts decision)

- Score: start at 100, deduct per drifted decision (critical -25, major -10, minor -3)
- **Remediation**: "Review decision DEC-XXX -- code has drifted from intent"

### Step 7: Aggregate and Report

Compute per-dimension scores. Overall score = min(all evaluated dimensions) -- weakest-link model.

- **PASS**: overall >= 90
- **WARN**: overall >= 60
- **FAIL**: overall < 60

Include current health trend from `state/health-history.json` (read-only).

Emit completion signal:
```
ai-eng signals emit scan_complete --actor=scan --detail='{"mode":"integrity","score":<N>,"verdict":"<VERDICT>"}'
```

## Output Contract

```markdown
# Integrity Report

## Overall: N/100 -- VERDICT
## Health Trend: [arrow] (from health-history.json)

| # | Dimension | Score | Verdict | Checks | Findings |
|---|-----------|-------|---------|--------|----------|
| 1 | Mirror Sync | N/100 | PASS/WARN/FAIL | N | N |
| 2 | Content Validation | N/100 | PASS/WARN/FAIL | N | N |
| 3 | Doctor Diagnostics | N/100 | PASS/WARN/FAIL | N | N |
| 4 | Governance Score | N/100 | PASS/WARN/FAIL | N | N |
| 5 | Decision Drift | N/100 | PASS/WARN/FAIL | N | N |

## Findings (if any)
| # | Severity | Dimension | Description | Location | Remediation |
|---|----------|-----------|-------------|----------|-------------|

## Remediation Plan
1. [Ordered fix steps, sequenced by dependency]

## Signals
{ "event": "integrity_check", "mode": "<mode>", "overall": N, "verdict": "PASS|WARN|FAIL", "dimensions": { "sync": N, "validate": N, "doctor": N, "governance": N, "drift": N }, "findings": { "blocker": N, "critical": N, "major": N, "minor": N }, "timestamp": "..." }
```

For `quick` mode, dimensions 3-5 show "-- (skipped)" and do not affect the overall score.
For `sync` mode, only dimension 1 is evaluated.

## When NOT to Use

- **Code quality issues** -- use `/ai-verify quality`. Integrity checks framework health, not code metrics.
- **Security vulnerabilities** -- use `/ai-verify security`. Integrity checks that security tools are configured, not what they find.
- **During active implementation** -- wait until a natural checkpoint. Mid-implementation state generates noise.
- **Single governance question** -- use `/ai-governance [mode]` for targeted checks.

## References

- `.agents/skills/governance/SKILL.md` -- governance validation modes (integrity, compliance, ownership, operational, risk, standards)
- `.agents/agents/ai-guard.md` -- proactive governance advisory and drift detection
- `.agents/agents/ai-verify.md` -- 7-mode assessment agent
- `standards/framework/core.md` -- governance structure, lifecycle, ownership
