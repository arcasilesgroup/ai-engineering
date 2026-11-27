---
"ai-engineering": patch
---

The Conventional Commits rule now runs at pre-push as well as at `commit-msg`, over exactly the commits a push sends, so a subject that arrives by a route the `commit-msg` hook never runs for — the validation pipeline writes its own fix commits and rewrites subjects after the commit exists — is refused before it leaves the clone. `src/floor/index.ts` holds the rule once, and `docs/git-floor.md` maps every commit route with the recorded run that showed which ones were judged.
