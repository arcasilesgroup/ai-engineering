# Three-Layer Architecture

> Framework, Team, and Personal layers that compose to create your complete configuration.

## Overview

The AI Engineering Framework uses a layered architecture that separates concerns and allows customization at different levels.

```
┌──────────────────────────────────────────────┐
│ LAYER 1: Framework (upstream, versioned)     │
│ Skills, hooks, agents, standards, workshop   │
│ → Updated via install.sh --update            │
├──────────────────────────────────────────────┤
│ LAYER 2: Team (project, committed)           │
│ CLAUDE.md, context/, learnings/, custom/     │
│ → Maintained by the team                     │
├──────────────────────────────────────────────┤
│ LAYER 3: Personal (local, NOT committed)     │
│ CLAUDE.local.md, ~/.claude/CLAUDE.md         │
│ → Individual engineer preferences            │
└──────────────────────────────────────────────┘
```

## Layer 1: Framework

**Scope:** Universal rules and tools that apply to all projects using the framework.

**What's included:**
- Skills (`/commit-push`, `/review`, `/test`, etc.)
- Agents (verify-app, code-architect, etc.)
- Hooks (auto-format, block-dangerous, etc.)
- Standards templates
- CI/CD templates

**How it's managed:**
- Versioned with semver
- Updated via `install.sh --update`
- Never modified directly in your project

## Layer 2: Team

**Scope:** Project-specific content shared across all team members.

**What's included:**
- `CLAUDE.md` TEAM section
- `context/` - Project context, architecture, glossary
- `learnings/` - Accumulated knowledge
- `.claude/skills/custom/` - Team custom skills
- `.claude/agents/custom/` - Team custom agents

**How it's managed:**
- Committed to git
- Maintained by the team
- Never overwritten by framework updates

### Team Content Examples

**context/project.md:**
```markdown
# Project: OrderService

## Overview
A microservice handling order lifecycle management.

## Objectives
- Process 10,000 orders/minute
- 99.9% uptime SLA
```

**learnings/dotnet.md:**
```markdown
## Azure Service Bus
- Always use sessions for ordered processing
- Discovered: 2024-03-15
- Context: Order processing was failing due to message reordering
```

## Layer 3: Personal

**Scope:** Individual preferences and local environment configuration.

**What's included:**
- `CLAUDE.local.md` - Project-specific personal overrides
- `~/.claude/CLAUDE.md` - Global personal preferences

**How it's managed:**
- NOT committed to git (`.gitignore`)
- Each developer maintains their own
- Overrides team settings

### Personal Content Examples

**CLAUDE.local.md:**
```markdown
## Sprint Context
- Working on: JIRA-1234 (User authentication)
- Focus areas: AuthController, TokenService
- Skip: PaymentService (not my area)

## Personal Preferences
- Prefer verbose logging during debugging
- Use tab width 4 (team uses 2)
```

**~/.claude/CLAUDE.md:**
```markdown
## Global Preferences
- Always use vim keybindings in examples
- Prefer functional programming style
- Timezone: UTC-5
```

## Loading Order

When Claude Code starts, it loads configurations in order:

1. `~/.claude/CLAUDE.md` (global personal)
2. `./CLAUDE.md` (project team)
3. `./CLAUDE.local.md` (project personal)

Later configurations override earlier ones.

## What Gets Updated vs Preserved

| Directory/File | Framework Updates | Notes |
|----------------|-------------------|-------|
| `.claude/skills/*` | Updated | Except `custom/` |
| `.claude/skills/custom/*` | Preserved | Team skills |
| `.claude/hooks/*` | Updated | |
| `.claude/agents/*` | Updated | Except `custom/` |
| `.claude/agents/custom/*` | Preserved | Team agents |
| `standards/*` | Updated | |
| `CLAUDE.md` (framework section) | Updated | Marked section only |
| `CLAUDE.md` (team section) | Preserved | |
| `context/*` | Preserved | |
| `learnings/*` | Preserved | |
| `CLAUDE.local.md` | Never touched | |

---
**See also:** [CLAUDE.md](Core-Concepts-CLAUDE-md) | [Updating](Installation-Updating)
