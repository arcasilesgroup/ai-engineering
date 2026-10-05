---
"ai-engineering": patch
---

`ai-git-cleanup`: the pass learns what a squash merge looks like, so a branch a
squash-merged pull request left behind is no longer stranded as "unmerged"
forever. A branch (not the current one, not checked out anywhere) whose tree is
byte-identical to a fetched `origin/main` has provably landed: tag
`archive/<branch>` as the receipt that its history stays reachable, then delete
it. It is the pass's only force-delete, earned by the whole-tree comparison; a
branch whose tree differs is parked and reported, never merged or re-opened on
the pass's initiative, and without a fetched `origin/main` the step refuses.
