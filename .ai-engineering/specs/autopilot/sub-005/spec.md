---
id: sub-005
parent: spec-090
title: "Reference Updates, Mirrors + Tests"
status: planned
files: ["CLAUDE.md", "GEMINI.md", "AGENTS.md", "README.md", "src/ai_engineering/templates/", "src/ai_engineering/installer/phases/governance.py", "tests/"]
depends_on: [sub-001, sub-002, sub-003, sub-004]
---

# Sub-Spec 005: Reference Updates, Mirrors + Tests

## Scope

Cross-cutting: update all references to old paths (lessons.md, learnings/, context.md), sync 4 IDE mirrors, update templates, update installer migration, update tests, update README.

## Exploration

### Existing Files
- CLAUDE.md/GEMINI.md/AGENTS.md — 5 references each to `contexts/team/lessons.md` (lines 28, 31, 66, 85, ~177).
- 4 IDE ai-onboard SKILL.md copies — 1 reference each to lessons path + instinct context.
- 4 IDE ai-learn SKILL.md copies — multiple references to learnings/.
- 4 IDE ai-instinct SKILL.md copies — references to context.md and v1 families.
- README.md line 187 — directory tree referencing lessons.md.
- Templates: 4 copies of CLAUDE.md, ai-onboard, ai-learn in src/ai_engineering/templates/project/.
- Tests: 12 test files reference instincts or lessons (2 need path updates, 2 need v2 schema updates).
- sync_command_mirrors.py — exists, handles .claude→.codex/.gemini/.github + templates sync.

### Grep Counts
- `contexts/team/lessons`: 45 files
- `instincts/context.md`: 43 files
- `learnings`: 80+ references (mostly in SKILL.md docs)

### Risks
- Mirror sync must run AFTER all canonical .claude/ files are updated.
- Template updates must match active project files exactly.
