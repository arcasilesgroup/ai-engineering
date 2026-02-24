---
spec: "020"
approach: "serial-phases"
---

# Plan — Multi-Agent Model Evolution

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `skills/<category>/<name>/SKILL.md` | Migrated skill content (one per skill, 46 total) |
| `skills/<category>/<name>/metadata.yml` | Optional: gating metadata when complex |
| `skills/workflows/commit/scripts/` | Pilot: deterministic commit gate scripts |
| `skills/dev/debug/references/` | Pilot: on-demand reference docs for debugging |
| `skills/review/security/references/` | Pilot: OWASP reference loaded on-demand |
| `standards/framework/skills-schema.md` | Skill directory and gating schema standard |

### Modified Files

| File | Change |
|------|--------|
| All 46 `skills/**/*.md` | Migrate from flat file to `SKILL.md` in directory |
| All 9 `agents/*.md` | Add structured YAML frontmatter |
| `skills/utils/` → `skills/patterns/` | Rename directory |
| `CLAUDE.md` | Progressive disclosure guidelines, updated skill paths |
| `AGENTS.md` | Updated skill/agent references |
| `codex.md` | Updated references |
| `.github/copilot-instructions.md` | Updated references |
| `.github/instructions/**` | Updated references |
| `.github/prompts/**` | Updated command paths |
| `.github/agents/**` | Updated agent paths |
| `.claude/commands/**` | Updated skill paths |
| `manifest.yml` | Reflect directory structure |
| `context/product/product-contract.md` | Active spec update |
| `standards/framework/core.md` | Add skill schema and gating rules |

### Mirror Copies

| Canonical | Template Mirror |
|-----------|----------------|
| `.ai-engineering/skills/**` | `src/ai_engineering/templates/.ai-engineering/skills/**` |
| `.ai-engineering/agents/**` | `src/ai_engineering/templates/.ai-engineering/agents/**` |

## File Structure

Post-migration skill directory structure:

```
skills/
├── workflows/
│   ├── commit/
│   │   ├── SKILL.md
│   │   └── scripts/          ← pilot
│   ├── pr/
│   │   └── SKILL.md
│   ├── acho/
│   │   └── SKILL.md
│   ├── pre-implementation/
│   │   └── SKILL.md
│   └── cleanup/
│       └── SKILL.md
├── dev/
│   ├── debug/
│   │   ├── SKILL.md
│   │   └── references/       ← pilot
│   ├── code-review/
│   │   └── SKILL.md
│   ├── refactor/
│   │   └── SKILL.md
│   ├── test-strategy/
│   │   └── SKILL.md
│   ├── migration/
│   │   └── SKILL.md
│   ├── deps-update/
│   │   └── SKILL.md
│   ├── cicd-generate/
│   │   └── SKILL.md
│   └── multi-agent/
│       └── SKILL.md
├── review/
│   ├── architecture/
│   │   └── SKILL.md
│   ├── security/
│   │   ├── SKILL.md
│   │   └── references/       ← pilot
│   ├── performance/
│   │   └── SKILL.md
│   ├── dast/
│   │   └── SKILL.md
│   └── container-security/
│       └── SKILL.md
├── quality/
│   ├── audit-code/
│   │   └── SKILL.md
│   ├── audit-report/
│   │   └── SKILL.md
│   ├── install-check/
│   │   └── SKILL.md
│   ├── release-gate/
│   │   └── SKILL.md
│   ├── test-gap-analysis/
│   │   └── SKILL.md
│   ├── sbom/
│   │   └── SKILL.md
│   └── docs-audit/
│       └── SKILL.md
├── govern/
│   ├── integrity-check/
│   │   └── SKILL.md
│   ├── contract-compliance/
│   │   └── SKILL.md
│   ├── ownership-audit/
│   │   └── SKILL.md
│   ├── accept-risk/
│   │   └── SKILL.md
│   ├── resolve-risk/
│   │   └── SKILL.md
│   ├── renew-risk/
│   │   └── SKILL.md
│   ├── create-agent/
│   │   └── SKILL.md
│   ├── create-skill/
│   │   └── SKILL.md
│   ├── create-spec/
│   │   └── SKILL.md
│   ├── delete-agent/
│   │   └── SKILL.md
│   └── delete-skill/
│       └── SKILL.md
├── docs/
│   ├── changelog/
│   │   └── SKILL.md
│   ├── explain/
│   │   └── SKILL.md
│   ├── writer/
│   │   └── SKILL.md
│   └── prompt-design/
│       └── SKILL.md
└── patterns/                  ← renamed from utils/
    ├── doctor/
    │   └── SKILL.md
    ├── git-helpers/
    │   └── SKILL.md
    ├── platform-detect/
    │   └── SKILL.md
    ├── python-patterns/
    │   └── SKILL.md
    ├── dotnet-patterns/
    │   └── SKILL.md
    └── nextjs-patterns/
        └── SKILL.md
```

## Session Map

| Phase | Name | Size | Scope | Dependencies |
|-------|------|------|-------|--------------|
| 0 | Scaffold | S | Spec files + branch | None |
| 1 | Schema & Standards | M | Define skill directory schema, gating metadata schema, agent frontmatter schema in standards | None |
| 2 | Skill Directory Migration (workflows + govern) | L | Migrate 16 skills to directory format | Phase 1 |
| 3 | Skill Directory Migration (dev + review + quality) | L | Migrate 19 skills to directory format | Phase 1 |
| 4 | Skill Directory Migration (docs + patterns) | M | Migrate 10 skills, rename utils → patterns | Phase 1 |
| 5 | Agent Frontmatter Evolution | M | Add structured metadata to all 9 agents | Phase 1 |
| 6 | Pilot Resources (commit, debug, security) | M | Add scripts/ and references/ to 3 pilot skills | Phases 2-3 |
| 7 | Cross-Reference Update | L | Update CLAUDE.md, AGENTS.md, codex.md, copilot-instructions, commands, prompts, agents, manifest | Phases 2-5 |
| 8 | Progressive Disclosure & Token Budget | M | CLAUDE.md guidelines, token measurement, documentation | Phase 7 |
| 9 | Integrity Check & Close | S | Run integrity-check, verify acceptance criteria, create done.md | Phase 8 |

## Patterns

- **Migration pattern**: for each skill, create directory → move content to `SKILL.md` → add AgentSkills frontmatter → add gating metadata → verify.
- **Agent evolution pattern**: add frontmatter block above existing Identity section → preserve all existing content → verify.
- **Cross-reference update**: systematic search-and-replace of old paths → verify no broken references.
- **Commit pattern**: one atomic commit per phase: `spec-020: Phase N — <description>`.
- **Rollback safety**: the migration is purely structural (content preserved); git revert is safe at any phase.
