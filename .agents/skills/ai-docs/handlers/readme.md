# Handler: readme

## Purpose

Diff-aware README updates. Identifies which README sections are affected by staged changes and updates only those sections, preserving user-authored content elsewhere.

## Pre-conditions

1. Read `.ai-engineering/manifest.yml` -- check `documentation.auto_update.readme`.
2. If `false`, skip silently and report "readme auto-update disabled".

## Procedure

### 1. Read the semantic diff

Read the full staged diff (`git diff --cached`) or branch diff (`git diff main...HEAD`). Identify:
- Which directories have changed files
- What types of changes occurred (new features, config changes, API changes, structural changes)
- Whether root-level project metadata changed (version, dependencies, install process)

### 2. Scan for README files

Scan project recursively for ALL README*.md files (README.md, README_es.md, etc.).

**Exclude**: `.venv/`, `node_modules/`, `.git/`, `__pycache__/`, `.pytest_cache/`, `build/`, `dist/`

### 3. Identify affected READMEs

For each README found, determine if the diff affects its directory:
- Root README.md: affected by version changes, new features, install changes, dependency changes
- Subdirectory READMEs: affected only if files in that directory or its children changed

Skip READMEs whose directories have no relevant changes.

### 4. Diff-aware section targeting

For each affected README:
1. Read the current README content
2. Read sibling files to understand the module/package purpose
3. Map each diff change to the README section it affects:
   - New CLI command -> Usage section
   - New dependency -> Installation section
   - New module/class -> API or Structure section
   - Changed behavior -> relevant feature section
4. Update ONLY the affected sections
5. Preserve existing structure, formatting, and user-authored content in unaffected sections

### 5. Apply Divio structure rules

When creating new sections or significantly expanding existing ones:
- **Tutorial**: learning-oriented, step-by-step, concrete outcomes
- **How-to**: task-oriented, assumes knowledge, goal-focused
- **Explanation**: understanding-oriented, context and reasoning
- **Reference**: information-oriented, accurate and complete

### 6. README structure (root)

Ensure root README.md contains at minimum:
- Project name and one-line description
- Quick start (3 steps max to "hello world")
- Installation, usage, configuration
- Contributing, license

### 7. Stage

`git add` all modified README files.

### 8. Report

List which READMEs were updated, which sections changed, and which were unchanged.

## Output

- Updated README files with diff-targeted changes
- Report: READMEs updated vs unchanged, sections modified per file
