---
name: resolve
description: Use when there are merge conflicts that need intelligent, intent-aware resolution — lock files, migrations, generated code, config, application code. Trigger for "resolve conflicts", "fix the merge", "rebase failed", "git is yelling at me". Never discards work without explicit approval.
effort: high
tier: core
capabilities: [tool_use]
governance:
  blocking: false
---

# /ai-resolve

Merge conflict resolution with intent-awareness. Categorizes conflicts
by type, applies safe automated strategies for mechanical conflicts,
and surfaces semantic conflicts for human judgment.

## When to use

- `git merge` / `git rebase` left conflict markers
- "Resolve conflicts on this PR"
- Long-running branch needs to catch up with `main`
- Migration / lockfile collisions during release crunch

## Categories + strategies

| Category | Examples | Strategy |
|----------|----------|----------|
| **Lock files** | `bun.lockb`, `package-lock.json`, `Cargo.lock`, `uv.lock` | Re-run install on the post-merge tree; commit fresh lock |
| **Migrations** | numbered SQL/alembic files | Renumber the incoming migration; never overwrite an applied one |
| **Generated** | `.claude/skills/`, `dist/`, OpenAPI clients, mirror files | Regenerate from source; never resolve by hand |
| **Config** | `.toml`, `.yaml` config | Merge keys; preserve both sides if semantically distinct |
| **Application code** | source files | Surface to user with both sides + intent question |

## Process

1. **Run `git status`** — list conflicted paths; classify each by
   category.
2. **Auto-resolve mechanical** — lock files, generated files, mirror
   files. Run regenerators; commit `chore(deps): regenerate locks`.
3. **Renumber migrations** — if both branches added migration 042,
   rename incoming to 043 and update references.
4. **Surface semantic conflicts** — for code conflicts, present:
   - both sides side-by-side with file context
   - the spec each side traces to
   - a proposed merge with rationale
5. **STOP for user approval** on every semantic conflict. Never
   silently pick a side.
6. **Run gates after resolve** — `/ai-verify` deterministic to confirm
   the post-merge tree is buildable and tests pass.

## Hard rules

- NEVER discard work without explicit user approval. `git checkout --theirs`
  or `--ours` requires confirmation per file.
- NEVER hand-edit generated files — regenerate from source.
- NEVER renumber a migration that has already been applied in any
  environment. Recreate downstream instead.
- Lock-file conflicts are NOT semantic; do not surface them to the user
  unless the regeneration produces unexpected dep-tree changes.

## Common mistakes

- Picking `--theirs` blindly to make the conflict go away
- Hand-editing generated files (next regenerate will overwrite)
- Forgetting to re-run install / regenerator after lockfile resolution
- Renumbering migrations after they've been applied to staging
- Skipping post-resolve verification — bad merges compile but break runtime
