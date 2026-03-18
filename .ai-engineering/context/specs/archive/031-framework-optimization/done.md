---
spec: "031"
status: "complete"
completed: "2026-03-02"
branch: "spec/031-framework-optimization"
---

# Done — Architecture Refactor: Agents, Skills & Standards

## Summary

Consolidated 19 narrow-specialist agents into 6 role-based agents (`ai:plan`, `ai:build`, `ai:review`, `ai:scan`, `ai:write`, `ai:triage`), restructured 44 skills from 6 nested categories to flat organization (47 total with 3 new skills), and unified 7 command prefixes into single `ai:` namespace.

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Agents | 19 | 6 |
| Skills | 44 | 47 |
| Skill categories | 6 nested | flat |
| Command prefixes | 7 | 1 (`ai:`) |
| Files changed | — | ~400+ |

## Quality Gate

| Check | Result |
|-------|--------|
| Unit tests | 761 passed |
| Integration tests | 402 passed |
| `ruff check` | pass |
| `ruff format` | pass |
| Agent count (all locations) | 6 |
| Skill count (all locations) | 47 |
| Orphaned old references | 0 |
| Pre-commit gates | all pass |

## Key Decisions

- **Only `ai:build` has code write permissions** — enforces separation of concerns.
- **`ai:review` uses individual modes** — `/ai:review security`, `/ai:review pr`, etc. instead of monolithic review.
- **`category` removed from skill schema** — replaced with optional `tags` array. Flat layout uses `skills/<name>/SKILL.md`.
- **Validator updated** — `_validate_skill_identity()` no longer checks `category` field, supporting flat layout.

## Phases Completed

1. Phase 0: Scaffold spec files
2. Phase 1: Author 6 new agents
3. Phase 2: Restructure 44 skills to flat layout
4. Phase 3: Author 3 new skills (work-item, agent-card, triage)
5. Phase 4: Update standards and manifest
6. Phase 5: External integration (.github/agents, .github/prompts, .claude/commands)
7. Phase 6: Update instruction files and cross-references
8. Phase 7: Update template mirrors
9. Phase 8: Delete 19 old agent files
10. Phase 9: Verification + test fixes

## Learnings

- Template mirror sync is the largest phase by file count (~295 files) — consider automating mirror generation in future specs.
- Validator service code must be updated alongside schema changes — the `category` field check in `_validate_skill_identity()` caused test failures until removed.
- Cross-reference updates in 47 skill bodies required both manual and agent-assisted editing — a reference registry could reduce this overhead.
