# Upgrading the AI Engineering Framework

## From v1.x to v2.0

### Overview

v2.0 migrates from commands to skills, consolidates agents, adds hooks, and introduces the versioning system. This is a breaking change.

### Automatic Upgrade

```bash
# From the framework repository
scripts/install.sh --update --target /path/to/your/project
```

The update script will:
1. Read your project's `.ai-version` to determine current version.
2. Show the changelog between versions.
3. Update framework-managed files (skills, hooks, agents, standards).
4. Preserve your customizations (CLAUDE.md, context/, learnings/, custom/).
5. Write the new `.ai-version`.

### Manual Upgrade

If you prefer to upgrade manually:

#### 1. Replace commands with skills

```bash
# Remove old commands
rm -rf .claude/commands/

# Copy new skills
cp -r <framework>/.claude/skills/ .claude/skills/
```

#### 2. Update agents

```bash
# Remove deprecated agents
rm .claude/agents/build-validator.md
rm .claude/agents/test-runner.md
rm .claude/agents/security-scanner.md
rm .claude/agents/quality-checker.md

# Copy new agents
cp <framework>/.claude/agents/verify-app.md .claude/agents/
cp <framework>/.claude/agents/code-architect.md .claude/agents/
cp <framework>/.claude/agents/oncall-guide.md .claude/agents/

# Update existing agents
cp <framework>/.claude/agents/code-simplifier.md .claude/agents/
```

#### 3. Add hooks

```bash
cp -r <framework>/.claude/hooks/ .claude/hooks/
chmod +x .claude/hooks/*.sh
```

#### 4. Update settings.json

Merge the new hooks configuration into your `.claude/settings.json`. See the framework's `settings.json` for the full structure. Important: preserve any custom permissions you've added.

#### 5. Update CLAUDE.md

Your `CLAUDE.md` has been customized for your project, so it is NOT overwritten automatically. You should manually add the new sections from the framework's `CLAUDE.md`:

- Verification Protocol
- Reconnaissance Before Writing
- Two Options for High Stakes
- Danger Zones
- Layered Memory
- Reliability Template

Also update the Skills and Agents sections to reflect the new structure.

#### 6. Add versioning files

```bash
cp <framework>/VERSION .ai-version
```

#### 7. Update .gitignore

Add these entries:
```
CLAUDE.local.md
.ai-version
```

### What Is Preserved During Upgrade

| Directory/File | Updated? | Notes |
|----------------|----------|-------|
| `.claude/skills/*` | Yes | Overwritten (except `custom/`) |
| `.claude/skills/custom/*` | No | Team custom skills preserved |
| `.claude/hooks/*` | Yes | Overwritten |
| `.claude/agents/*` | Yes | Overwritten (except `custom/`) |
| `.claude/agents/custom/*` | No | Team custom agents preserved |
| `.claude/settings.json` | Merged | Custom permissions preserved, hooks updated |
| `standards/*` | Yes | Overwritten |
| `workshop/*` | Yes | Overwritten |
| `CLAUDE.md` | No | Team-customized, never overwritten |
| `context/*` | No | Project-specific, preserved |
| `learnings/*` | No | Accumulated knowledge, preserved |
| `CLAUDE.local.md` | No | Personal, never touched |
| `pipelines/*` | No | CI/CD customized, preserved |
| `.github/workflows/*` | No | CI/CD customized, preserved |
| `.github/copilot-instructions.md` | Yes | Overwritten |
| `.github/instructions/*` | Yes | Overwritten |

### Verification

After upgrading, run:

```
/validate
```

This will check that all framework files are present, correctly structured, and platform detection is working.
