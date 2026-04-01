---
name: ai-review
description: "Use when code changes need human-quality judgment: PR reviews, file reviews, diff analysis, and architecture feedback. Trigger for 'review this', 'give me feedback', 'look over my PR', 'any issues with this', or 'is this merge-ready'. Default mode runs the full specialist roster through 3 macro-agents; use `--full` to run one agent per specialist. For evidence-backed gates, use /ai-verify instead."
effort: max
argument-hint: "[--full] [PR number or file paths]"
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

## Step 0: Load Stack Contexts

Follow `.ai-engineering/contexts/stack-context.md`. Apply loaded standards to all subsequent work.

## Profiles

### Default: `normal`

Runs the full specialist roster through 3 fixed macro-agents:

1. `correctness` + `testing` + `compatibility`
2. `security` + `backend` + `performance`
3. `architecture` + `maintainability` + `frontend` + `design`

All specialist lenses still run. The grouping controls cost only. Final output stays attributed by original specialist lens.

### Explicit: `--full`

Runs one agent per specialist with the same output contract and the same adversarial validation stage.

## Specialist Roster

| Specialist | Agent File | Focus |
|------------|-----------|-------|
| `security` | `reviewer-security.md` | vulnerabilities, auth, data exposure, dependency risk |
| `backend` | `reviewer-backend.md` | API boundaries, service logic, persistence, jobs |
| `performance` | `reviewer-performance.md` | query shape, complexity, hot paths, memory |
| `correctness` | `reviewer-correctness.md` | logic bugs, null handling, races, edge cases |
| `testing` | `reviewer-testing.md` | coverage, quality, edge cases, mocking patterns |
| `compatibility` | `reviewer-compatibility.md` | breaking changes, backwards compat, migrations |
| `architecture` | `reviewer-architecture.md` | necessity, patterns, reuse, proportionality |
| `maintainability` | `reviewer-maintainability.md` | complexity, readability, naming, duplication |
| `frontend` | `reviewer-frontend.md` | React, hooks, a11y, TypeScript (conditional) |
| `design` | `reviewer-design.md` | CSS, animation, UI components, visual design (conditional) |

All specialist agents are dispatched via the `Agent` tool from `.claude/agents/`. They are not read inline -- each runs in its own context window.

## Dispatch Architecture

### Pre-Review Phase
- **Context Explorer** (`review-context-explorer.md`): Dispatched via `Agent` tool. Gathers architectural context beyond the diff. Output is serialized and passed to every specialist.

### Specialist Phase
- **Normal mode**: 3 macro-agent dispatches via `Agent` tool. Each macro-agent receives the specialist instructions for its group + shared context.
- **Full mode**: 10 individual agent dispatches via `Agent` tool. Each specialist agent runs independently.

### Validation Phase
- **Finding Validator** (`review-finding-validator.md`): Dispatched via `Agent` tool. Receives ONLY the YAML finding blocks (no reasoning chain). Reads code fresh. Issues CONFIRMED or DISMISSED verdict per finding.

## Output Contract

Every report should:

- group findings by severity first and specialist lens second
- keep attribution by original specialist even in `normal`
- include `not_applicable` or `low_signal` outcomes when a specialist had little to contribute
- show which findings survived adversarial validation

## Common Mistakes

- Treating the 3 macro-agents in `normal` as reduced coverage. They are not.
- Reporting by macro-agent instead of original specialist lens.
- Skipping context exploration before review.
- Treating style preferences as blocking findings.
- Leaving findings unchallenged by the validator stage.
- Reading specialist agent files inline instead of dispatching via Agent tool.

## Handlers

### Orchestration
Load `handlers/review.md` for the main review dispatch logic.

### Language-Specific Review Criteria
For each language detected in the diff, load the corresponding handler for language-specific review criteria.

| Handler | Trigger | File |
|---------|---------|------|
| Generic | Default for unrecognized languages | `handlers/lang-generic.md` |
| C++ | `.cpp`, `.h`, `.hpp` files | `handlers/lang-cpp.md` |
| Flutter | `.dart` files | `handlers/lang-flutter.md` |
| Go | `.go` files | `handlers/lang-go.md` |
| Java | `.java` files | `handlers/lang-java.md` |
| Kotlin | `.kt` files | `handlers/lang-kotlin.md` |
| Python | `.py` files | `handlers/lang-python.md` |
| Rust | `.rs` files | `handlers/lang-rust.md` |
| TypeScript | `.ts`, `.tsx` files | `handlers/lang-typescript.md` |

## Integration

- **Called by**: user directly, `/ai-pr`, `/ai-dispatch`
- **Dispatches**: `review-context-explorer.md`, `reviewer-*.md`, `review-finding-validator.md` (all via Agent tool)
- **Read-only**: never modifies source code
- **See also**: after merge, `/ai-learn single <pr>` can extract review patterns

$ARGUMENTS
