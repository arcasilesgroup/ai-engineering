---
name: ai-verify
description: "Use when verification with evidence is needed — not assumptions. Trigger for 'check my code', 'is this ready to merge', 'run the tests', 'is coverage good enough', 'scan for security issues', 'does this meet our standards', 'prove it works'. Runs 7 specialists (governance, security, architecture, quality, performance, a11y, feature) with `normal` implicit and `--full` explicit for the expensive platform pass. For narrative code review with human judgment, use /ai-review instead."
effort: max
argument-hint: "claim|governance|security|quality|performance|a11y|feature|architecture|platform [--full]"
---


# Verify

## Purpose

Evidence before claims. This skill has two faces: (1) a verification protocol that proves claims with commands, and (2) a specialist verification surface that aggregates deterministic evidence into merge-readiness judgments. Both share the same principle: run the command, read the output, check the exit code. No guessing.

## When to Use

- Before claiming "it works" (run the test, show the output)
- Before claiming "it's secure" (run the scan, show the findings)
- Before claiming "Done!" (verify every acceptance criterion with evidence)
- When running quality/security/governance scans on a codebase

## Process

### Step 0: Load Contexts

Follow `.ai-engineering/contexts/step-zero-protocol.md`. Apply loaded standards to all subsequent work.

### Verification Protocol (claim mode)

Load `.ai-engineering/contexts/evidence-protocol.md` for the IRRV evidence collection protocol.

### Specialist Modes

| Specialist | Command | What it assesses |
|------------|---------|------------------|
| `governance` | `/ai-verify governance` | Integrity, compliance, ownership boundaries |
| `security` | `/ai-verify security` | Secrets, dependency vulns, security tooling |
| `architecture` | `/ai-verify architecture` | Cycles, boundary drift, structural issues |
| `quality` | `/ai-verify quality` | Lint, duplication, quality gates |
| `performance` | `/ai-verify performance` | Benchmark/perf evidence and hotspot signal |
| `a11y` | `/ai-verify a11y` | Accessibility applicability and UI checks |
| `feature` | `/ai-verify feature` | Spec/plan completeness and handoff readiness |
| `platform` | `/ai-verify platform` | All 7 specialists aggregated into one verdict |

### Profiles

- `normal` is implicit and covers all 7 specialists through 2 fixed macro-agents:
  - `macro-agent-1`: governance, security, architecture
  - `macro-agent-2`: quality, performance, a11y, feature
- `--full` is explicit and runs the same 7 specialists one per agent.
- Output is always reported by original specialist lens, not by macro-agent bucket.

See `handlers/verify.md` for the orchestration contract.

### Scan Output Contract

Every scan mode produces:

```markdown
## Score: N/100
## Verdict: PASS | WARN | FAIL
## Profile: normal | full

## Specialists
| Specialist | Runner | Verdict | Score | Applicability |

## Findings (grouped by specialist)
| # | Severity | Category | Description | Location |

## Gate Check
- Blocker findings: N (threshold: 0)
- Critical findings: N (threshold: 0)
```

### Scan Thresholds

| Mode | Blocker if... | Critical if... |
|------|--------------|----------------|
| governance | Any integrity FAIL | Any compliance FAIL |
| security | Critical/high CVE | Any secret detected |
| quality | Coverage < 80% | Blocker/critical lint |
| performance | Benchmark regression with evidence | No trustworthy performance evidence path |
| architecture | Circular dependency | Critical structural drift |
| **platform** | Any blocker in ANY mode | Score < 60 |

## Verification Checklist (use before claiming DONE)

```
- [ ] Every acceptance criterion verified with a command
- [ ] All tests pass (exact count reported)
- [ ] Lint/format clean (zero warnings)
- [ ] No secrets in staged files
- [ ] Coverage maintained or improved (exact % reported)
- [ ] No forbidden words used in the completion report
```

## Common Mistakes

- Claiming success without running the command
- Pretending a specialist did not run instead of reporting `not applicable`
- Ignoring warnings when exit code is 0
- Using forbidden words ("should work") instead of evidence
- Not checking exit codes
- Reporting coverage or scan results from memory instead of from the tool output

## Integration

- **Called by**: `/ai-dispatch` (post-task review), `ai-build` agent handoffs, user directly
- **Calls**: stack-specific tools (ruff, gitleaks, pip-audit, integrity validator, structural analysis)
- **Read-only**: never modifies source code -- produces findings with remediation and evidence-backed summaries

$ARGUMENTS
