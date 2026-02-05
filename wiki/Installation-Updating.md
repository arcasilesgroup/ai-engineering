# Updating the Framework

> Keep your installation up to date with the latest skills, agents, and standards.

## Quick Update

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git /tmp/ai-framework
/tmp/ai-framework/scripts/install.sh --update --target /path/to/your/project
rm -rf /tmp/ai-framework
```

## What Gets Updated

| Component | Updated? | Notes |
|-----------|----------|-------|
| `.claude/skills/*` | Yes | Except `custom/` |
| `.claude/skills/custom/*` | **No** | Team skills preserved |
| `.claude/hooks/*` | Yes | |
| `.claude/agents/*` | Yes | Except `custom/` |
| `.claude/agents/custom/*` | **No** | Team agents preserved |
| `.claude/settings.json` | Merged | Permissions preserved, hooks updated |
| `standards/*` | Yes | |
| `CLAUDE.md` (framework section) | Yes | |
| `CLAUDE.md` (team section) | **No** | |
| `context/*` | **No** | |
| `learnings/*` | **No** | |
| `CLAUDE.local.md` | **No** | |
| `pipelines/*` | **No** | CI/CD preserved |
| `.github/workflows/*` | **No** | CI/CD preserved |

## CLAUDE.md Sections

The update process respects CLAUDE.md sections:

```markdown
<!-- BEGIN:AI-FRAMEWORK:v2.0.0 -->
[This section is REPLACED during update]
<!-- END:AI-FRAMEWORK -->

<!-- BEGIN:TEAM -->
[This section is PRESERVED during update]
<!-- END:TEAM -->
```

## Migrating Legacy CLAUDE.md

If your CLAUDE.md doesn't have section markers:

```
/migrate-claude-md
```

This will:
1. Create a backup of your current CLAUDE.md
2. Add section markers
3. Preserve your team customizations in the TEAM section

## Version Checking

Check your current version:

```bash
cat .ai-version
```

Check the latest version:

```bash
cat /tmp/ai-framework/VERSION
```

## Auto-Update Detection

The framework includes a hook that checks for updates at session end:
- Compares local `.ai-version` with upstream `VERSION`
- Shows a warning if outdated (non-blocking)
- Suggests running the update command

## Manual Update Steps

If you prefer to update manually:

### 1. Replace Skills

```bash
# Backup custom skills
cp -r .claude/skills/custom /tmp/custom-skills-backup

# Replace skills
rm -rf .claude/skills
cp -r /tmp/ai-framework/.claude/skills .claude/skills

# Restore custom skills
cp -r /tmp/custom-skills-backup .claude/skills/custom
```

### 2. Replace Agents

```bash
# Backup custom agents
cp -r .claude/agents/custom /tmp/custom-agents-backup

# Replace agents
rm -rf .claude/agents
cp -r /tmp/ai-framework/.claude/agents .claude/agents

# Restore custom agents
cp -r /tmp/custom-agents-backup .claude/agents/custom
```

### 3. Replace Hooks

```bash
cp -r /tmp/ai-framework/.claude/hooks .claude/hooks
chmod +x .claude/hooks/*.sh
```

### 4. Replace Standards

```bash
cp -r /tmp/ai-framework/standards .
```

### 5. Update CLAUDE.md Framework Section

Manually copy the content between `<!-- BEGIN:AI-FRAMEWORK -->` and `<!-- END:AI-FRAMEWORK -->` markers.

### 6. Update Version

```bash
cp /tmp/ai-framework/VERSION .ai-version
```

## Verification

After updating, verify the installation:

```
/validate
```

## Rollback

If an update causes issues:

1. **Git reset** (if not committed):
   ```bash
   git checkout -- .claude/ standards/ CLAUDE.md
   ```

2. **From backup** (if available):
   ```bash
   cp -r /path/to/backup/.claude .
   cp -r /path/to/backup/standards .
   ```

3. **Reinstall specific version:**
   ```bash
   cd /tmp/ai-framework
   git checkout v1.9.0  # Previous version
   ./scripts/install.sh --update --target /path/to/project
   ```

---
**See also:** [Three-Layer Architecture](Core-Concepts-Three-Layer-Architecture) | [Breaking Changes](Migration-Breaking-Changes)
