---
name: ai-verify
description: Use when verification with evidence is needed — not assumptions. Trigger for 'check my code', 'is this ready to merge', 'run the tests', 'is coverage good enough', 'scan for security issues', 'does this meet our standards', 'prove it works'. Runs 7 scan modes (governance, security, quality, performance, a11y, feature, architecture). For narrative code review with human judgment, use /ai-review instead.
effort: max
argument-hint: "claim|governance|security|quality|performance|a11y|feature|architecture|platform"
mode: agent
---



# Verify

## Purpose

Evidence before claims. This skill has two faces: (1) a verification protocol that proves claims with commands, and (2) a multi-mode scanner for quality, security, and governance. Both share the same principle: run the command, read the output, check the exit code. No guessing.

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

### Scan Modes (7 parallel modes)

**CLI-backed** (run via `ai-eng verify <mode>`):

| Mode | Command | What it assesses |
|------|---------|------------------|
| `governance` | `/ai-verify governance` | Integrity, compliance, ownership boundaries |
| `security` | `/ai-verify security` | OWASP SAST, secret detection, dependency vulns |
| `quality` | `/ai-verify quality` | Coverage, complexity, duplication, lint |
| `platform` | `/ai-verify platform` | All 7 modes aggregated -> GO/NO-GO |

**Agentic** (invoked via skill argument, no CLI backing):

| Mode | Command | What it assesses |
|------|---------|------------------|
| `performance` | `/ai-verify performance` | N+1 queries, O(n^2), memory leaks, bundle size |
| `a11y` | `/ai-verify a11y` | WCAG 2.1 AA compliance |
| `feature` | `/ai-verify feature` | Spec vs code gaps, disconnected implementations |
| `architecture` | `/ai-verify architecture` | Drift, coupling, cohesion, boundaries |

Auto-detect: when invoked without a mode, infer from context.

**Delegation**: `security` mode delegates full execution to `/ai-security`. `governance` mode delegates full execution to `/ai-governance`. ai-verify acts as the entry point; the specialist skill owns the logic.

### Scan Output Contract

Every scan mode produces:

```markdown
## Score: N/100
## Verdict: PASS | WARN | FAIL

## Findings
| # | Severity | Category | Description | Location | Remediation |

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
| performance | N+1 in critical path | O(n^2) in hot path |
| architecture | Circular dependency | Critical drift from spec |
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
- Running a subset of tests instead of the full suite
- Ignoring warnings when exit code is 0
- Using forbidden words ("should work") instead of evidence
- Not checking exit codes
- Reporting coverage from memory instead of from the tool output

## Integration

- **Called by**: `/ai-dispatch` (post-task review), `ai-build agent` (after implementation), user directly
- **Calls**: stack-specific tools (pytest, ruff, gitleaks, etc.)
- **Delegates**: `/ai-security` (security mode), `/ai-governance` (governance mode)
- **Read-only**: never modifies source code -- produces findings with remediation

$ARGUMENTS
