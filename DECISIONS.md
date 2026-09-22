# DECISIONS.md — ADR-lite: one standing decision per entry [Decision → Reason]

## D-001 · ai-engineering governs this repo (2026-09-15)
**Decision:** {ai} Engineering 2.2.0 installed (init), global skill canon, local receipts.
**Reason:** proof > promise — a decision that always comes out the same is code, not a prompt.

## D-002 · Governance improves by observability, not by more stoppers (2026-09-20)
**Decision:** the policy guard (bash-guard port) completed the command-scope half of least-agency; the next milestone takes research/001's R1 (richer gc aggregate: per-guard/tool/surface + daily series + baseline-deviation WARN), R2 (cross-session deny ledger — signal only, never a verdict; guard-level count for variant probes) and optionally R3 (OTLP alias, off by default). Evidence, ASI cross-check and rejections in research/001.
**Reason:** OWASP 2026: "least agency without observability is blind risk reduction" — the receipts already carry the signal; the 30-day gc window is what throws it away.

## D-003 · Observability ships as signal inside the gc (2026-09-21)
**Decision:** research/001 R1+R2 built (richer summary.json + denies.json ledger + deviation WARN at 3x, fixed); R3 (OTLP alias) and the injection fold-miss stay out until real demand. blueprint §10 amended to match.
**Reason:** the receipts already carry the story; the 30-day sweep threw it away. Pre-committed cut: if after 90 days the ledger recorded zero repeats and doctor flagged zero deviations on this repo, the layer is removed — ceremony fails the same §10.2 test the guards face.
