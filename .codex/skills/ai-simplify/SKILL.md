---
name: ai-simplify
description: On-demand code simplification — guard clauses, method extraction, nesting flattening, dead code removal, conditional simplification. Behavior preserved; tests pass after every change. Scoped to operator-chosen files or current diff. No PR, no auto-commit. Trigger for 'simplify this file', 'reduce complexity here', 'clean up the in-flight diff', 'flatten this nesting'. Not for scheduled repo-wide sweeps — use /ai-simplify-sweep. Not for structural changes (file moves, renames) — use /ai-refactor.
effort: mid
argument-hint: "[paths|--diff] [--conservative|--aggressive]"
tags: [refactor, complexity, simplification]
model_tier: sonnet
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-simplify/SKILL.md
edit_policy: generated-do-not-edit
---



# Simplify

Discoverable wrapper around the `ai-simplify` agent: dispatches the agent via the Agent tool, validates after every change, applies the self-check protocol, and reports the simplifications made. On-demand only — there is no scheduling, no PR-opening side effect, no auto-commit. The complement of `/ai-simplify-sweep` (which IS scheduled, IS repo-wide, and DOES open a draft PR).

## Quick start

```
/ai-simplify                              # current diff, default aggressiveness
/ai-simplify src/auth/login.py            # scoped to a single file
/ai-simplify src/auth/ --conservative     # scoped to directory, conservative
/ai-simplify --diff --aggressive          # current diff, aggressive defaults
```

## Workflow

Principles applied: §10.1 KISS (the simplified version must actually be simpler — not just different; the self-check protocol enforces it); §10.7 Clean Code (names tell the story, functions do one thing well, cyclomatic complexity ≤8 per the engineering principles).

1. **Step 0** — load stack contexts: read `.ai-engineering/manifest.yml` `providers.stacks` and apply `.ai-engineering/overrides/<stack>/conventions.md` so the stack-specific linter is wired up before any edit.
2. **Detect target** — `$ARGUMENTS` resolves to one of: explicit paths, `--diff` (current staged changes), or empty (current diff is the default).
3. **Dependency preflight** — verify `.codex/agents/ai-simplify.md` is on disk. STOP and report the exact missing path if absent.
4. **Dispatch** — invoke the `ai-simplify` agent via the Agent tool with `{paths, aggressiveness}`. The agent runs in its own context window. The agent applies guard clauses, extracts methods, flattens nesting, removes dead code, simplifies conditionals — and validates after EVERY change (stack-specific linter + tests if fast).
5. **Self-check** — for each simplification the agent applies, the self-check protocol must answer favourably: (a) is the simplified version actually simpler, or just different? (b) would a newcomer find the new version easier to understand? (c) did the change introduce a new abstraction — and if so, does it earn its existence? (d) am I reducing complexity or just moving it somewhere else? Any unfavourable answer → revert.
6. **Render report** — emit the simplification report grouped by file, with columns `File | Change | Complexity Before | After | Lines Saved`.
7. **No PR, no commit** — `/ai-simplify` is the in-flight lane. The operator owns the next commit. (The scheduled `/ai-simplify-sweep` is the lane that opens a draft PR.)

## When to Use

- Mid-feature, when a function you just wrote feels deeper than it should be.
- After a code-review round that flagged complexity above the cyclomatic ≤10 or cognitive ≤15 threshold.
- When you want to reduce nesting or extract a helper before shipping the current diff.
- NOT for repo-wide entropy sweeps — those are `/ai-simplify-sweep` territory (scheduled, draft-PR, conservative-only).
- NOT for structural changes (moves, renames, splits) — that is refactor work, not simplification.

## Distinction from /ai-simplify-sweep

| Aspect | `/ai-simplify` (this skill) | `/ai-simplify-sweep` (existing) |
|---|---|---|
| Invocation | On-demand by operator | On-demand by operator (weekly cadence recommended) |
| Scope | Operator-chosen paths or current diff | Repo-wide sweep |
| PR behaviour | No PR (in-flight work) | Always opens draft PR |
| Auto-commit | No (operator owns next commit) | Yes (`/ai-commit` before PR) |
| Aggressiveness | Operator-chosen (`--conservative` / `--aggressive`) | Conservative-only |
| Telemetry | `framework_event kind=simplify_ondemand_run` | `framework_event kind=simplify_sweep_*` |

The two skills share the same `ai-simplify` agent engine. They differ in invocation cadence, scope, and post-conditions — not in the actual simplification logic.

## Output Contract

```markdown
## Simplification Report

| File | Change | Complexity Before | After | Lines Saved |
|------|--------|-------------------|-------|-------------|

### Summary
- Files simplified: N
- Total complexity reduction: N points
- Lines removed: N
- All tests passing: YES / NO
```

If `All tests passing: NO`, the skill MUST report the failing test, MUST NOT auto-revert the file (the operator decides whether to keep the partial simplification or roll back), and MUST emit `framework_event kind=simplify_test_regression` so the failure is auditable.

## Boundaries

- **Behaviour MUST be preserved** — same inputs produce same outputs.
- **Tests MUST pass** after every change; if a fast (<30s) test suite exists, run it after each file.
- **Never modifies test files** — tests are the immutable specification; simplification operates on production code only.
- **Never simplifies code already below thresholds** — there is no value in churning compliant code.
- **One file at a time, validate before moving to next** — never batch-apply across multiple files without intermediate validation.
- **External API signatures are immutable** — public function signatures, exported types, and CLI contracts are off-limits; only internals are refactored.
- **No new abstractions** — simplification reduces complexity in existing structure; it does NOT introduce protocols, base classes, or extension points (that is refactor / build territory).
- **No PR, no auto-commit** — the operator owns the resulting diff.

## Examples

### Example 1 — scoped simplification of a single file

User: "simplify src/auth/login.py — the nested if/else is hard to follow"

```
/ai-simplify src/auth/login.py
```

Skill dispatches the `ai-simplify` agent scoped to `src/auth/login.py`. The agent flags three opportunities: (1) the outer `if user is not None` can be inverted into an early-return guard clause, (2) the inner `if user.active` can also be a guard clause, (3) the trailing `else: return None` becomes unreachable. After each edit the agent runs `ruff check src/auth/login.py` + `ruff format --check`. The skill renders the report: 1 file simplified, 3 complexity points reduced, 8 lines removed, all tests passing.

### Example 2 — simplify the current in-flight diff

User: "simplify whatever I have staged before I open the PR"

```
/ai-simplify --diff --conservative
```

Skill dispatches the `ai-simplify` agent in conservative mode against `git diff --staged` output. The agent applies only the safest simplifications (guard clauses, dead-branch removal, single-call-site inlines) — no aggressive refactors. After each edit, validation runs. The skill renders the report. The operator reviews the diff and either commits or selectively rolls back. No PR is opened (that is `/ai-simplify-sweep`'s job).

## Integration

**Called by**: operators directly via `/ai-simplify` (ad-hoc, single-file or
diff-scoped). Not auto-invoked by any other skill.

**Calls**: the `ai-simplify` agent (`.codex/agents/ai-simplify.md`) via the
Agent tool with the operator-chosen scope. Validation runs after each edit;
the agent rolls back on test failure (behavior-preserving contract).

**See also**:
- `.codex/skills/ai-simplify-sweep/SKILL.md` — scheduled wrapper with draft-PR side effect (different cadence and contract).
- `.ai-engineering/manifest.yml` `quality` section — complexity thresholds the agent consults (cyclomatic ≤10, cognitive ≤15, nesting ≤3, method length ≤50).
- `.ai-engineering/overrides/<stack>/conventions.md` — stack overrides.
- Engineering anchors: CLAUDE.md §10.1 KISS, §10.7 Clean Code.
- D-134-07 (cohesion test — first-class agents must have a discoverable slash-skill).

$ARGUMENTS
