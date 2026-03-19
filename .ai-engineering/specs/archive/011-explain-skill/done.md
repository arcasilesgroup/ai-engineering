---
spec: "011"
completed: "2026-02-11"
---

# Done — Explain Skill

## Summary

Created the `swe:explain` skill — a Feynman-style explanation skill with 3-tier depth (Quick/Standard/Deep) and 6 explanation sections (One-Liner, Analogy, Step-by-Step, Gap Check, Prove It, Context Map).

## Deliverables

| Deliverable | Status |
|-------------|--------|
| Canonical skill file | `.ai-engineering/skills/docs/explain.md` |
| Template mirror | `src/ai_engineering/templates/.ai-engineering/skills/docs/explain.md` (byte-identical) |
| Slash command | `.claude/commands/swe/explain.md` |
| Command mirror | `src/ai_engineering/templates/project/.claude/commands/swe/explain.md` (byte-identical) |
| 8 instruction files | All list explain.md under SWE Skills |
| Counter update | 32 → 33 skills in product-contract |
| CHANGELOG | Entry under [Unreleased] → Added |
| Cross-references | 3 skills + 2 agents (canonical + mirror = 10 files) |

## Commits

1. `spec-011: Phase 0 — scaffold spec files and activate`
2. `spec-011: Phase 1 — author explain skill`
3. `spec-011: Phase 2 — mirror + command wrappers`
4. `spec-011: Phase 3 — register in instruction files + counters + changelog`
5. `spec-011: Phase 4 — cross-references`
6. `spec-011: Phase 5 — verify and close`
