---
name: ai-resolve-conflicts
description: "Resolves git conflicts intent-aware: categorizes by type (lock files, migrations, generated, config, code), regenerates or merges per category, never blindly accepts. Trigger for 'I have conflicts', 'rebase failed', 'merge conflict', 'cherry-pick failed', 'unmerged paths'. Not for branch hygiene; use /ai-branch-cleanup instead. Not for committing the resolution; use /ai-commit instead."
effort: cheap
argument-hint: ""
---


# Resolve Conflicts

Intent-aware git conflict resolution: detect the operation, categorize files by strategy (lock, migration, generated, config, code), and resolve with awareness of both sides — never blindly accept. Use it whenever `git status` shows unmerged paths after a rebase, merge, cherry-pick, or revert.

```
/ai-resolve-conflicts     # auto-detect and resolve current conflicts
```

## Workflow

Principles: §10.1 KISS (category-routing over a single generic merge); §10.4 DRY (regenerate lock/generated files rather than hand-merge).

1. **Detect operation** in progress:

   ```bash
   test -d .git/rebase-merge || test -d .git/rebase-apply  # rebase
   test -f .git/MERGE_HEAD                                  # merge
   test -f .git/CHERRY_PICK_HEAD                            # cherry-pick
   test -f .git/REVERT_HEAD                                 # revert
   ```

2. **List conflicts** — `git diff --name-only --diff-filter=U`.
3. **Categorize** each file:

   | Category | File patterns | Strategy |
   |----------|--------------|----------|
   | Lock files | `*.lock`, `poetry.lock`, `Cargo.lock`, `package-lock.json`, `uv.lock` | Accept theirs, regenerate |
   | Migrations | `migrations/`, `alembic/versions/` | Ask user (order matters) |
   | Generated | `*.min.js`, `*.min.css`, `dist/`, `build/` | Accept theirs, rebuild |
   | Config | `*.yml`, `*.toml`, `*.json` (non-lock) | AI merge with validation |
   | Code | everything else | AI analysis |

4. **Resolve by category**:
   - **Lock files** — `git checkout --theirs <lockfile>`, then regenerate (`npm install` / `cargo generate-lockfile` / `uv lock`).
   - **Migrations** — present both sides + migration graph; ask which order (never auto-resolve — ordering is semantic).
   - **Config** — merge preserving both sides' additions; validate against schema if available.
   - **Code** — per hunk: (a) read 50 lines context each side, (b) identify intent per side, (c) check commit messages, (d) propose resolution preserving both intents, (e) if intents conflict, present options to the user.
5. **Stacked-PR detection** — compare base/HEAD/incoming similarity; on high overlap, likely a stacked-PR rebase → prefer incoming (later branch) and warn about cascade to downstream branches.
6. **Validate** — `git diff` to review; run stack-specific checks (build/lint/test); present a summary before continuing.
7. **Continue** — `git add <resolved-files>`, then `git rebase --continue` (or `merge`/`revert`/`cherry-pick --continue`). If new conflicts appear (common in multi-commit rebases), loop back to step 1 until the operation completes.

## Examples

User: "merge conflict in src/auth.ts, both branches changed the token validator"

```
/ai-resolve-conflicts
```

Reads both sides, categorizes as code, applies intent-aware resolution (preserves both validators if non-overlapping; otherwise asks the user with a unified diff), stages, continues the operation.

## Integration

Called by: `/ai-pr` watch-and-fix loop (CI repair), user directly. Calls: git (rebase / merge / cherry-pick continuation), package managers (lock-file regeneration). See also: `/ai-branch-cleanup` (after resolution), `/ai-commit` (commit the resolved state).

$ARGUMENTS
