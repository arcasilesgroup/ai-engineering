---
"ai-engineering": minor
---

Landed lanes now close on their own. When a session opens, every branch whose landing is proven (its PR merged, `ai-eng worktree merge` recorded it, or a merge brought it into the base) is removed without asking: its tip is kept first in `refs/archive/<branch>`, its folder goes only when it holds no uncommitted work, and a folder another session is writing in, or the branch checked out where the session opens, is left alone. The session is told in one line, with the command that brings a branch back. `ai-eng work tidy` keeps each tip in `refs/archive/` the same way, and fast-forwards the base checked out here when it is clean and behind its upstream.
