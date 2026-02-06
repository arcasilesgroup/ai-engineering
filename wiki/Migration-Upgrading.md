# Upgrading

> How to upgrade the framework between versions.

## Quick Upgrade

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

## Upgrading from v1.x to v2.0

### Automatic Upgrade

```bash
/tmp/ai-framework/scripts/install.sh --update --target /path/to/project
```

The update script will:
1. Read your project's `.ai-version`
2. Show the changelog between versions
3. Update framework-managed files
4. Preserve your customizations
5. Update CLAUDE.md framework section (if markers present)
6. Write the new `.ai-version`

### Manual Upgrade Steps

If you prefer manual upgrade:

#### 1. Replace Skills (Commands → Skills)

```bash
# Remove old commands
rm -rf .claude/commands/

# Backup custom skills
cp -r .claude/skills/custom /tmp/custom-skills-backup 2>/dev/null || true

# Copy new skills
rm -rf .claude/skills
cp -r /tmp/ai-framework/.claude/skills .claude/skills

# Restore custom skills
cp -r /tmp/custom-skills-backup .claude/skills/custom 2>/dev/null || true
```

#### 2. Update Agents

```bash
# Remove deprecated agents
rm -f .claude/agents/build-validator.md
rm -f .claude/agents/test-runner.md
rm -f .claude/agents/security-scanner.md
rm -f .claude/agents/quality-checker.md

# Backup custom agents
cp -r .claude/agents/custom /tmp/custom-agents-backup 2>/dev/null || true

# Copy new agents
rm -rf .claude/agents
cp -r /tmp/ai-framework/.claude/agents .claude/agents

# Restore custom agents
cp -r /tmp/custom-agents-backup .claude/agents/custom 2>/dev/null || true
```

#### 3. Add Hooks

```bash
cp -r /tmp/ai-framework/.claude/hooks .claude/hooks
chmod +x .claude/hooks/*.sh
```

#### 4. Update settings.json

Merge the new hooks configuration into your `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [...],
    "PostToolUse": [...],
    "Notification": [...]
  }
}
```

Preserve any custom permissions you've added.

#### 5. Update CLAUDE.md

If your CLAUDE.md has section markers, update the framework section.

If not, run `/migrate-claude-md` to add markers, or manually:
1. Copy your Project Overview and custom content
2. Replace CLAUDE.md with the new template
3. Paste your content into the TEAM section

#### 6. Update Version

```bash
cp /tmp/ai-framework/VERSION .ai-version
```

#### 7. Update .gitignore

Add these entries:
```
CLAUDE.local.md
.ai-version
```

## Migrating CLAUDE.md

### If You Have Section Markers

Your CLAUDE.md already has:
```markdown
<!-- BEGIN:AI-FRAMEWORK:vX.X.X -->
...
<!-- END:AI-FRAMEWORK -->

<!-- BEGIN:TEAM -->
...
<!-- END:TEAM -->
```

The update script will automatically update the framework section.

### If You Don't Have Section Markers

Run the migration skill:

```
/migrate-claude-md
```

This will:
1. Create a backup of your current CLAUDE.md
2. Add section markers
3. Preserve your customizations in the TEAM section

### Manual Migration

1. Identify your customizations (project description, custom rules)
2. Copy them to a temporary file
3. Replace CLAUDE.md with the new template
4. Paste your customizations into the TEAM section

## Verification

After upgrading:

```
/validate
```

Expected output:
```
✓ CLAUDE.md present (v2.0.0)
✓ .claude/settings.json present
✓ Skills directory present (11 skills)
✓ Agents directory present (4 agents)
✓ Hooks configured
✓ Standards present
✓ Platform detected

Framework is correctly installed.
```

## Rollback

If the upgrade causes issues:

### Git Reset (If Not Committed)

```bash
git checkout -- .claude/ standards/ CLAUDE.md
```

### From Backup

```bash
cp -r /path/to/backup/.claude .
cp -r /path/to/backup/standards .
cp /path/to/backup/CLAUDE.md .
```

### Reinstall Previous Version

```bash
cd /tmp/ai-framework
git checkout v1.9.0  # Previous version tag
./scripts/install.sh --update --target /path/to/project
```

---
**See also:** [Changelog](Migration-Changelog) | [Breaking Changes](Migration-Breaking-Changes)
