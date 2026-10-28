---
name: ai-git-cleanup
description: >-
  Preview and remove finished local Git work using native Git safeguards. Show
  worktrees and branches merged into the selected base, preserve dirty or
  unmerged work, and never force-delete by default. Use for "tidy up", "delete
  old branches", "start fresh", or when the user names ai-git-cleanup.
license: Apache-2.0
---

# ai-git-cleanup — preview finished local work

Start with a read-only preview. Never fetch, push, delete remote branches, or
assume a default branch. Resolve the local base from the person's explicit
choice or repository configuration; if neither identifies one, ask once. Keep
`$base_ref` for Git comparisons and resolve `$base_branch` to that selected
base's short local branch name; the base itself is never a deletion candidate.
The cleanup pass never asks for a branch or worktree name.

```bash
git worktree list
git worktree prune --dry-run
git branch --merged "$base_ref" --format='%(refname:short)' | grep -Fvx -- "$base_branch"
```

For each candidate, set `$worktree_path` to its exact checkout path and show
the branch, checkout path, and status before changing anything. Before
requesting approval, list every ignored path in the worktree:

```bash
git -C "$worktree_path" ls-files --others --ignored --exclude-standard
```

Show every returned path relative to the worktree root and explain that removing
the worktree deletes it. If the command fails or cannot prove the complete list,
keep the candidate. Never delete ignored paths by default: the person must
explicitly approve deletion of every listed path after seeing the paths and
consequences, including paths classified as regenerable. Immediately before
removal, rerun the listing and keep the candidate if it differs from the preview
or cannot be read. Keep the current checkout, detached worktrees, dirty
worktrees, branches checked out elsewhere, and branches not merged into the
selected base.
Ignored output is regenerable only at `node_modules/`, `dist/`, `coverage/`,
`.stryker-tmp/`, `reports/`, `.ai-engineering/receipts/`,
`.ai-engineering/cache/`, `.ai-engineering/workflow/playwright/`,
`*.bun-build`, `.claude/reviews/`, and `*.DS_Store`; anything else ignored is
data. These existing system and editor noise paths are the only ignored outputs
the repository marks regenerated. Match each exact path relative to the worktree root:
`reports-archive/` and
`packages/x/dist` are not matches. For each removal, report every ignored path it drops and the acknowledged
consequence.

After the person approves the preview, remove only clean, merged worktrees with
`git worktree remove -- "<path>"`, prune stale registrations with
`git worktree prune`, and delete merged local branches with
`git branch -d -- "<branch>"`. Git's refusal is the safety result: report it
and keep the candidate. Never use `-D`, `--force`, or retry a refusal.

For a named worktree that the person explicitly wants removed despite unmerged
work, use `ai-eng worktree rm <slug>` and follow its confirmation and safety
checks; this skill's automatic pass never substitutes for that request.

## Lifecycle

Lane: any
Writes: nothing
Read by: the person who asked for cleanup
Dies: after each preview and approved pass
Next: none
