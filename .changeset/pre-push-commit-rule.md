---
"ai-engineering": patch
---

The Conventional Commits rule now runs at pre-push as well as at `commit-msg`, over exactly the commits a push introduces, so a subject that arrives by a route the `commit-msg` hook never runs for — the validation pipeline writes its own fix commits and rewrites subjects after the commit exists — is refused before it leaves the clone, while history inherited from the base stays out of the gate. `src/floor/index.ts` holds the rule once, and `docs/git-floor.md` maps every commit route, names the one deliberate bypass (merge commits, judged only by `commit-msg` when the merge is made here), and carries the recorded run that showed which routes were judged.
