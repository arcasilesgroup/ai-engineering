---
name: ai-verify
description: "Use when verification with evidence is needed — not assumptions. Trigger for 'check my code', 'is this ready to merge', 'run the tests', 'is coverage good enough', 'scan for security issues', 'does this meet our standards', 'prove it works'. Runs 4 specialists (deterministic, governance, architecture, feature) with `normal` implicit and `--full` explicit. For narrative code review with human judgment, use /ai-review instead."
effort: max
argument-hint: "claim|governance|security|quality|feature|architecture|platform [--full]"
---

# Verify

## Quick start

```
/ai-verify                      # normal: deterministic + LLM judgment
/ai-verify --full               # one agent per specialist
/ai-verify quality              # deterministic quality scan only
/ai-verify platform             # 4-specialist aggregate verdict
```

## Workflow

Evidence before claims. Two faces: (1) a verification protocol that proves claims with commands, and (2) a specialist verification surface that aggregates deterministic evidence into merge-readiness judgments. Same principle: run the command, read the output, check the exit code. No guessing. This SKILL.md owns the user-facing contract; verifier agent files provide specialist lenses and must not redefine mode semantics.

1. **Step 0** — load contexts per `.ai-engineering/contexts/stack-context.md`.
2. **Dependency preflight** — verify `.claude/skills/ai-verify/handlers/verify.md` plus required `.claude/agents/verify*-*.md` files exist for the selected mode (`normal` requires governance + architecture + feature; `--full` requires all four; individual modes require only the matching specialist). STOP and report exact missing path(s) — never improvise.
3. **Run protocol** — load `.ai-engineering/contexts/evidence-protocol.md` for the IRRV protocol; if unavailable, the only inline fallback is: per claim, identify command → run → capture output + exit code → classify CONFIRMED (exit 0 + expected) or REFUTED.
4. **Dispatch specialists** via the Agent tool (never read them inline). Output is always reported by original specialist lens.

## Dispatch threshold

Dispatch the `ai-verify` agent for any merge-readiness check, scan, or evidence-backed claim. Hand off via `Agent` tool — each specialist runs in its own context window. The agent file (`.claude/agents/ai-verify.md`) is the orchestrator handle; the procedural contract — modes, profiles, output contract — lives here.

## When to Use

- Before claiming "it works" (run the test, show the output)
- Before claiming "it's secure" (run the scan, show the findings)
- Before claiming "Done!" (verify every acceptance criterion with evidence)
- When running quality/security/governance scans on a codebase

## Specialist Roster & Modes

| Specialist | Agent File | Lens |
| --- | --- | --- |
| `deterministic` | `verify-deterministic.md` | Security, quality, dependencies, tests (tool-driven) |
| `governance` | `verifier-governance.md` | Compliance, ownership, gate enforcement (LLM) |
| `architecture` | `verifier-architecture.md` | Alignment, layer violations (LLM) |
| `feature` | `verifier-feature.md` | Spec coverage, acceptance criteria (LLM) |

| Mode | What runs |
| --- | --- |
| `normal` (implicit) | 2 macro-agents: deterministic first, then LLM judgment (gov+arch+feature in one) |
| `--full` | 4 individual specialists in parallel after deterministic |
| `quality` / `security` | Deterministic agent only (one scan slice) |
| `governance` / `architecture` / `feature` | That specialist only |
| `platform` | 4-specialist aggregate verdict |

Both profiles run the same four specialists — difference is grouping, not coverage. Deterministic always runs first and feeds every judgment path. See `handlers/verify.md` for orchestration.

## Output Contract

Every scan mode produces score / verdict (PASS/WARN/FAIL) / profile / specialist table / findings table grouped by specialist / gate check (blocker + critical thresholds).

| Mode | Blocker if… | Critical if… |
| --- | --- | --- |
| deterministic | Any secret detected, any test failure | Coverage < 80%, critical lint |
| governance | Any integrity FAIL | Any compliance FAIL |
| architecture | Circular dependency | Critical structural drift |
| feature | Spec goal missing | Acceptance criterion unmet |
| **platform** | Any blocker in ANY mode | Score < 60 |

## Verification Checklist (before claiming DONE)

- Every acceptance criterion verified with a command
- All tests pass (exact count reported)
- Lint/format clean (zero warnings)
- No secrets in staged files
- Coverage maintained or improved (exact % reported)
- No forbidden words used in the completion report

## Common Mistakes

- Claiming success without running the command
- Assuming `--full` adds specialist coverage instead of changing decomposition
- Pretending a specialist did not run instead of reporting `not applicable`
- Ignoring warnings when exit code is 0
- Using forbidden words ("should work") instead of evidence
- Reading specialist agent files inline instead of dispatching via Agent tool

## Examples

### Example 1 — pre-merge platform sweep

User: "is this branch ready to merge?"

```
/ai-verify platform
```

Dispatches all 4 specialist agents in parallel, aggregates findings, scores against the gate, returns PASS / WARN / FAIL with evidence per finding.

### Example 2 — quality-only sweep mid-implementation

User: "before I keep going, run the quality checks"

```
/ai-verify quality
```

Runs the deterministic specialist (lint, format, type-check, tests, coverage), reports findings inline so the build loop can fix in place.

## Integration

Called by: `/ai-dispatch` (post-task), `/ai-autopilot` (Phase 5), `/ai-build` (handoff), user directly. Dispatches: `verify-deterministic`, `verifier-governance`, `verifier-architecture`, `verifier-feature` agents. Read-only: never modifies code. See also: `/ai-review` (narrative review), `/ai-eval` (AI reliability over time).

$ARGUMENTS
