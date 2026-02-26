---
spec: "024"
approach: "incremental"
---

# Plan — Model Tiering + Documentation Enforcement

## Architecture

### Modified Files

| File | Change |
|------|--------|
| `standards/framework/skills-schema.md` | Add `model_tier` field + Model Tier Standard section |
| `skills/workflows/commit/SKILL.md` | Add `model_tier: fast` + documentation gate step |
| `skills/workflows/pr/SKILL.md` | Add `model_tier: fast` + documentation gate step + checklist |
| `skills/workflows/acho/SKILL.md` | Add `model_tier: fast` + doc gate reference |
| `skills/workflows/cleanup/SKILL.md` | Add `model_tier: fast` |
| `skills/workflows/pre-implementation/SKILL.md` | Add `model_tier: fast` |
| `.claude/commands/commit.md` | Add model tier dispatch hint |
| `.claude/commands/pr.md` | Add model tier dispatch hint |
| `.claude/commands/acho.md` | Add model tier dispatch hint |
| `.claude/commands/cleanup.md` | Add model tier dispatch hint |
| `.claude/commands/pre-implementation.md` | Add model tier dispatch hint |
| `.github/prompts/commit.prompt.md` | Add advisory model tier note |
| `.github/prompts/pr.prompt.md` | Add advisory model tier note |
| `.github/prompts/acho.prompt.md` | Add advisory model tier note |
| `.github/prompts/cleanup.prompt.md` | Add advisory model tier note |
| `.github/prompts/pre-implementation.prompt.md` | Add advisory model tier note |
| `standards/framework/core.md` | Add doc gate to non-negotiables |
| `standards/framework/quality/core.md` | Add doc gate to gate table |
| `manifest.yml` | Add model_tier to commands |
| `state/decision-store.json` | Add D024-001, D024-002 |
| `CHANGELOG.md` (repo root) | Add spec-024 entries |

### Mirror Copies

All modified `.ai-engineering/` files require template mirror sync in `src/ai_engineering/templates/.ai-engineering/`.

## Session Map

| Phase | Name | Size | Sessions | Dependencies |
|-------|------|------|----------|-------------|
| 0 | Scaffold | S | 1 | — |
| 1 | Schema | S | 1 | Phase 0 |
| 2 | Tier Assignment | S | 1 | Phase 1 ║ Phase 4 |
| 3 | Wrappers | S | 1 | Phase 2 ║ Phase 4 |
| 4 | Documentation Gate | M | 1 | Phase 1 ║ Phase 2-3 |
| 5 | Standards Alignment | S | 1 | Phase 4 |
| 6 | Registration + Integrity | S | 1 | Phase 5 |

## Two-Tier Model Design

| Tier | Value | Claude Code | Copilot | Generic |
|------|-------|-------------|---------|---------|
| Default | _(omitted)_ | Opus 4.6 | User choice (Opus, GPT-5.3-Codex) | Most capable |
| Fast | `fast` | Haiku via `model: "haiku"` | User choice (Haiku, GPT-5.3-Codex) | Most cost-efficient |

## Patterns

- One atomic commit per phase.
- Decisions recorded in `decision-store.json`.
- `integrity-check` at Phase 6 closure.
