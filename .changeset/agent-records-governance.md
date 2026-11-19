---
"ai-engineering": patch
---

An agent can now finish an `ai-eng update` on its own: the self-protect guard lets it `git add` and `git commit` the files ai-eng wrote (the lock, the carriers), while every command that changes their bytes — an edit, a redirect, `git checkout` or `git restore` over them — stays denied. Before, naming the lock in `git add` was refused even though `git add -A` staged it anyway, so updating every project agentically needed a person for each commit.

The one-writer lease now holds only writes into the leased folder: a second session writing a temp file or a file in another checkout is no longer stopped. Failed or killed mutation runs no longer leave `.stryker-tmp` behind, and the CLI proof hands hooks a native path on Windows.
