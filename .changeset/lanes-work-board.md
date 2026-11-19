---
"ai-engineering": minor
---

New `ai-eng work`: one board for every lane in the repo — each branch with its folder and PR, every stash, and every worktree whose folder is gone — computed from git and the forge each time, never stored. A lane leaves by one of three doors: `ai-eng work tidy` removes what provably landed (the forge merged that exact tip, or the base holds it and its remote branch is gone), `ai-eng work park <branch> "<reason>" [--until YYYY-MM-DD]` records why it waits, and `ai-eng work drop <branch>` keeps the tip in `refs/archive/` before the branch goes. A session start in Claude Code or Codex now adds one line about the lanes that need a decision.

`ai-eng worktree new` refuses a fourth active lane (`[work] max_active`, default 3), a new `no-stash` guard denies creating a stash (reading and restoring one still work), `/ai-pr` closes the lane once the PR is merged, and `AGENTS.md`'s "Where to work" is now seven numbered rules. The `ai-git-cleanup` skill is removed: its merged-branch test missed squash and rebase merges, and `ai-eng work tidy` replaces it.
