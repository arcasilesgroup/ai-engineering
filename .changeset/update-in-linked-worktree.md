---
"ai-engineering": patch
---

`ai-eng update` works inside a linked git worktree. It failed there with `ENOTDIR` while writing `.git/hooks`, because in a worktree `.git` is a file and the hooks live in the repository's shared git folder. Update now leaves those shared hooks to the main checkout and keeps them in the lock, so a lock committed from a worktree matches one from the main checkout. `ai-eng doctor` reads the hooks from where git actually runs them.
