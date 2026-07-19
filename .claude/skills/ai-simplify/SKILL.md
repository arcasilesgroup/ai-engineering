---
name: ai-simplify
description: "On-demand code simplification — guard clauses, method extraction, nesting flattening, dead code removal, conditional simplification. Behavior preserved; tests pass after every change. Scoped to operator-chosen files or current diff. No PR, no auto-commit. Trigger for 'simplify this file', 'reduce complexity here', 'clean up the in-flight diff', 'flatten this nesting'. Not for scheduled repo-wide sweeps — use /ai-simplify-sweep. Not for structural changes (file moves, renames) — use /ai-refactor."
effort: mid
argument-hint: "[paths|--diff] [--conservative|--aggressive]"
tags: [refactor, complexity, simplification]
---

# Simplify

Discoverable wrapper around the `ai-simplify` agent: dispatches it via the Agent tool, validates after every change, applies the self-check protocol, and reports the simplifications made. On-demand only — no scheduling, no PR, no auto-commit (the complement of `/ai-simplify-sweep`, which IS scheduled, repo-wide, and opens a draft PR).

## Quick start

```
/ai-simplify                              # current diff, default aggressiveness
/ai-simplify src/auth/login.py            # scoped to a single file
/ai-simplify src/auth/ --conservative     # scoped to directory, conservative
/ai-simplify --diff --aggressive          # current diff, aggressive
```

## Workflow

Principles applied: §10.1 KISS (the simplified version must actually be simpler — not just different); §10.7 Clean Code (names tell the story, functions do one thing, cyclomatic complexity ≤ 8).

1. **Step 0 — load contexts** — read `.ai-engineering/manifest.yml` `providers.stacks`; apply `.ai-engineering/overrides/<stack>/conventions.md` so the stack linter is wired before any edit.
2. **Detect target** — `$ARGUMENTS` resolves to explicit paths, `--diff` (staged changes), or empty (current diff, the default).
3. **Dependency preflight** — verify `.claude/agents/ai-simplify.md` exists. STOP and report the exact missing path if absent.
4. **Dispatch** — invoke the `ai-simplify` agent via the Agent tool with `{paths, aggressiveness}`. It applies guard clauses, extracts methods, flattens nesting, removes dead code, simplifies conditionals — validating after EVERY change (stack linter + fast tests).
5. **Self-check** (per simplification; any No -> revert) — (a) is it actually simpler, or just different? (b) would a newcomer find it easier? (c) if it adds an abstraction, does that abstraction earn its existence? (d) is complexity reduced, or just moved?
6. **Render report** — grouped by file: `File | Change | Complexity Before | After | Lines Saved`.
7. **No PR, no commit** — the in-flight lane; the operator owns the next commit.

## Distinction from /ai-simplify-sweep

| Aspect | `/ai-simplify` | `/ai-simplify-sweep` |
|---|---|---|
| Invocation | On-demand by operator | On-demand (weekly cadence recommended) |
| Scope | Operator-chosen paths or current diff | Repo-wide sweep |
| PR | None (in-flight work) | Always opens a draft PR |
| Auto-commit | No (operator owns next commit) | Yes (`/ai-commit` before PR) |
| Aggressiveness | Operator-chosen | Conservative-only |
| Telemetry | `kind=simplify_ondemand_run` | `kind=simplify_sweep_*` |

Both share the same `ai-simplify` agent engine — they differ in cadence, scope, and post-conditions, not in simplification logic.

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

If `All tests passing: NO`: report the failing test, do NOT auto-revert (the operator decides), and emit `framework_event kind=simplify_test_regression` so the failure is auditable.

## Boundaries

- **Behaviour preserved** — same inputs, same outputs.
- **Tests pass after every change** — run any fast (<30s) suite after each file.
- **Never modifies test files** — tests are the immutable spec; simplify production code only.
- **Never churns compliant code** — no value simplifying code already below thresholds.
- **One file at a time**, validate before the next — never batch across files without intermediate validation.
- **External API signatures are immutable** — public signatures, exported types, CLI contracts are off-limits; refactor internals only.
- **No new abstractions** — reduce complexity in existing structure; do not add protocols/base classes/extension points.
- **No PR, no auto-commit** — the operator owns the resulting diff.

## Examples

### Example — scoped simplification of a single file

User: "simplify src/auth/login.py — the nested if/else is hard to follow"

```
/ai-simplify src/auth/login.py
```

Dispatches the agent scoped to the file. It inverts the outer `if user is not None` into an early-return guard, converts the inner `if user.active` to a guard, and drops the now-unreachable trailing `else: return None`. After each edit it runs `ruff check` + `ruff format --check`. Report: 1 file simplified, 3 complexity points reduced, 8 lines removed, all tests passing.

## Integration

Called by: operators directly via `/ai-simplify` (single-file or diff-scoped) — not auto-invoked by any other skill. Calls: the `ai-simplify` agent (`.claude/agents/ai-simplify.md`) via the Agent tool with the operator-chosen scope; validates after each edit, rolls back on test failure. See also: `.claude/skills/ai-simplify-sweep/SKILL.md` (scheduled draft-PR wrapper); `.ai-engineering/manifest.yml` `quality` thresholds (cyclomatic ≤ 10, cognitive ≤ 15, nesting ≤ 3, method length ≤ 50). Anchors: §10.1 KISS, §10.7 Clean Code; D-134-07 (agents need a discoverable slash-skill).

**Inline fallback** — Agent-tool dispatch is the primary path. On a harness without a subagent/Agent-tool primitive, execute this skill by reading the specialist agent file (`.claude/agents/ai-simplify.md`) inline and running its steps in-context, sequentially, applying the same per-edit validation and self-check; inline-sequential execution is the floor, not an alternate behaviour.

$ARGUMENTS
