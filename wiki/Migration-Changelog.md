# Changelog

> Version history and release notes.

## Version 2.0.0 (Current)

**Release Date:** 2024

### Major Changes

- **Skills replace Commands** — All commands migrated to the new skills system
- **Consolidated Agents** — Combined multiple agents into fewer, more capable ones
- **Hooks System** — New Claude Code hooks for automation
- **CLAUDE.md Sectioning** — Safe updates with framework/team separation
- **Multi-platform Support** — Auto-detect GitHub or Azure DevOps
- **Tool Installation** — `--install-tools` flag for automated setup

### New Features

#### Skills (21 total)
- `/commit-push` — Smart commit with secret scanning + push
- `/commit-push-pr` — Full cycle to PR
- `/pr` — Create pull requests (GitHub + Azure DevOps)
- `/review` — Code review against standards
- `/test` — Generate and run tests
- `/fix` — Fix build/test/lint errors
- `/refactor` — Safe refactoring
- `/security-audit` — OWASP security review
- `/quality-gate` — Full quality checks
- `/blast-radius` — Impact analysis
- `/deploy-check` — Pre-deployment verification
- `/document` — Generate documentation
- `/create-adr` — Architecture Decision Records
- `/learn` — Record learnings
- `/validate` — Framework validation
- `/setup-project` — Initialize projects
- `/migrate-claude-md` — Migrate legacy CLAUDE.md
- Plus .NET-specific skills

#### Agents (6 total)
- `verify-app` — The "finisher" (replaces build-validator, test-runner, security-scanner, quality-checker)
- `code-architect` — Design before implementing
- `oncall-guide` — Production incident debugging
- `doc-generator` — Documentation updates
- `code-simplifier` — Complexity reduction

#### Hooks (5 total)
- `auto-format.sh` — Format after edits
- `block-dangerous.sh` — Block destructive commands
- `block-env-edit.sh` — Protect .env files
- `notify.sh` — Desktop notifications
- `pre-push` — Vulnerability check (Git)

### Breaking Changes

See [Breaking Changes](Migration-Breaking-Changes) for migration details.

### Deprecations

- Old command format (`/command-name`) → Use new skill format
- Individual agents (build-validator, test-runner) → Use `verify-app`

---

## Version 1.0.0

**Release Date:** 2024

### Initial Release

- **Commands** — Initial set of slash commands
- **Agents** — Individual agents for each task
- **Standards** — 10 standards files
- **CI/CD** — GitHub Actions + Azure Pipelines
- **Install Script** — Basic installation

---

## Upgrade Path

| From | To | Guide |
|------|-----|-------|
| 1.x | 2.0 | [Upgrading](Migration-Upgrading) |

## Version Policy

The framework follows [Semantic Versioning](https://semver.org/):

- **Major** (X.0.0) — Breaking changes
- **Minor** (x.Y.0) — New features, backwards compatible
- **Patch** (x.y.Z) — Bug fixes

## Release Schedule

- **Major releases:** As needed for significant changes
- **Minor releases:** Monthly with new features
- **Patch releases:** As needed for bug fixes

## Getting Updates

```bash
# Check current version
cat .ai-version

# Update to latest
git clone https://github.com/arcasilesgroup/ai-engineering.git /tmp/ai-framework
/tmp/ai-framework/scripts/install.sh --update --target .
```

---
**See also:** [Upgrading](Migration-Upgrading) | [Breaking Changes](Migration-Breaking-Changes)
