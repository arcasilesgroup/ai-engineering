---
name: ai-code
description: "Writes production code that satisfies stack-context standards on the first pass: interface-first design, backward-compatibility checks, lightweight self-review. Trigger for 'implement this', 'write the code for', 'add X to Y', 'build this function', 'make this work'. Not for tests; use /ai-test instead. Not for debugging; use /ai-debug instead. Not for refactoring; use /ai-simplify instead."
effort: high
argument-hint: "[task description or file:target]"
mirror_family: gemini-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-code/SKILL.md
edit_policy: generated-do-not-edit
---


# Code

## Purpose

Code implementation skill. Writes code that satisfies loaded context standards on the first pass. Lightweight self-review at build-time; full validation deferred to /ai-review.

## When to Use

- New features and implementing approved plans
- Adding functionality to existing modules
- Writing utility/helper code

NOT for: tests (use /ai-test), debugging (use /ai-debug), refactoring (dispatch `ai-simplify`), schema work (use /ai-schema).

## Process

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

### Step 1: Pre-Coding Checklist

Before writing any code:

1. **Restate the task** in one sentence -- confirm understanding
2. **Identify target files** -- existing files to modify or new files to create
3. **Search for existing patterns** -- grep for similar implementations in the codebase to match conventions
4. **Check state.db.decisions** -- read `.ai-engineering/state/state.db.decisions` for relevant architectural decisions

### Step 2: File Placement Protocol

1. New files go in the directory matching existing project structure -- follow the pattern, do not invent new paths
2. Test files mirror source structure (e.g., `src/foo/bar.py` -> `tests/foo/test_bar.py`)
3. Never create top-level files without explicit user instruction
4. If unsure about placement, check 3 similar files in the codebase and follow their pattern

### Step 3: Interface-First Design

1. Define public interfaces (protocols, abstract classes, type signatures) before writing implementation
2. Document the contract: inputs, outputs, errors, side effects
3. If the interface touches other modules, check those modules' existing contracts first
4. Skip for trivial changes (single-function additions, config updates)

### Step 4: Write Code

Implement following all loaded context standards. Apply stack-specific conventions from Step 0 and `.ai-engineering/contexts/operational-principles.md`. Write the minimal code that satisfies the requirement.

### Step 5: Backward Compatibility Check

1. If changing a public function signature: add deprecation path or confirm breaking change is intentional
2. If modifying config format: ensure backward-compatible parsing
3. If renaming exports: grep for all callers and update them
4. Skip for internal/private code

### Step 6: Self-Review

Follow `handlers/compliance-trace.md` for the compliance trace protocol.

## Common Mistakes

- Writing code before loading contexts (standards drift)
- Inventing new file paths instead of following existing project structure
- Skipping interface definition for non-trivial features
- Not checking for callers when changing public signatures
- Ignoring anti-patterns listed in context files
- Self-reviewing against general knowledge instead of loaded context rules

## Examples

### Example 1 — implement a feature from a plan task

User: "implement T-1.2: add the JWT validator function in src/auth/jwt.py"

```
/ai-code "T-1.2 JWT validator in src/auth/jwt.py"
```

Loads stack context, places file by mirroring existing structure, defines the interface, writes minimal compliant implementation, runs the compliance trace.

### Example 2 — extend an existing module with backward compatibility

User: "add a new `--strict` flag to the validate command without breaking existing callers"

```
/ai-code "add --strict flag to validate command, preserve existing behavior"
```

Greps for callers, defines additive flag with default that matches current behavior, runs backward-compatibility check before commit.

## Integration

Called by: `ai-build` agent, `/ai-dispatch`, user directly. Calls: stack-specific linters (post-edit validation via `ai-build` Step 4). Transitions to: `/ai-test` (GREEN), `/ai-verify` (quality), `/ai-review` (review). See also: `/ai-test`, `/ai-debug`, `/ai-simplify`.

$ARGUMENTS
