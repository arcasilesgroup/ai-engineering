# Lanes

One task is one lane: a branch, its folder and its pull request. `ai-eng work` lists every
lane from git and the forge. A lane leaves in one of three ways:

- `ai-eng work tidy` closes a landed lane.
- `ai-eng work park <branch> "<reason>"` pauses one, with the reason.
- `ai-eng work drop <branch>` drops one, keeping its commits in `refs/archive/`.

`ai-eng worktree new <branch>` starts from your current `HEAD` and refuses a fourth active
lane. Worktrees live beside the repository in `<repo>.worktrees`, or under `[git]
worktrees_dir`. `ai-eng worktree merge <slug>` merges a reviewed feature locally and keeps
its folder until `ai-eng worktree rm <slug>`. None of these commands pushes. The contributor
workflow is in [CONTRIBUTING.md](../CONTRIBUTING.md).
