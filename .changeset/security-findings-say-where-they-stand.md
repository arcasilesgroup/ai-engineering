---
"ai-engineering": patch
---

`ai-security` findings now say where they stand, not only that they were real. A confirmed finding carried `verdict: "confirmed"` and nothing else, so one fixed in the same session kept reading as a live vulnerability: the next audit re-derived it, `REPORT.md` was the only artifact that said "fixed", and the milestone CHECK "zero open HIGH findings" had nothing in the machine-readable half to evaluate.

Every confirmed finding now carries a `disposition` — `{"status": "open"}` while the vulnerability is in the tree, or `{"status": "fixed", "landed_in": "<sha>"}` once the fix has landed. The schema refuses `fixed` without the commit that carries it, so no report can claim a fix nobody can resolve. Phase 5 requires the field, and the prior-run ledger reads it: a `fixed` finding is closed ground, an `open` one is where the next run digs.

A `findings.json` written before this change is refused by `validate-findings.cjs` until it is stamped, which is the point — the two runs this repository keeps were stamped with the commits that carry their fixes.
