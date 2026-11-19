---
"ai-engineering": minor
---

New `lease` guard: one folder, one writer. The first session that writes in a folder (a file edit, or a git command that writes the index, a ref or the tree) holds it; another session's write there is denied and sent to a worktree. The hold lives in the folder's git directory, lapses after 15 minutes without a write (`[work] lease_minutes`), ends at once with Claude Code's `SessionEnd`, and `ai-eng work release` frees it by hand. Reading, testing and building are never held, and a host that sends no session id is never judged.
