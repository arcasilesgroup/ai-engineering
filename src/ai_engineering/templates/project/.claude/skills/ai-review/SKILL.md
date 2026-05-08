---
name: ai-review
description: "Reviews code changes with human-quality judgment: PR reviews, file reviews, diff analysis, architecture feedback. Default mode runs the full specialist roster through 3 macro-agents; pass `--full` for one agent per specialist. Trigger for 'review this', 'give me feedback', 'look over my PR', 'any issues with this', 'is this merge-ready'. Not for evidence-backed gates; use /ai-verify instead. Not for narrative writing; use /ai-write instead."
effort: max
argument-hint: "[--full] [PR number or file paths]"
---

# Review

## Quick start

```
/ai-review                      # normal: 3 macro-agents, validator stage
/ai-review --full               # one agent per specialist (8-10)
/ai-review 42                   # review PR #42
/ai-review src/auth/            # review specific paths
```

## Workflow

High-signal code review with full specialist coverage and aggressive false-positive control. `review` is review-only. This SKILL.md owns the user-facing contract; reviewer agent files provide specialist lenses and validation stages, not a competing surface.

1. **Step 0** — load contexts per `.ai-engineering/contexts/stack-context.md`.
2. **Detect target** — PR number, file paths, or current diff.
3. **Dependency preflight** — verify `.claude/skills/ai-review/handlers/review.md`, `reviewer-context.md`, `reviewer-validator.md`, plus required `.claude/agents/reviewer-*.md` files for the selected mode and detected diff scope (`frontend` conditional on UI work — covers React, hooks, animation, typography, forms, a11y). STOP and report exact missing path(s) — never paraphrase missing reviewer instructions inline.
4. **Pre-review** — dispatch `reviewer-context.md` via Agent tool; serialize output for every specialist.
5. **Specialists** — `normal` = 3 macro-agents; `--full` = one agent per specialist. Both run the full roster — grouping controls cost only.
6. **Validate** — dispatch `reviewer-validator.md` with YAML finding blocks only (no reasoning chain). Code is read fresh; verdict CONFIRMED or DISMISSED per finding.
7. **Emit** — Findings / Risks / Recommendations / Self-Challenge, attributed by original specialist lens.

## Dispatch threshold

Dispatch the `ai-review` agent for any narrative review (PR, branch, diff, or path scope). Each specialist runs in its own context window via the Agent tool. The agent file (`.claude/agents/ai-review.md`) is the orchestrator handle; profiles, roster, output contract, and validator stage live here.

## When to Use

- Before merging a PR
- After completing a feature
- When reviewing someone else's code
- When you need architecture-aware feedback instead of deterministic gates (use `/ai-verify` for evidence gates).

## Specialist Roster

| Specialist | Agent File | Focus |
| --- | --- | --- |
| `security` | `reviewer-security.md` | vulnerabilities, auth, data exposure, dependency risk |
| `backend` | `reviewer-backend.md` | API boundaries, service logic, persistence, jobs |
| `performance` | `reviewer-performance.md` | query shape, complexity, hot paths, memory |
| `correctness` | `reviewer-correctness.md` | logic bugs, null handling, races, edge cases |
| `testing` | `reviewer-testing.md` | coverage, quality, edge cases, mocking patterns |
| `compatibility` | `reviewer-compatibility.md` | breaking changes, backwards compat, migrations |
| `architecture` | `reviewer-architecture.md` | necessity, patterns, reuse, proportionality |
| `maintainability` | `reviewer-maintainability.md` | complexity, readability, naming, duplication |
| `frontend` | `reviewer-frontend.md` | React, hooks, a11y, TypeScript, animation, typography, forms (conditional; absorbs the legacy `design` lens per D-127-10) |

`normal` macro-agent grouping: (1) correctness + testing + compatibility, (2) security + backend + performance, (3) architecture + maintainability + frontend.

## Output Contract

Group findings by severity first, then specialist lens. Keep attribution by original specialist even in `normal`. Include `not_applicable` / `low_signal` outcomes when a specialist had little to contribute. Show which findings survived adversarial validation.

## Language Handlers

For each language detected in the diff, load the matching handler from `handlers/lang-{generic,cpp,flutter,go,java,kotlin,python,rust,typescript}.md` for language-specific review criteria.

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

Dispatches one agent per specialist (correctness, security, performance, architecture, testing, frontend, backend, maintainability, compatibility), runs the validator stage, deduplicates and ranks findings.

## Integration

Called by: user directly, `/ai-pr`, `/ai-build`, `/ai-autopilot` (Phase 5). Dispatches: `reviewer-context`, `reviewer-*`, `reviewer-validator` agents. Read-only: never modifies code. See also: `/ai-verify` (evidence-backed gates), `/ai-learn` (extract review patterns post-merge).

$ARGUMENTS
