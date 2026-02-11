---
spec: "008"
title: "Claude Code Optimization"
status: "IN_PROGRESS"
created: "2026-02-11"
branch: "spec-008/claude-code-optimization"
base: "2ebbd30"
---

# Spec 008 — Claude Code Optimization

## Problem

Claude Code sessions in this repository lack project-level permission settings (`.claude/settings.json`), a session start protocol ensuring agents read the active spec before work, and enriched command wrappers with preconditions. This causes:

1. **Permission drift** — each session starts without pre-approved tool permissions, requiring manual approvals.
2. **Context amnesia** — agents skip reading `_active.md` and `decision-store.json`, re-asking decided questions.
3. **Command fragility** — `/commit`, `/pr`, `/acho` execute without verifying branch safety or spec alignment.

## Solution

1. **`.claude/settings.json`** — project-level permissions for Bash, MCP, and tool access patterns.
2. **Session Start Protocol** — mandatory read sequence in CLAUDE.md/AGENTS.md before non-trivial work.
3. **Installer `.claude/` tree deployment** — expand installer to copy entire `.claude/` directory (not just commands).
4. **Command enrichment** — add precondition blocks to commit/pr/acho wrappers.

## Scope

### In Scope

- Create `.claude/settings.json` (root + template mirror).
- Insert Session Start Protocol in CLAUDE.md and AGENTS.md.
- Adapt installer `_PROJECT_TEMPLATE_TREES` for full `.claude/` directory.
- Enrich commit.md, pr.md, acho.md with preconditions.
- Governance registration (manifest, decision store, audit log).

### Out of Scope

- Claude hooks (`.claude/hooks/`) — git hooks provide agnostic enforcement.
- MCP server configuration — session-specific, not project-level.

## Decisions

- **S0-009**: `.claude/settings.json` provides project-level permissions; no Claude hooks — git hooks enforce agnostically.
