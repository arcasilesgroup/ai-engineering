---
"ai-engineering": minor
---

One worktree per feature: a session that writes code works in `<repo>.worktrees/<slug>`, merges into the local `main` when it closes, and never pushes, while the new `ai-eng worktree new|rm|list` verb manages those copies and the human decides the pull request against `origin/main`.
