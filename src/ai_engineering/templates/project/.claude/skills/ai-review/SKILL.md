---
name: ai-review
description: "Reviews code changes with human-quality judgment: PR reviews, file reviews, diff analysis, architecture feedback. Default mode runs the full specialist roster through 3 macro-agents; pass `--full` for one agent per specialist. Trigger for 'review this', 'give me feedback', 'look over my PR', 'any issues with this', 'is this merge-ready'. Not for evidence-backed gates; use /ai-verify instead. Not for narrative writing; use /ai-prose instead."
effort: mid
argument-hint: "[--full] [PR number or file paths]"
---

# Review

Reviews code changes with human-quality judgment — PR reviews, file reviews, diff analysis, architecture feedback — dispatching a full specialist roster through macro-agents with aggressive false-positive control. Use it for "review this", "look over my PR", or "is this merge-ready".

## Workflow

Principles applied: §10.7 Clean Code (readability, naming, single-responsibility); §10.4 DRY (flag duplication and missed reuse). High-signal review with full specialist coverage and aggressive false-positive control. This SKILL.md owns the user-facing contract; reviewer agent files provide specialist lenses and validation stages.

1. **Step 0 — load contexts** — read `.ai-engineering/manifest.yml` `providers.stacks`; apply `.ai-engineering/overrides/<stack>/conventions.md` per stack.
2. **Detect target** — PR number, file paths, or current diff.
3. **Dependency preflight** — verify `review-context.md`, `review-validator.md`, plus the `.claude/agents/reviewer-*.md` files the selected mode + diff scope need (`frontend` conditional on UI work — React, hooks, animation, typography, forms, a11y). STOP and report the exact missing path — never paraphrase reviewer instructions inline.
4. **Pre-review** — dispatch `review-context.md` via the Agent tool; serialize its output for every specialist.
5. **Specialists** — `normal` = 3 macro-agents; `--full` = one agent per specialist. Both run the full roster — grouping controls cost only.
6. **Validate** — dispatch `review-validator.md` with YAML finding blocks only (no reasoning chain). Code is read fresh; verdict CONFIRMED or DISMISSED per finding.
7. **Emit** — Findings / Risks / Recommendations / Self-Challenge, attributed by original specialist lens.

## Dispatch threshold

Dispatch the `ai-review` agent for any narrative review over ≥ 1 changed file (PR, branch, diff, or path scope). Each specialist runs in its own context window via the Agent tool. `.claude/agents/ai-review.md` is the orchestrator handle; profiles, roster, output contract, and validator stage live here.

## Specialist Roster

Spec-140 W3 collapsed the roster from 11 specialists to 6. `reviewer-architecture` (DRY/reuse/proportionality) and `reviewer-maintainability` (readability/naming) are absorbed into `reviewer-correctness`. `reviewer-backend` was deleted (this repo is a Python CLI, no separate backend tier).

| Specialist | Agent File | Focus |
| --- | --- | --- |
| `correctness` | `reviewer-correctness.md` | logic bugs, null handling, races, edge cases + absorbed architecture (DRY/reuse) + maintainability (readability/naming) |
| `security` | `reviewer-security.md` | vulnerabilities, auth, data exposure, dependency risk |
| `testing` | `reviewer-testing.md` | coverage, quality, edge cases, mocking patterns |
| `performance` | `reviewer-performance.md` | query shape, complexity, hot paths, memory |
| `frontend` | `reviewer-frontend.md` | React, hooks, a11y, TypeScript, animation, typography, forms (conditional; absorbs legacy `design` lens, D-127-10) |
| `compatibility` | `reviewer-compatibility.md` | breaking changes, backwards compat, migrations |

`normal` macro-agent grouping: (1) correctness + testing + compatibility, (2) security + performance, (3) frontend (conditional on UI diff; merges with macro-agent-2 when not dispatched).

## Output Contract

Group findings by severity first, then original specialist lens (keep attribution even in `normal`). Include `not_applicable` / `low_signal` outcomes where a specialist had little to contribute. Show which findings survived adversarial validation.

## Stack-specific review guidance

For each stack in the diff, load `.ai-engineering/overrides/<stack>/review.md` (D-133-10). Greenfield mode (stacks=[]): use generic review criteria + hint "add a project file and run `ai-eng doctor --fix`".

## Common Mistakes

- Treating the 3 macro-agents in `normal` as reduced coverage — they are not.
- Reporting by macro-agent instead of original specialist lens.
- Treating style preferences as blocking findings.
- Reading specialist agent files inline instead of dispatching via the Agent tool.

## Examples

### Example — review a PR before approval

User: "review PR #42"

```
/ai-review 42
```

Dispatches the 3 macro-agents (correctness/testing/compat, security/perf, conditional frontend) over the diff, aggregates findings with corroboration, runs the validator stage, and emits the Findings table with severity + remediation.

## Integration

Called by: user directly, `/ai-pr`, `/ai-build`, `/ai-autopilot` (Phase 5). Dispatches: `review-context`, `reviewer-*`, `review-validator` agents. Read-only: never modifies code. See also: `/ai-verify` (evidence-backed gates), `/ai-learn` (extract review patterns post-merge).

**Inline fallback.** Agent-tool dispatch is the primary path. On a harness without a subagent/Agent-tool primitive, execute this skill by reading the specialist agent file(s) (`review-context.md`, the selected `reviewer-*.md`, `review-validator.md`) inline and running their steps in-context, sequentially — inline-sequential is the floor, not a substitute for the dispatch when it is available.

$ARGUMENTS
