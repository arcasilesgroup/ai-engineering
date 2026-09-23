---
"ai-engineering": minor
---

Session handoff improvements (research 006 R1/R2/R3). `ai-eng briefing` generates a session handoff briefing with spec gates, plan step, recent denies, and receipt summary — closing the "rebuild state from scratch" gap (20/90 sessions needed manual "continua"). Receipts now carry `session_id` and `summarizeBySession()` groups them for per-session queries. Research cache (`research-cache/`) persists findings between sessions with doctor reporting and gc auto-prune for entries >30d.
