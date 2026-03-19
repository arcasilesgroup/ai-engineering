---
spec: "043"
approach: "serial-phases"
---

# Plan — Slim Root Instructions

## Architecture

### Modified Files

| File | Change | Size |
|------|--------|------|
| `CLAUDE.md` | Slim to ~60 lines: keep prohibitions + session start + pointers | M |
| `AGENTS.md` | Slim to ~70 lines: keep agent mandates + session start + pointers | M |
| `.github/copilot-instructions.md` | Slim to ~40 lines: keep spec-as-gate + session start + pointers | S |
| `.ai-engineering/context/product/framework-contract.md` | Add command contract section, consolidate pipeline strategy | S |
| `.ai-engineering/context/product/product-contract.md` | Verify skills/agents/CLI tables are complete (already there) | S |
| `.ai-engineering/skills/spec/SKILL.md` | Add "read product-contract §7" directive in Phase 5 | S |
| `.ai-engineering/skills/pr/SKILL.md` | Add "read product-contract §7" directive | S |
| `.ai-engineering/agents/plan.md` | Add explicit "read contracts" step in Behavior section | S |

### Mirror Copies

Template mirrors in `src/ai_engineering/templates/.ai-engineering/` will need sync after merge — handled by `ai-eng validate`.

## Session Map

### Phase 1: Consolidate Contracts [M]

Ensure `framework-contract.md` and `product-contract.md` have all the content that will be removed from root files.

- Add Command Contract section to `framework-contract.md`
- Verify pipeline strategy is complete in `framework-contract.md`
- Verify skills/agents tables are current in `product-contract.md`
- Verify CLI commands table is in `product-contract.md`

### Phase 2: Slim Root Files [M]

Rewrite the 3 root instruction files to pointer format.

- Slim `CLAUDE.md` to ~60 lines
- Slim `AGENTS.md` to ~70 lines
- Slim `copilot-instructions.md` to ~40 lines

### Phase 3: Add Loading Directives to Skills [S]

Add explicit "read contract" directives to skills that need product/governance context.

- Update `skills/spec/SKILL.md`
- Update `skills/pr/SKILL.md`
- Update `agents/plan.md`

## Patterns

- One canonical location per piece of information
- Root files = platform-specific behavior + pointers
- Contracts = source of truth for governance and product context
- On-demand loading respects progressive disclosure budget
