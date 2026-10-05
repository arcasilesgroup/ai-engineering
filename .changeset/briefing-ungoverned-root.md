---
"ai-engineering": patch
---

Briefing: an ungoverned root reads no foreign receipt store. `summarizeReceipts`
now takes a tri-state `dir` — `undefined` resolves the caller's repository,
`null` means this root has no store at all, a string means that store — so a
temp-root briefing stops resolving the process's nearest governed repo and
scanning the host checkout's receipts (5 s per call → 0 ms).
