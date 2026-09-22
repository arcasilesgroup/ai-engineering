---
"ai-engineering": minor
---

Governance by observability, not by more stoppers (research/001 R1+R2). `doctor`'s receipts line is no longer four numbers: it names the top denier guard/tool, the ledger's repeat count, and WARNs when the last 7 days of denies pass 3x the prior week. The gc that already collects receipts now merges a 90-day daily series into `summary.json` instead of overwriting it, and prunes the new `receipts/denies.json` ledger (age + newest-500) instead of deleting it. The ledger is the cross-session memory OWASP ASI01/ASI06 need: when a guard denies a call this exact machine already denied, the human message says `· this exact call has been denied N times before`. Signal only — no verdict, no new config, no dependency; deny receipts finally carry their real tool instead of `unknown`.
