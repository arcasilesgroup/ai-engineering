# DECISIONS.md — ADR-lite: ≤6 lines per decision [Problem → Decision → Reason]

## D-001 · ai-engineering governs this repo (2026-09-01)
**Problem:** agents need common ground: guards, git floor, executable contract.
**Decision:** planted {ai} Engineering 2.0.0 (init), global skill canon, local receipts.
**Reason:** proof > promise — a decision that always comes out the same is code, not a prompt.

## D-002 · §14 mockups are the CLI visual contract (2026-09-01)
**Problem:** the human verbs (init/doctor/update/upgrade/config/uninstall) drifted from the blueprint: raw stdout breaks the clack frame mid-flow (user: "feo feo feo").
**Decision:** blueprint §14 mockups are the acceptance standard; src/ui.ts is the single frame layer over clack 1.7.0 (no new deps); machine verbs keep byte-stable stdout. Research: .ai-engineering/brainstorm.md @ git b3d70782.
**Reason:** the manual already decided the UX line by line; the gap was implementation depth, not design.
