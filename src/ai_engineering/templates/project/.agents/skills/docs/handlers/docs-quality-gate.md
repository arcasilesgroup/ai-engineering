# Handler: docs-quality-gate

## Purpose

Verify that all documentation outputs from the parallel subagents (changelog, readme, solution-intent-sync, docs-portal) collectively cover every semantic change in the diff. Zero uncovered items is the pass criterion.

## When Called

Runs AFTER subagents 1-4 complete. This is the 5th subagent in the `/ai-pr` documentation dispatch -- it validates the outputs of the other four.

## Procedure

### 1. Read the full staged diff

Run `git diff --cached` (or `git diff main...HEAD` for full branch diff). Parse every semantic change:

- New functions or methods (name, module, signature)
- Modified function signatures (parameters added/removed/changed)
- Renamed or moved classes/modules
- Deleted modules, classes, or functions
- Changed behavior (logic changes in existing functions)
- New or modified CLI commands
- Configuration format changes
- New dependencies added or removed
- API endpoint changes (routes, request/response schemas)

### 2. Read all documentation outputs

Read the documentation changes produced by subagents 1-4:
- **CHANGELOG.md** -- staged entries from the changelog subagent
- **README*.md** -- staged changes from the readme subagent
- **docs/solution-intent.md** -- staged changes from the solution-intent-sync subagent
- **External portal** -- changes reported by the docs-portal subagent (if applicable)

### 3. Map changes to documentation coverage

For each semantic change from step 1, determine which documentation output covers it:
- User-visible feature/fix -> should appear in CHANGELOG.md
- New CLI command or install step -> should appear in README.md
- Architecture change (new skill, agent, stack) -> should appear in solution-intent
- Internal refactoring -> may be excluded from all docs (acceptable if truly internal)

### 4. Produce coverage checklist

Generate a table mapping each semantic change to its documentation:

```
| Change | Type | Covered By | Status |
|--------|------|------------|--------|
| Added /ai-docs skill | feature | CHANGELOG, solution-intent | COVERED |
| New docs-portal handler | feature | CHANGELOG | COVERED |
| Removed ai-solution-intent | removal | CHANGELOG, solution-intent | COVERED |
| Renamed internal helper | refactoring | (internal) | EXCLUDED |
| New CLI flag --docs | feature | CHANGELOG, README | COVERED |
| Changed manifest schema | breaking | CHANGELOG | COVERED |
| Updated dependency X | dependency | (no user impact) | EXCLUDED |
```

### 5. Evaluate pass/fail

- **PASS**: Zero uncovered items (all user-visible changes have documentation)
- **FAIL**: One or more user-visible changes lack documentation coverage

Items marked EXCLUDED (internal changes with no user impact) do not count against the gate.

### 6. Report

- Coverage checklist table
- Summary: N changes covered, N excluded (internal), N uncovered
- If FAIL: list uncovered items with recommended documentation target (which doc should cover each)

## Output

- Coverage report (table format)
- PASS/FAIL determination
- If FAIL: specific recommendations for which documentation to update
