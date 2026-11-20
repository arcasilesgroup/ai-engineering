---
"ai-engineering": patch
---

`ai-eng work` and `ai-eng work tidy` now see a branch as landed without asking the forge when git can prove it: the branch was merged into the base by a merge commit, its whole change was squash-merged into the base, or `ai-eng worktree merge` recorded merging it. Both commands also run `git fetch --prune` first (best effort, ten seconds at most), so a branch the forge deleted on merge reads as gone. A branch created on the base with nothing of its own still does not count as landed.
