# Handler: changelog

## Purpose

Generate or update CHANGELOG.md entries from semantic diff analysis. Reads the full git diff (not just commit messages) to classify changes by user impact.

## Pre-conditions

1. Read `.ai-engineering/manifest.yml` -- check `documentation.auto_update.changelog`.
2. If `false`, skip silently and report "changelog auto-update disabled".

## Procedure

### 1. Read the semantic diff

Read the full staged diff (`git diff --cached`) or branch diff (`git diff main...HEAD`), not just commit messages. Extract:
- New functions, classes, modules added
- Modified function signatures or behavior
- Deleted or renamed public APIs
- Changed configuration formats
- New or modified CLI commands
- Dependency additions/removals/upgrades

### 2. Classify by user impact

For each change from the diff:
- **User-visible**: behavior change, new capability, bug fix, performance improvement
- **Internal**: refactoring, tests, CI, code style (exclude from changelog)
- **Breaking**: API change, feature removal, config format change (requires migration guide)
- **Security**: vulnerability fix (include CVE, impact, affected versions)

### 3. Map to Keep a Changelog categories

- **Added**: new capability users could not do before
- **Changed**: existing capability improved or different
- **Deprecated**: still works, include removal timeline
- **Removed**: previously available, now gone
- **Fixed**: was broken, now works
- **Security**: vulnerability fix with CVE reference

### 4. Transform to user-facing language

```
Bad:  "Refactored ReportExporter to support pagination"
Good: "Reports now load 3x faster when filtering large datasets"

Bad:  "Added fallback in auth middleware"
Good: "Fixed an issue where login would fail silently on network timeout"
```

Rules:
- Start with "You can now..." / "Fixed an issue where..." / present tense
- No internal references (class names, module paths, variable names)
- Quantify impact where possible (speed, count, scope)

### 5. Format CHANGELOG.md

- Add entries under `[Unreleased]` section
- For releases: rename to `[X.Y.Z] - YYYY-MM-DD`, add comparison links at bottom
- Follow Keep a Changelog format strictly
- Group entries by category (Added, Changed, Fixed, etc.)

### 6. Quality check -- reject and rewrite if any entry contains

- "Various bug fixes" or "minor improvements" (too vague)
- "Updated dependencies" without impact statement
- Internal jargon (module names, class names without context)
- Missing dates on release sections
- Breaking changes buried in Changed instead of prominently flagged

### 7. Stage

`git add CHANGELOG.md`

## Output

- CHANGELOG.md entries in Keep a Changelog format
- Report: number of entries added per category, number of internal changes excluded
