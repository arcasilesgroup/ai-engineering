---
spec: "008"
phases: 4
sessions: 1
---

# Plan — Claude Code Optimization

## Architecture

This spec adds Claude Code-specific configuration files and protocol changes. All changes are additive — no existing behavior is modified, only enriched.

### Key Files

| File | Action | Purpose |
|------|--------|---------|
| `.claude/settings.json` | CREATE | Project-level permissions |
| `src/.../project/.claude/settings.json` | CREATE | Template mirror |
| `CLAUDE.md` | EDIT | Session Start Protocol |
| `AGENTS.md` | EDIT | Session Start Protocol |
| `src/.../project/CLAUDE.md` | EDIT | Mirror sync |
| `src/.../project/AGENTS.md` | EDIT | Mirror sync |
| `src/.../installer/templates.py` | EDIT | `.claude/` tree deployment |
| `.claude/commands/commit.md` | EDIT | Preconditions |
| `.claude/commands/pr.md` | EDIT | Preconditions |
| `.claude/commands/acho.md` | EDIT | Preconditions |
| `src/.../commands/commit.md` | EDIT | Mirror preconditions |
| `src/.../commands/pr.md` | EDIT | Mirror preconditions |
| `src/.../commands/acho.md` | EDIT | Mirror preconditions |
| `.ai-engineering/manifest.yml` | EDIT | Register settings.json |
| `.ai-engineering/state/decision-store.json` | EDIT | S0-009 |
| `.ai-engineering/state/audit-log.ndjson` | APPEND | Event |

## Session Map

| Phase | Tasks | Serial |
|-------|-------|--------|
| 0 — Spec Lifecycle | Close 005, scaffold 008, activate | S |
| 1 — Settings + Protocol | settings.json, Session Start Protocol, mirrors | S |
| 2 — Installer | `_PROJECT_TEMPLATE_TREES` adaptation | S |
| 3 — Commands | Preconditions in commit/pr/acho + mirrors | S |
| 4 — Governance | Manifest, decision store, audit log | S |

## Patterns

- **Mirror parity**: root files must be byte-identical to `src/.../templates/project/` counterparts.
- **Additive edits**: Session Start Protocol inserted as new section, preserving all existing content.
- **Installer expansion**: `_PROJECT_TEMPLATE_TREES` covers `.claude/` entirely, not just `.claude/commands/`.
