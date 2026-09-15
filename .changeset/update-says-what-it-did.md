---
"ai-engineering": patch
---

`ai-eng update` reports both halves it owns, and a no-op is no longer printed as a write. The machine half was visible only when something was wrong: a healthy canon, an unchanged git floor and a carrier already at the binary's bytes printed nothing, so a run that verified everything looked exactly like a run that never looked — and the module carriers were rewritten and counted every time, which is how "all 7 assets current — nothing to sync" arrived with a line claiming the machine side was the work.

The repo and the machine now each report as one block, every part named with its outcome: `Repo assets` lists the files it holds when there is nothing to write, `Machine side` names the canon, each declared surface's carrier, the git floor and the machine ledger, and the closing line says whether anything was written at all. Identical bytes are skipped rather than rewritten, so `written` means a change.

What an existing install will notice: the second `ai-eng update` in a row now ends in "Nothing written — the repo and the machine already match ai-eng <version>" instead of the counts of a run that looked like it had done something.
