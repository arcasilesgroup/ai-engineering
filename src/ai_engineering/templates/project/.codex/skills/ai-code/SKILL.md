---
name: ai-code
description: "Use when writing new production code: implementing features, adding functions, creating modules, or building approved plan tasks. Trigger for 'implement this', 'write the code for', 'add X to Y', 'build this function', 'make this work'. Loads language/framework context, applies interface-first design and backward-compatibility checks. Not for tests (/ai-test), debugging (/ai-debug), or refactoring (/ai-simplify)."
effort: high
argument-hint: "[task description or file:target]"
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

### Step 0: Load Stack Contexts

Follow `.ai-engineering/contexts/stack-context.md`. Apply loaded standards to all subsequent work.

### Step 1: Pre-Coding Checklist

Before writing any code:

1. **Restate the task** in one sentence -- confirm understanding
2. **Identify target files** -- existing files to modify or new files to create
3. **Search for existing patterns** -- grep for similar implementations in the codebase to match conventions
4. **Check decision-store.json** -- read `.ai-engineering/state/decision-store.json` for relevant architectural decisions

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

Implement following all loaded context standards. Apply stack-specific conventions from Step 0. Use YAGNI -- write the minimal code that satisfies the requirement.

### Step 5: Backward Compatibility Check

1. If changing a public function signature: add deprecation path or confirm breaking change is intentional
2. If modifying config format: ensure backward-compatible parsing
3. If renaming exports: grep for all callers and update them
4. Skip for internal/private code

### Step 6: Self-Review (Compliance Trace)

After writing code and before post-edit validation, perform a self-check against the loaded context files. This is a lightweight build-time check covering 3 critical categories. Full exhaustive validation (5 categories including idiomatic patterns and testing) is deferred to /ai-review.

**6a. Identify applicable context file**

For each file touched, identify the language from its extension (same mapping as lang-generic.md Step 1). The applicable context file `.ai-engineering/contexts/languages/{lang}.md` was already loaded in Step 0.

**6b. Map categories to context file sections**

Scan the loaded context file's H2 headers (`##`) to locate the relevant sections for each category. Not all languages have all sections -- report `n/a` when the context file lacks a matching section.

| Category | Match H2 headers containing | Example headers |
|----------|----------------------------|-----------------|
| Naming conventions | "naming", "conventions", "style" | `## Naming Conventions`, `## Code Style` |
| Anti-patterns | "anti-pattern" | `## Common Anti-Patterns`, `## Anti-Patterns` |
| Error handling | "error handling", "error", "exception" | `## Error Handling`, `## Exception Handling` |

If a context file has no H2 header matching a category, that category is `n/a` for the language.

**6c. Check each category**

1. **Naming conventions** -- verify all new identifiers (functions, variables, classes, constants) follow the casing, prefixes, suffixes, and forbidden patterns documented in the matched section.
2. **Anti-patterns** -- verify no new code matches any anti-pattern explicitly listed in the matched section.
3. **Error handling** -- verify error handling in new code follows the conventions documented in the matched section (e.g., specific exception types, error propagation patterns, logging requirements).

**6d. Produce the compliance trace**

```
### Compliance Trace

| Category | Status | Details |
|----------|--------|---------|
| Naming conventions | checked | All new names follow {lang}.md conventions |
| Anti-patterns | checked | No anti-patterns from {lang}.md detected |
| Error handling | n/a | {lang}.md has no error handling section |
```

Status values:
- `checked` -- validated against loaded context, no violations found
- `deviation` -- violation found; Details column names the specific rule and location
- `n/a` -- loaded context file has no section for this category

**6e. Deviation-found behavior**

If any category has status `deviation`, fix the violation before proceeding to post-edit validation. After fixing, update the compliance trace to record the fix:

```
| Anti-patterns | deviation (fixed) | bare except at line 42 -- fixed to except ValueError per python.md |
```

Do not proceed with a `deviation` status that has not been fixed. If a deviation is intentional and cannot be fixed, document the justification in the Details column and escalate to the user for approval.

## Common Mistakes

- Writing code before loading contexts (standards drift)
- Inventing new file paths instead of following existing project structure
- Skipping interface definition for non-trivial features
- Not checking for callers when changing public signatures
- Ignoring anti-patterns listed in context files
- Self-reviewing against general knowledge instead of loaded context rules

## Integration

- **Called by**: `ai-build agent` (classify mode: code), `/ai-dispatch` (implementation tasks), user directly
- **Calls**: stack-specific linters (post-edit validation via ai-build Step 4)
- **Transitions to**: `/ai-test` (TDD GREEN phase), `/ai-verify` (quality validation), `/ai-review` (full review)

$ARGUMENTS
