---
name: code
description: Use when writing new code, implementing features, or adding functionality. Pre-coding checklist, context-aware coding with layer precedence, interface-first design, backward-compatibility checks, self-review.
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

NOT for: tests (use /ai-test), debugging (use /ai-debug), refactoring (use /ai-simplify), schema work (use /ai-schema).

## Process

### Step 0: Load Contexts

Read `.ai-engineering/manifest.yml` field `providers.stacks` for the project's declared stacks. Then load the applicable context files:

1. **Languages** -- read `.ai-engineering/contexts/languages/{lang}.md` for each detected language.
   Available (14): bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, rust, sql, swift, typescript
2. **Frameworks** -- read `.ai-engineering/contexts/frameworks/{fw}.md` for each detected framework.
   Available (15): android, api-design, aspnetcore, backend-patterns, bun, claude-api, deployment-patterns, django, flutter, ios, mcp-sdk, nextjs, nodejs, react, react-native
3. **Team** -- read `.ai-engineering/contexts/team/*.md` for all team conventions.

Apply with precedence: **team > frameworks > languages** (declared in `manifest.yml contexts.precedence`). When a team convention conflicts with a framework default, team wins.

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

Check written code against loaded contexts for 3 critical categories:

1. **Naming conventions** -- verify casing, prefixes, suffixes match context rules
2. **Anti-patterns** -- verify no code matches anti-patterns listed in context files
3. **Error handling** -- verify error handling follows documented conventions

Produce a compliance trace:

```
## Compliance Trace
| Category | Status | Notes |
|----------|--------|-------|
| Naming conventions | PASS/DEVIATION | [details if deviation] |
| Anti-patterns | PASS/DEVIATION | [details if deviation] |
| Error handling | PASS/DEVIATION | [details if deviation] |
```

Fix deviations before reporting task complete. If a deviation is intentional, document the reason.

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
