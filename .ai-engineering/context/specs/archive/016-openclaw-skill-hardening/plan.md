---
spec: "016"
approach: "serial-phases"
---

# Plan — OpenClaw-Inspired Skill & Standards Hardening

## Architecture

### New Files

| File | Purpose | Phase |
|------|---------|-------|
| `skills/utils/doctor.md` | Unified environment diagnostics skill | 4 |
| `skills/dev/multi-agent.md` | Multi-agent orchestration patterns skill | 5 |
| `.claude/commands/utils/doctor.md` | Slash command wrapper for doctor skill | 4 |
| `.claude/commands/dev/multi-agent.md` | Slash command wrapper for multi-agent skill | 5 |

### Modified Files

| File | Change | Phase |
|------|--------|-------|
| All 43 skill files | Add YAML frontmatter | 1 |
| 6+ confusable skills | Add "When NOT to Use" section | 2 |
| `standards/framework/stacks/python.md` | Add Test Tiers section | 3 |
| `standards/framework/quality/core.md` | Map test tiers to gate stages | 3 |
| `skills/dev/test-strategy.md` | Reference test tier classification | 3 |
| `manifest.yml` | Register new skills | 4, 5 |
| `CLAUDE.md` | Add references to new skills | 4, 5 |
| Skills with binary deps | Add `requires.bins` field | 6 |
| `skills/govern/integrity-check.md` | Add frontmatter validation | 7 |
| `skills/govern/create-skill.md` | Update template with frontmatter | 7 |
| `agents/platform-auditor.md` | Reference multi-agent skill | 5 |
| `context/product/product-contract.md` | Update counters and active spec | 8 |
| Instruction files (CLAUDE.md, AGENTS.md) | Update skill counts | 8 |

### Mirror Copies

| Canonical | Mirror |
|-----------|--------|
| `.ai-engineering/skills/utils/doctor.md` | `src/ai_engineering/templates/.ai-engineering/skills/utils/doctor.md` |
| `.ai-engineering/skills/dev/multi-agent.md` | `src/ai_engineering/templates/.ai-engineering/skills/dev/multi-agent.md` |

## File Structure

```
.ai-engineering/
  context/specs/016-openclaw-skill-hardening/
    spec.md       ← WHAT
    plan.md       ← HOW (this file)
    tasks.md      ← DO
    done.md       ← DONE (at closure)
```

## Session Map

| Phase | Name | Size | Description |
|-------|------|------|-------------|
| 0 | Scaffold | S | Create spec files, activate |
| 1 | YAML Frontmatter | L | Add frontmatter to all 43 skills |
| 2 | Anti-patterns | M | Add "When NOT to Use" to 6+ confusable skills |
| 3 | Test Tiers | M | Update standards with tier classification |
| 4 | Doctor Skill | M | Create utils:doctor + slash command |
| 5 | Multi-Agent Skill | M | Create dev:multi-agent + slash command |
| 6 | Install Gating | M | Add requires.bins to applicable skills |
| 7 | Governance Updates | S | Update integrity-check, create-skill template |
| 8 | Cross-References | S | Update counters, product-contract |
| 9 | Close | S | Verify, done.md, PR |

## Patterns

- **Frontmatter schema**: `name` (kebab-case), `version` (semver), `category` (matching directory), `requires.bins` (array, optional), `requires.stacks` (array, optional), `tags` (array).
- **Anti-pattern format**: `## When NOT to Use` section placed after `## Trigger`, containing bulleted list of incorrect use cases with redirect to correct skill.
- **Commit convention**: `spec-016: Phase N — <description>` per phase.
- **Skill registration**: follow `govern:create-skill` procedure for new skills (Phase 4, 5).
- **Mirror sync**: canonical files are source of truth; templates mirror byte-identical.
