# Corpus: ai-debug

Finds the root cause of broken behaviour and names it at `file:line`, then writes the check
that fails for that reason before changing anything. It also resolves merge and rebase
conflicts by intent rather than by taking a side. A fix arrives only after the cause is named
and a check fails because of it.

## Routes here

- "it's not working, the upload just hangs" — a symptom that reproduces is the starting point here, and the first useful thing is a reproduction, not a change.
- "this used to work last week" — something changed and the cause has to be pointed at, not guessed at.
- "I'm getting a TypeError from the parser and I don't know why" — the failing output gets read in full, first error first, and the cause named at a line.
- "CI is failing but it passes on my machine" — a failure with two plausible causes needs the observation that tells them apart, made rather than assumed.
- "why is the cache returning stale rows for one tenant?" — the behaviour is wrong, so this is a cause hunt and not a tour of the cache module.
- "I have conflicts in the lock file after the rebase" — conflicts are resolved here by reading both sides for intent, and lock files are regenerated rather than merged by hand.
- "the rebase failed halfway and I don't want to take the wrong side" — the same clause: if two people meant different things, that is a conversation, not a resolution.

## Refuses

- "this module has no tests, can you add some?" — use `/ai-review`, because nothing is broken and test coverage on working code is judged there, not diagnosed here.
- "review this branch before I merge it" — use `/ai-review`, because there is no symptom to reproduce and a diff is judged at its boundaries, not traced from a failure.
- "walk me through how auth works, I've never seen this code" — use `/ai-explore`, because the ask is a tour of an unfamiliar area and nothing is failing.
- "the cause is clear, now design the fix across the three call sites" — use `/ai-plan`, because once the cause is named, splitting the work into tasks with a check and a rollback each is planning.
- "is this a known bug upstream, what do the release notes say?" — use `/ai-research`, because the evidence is outside this repository and has to arrive with a numbered citation.
- "save the workaround so nobody loses an afternoon on it again" — use `/ai-note`, because a finding that cost real time becomes committed markdown with a header that lets it be detected as stale.
- "the fix works, commit it and open the PR" — use `/ai-ship`, because landing the work is commits, changelog and a pull request.
