---
"ai-engineering": patch
---

The one-folder-one-writer lease now judges a write in the folder it lands in. When another session held the main checkout, the lease sent you to a worktree and then blocked your `git -C <worktree> commit` or `cd <worktree> && git add` there, because it only looked at where the session started. A git command aimed at a worktree now takes that worktree's lease; one aimed back at the held checkout is still stopped, and a `cd` the shell may not have run first (after `||`, in a subshell or pipeline, or into a folder that does not exist) is not believed. A worktree nested inside the checkout counts as its own folder too.
