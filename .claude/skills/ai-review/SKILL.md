---
name: ai-review
description: "Reviews code changes with human-quality judgment: PR reviews, file reviews, diff analysis, architecture feedback. Default mode runs the full specialist roster through 3 macro-agents; pass `--full` for one agent per specialist. Trigger for 'review this', 'give me feedback', 'look over my PR', 'any issues with this', 'is this merge-ready'. Not for evidence-backed gates; use /ai-verify instead. Not for narrative writing; use /ai-prose instead."
effort: mid
model_tier: sonnet
argument-hint: "[--full] [PR number or file paths]"
---

# Review

## Quick start

```
/ai-review                      # normal: 3 macro-agents, validator stage
/ai-review --full               # one agent per specialist (6 post-W3)
/ai-review 42                   # review PR #42
/ai-review src/auth/            # review specific paths
```

## Workflow

High-signal code review with full specialist coverage and aggressive false-positive control. `review` is review-only. This SKILL.md owns the user-facing contract; reviewer agent files provide specialist lenses and validation stages, not a competing surface.

1. **Step 0** — load stack contexts: read `.ai-engineering/manifest.yml` `providers.stacks` and apply `.ai-engineering/overrides/<stack>/conventions.md` for each stack.
2. **Detect target** — PR number, file paths, or current diff.
3. **Dependency preflight** — verify `review-context.md`, `review-validator.md`, plus required `.claude/agents/reviewer-*.md` files for the selected mode and detected diff scope (`frontend` conditional on UI work — covers React, hooks, animation, typography, forms, a11y). STOP and report exact missing path(s) — never paraphrase missing reviewer instructions inline.
4. **Pre-review** — dispatch `review-context.md` via Agent tool; serialize output for every specialist.
5. **Specialists** — `normal` = 3 macro-agents; `--full` = one agent per specialist. Both run the full roster — grouping controls cost only.
6. **Validate** — dispatch `review-validator.md` with YAML finding blocks only (no reasoning chain). Code is read fresh; verdict CONFIRMED or DISMISSED per finding.
7. **Emit** — Findings / Risks / Recommendations / Self-Challenge, attributed by original specialist lens.

## Dispatch threshold

Dispatch the `ai-review` agent for any narrative review (PR, branch, diff, or path scope). Each specialist runs in its own context window via the Agent tool. The agent file (`.claude/agents/ai-review.md`) is the orchestrator handle; profiles, roster, output contract, and validator stage live here.

## When to Use

- Before merging a PR
- After completing a feature
- When reviewing someone else's code
- When you need architecture-aware feedback instead of deterministic gates (use `/ai-verify` for evidence gates).

## Specialist Roster

Spec-140 W3 collapsed the roster from 11 specialists to 6. `reviewer-architecture` (DRY/reuse/proportionality) and `reviewer-maintainability` (readability/naming) heuristics are absorbed into `reviewer-correctness`. `reviewer-backend` was deleted outright (categorically mismatched: this repo is a Python CLI, no separate backend tier).

| Specialist | Agent File | Focus |
| --- | --- | --- |
| `correctness` | `reviewer-correctness.md` | logic bugs, null handling, races, edge cases + absorbed architecture (DRY/reuse/proportionality) + maintainability (readability/naming) lenses |
| `security` | `reviewer-security.md` | vulnerabilities, auth, data exposure, dependency risk |
| `testing` | `reviewer-testing.md` | coverage, quality, edge cases, mocking patterns |
| `performance` | `reviewer-performance.md` | query shape, complexity, hot paths, memory |
| `frontend` | `reviewer-frontend.md` | React, hooks, a11y, TypeScript, animation, typography, forms (conditional; absorbs the legacy `design` lens per D-127-10) |
| `compatibility` | `reviewer-compatibility.md` | breaking changes, backwards compat, migrations |

`normal` macro-agent grouping: (1) correctness + testing + compatibility, (2) security + performance, (3) frontend (conditional on UI diff; merges with macro-agent-2 when not dispatched).

## Output Contract

Group findings by severity first, then specialist lens. Keep attribution by original specialist even in `normal`. Include `not_applicable` / `low_signal` outcomes when a specialist had little to contribute. Show which findings survived adversarial validation.

## Stack-specific review guidance

spec-133 D-133-10 consolidates stack-specific review guidance into the
`.ai-engineering/overrides/<stack>/review.md` files. For each stack
detected in the diff, load `overrides/<stack>/review.md`. Greenfield
mode (stacks=[]): use generic review criteria + hint
"add a project file and run `ai-eng doctor --fix`".

## Common Mistakes

- Treating the 3 macro-agents in `normal` as reduced coverage — they are not.
- Reporting by macro-agent instead of original specialist lens.
- Skipping context exploration before review, or skipping the validator stage.
- Treating style preferences as blocking findings.
- Reading specialist agent files inline instead of dispatching via Agent tool.

## Examples

### Example 1 — review a PR before approval

User: "review PR #42"

```
/ai-review 42
```

Dispatches the 3 macro-agents (correctness, frontend, security/perf) over the diff, aggregates findings with corroboration, emits the Findings table with severity + remediation.

### Example 2 — full-coverage review on a complex diff

User: "do the full reviewer roster on this branch"

```
/ai-review --full
```

Dispatches one agent per specialist (correctness, security, testing, performance, frontend, compatibility — 6 post-W3), runs the validator stage, deduplicates and ranks findings.

## Integration

Called by: user directly, `/ai-pr`, `/ai-build`, `/ai-autopilot` (Phase 5). Dispatches: `review-context`, `reviewer-*`, `review-validator` agents. Read-only: never modifies code. See also: `/ai-verify` (evidence-backed gates), `/ai-learn` (extract review patterns post-merge).

$ARGUMENTS
