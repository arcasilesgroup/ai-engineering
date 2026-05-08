---
name: ai-resolve-conflicts
description: "Resolves git conflicts intent-aware: categorizes by type (lock files, migrations, generated, config, code), regenerates or merges per category, never blindly accepts. Trigger for 'I have conflicts', 'rebase failed', 'merge conflict', 'cherry-pick failed', 'unmerged paths'. Not for branch hygiene; use /ai-cleanup instead. Not for committing the resolution; use /ai-commit instead."
effort: medium
argument-hint: ""
---


# Resolve Conflicts

## Purpose

Intelligent git conflict resolution. Detects conflict type, categorizes files by resolution strategy, and resolves conflicts with awareness of both sides' intent. Handles lock files, migrations, and code conflicts differently.

## Trigger

- Command: `/ai-resolve-conflicts`
- Context: git operation resulted in conflicts (rebase, merge, cherry-pick, revert).
- Auto-detect: `git status` shows "Unmerged paths" or "both modified".

## Workflow

1. **Detect conflict type** -- determine the operation that caused conflicts:

   ```bash
   # Check which operation is in progress
   test -d .git/rebase-merge || test -d .git/rebase-apply  # rebase
   test -f .git/MERGE_HEAD                                  # merge
   test -f .git/CHERRY_PICK_HEAD                            # cherry-pick
   test -f .git/REVERT_HEAD                                 # revert
   ```

2. **List conflicted files** -- `git diff --name-only --diff-filter=U`

3. **Categorize each file** by resolution strategy:

   | Category | File patterns | Strategy |
   |----------|--------------|----------|
   | Lock files | `*.lock`, `poetry.lock`, `Cargo.lock`, `package-lock.json`, `uv.lock` | Accept theirs, regenerate |
   | Migrations | `migrations/`, `alembic/versions/` | Ask user (order matters) |
   | Generated | `*.min.js`, `*.min.css`, `dist/`, `build/` | Accept theirs, rebuild |
   | Config | `*.yml`, `*.toml`, `*.json` (non-lock) | AI merge with validation |
   | Code | everything else | AI analysis |

4. **Resolve by category** (per the strategy column above):

   **Lock files** — `git checkout --theirs <lockfile>` then regenerate (`npm install` / `cargo generate-lockfile` / `uv lock` / etc.).

   **Migrations** — present both sides with the migration graph; ask which order to apply (never auto-resolve — ordering is semantic).

   **Config files** — merge intelligently preserving both sides' additions; validate against schema if available.

   **Code conflicts** — for each hunk: (a) read 50 lines context each side, (b) identify intent per side, (c) check commit messages, (d) propose resolution preserving both intents, (e) if intents conflict, present options to user.

5. **Stacked PR detection** -- if resolving conflicts between branches in a stack:
   a. Compare base, HEAD, and incoming for similarity
   b. If high overlap, likely a stacked PR rebase -- prefer incoming (later branch)
   c. Warn user about potential cascade to downstream branches

6. **Validate resolution**:
   - Run `git diff` to review all resolutions
   - Run stack-specific checks (build, lint, test)
   - Present summary before continuing the operation

7. **Continue operation**:
   ```bash
   git add <resolved-files>
   git rebase --continue   # or git merge --continue / git revert --continue / git cherry-pick --continue
   ```

   If the continue operation produces new conflicts (common during multi-commit rebases), loop back to the conflict detection step and resolve the next round. Repeat until the operation completes.

## Quick Reference

```
/ai-resolve-conflicts     # auto-detect and resolve current conflicts
```

No arguments needed -- the skill reads git state directly.

## Examples

### Example 1 — rebase that hit a lock-file conflict

User: "rebase failed on package-lock.json"

```
/ai-resolve-conflicts
```

Detects the rebase-in-progress, classifies `package-lock.json` as a generated file, regenerates via `npm install`, stages the result, runs `git rebase --continue`.

### Example 2 — merge with code conflict needing intent-aware resolution

User: "merge conflict in src/auth.ts, both branches changed the token validator"

```
/ai-resolve-conflicts
```

Reads both sides, detects category = code, applies intent-aware resolution (preserves both validators if non-overlapping; otherwise asks the user with a unified diff).

## Integration

Called by: `/ai-pr` watch-and-fix loop (CI repair), user directly. Calls: git (rebase / merge / cherry-pick continuation), package managers (lock-file regeneration). See also: `/ai-cleanup` (after resolution), `/ai-commit` (commit the resolved state).

$ARGUMENTS
