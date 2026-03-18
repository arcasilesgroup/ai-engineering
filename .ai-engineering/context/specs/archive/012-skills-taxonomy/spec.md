# Spec 012: Skills Taxonomy Reorganization

## Problem

The original skills taxonomy used 6 categories (33 skills) with tautological naming (`swe/` for software engineering skills in a software engineering framework) and inconsistent groupings (`lifecycle/` mixed governance and creation tasks).

## Solution

Reorganize into 7 activity-based categories (32 skills):

- **dev/** (6) — extracted from `swe/` for development-focused skills
- **review/** (3) — extracted from `swe/` for review-focused skills
- **docs/** (4) — extracted from `swe/` for documentation skills
- **govern/** (9) — renamed from `lifecycle/` for governance skills
- **quality/** (3) — absorbed `validation/` skills
- **workflows/** (4) — unchanged
- **utils/** (3) — unchanged, `python-mastery` renamed to `python-patterns`

## Scope

- Rename category directories
- Move and rename skill files
- Update all 40 `.claude/commands/` wrappers
- Update CLAUDE.md, AGENTS.md, codex.md, copilot-instructions.md skill sections
- Update manifest.yml and templates

## Decision

Recorded as S0-010 in `state/decision-store.json`.
