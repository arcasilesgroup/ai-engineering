---
name: ai-review
description: "Reviews code changes with human-quality judgment: PR reviews, file reviews, diff analysis, architecture feedback. Default mode runs the full specialist roster through 3 macro-agents; pass `--full` for one agent per specialist. Trigger for 'review this', 'give me feedback', 'look over my PR', 'any issues with this', 'is this merge-ready'. Not for evidence-backed gates; use /ai-verify instead. Not for narrative writing; use /ai-write instead."
effort: max
argument-hint: "[--full] [PR number or file paths]"
mode: agent
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-review/SKILL.md
edit_policy: generated-do-not-edit
---


# Review

## Purpose

High-signal code review with full specialist coverage and aggressive false-positive control.
`review` is review-only. It no longer owns `find` or `learn`.
This SKILL.md owns the user-facing contract; reviewer agent files provide specialist lenses and validation stages, not a competing surface.

## When to Use

- Before merging a PR
- After completing a feature
- When reviewing someone else's code
- When you need architecture-aware feedback instead of deterministic gates

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Dependency Preflight

Before dispatching any review agent, verify these files exist:

- `.github/skills/ai-review/handlers/review.md`
- `.github/agents/review-context-explorer.md`
- `.github/agents/review-finding-validator.md`
- every required `.github/agents/reviewer-*.md` file for the selected mode and detected diff scope

Required reviewer files are mode-sensitive:

- `normal`: the three macro-agents still depend on the underlying reviewer files for `correctness`, `testing`, `compatibility`, `security`, `backend`, `performance`, `architecture`, and `maintainability`, plus `frontend` and `design` when the diff includes frontend/UI work.
- `--full`: one file per specialist lens, with the same conditional `frontend` and `design` behavior.

If any required file is missing: STOP and report the exact missing path(s). Never paraphrase missing reviewer instructions inline.

## Workflow

1. Detect target (PR number, file paths, or current diff).
2. Pick profile (`normal` = 3 macro-agents; `--full` = 8 specialist agents).
3. Dispatch agents in parallel via the Agent tool.
4. Aggregate findings, deduplicate, classify by severity, apply false-positive control.
5. Emit the structured output contract (Findings / Risks / Recommendations / Self-Challenge).

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

| Specialist        | Agent File                    | Focus                                                      |
| ----------------- | ----------------------------- | ---------------------------------------------------------- |
| `security`        | `reviewer-security.md`        | vulnerabilities, auth, data exposure, dependency risk      |
| `backend`         | `reviewer-backend.md`         | API boundaries, service logic, persistence, jobs           |
| `performance`     | `reviewer-performance.md`     | query shape, complexity, hot paths, memory                 |
| `correctness`     | `reviewer-correctness.md`     | logic bugs, null handling, races, edge cases               |
| `testing`         | `reviewer-testing.md`         | coverage, quality, edge cases, mocking patterns            |
| `compatibility`   | `reviewer-compatibility.md`   | breaking changes, backwards compat, migrations             |
| `architecture`    | `reviewer-architecture.md`    | necessity, patterns, reuse, proportionality                |
| `maintainability` | `reviewer-maintainability.md` | complexity, readability, naming, duplication               |
| `frontend`        | `reviewer-frontend.md`        | React, hooks, a11y, TypeScript (conditional)               |
| `design`          | `reviewer-design.md`          | CSS, animation, UI components, visual design (conditional) |

All specialist agents are dispatched via the `Agent` tool from `.github/agents/`. They are not read inline -- each runs in its own context window.

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

| Handler    | Trigger                            | File                          |
| ---------- | ---------------------------------- | ----------------------------- |
| Generic    | Default for unrecognized languages | `handlers/lang-generic.md`    |
| C++        | `.cpp`, `.h`, `.hpp` files         | `handlers/lang-cpp.md`        |
| Flutter    | `.dart` files                      | `handlers/lang-flutter.md`    |
| Go         | `.go` files                        | `handlers/lang-go.md`         |
| Java       | `.java` files                      | `handlers/lang-java.md`       |
| Kotlin     | `.kt` files                        | `handlers/lang-kotlin.md`     |
| Python     | `.py` files                        | `handlers/lang-python.md`     |
| Rust       | `.rs` files                        | `handlers/lang-rust.md`       |
| TypeScript | `.ts`, `.tsx` files                | `handlers/lang-typescript.md` |

## Examples

### Example 1 — review a PR before approval

User: "review PR #42"

```
/ai-review 42
```

Dispatches the 3 macro-agents (correctness, design, security/perf) over the diff, aggregates findings with corroboration, emits the Findings table with severity + remediation.

### Example 2 — full-coverage review on a complex diff

User: "do the full reviewer roster on this branch"

```
/ai-review --full
```

Dispatches one agent per specialist (correctness, design, security, performance, architecture, testing, frontend, backend), runs the validator stage, deduplicates and ranks findings.

## Integration

Called by: user directly, `/ai-pr`, `/ai-dispatch`, `/ai-autopilot` (Phase 5). Dispatches: `review-context-explorer`, `reviewer-*`, `review-finding-validator` agents. Read-only: never modifies code. See also: `/ai-verify` (evidence-backed gates), `/ai-learn` (extract review patterns post-merge).

$ARGUMENTS
