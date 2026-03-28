---
name: ai-review
description: "Use when code changes need human-quality judgment: PR reviews, file reviews, diff analysis, and architecture feedback. Trigger for 'review this', 'give me feedback', 'look over my PR', 'any issues with this', or 'is this merge-ready'. Default mode runs the full specialist roster through 3 macro-agents; use `--full` to run one agent per specialist. For evidence-backed gates, use /ai-verify instead."
effort: max
argument-hint: "[--full] [PR number or file paths]"
mode: agent
---


# Review

## Purpose

High-signal code review with full specialist coverage and aggressive false-positive control.
`review` is review-only. It no longer owns `find` or `learn`.

## When to Use

- Before merging a PR
- After completing a feature
- When reviewing someone else's code
- When you need architecture-aware feedback instead of deterministic gates

## Step 0: Load Contexts

Follow `.ai-engineering/contexts/step-zero-protocol.md`. Apply loaded standards to all subsequent work.

## Profiles

### Default: `normal`

Runs the full specialist roster through 3 fixed macro-agents:

1. `correctness` + `testing` + `compatibility`
2. `security` + `backend` + `performance`
3. `architecture` + `maintainability` + `frontend`

All specialist lenses still run. The grouping controls cost only. Final output stays attributed by original specialist lens.

### Explicit: `--full`

Runs one agent per specialist with the same output contract and the same adversarial validation stage.

## Specialist Roster

| Specialist | Focus |
|------------|-------|
| `security` | vulnerabilities, auth, data exposure, dependency risk |
| `backend` | API boundaries, service logic, persistence, jobs, operational paths |
| `performance` | query shape, complexity, hot paths, memory and bundle pressure |
| `correctness` | logic bugs, null handling, races, edge cases |
| `testing` | missing tests, weak assertions, coverage of changed behavior |
| `compatibility` | public API breakage, migration risk, version expectations |
| `architecture` | boundaries, layering, coupling, drift from established patterns |
| `maintainability` | complexity, readability, naming, duplication, hidden coupling |
| `frontend` | UX states, accessibility, rendering, responsiveness |

## Internal Assets

- `handlers/review.md` is the single orchestration handler
- `context-explorer.md` gathers pre-review context before specialists run
- `finding-validator.md` adversarially challenges every emitted finding
- `reviewer-*.md` resources define the specialist review lenses
- `handlers/lang-*.md` remain the language-specific supplements for diff-aware review

## Output Contract

Every report should:

- group findings by severity first and specialist lens second
- keep attribution by original specialist even in `normal`
- include `not_applicable` or `low signal` outcomes when a specialist had little to contribute
- show which findings survived adversarial validation

## Common Mistakes

- Treating the 3 macro-agents in `normal` as reduced coverage. They are not.
- Reporting by macro-agent instead of original specialist lens.
- Skipping context exploration before review.
- Treating style preferences as blocking findings.
- Leaving findings unchallenged by the validator stage.

## Integration

- **Called by**: user directly, `/ai-pr`, `/ai-dispatch`
- **Calls**: `handlers/review.md`, `context-explorer.md`, `finding-validator.md`, `reviewer-*.md`, `handlers/lang-*.md`
- **Read-only**: never modifies source code

$ARGUMENTS
