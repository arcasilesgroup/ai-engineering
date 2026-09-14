---
"ai-engineering": patch
---

The CI workflow `init` installs no longer reddens a project between milestones. Its spec-run step called `ai-eng spec run` unconditionally, and the binary is right to exit 2 when there is no `spec.html` — so a project with no live contract, which is the normal state after a contract closes, had a failing gate for a state that is not a failure. The step distinguishes the two now: no `spec.html` and no pin in the lock is "nothing to enforce between milestones" (exit 0), while a lock that still pins an approved contract whose `spec.html` has vanished fails and names the reason, because that is a contract someone deleted. A live contract still runs, and a check that cannot run is still a FAIL — the guard is about the state, never about a check.
