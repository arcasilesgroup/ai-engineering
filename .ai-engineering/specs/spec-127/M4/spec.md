---
id: sub-005
parent: spec-127
milestone: M4
title: "Renames + Mergers (46 skills, 23 agents, no aliases)"
status: planning
files:
  - .claude/skills/ai-build/
  - .claude/skills/ai-visual/
  - .claude/skills/ai-gtm/
  - .claude/skills/ai-mcp-audit/
  - .claude/skills/ai-simplify-sweep/
  - .claude/skills/ai-observe/
  - .claude/skills/ai-skill-tune/
  - .claude/skills/ai-ide-audit/
  - .claude/skills/ai-board/
  - .claude/agents/ai-build.md
  - .claude/agents/reviewer-context.md
  - .claude/agents/reviewer-validator.md
  - .claude/skills/ai-help/SKILL.md
  - tests/mirrors/test_count_parity.py
  - .github/skills/**
  - .codex/skills/**
  - .gemini/skills/**
  - CHANGELOG.md
depends_on:
  - sub-003
---

# Sub-Spec 005: M4 — Renames + Mergers

## Scope

Apply the rename + merger surface per D-127-04 (no aliases, single rename
commit each), D-127-05 (`/ai-canvas` → `/ai-visual`), D-127-10 (final counts
46 skills, 23 agents), D-127-11 (`/ai-build` canonical implementation
gateway), D-127-12 (`/ai-autopilot` single autonomous wrapper).

Skill renames: `/ai-dispatch` → `/ai-build`, `/ai-canvas` → `/ai-visual`,
`/ai-market` → `/ai-gtm`, `/ai-mcp-sentinel` → `/ai-mcp-audit`,
`/ai-entropy-gc` → `/ai-simplify-sweep`, `/ai-instinct` → `/ai-observe`,
`/ai-skill-evolve` → `/ai-skill-tune`, `/ai-platform-audit` → `/ai-ide-audit`.

Skill mergers: `/ai-run` deleted (`--backlog` flag added to `/ai-autopilot`),
`ai-board-discover` + `ai-board-sync` → `/ai-board <discover|sync>` subcommand,
`/ai-release-gate` → `/ai-verify --release` mode flag.

Agent renames: `review-context-explorer` → `reviewer-context`,
`review-finding-validator` → `reviewer-validator`. Agent deletions:
`ai-run-orchestrator` (functionality absorbed by `ai-autopilot --source
<github|ado|local>`), `reviewer-design` (rules absorbed into
`reviewer-frontend`).

Update `/ai-help` to matchback-suggest new name on legacy-name typo (≤30 LOC).
Re-run `python .ai-engineering/scripts/sync_command_mirrors.py`. Verify
`tests/mirrors/test_count_parity.py` green; skill count = 46, agent count
= 23. Update CHANGELOG.md with rename table + deletion list.

## Exploration

### Rename inventory (8 skills + 2 agents)

Skill renames (single commit each per D-127-04):
- `ai-dispatch` → `ai-build` (D-127-11 canonical implementation gateway)
- `ai-canvas` → `ai-visual` (D-127-05)
- `ai-market` → `ai-gtm`
- `ai-mcp-sentinel` → `ai-mcp-audit`
- `ai-entropy-gc` → `ai-simplify-sweep`
- `ai-instinct` → `ai-observe`
- `ai-skill-evolve` → `ai-skill-tune`
- `ai-platform-audit` → `ai-ide-audit`

All source dirs present at `.claude/skills/`. Each rename: `git mv` skill dir,
update `name:` frontmatter in SKILL.md, update `.claude/settings.json` skill
registration, update `.claude/agents/<name>.md` if pair exists.

Agent renames:
- `review-context-explorer.md` → `reviewer-context.md`
- `review-finding-validator.md` → `reviewer-validator.md`

### Mergers (3)

- `/ai-run` deleted; `--backlog` flag added to `/ai-autopilot` skill body
  (D-127-12 single autonomous wrapper)
- `ai-board-discover` + `ai-board-sync` → `/ai-board <discover|sync>`
  subcommand; merge SKILL.md bodies, preserve both code paths under
  `## Subcommands`
- `/ai-release-gate` → `/ai-verify --release` mode flag; delete release-gate
  skill dir, extend `/ai-verify` SKILL.md with `--release` doc

### Agent deletions (3)

- `ai-run-orchestrator.md` (functionality absorbed by `ai-autopilot --source
  <github|ado|local>` flag)
- `reviewer-design.md` (rules absorbed into `reviewer-frontend.md` body)
- `ai-dispatch.md` if duplicate after `ai-build` rename

### `/ai-help` matchback-suggest

Update `.claude/skills/ai-help/SKILL.md` to detect legacy-name typos and
suggest the new name. ≤30 LOC addition; lookup table of `{legacy: new}`.

### Mirror regen

Run `python .ai-engineering/scripts/sync_command_mirrors.py` after every rename
batch; verify `.github/`, `.codex/`, `.gemini/` regenerate proportionally.

### Test surface

`tests/mirrors/test_count_parity.py` asserts skill count = 46 across all 4
mirror trees + agent count = 23. RED first (no test yet), GREEN after counts
land.

### Dependency

- sub-003 (M2): CSO descriptions must exist on the new names before commit.
  Without M2, M4 commits ship descriptions that re-grade as D in M2.
