# Module 10: Versioning, Updates & Personalization

## Overview

Learn how to keep the framework up to date, customize it for your team, and personalize it for individual engineers.

---

## Framework Architecture: 3 Layers

```
┌──────────────────────────────────────────────┐
│ LAYER 1: Framework (upstream, versioned)     │
│ Skills, hooks, agents, standards, workshop   │
│ → Updated via install.sh --update            │
│ → NEVER edited directly in the project       │
├──────────────────────────────────────────────┤
│ LAYER 2: Team (project, committed)           │
│ CLAUDE.md, context/, learnings/,             │
│ .claude/skills/custom/, .claude/agents/custom/│
│ → Maintained by the team                     │
│ → NEVER overwritten by updates               │
├──────────────────────────────────────────────┤
│ LAYER 3: Personal (local, NOT committed)     │
│ CLAUDE.local.md, ~/.claude/CLAUDE.md,        │
│ .claude/settings.local.json                  │
│ → Individual engineer preferences            │
│ → NEVER shared or overwritten                │
└──────────────────────────────────────────────┘
```

---

## Checking Your Version

```bash
# In your project
cat .ai-version
# → 2.0.0

# In the framework repo
cat VERSION
# → 2.0.0
```

If `.ai-version` is lower than `VERSION`, you can update.

---

## Updating the Framework

### Automatic Update

```bash
# From the framework repository
scripts/install.sh --update --target /path/to/your/project
```

This will:
1. Read `.ai-version` from your project.
2. Show the changelog between versions.
3. Update framework files (skills, hooks, agents, standards).
4. Preserve your customizations (CLAUDE.md, context/, learnings/, custom/).
5. Write the new `.ai-version`.

### What Gets Updated vs Preserved

| Updated (overwritten) | Preserved (never touched) |
|----------------------|--------------------------|
| `.claude/skills/*` | `.claude/skills/custom/*` |
| `.claude/hooks/*` | `CLAUDE.md` |
| `.claude/agents/*` | `context/*` |
| `standards/*` | `learnings/*` |
| `workshop/*` | `.claude/agents/custom/*` |
| `.github/copilot-instructions.md` | `CLAUDE.local.md` |
| `.github/instructions/*` | `pipelines/*` |
| `.claude/settings.json` (merged) | `.github/workflows/*` |

### Manual Update

See [UPGRADING.md](../UPGRADING.md) for step-by-step manual upgrade instructions.

---

## Team Customization (Layer 2)

### Custom Skills

Create team-specific skills in `.claude/skills/custom/`:

```
.claude/skills/custom/
├── deploy-staging/SKILL.md
├── notify-slack/SKILL.md
└── run-e2e/SKILL.md
```

These are never overwritten by framework updates.

**Example custom skill:**

```markdown
---
name: deploy-staging
description: Deploy to staging environment
disable-model-invocation: true
---

## Context

Deploys the current branch to the staging environment.

## Steps

### 1. Verify Prerequisites
- Ensure all tests pass: run verify-app agent
- Ensure branch is pushed

### 2. Deploy
- Run: `az webapp deploy --name my-app-staging ...`

### 3. Verify
- Smoke test the staging URL

## Verification
- Staging environment is accessible
- Smoke tests pass
```

### Custom Agents

Create team-specific agents in `.claude/agents/custom/`:

```
.claude/agents/custom/
├── perf-profiler.md
└── data-migrator.md
```

---

## Personal Customization (Layer 3)

### CLAUDE.local.md

Your personal session context. Not committed to the repository.

```bash
cp CLAUDE.local.md.example CLAUDE.local.md
```

Edit it with:
- Current sprint and work items
- Personal preferences
- Local environment details

### ~/.claude/CLAUDE.md

Your global preferences, applied to ALL projects:

```markdown
# My Preferences
- Always use English for commit messages
- Prefer explicit types over type inference
- Run tests after every implementation step
- I prefer 90% coverage (team standard is 80%)
```

### .claude/settings.local.json

Personal permission and hook overrides:

```json
{
  "permissions": {
    "allow": ["Bash(docker:*)"]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "say 'done' 2>/dev/null || true" }]
      }
    ]
  }
}
```

---

## Semantic Versioning

The framework follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes — command/skill format changes, removed features, changed directory structure.
- **MINOR** (0.X.0): New features — new skills, agents, standards, hooks. Backward compatible.
- **PATCH** (0.0.X): Bug fixes — typos, corrections, small improvements.

---

## Contributing to the Framework

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- How to create new skills
- How to create new hooks
- How to add support for new platforms
- Versioning policy

---

## Exercise

1. Check your project's framework version with `cat .ai-version`.
2. Create a custom skill in `.claude/skills/custom/my-skill/SKILL.md`.
3. Create a `CLAUDE.local.md` with your current sprint context.
4. Verify everything works with `/validate`.

## Next

You've completed the full workshop. Return to [Module 0: Introduction](00-introduction.md) for a refresher on any topic.
