---
name: ai-resolve-conflicts
description: Use whenever git reports conflicts, you see <<<<<<< markers, or git operations stop mid-flight. Trigger for 'I have conflicts', 'rebase failed', 'merge conflict', 'cherry-pick failed', 'unmerged paths', 'git stopped with conflicts', 'I see <<<<<<< in the file'. Categorizes conflicts by type — lock files (regenerate), migrations (ask user), generated files (accept theirs), config (AI merge), code (intent-aware resolution).
effort: medium
argument-hint: 
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-resolve-conflicts/SKILL.md
edit_policy: generated-do-not-edit
---



# Resolve Conflicts

## Purpose

Intelligent git conflict resolution. Detects conflict type, categorizes files by resolution strategy, and resolves conflicts with awareness of both sides' intent. Handles lock files, migrations, and code conflicts differently.

## Trigger

- Command: `/ai-resolve-conflicts`
- Context: git operation resulted in conflicts (rebase, merge, cherry-pick, revert).
- Auto-detect: `git status` shows "Unmerged paths" or "both modified".

## Procedure

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

## Integration

- **Called by**: `/ai-pr` watch-and-fix loop (Step 5, automated CI repair), user directly
- **Calls**: git (rebase, merge, cherry-pick continuation commands)
- **Transitions to**: calling workflow resumes after conflicts resolved

## Quick Reference

```
/ai-resolve-conflicts     # auto-detect and resolve current conflicts
```

No arguments needed -- the skill reads git state directly.

$ARGUMENTS
