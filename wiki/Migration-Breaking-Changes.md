# Breaking Changes

> Breaking changes between versions and how to migrate.

## v2.0.0 Breaking Changes

### Commands → Skills

**What Changed:**
- Commands directory renamed from `.claude/commands/` to `.claude/skills/`
- Command files are now called skills
- Invocation remains the same (`/skill-name`)

**Migration:**
```bash
# Automatic
./install.sh --update

# Manual
rm -rf .claude/commands/
cp -r <framework>/.claude/skills .claude/skills
```

### Consolidated Agents

**What Changed:**
- `build-validator`, `test-runner`, `security-scanner`, `quality-checker` → `verify-app`
- New agents: `code-architect`, `oncall-guide`

**Old agents removed:**
- `build-validator.md`
- `test-runner.md`
- `security-scanner.md`
- `quality-checker.md`

**Migration:**
```bash
# Remove old agents
rm -f .claude/agents/build-validator.md
rm -f .claude/agents/test-runner.md
rm -f .claude/agents/security-scanner.md
rm -f .claude/agents/quality-checker.md

# Copy new agents
cp <framework>/.claude/agents/*.md .claude/agents/
```

**Usage change:**
```
# Old
Run build-validator and security-scanner agents.

# New
Run the verify-app agent.
```

### Hooks Added

**What Changed:**
- New `.claude/hooks/` directory with 4 scripts
- New hooks configuration in `settings.json`

**Migration:**
```bash
# Copy hooks
cp -r <framework>/.claude/hooks .claude/hooks
chmod +x .claude/hooks/*.sh

# Update settings.json to include hooks configuration
```

### CLAUDE.md Sectioning

**What Changed:**
- CLAUDE.md now has section markers
- Framework content wrapped in `<!-- BEGIN:AI-FRAMEWORK -->` markers
- Team content wrapped in `<!-- BEGIN:TEAM -->` markers

**Migration:**
```
/migrate-claude-md
```

Or manually add markers around your content.

### settings.json Structure

**What Changed:**
- Added `hooks` section
- Permissions structure unchanged

**New structure:**
```json
{
  "permissions": {
    "allow": [...]
  },
  "hooks": {
    "PreToolUse": [...],
    "PostToolUse": [...],
    "Notification": [...]
  }
}
```

**Migration:**
Add the hooks section while preserving your permissions.

### Version File

**What Changed:**
- New `.ai-version` file tracks installed version
- Framework version in `VERSION` file

**Migration:**
```bash
cp <framework>/VERSION .ai-version
echo ".ai-version" >> .gitignore
```

### /commit Renamed to /commit-push

**What Changed:**
- The `/commit` skill is now `/commit-push`
- The skill now includes automatic push to remote after committing
- Same secret scanning and conventional commit message generation

**Migration:**
```
# Old
/commit

# New
/commit-push
```

**Why:** The new skill combines commit and push into a single workflow, reducing the steps needed for the common case of committing and immediately pushing changes.

---

## v1.x Breaking Changes

### Initial Release

No breaking changes from previous versions (initial release).

---

## Migration Checklist

### v1.x → v2.0

- [ ] Backup current installation
- [ ] Run `./install.sh --update` OR manual steps below:
  - [ ] Remove `.claude/commands/`
  - [ ] Copy new `.claude/skills/`
  - [ ] Remove deprecated agents
  - [ ] Copy new agents
  - [ ] Copy hooks
  - [ ] Update `settings.json`
  - [ ] Migrate CLAUDE.md sections
  - [ ] Create `.ai-version`
  - [ ] Update `.gitignore`
- [ ] Run `/validate`
- [ ] Test skills: `/commit-push`, `/review`, `/test`
- [ ] Test agents: `verify-app`
- [ ] Verify hooks work (edit a file, check auto-format)

---

## Getting Help

If you encounter issues during migration:

1. Check the [FAQ](FAQ)
2. Review [Upgrading](Migration-Upgrading) guide
3. [Open an issue](https://github.com/arcasilesgroup/ai-engineering/issues)

---
**See also:** [Upgrading](Migration-Upgrading) | [Changelog](Migration-Changelog)
