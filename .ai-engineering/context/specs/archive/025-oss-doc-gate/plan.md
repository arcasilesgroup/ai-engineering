---
spec: "025"
approach: "incremental"
---

# Plan — OSS Documentation Gate

## Architecture

### Modified Files

| File | Change |
|------|--------|
| `skills/workflows/commit/SKILL.md` | Enhanced documentation gate (CHANGELOG + README + external portal) |
| `skills/workflows/pr/SKILL.md` | Enhanced documentation gate + PR checklist items |
| `skills/workflows/acho/SKILL.md` | Updated doc gate inheritance references |
| `standards/framework/core.md` | Updated non-negotiables and command governance for OSS docs |
| `standards/framework/quality/core.md` | Documentation gate in pre-commit gate table |
| `state/decision-store.json` | D025-001 (doc gate enforcement) |
| `CHANGELOG.md` (repo root) | Spec-025 entries |

### Mirror Copies

All modified `.ai-engineering/` files require template mirror sync in `src/ai_engineering/templates/.ai-engineering/`.

## Session Map

| Phase | Name | Size | Dependencies |
|-------|------|------|-------------|
| 0 | Revert model_tier changes | S | — |
| 1 | Enhanced doc gate in 3 workflow skills | S | Phase 0 |
| 2 | Standards alignment | S | Phase 1 |
| 3 | Decision store + spec + CHANGELOG | S | Phase 2 |

## Patterns

- One atomic commit per phase.
- Decisions recorded in `decision-store.json`.
- `integrity-check` at closure.
