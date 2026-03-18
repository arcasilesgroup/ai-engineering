# Spec 012: Skills Taxonomy — Done

## Completion Date

2026-02-11

## Summary

Skills taxonomy reorganized from 6 categories (33 skills) to 7 categories (32 skills). Category names are now activity-based, short (3-8 chars), lowercase, no hyphens.

## Changes Delivered

- Eliminated tautological `swe/` by splitting into `dev/` (6), `review/` (3), `docs/` (4)
- Renamed `lifecycle/` to `govern/` (9)
- Absorbed `validation/` into `quality/` (3)
- Merged `pr-creation.md` into `workflows/pr.md` (net -1 skill)
- Renamed files for brevity: `dependency-update` -> `deps-update`, `architecture-analysis` -> `architecture`, `python-mastery` -> `python-patterns`
- Updated all 40 `.claude/commands/` wrappers
- Updated CLAUDE.md, AGENTS.md, codex.md, copilot-instructions.md

## Quality Gate

- All skill files exist at new paths
- All command wrappers point to correct locations
- All instruction files updated (template versions)
- Decision S0-010 recorded

## Decision Reference

- S0-010: Skills taxonomy reorganization — category naming and structure

## Learnings

- `.github/` canonical copies were not updated during the reorganization, causing reverse drift (templates ahead of canonical). Remediated in follow-up governance audit.
