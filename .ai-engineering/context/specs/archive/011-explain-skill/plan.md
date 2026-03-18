---
spec: "011"
approach: "serial-phases"
---

# Plan — Explain Skill

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `.ai-engineering/skills/docs/explain.md` | Canonical skill: Feynman-style explanations |
| `src/ai_engineering/templates/.ai-engineering/skills/docs/explain.md` | Template mirror (byte-identical) |
| `.claude/commands/swe/explain.md` | Slash command wrapper |
| `src/ai_engineering/templates/project/.claude/commands/swe/explain.md` | Command mirror (byte-identical) |

### Modified Files

| File | Change |
|------|--------|
| `.ai-engineering/context/specs/_active.md` | Point to 011-explain-skill |
| `.ai-engineering/context/product/product-contract.md` | Active spec → 011, counter 32 → 33 |
| `CLAUDE.md` | Add explain.md to SWE Skills list |
| `AGENTS.md` | Add explain.md to SWE Skills list |
| `codex.md` | Add explain.md to SWE Skills list |
| `.github/copilot-instructions.md` | Add explain.md to SWE Skills list |
| `src/ai_engineering/templates/project/CLAUDE.md` | Add explain.md to SWE Skills list |
| `src/ai_engineering/templates/project/AGENTS.md` | Add explain.md to SWE Skills list |
| `src/ai_engineering/templates/project/codex.md` | Add explain.md to SWE Skills list |
| `src/ai_engineering/templates/project/copilot-instructions.md` | Add explain.md to SWE Skills list |
| `CHANGELOG.md` | Add entry under [Unreleased] → Added |
| `.ai-engineering/skills/dev/debug.md` | Add explain.md cross-reference |
| `.ai-engineering/skills/dev/code-review.md` | Add explain.md cross-reference |
| `.ai-engineering/skills/review/architecture.md` | Add explain.md cross-reference |
| `.ai-engineering/agents/debugger.md` | Add explain.md cross-reference |
| `.ai-engineering/agents/architect.md` | Add explain.md cross-reference |
| `src/ai_engineering/templates/.ai-engineering/skills/dev/debug.md` | Mirror cross-reference |
| `src/ai_engineering/templates/.ai-engineering/skills/dev/code-review.md` | Mirror cross-reference |
| `src/ai_engineering/templates/.ai-engineering/skills/review/architecture.md` | Mirror cross-reference |
| `src/ai_engineering/templates/.ai-engineering/agents/debugger.md` | Mirror cross-reference |
| `src/ai_engineering/templates/.ai-engineering/agents/architect.md` | Mirror cross-reference |

## Session Map

| Phase | Size | Description |
|-------|------|-------------|
| 0 | S | Scaffold spec files + activate |
| 1 | M | Author canonical explain.md skill file |
| 2 | S | Template mirror + slash command wrapper + command mirror |
| 3 | M | 8 instruction files + counter + changelog |
| 4 | S | Cross-references: 3 skills + 2 agents (canonical + mirror) |
| 5 | S | 8-point verification checklist + content-integrity |
