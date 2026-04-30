---
name: ai-verify
description: "Use when verification with evidence is needed — not assumptions. Trigger for 'check my code', 'is this ready to merge', 'run the tests', 'is coverage good enough', 'scan for security issues', 'does this meet our standards', 'prove it works'. Runs 4 specialists (deterministic, governance, architecture, feature) with `normal` implicit and `--full` explicit. For narrative code review with human judgment, use /ai-review instead."
effort: max
argument-hint: "claim|governance|security|quality|feature|architecture|platform [--full]"
---


# Verify

## Purpose

Evidence before claims. This skill has two faces: (1) a verification protocol that proves claims with commands, and (2) a specialist verification surface that aggregates deterministic evidence into merge-readiness judgments. Both share the same principle: run the command, read the output, check the exit code. No guessing. This SKILL.md owns the user-facing contract; verifier agent files provide specialist lenses and must not redefine mode semantics.

## When to Use

- Before claiming "it works" (run the test, show the output)
- Before claiming "it's secure" (run the scan, show the findings)
- Before claiming "Done!" (verify every acceptance criterion with evidence)
- When running quality/security/governance scans on a codebase

## Process

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Dependency Preflight

Before dispatching any verify agent, verify these files exist:

- `.claude/skills/ai-verify/handlers/verify.md`
- `.codex/agents/verify-deterministic.md`
- every required `.codex/agents/verifier-*.md` file for the selected mode

Required verifier files are mode-sensitive:

- `normal`: `verifier-governance.md`, `verifier-architecture.md`, and `verifier-feature.md` remain required because the judgment macro-agent still consumes those instructions.
- `--full`: one file per specialist (`verify-deterministic.md`, `verifier-governance.md`, `verifier-architecture.md`, `verifier-feature.md`).
- individual specialist modes: verify only the handler plus the exact specialist file(s) needed by the selected mode.

If any required file is missing: STOP and report the exact missing path(s). Never improvise missing handler or agent behavior.

### Verification Protocol (claim mode)

Load `.ai-engineering/contexts/evidence-protocol.md` for the IRRV evidence collection protocol.

If the evidence-protocol file is unavailable, use this inline process: for each claim, identify the verification command (test, lint, scan), run it, capture the output and exit code, and classify the claim as CONFIRMED (exit 0 + expected output) or REFUTED (non-zero exit or unexpected output). This is the only allowed inline fallback; it does not authorize improvising missing handlers or agent files.

### Specialist Surface

| Specialist      | Agent File                 | What it assesses                                           |
| --------------- | -------------------------- | ---------------------------------------------------------- |
| `deterministic` | `verify-deterministic.md`  | Security, quality, dependencies, tests (tool-driven)       |
| `governance`    | `verifier-governance.md`   | Compliance, ownership, gate enforcement (LLM judgment)     |
| `architecture`  | `verifier-architecture.md` | Solution-intent alignment, layer violations (LLM judgment) |
| `feature`       | `verifier-feature.md`      | Spec coverage, acceptance criteria (LLM judgment)          |

All specialist agents are dispatched via the `Agent` tool from `.codex/agents/`. They are not read inline -- each runs in its own context window.

### Dispatch Architecture

**Normal mode** (2 macro-agents):

1. **Deterministic** (runs first): Dispatched via Agent tool. Executes all tool-driven checks and produces structured evidence.
2. **LLM Judgment** (runs second, consumes deterministic output): Dispatched via Agent tool with governance + architecture + feature instructions. Uses deterministic evidence as input.

**Full mode** (4 individual agents):

1. Deterministic agent dispatched first
2. Governance, architecture, and feature agents dispatched in parallel, each receiving deterministic output

Both profiles run the same four specialists. The difference is grouping and parallelism, not coverage.

### Individual Specialist Modes

| Command                   | What it runs                                  |
| ------------------------- | --------------------------------------------- |
| `/ai-verify governance`   | Governance agent only                         |
| `/ai-verify security`     | Deterministic agent (security scan only)      |
| `/ai-verify architecture` | Architecture agent only                       |
| `/ai-verify quality`      | Deterministic agent (quality scan only)       |
| `/ai-verify feature`      | Feature agent only                            |
| `/ai-verify platform`     | All 4 specialists aggregated into one verdict |

### Profiles

- `normal` is implicit and covers all specialists through 2 fixed macro-agents.
- `--full` is explicit and runs the same specialists one per agent.
- Deterministic always runs first and feeds every judgment path.
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

| Mode          | Blocker if...                         | Critical if...                |
| ------------- | ------------------------------------- | ----------------------------- |
| deterministic | Any secret detected, any test failure | Coverage < 80%, critical lint |
| governance    | Any integrity FAIL                    | Any compliance FAIL           |
| architecture  | Circular dependency                   | Critical structural drift     |
| feature       | Spec goal missing                     | Acceptance criterion unmet    |
| **platform**  | Any blocker in ANY mode               | Score < 60                    |

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
- Assuming `--full` adds specialist coverage instead of changing decomposition
- Pretending a specialist did not run instead of reporting `not applicable`
- Ignoring warnings when exit code is 0
- Using forbidden words ("should work") instead of evidence
- Reading specialist agent files inline instead of dispatching via Agent tool

## Integration

- **Called by**: `/ai-dispatch` (post-task review), `ai-build` agent handoffs, user directly
- **Dispatches**: `verify-deterministic.md`, `verifier-governance.md`, `verifier-architecture.md`, `verifier-feature.md` (all via Agent tool)
- **Read-only**: never modifies source code -- produces findings with remediation

$ARGUMENTS
