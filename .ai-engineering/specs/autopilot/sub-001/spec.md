---
id: sub-001
parent: spec-090
title: "LESSONS.md Consolidation"
status: planned
files: [".ai-engineering/LESSONS.md", ".ai-engineering/contexts/team/lessons.md", ".ai-engineering/learnings/", ".claude/skills/ai-learn/SKILL.md", ".gemini/skills/ai-learn/SKILL.md", ".codex/skills/ai-learn/SKILL.md", ".github/skills/ai-learn/SKILL.md", "src/ai_engineering/state/defaults.py", ".ai-engineering/manifest.yml", "src/ai_engineering/installer/phases/governance.py"]
depends_on: []
---

# Sub-Spec 001: LESSONS.md Consolidation

## Scope

Implements D-090-01 (move LESSONS.md to .ai-engineering/ root), D-090-02 (eliminate learnings/ directory), D-090-03 (refactor /ai-learn to write directly to LESSONS.md), and D-090-09 (APPEND_ONLY ownership rule).

## Exploration

### Existing Files
- `.ai-engineering/contexts/team/lessons.md` — 211 lines, 22 lessons in Context/Learning/Rule format. TEAM_MANAGED, DENY policy via `contexts/team/**` glob in defaults.py line 70.
- `.ai-engineering/learnings/index.jsonl` — 1 line, single JSON entry. Dead-end store, zero consumers. Referenced only in manifest.yml line 180.
- `.claude/skills/ai-learn/SKILL.md` — 93 lines, 3 modes (single/batch/apply). Step 0 creates learnings/ dir. apply mode never implemented. Mirrored in 4 IDEs + 4 templates = 8 copies.
- `src/ai_engineering/state/defaults.py` — 196 lines. `_DEFAULT_OWNERSHIP_PATHS` at lines 46-161 (17 entries). Line 70: `contexts/team/**` → TEAM_MANAGED, DENY. No entry for learnings/ or LESSONS.md.
- `.ai-engineering/manifest.yml` — 189 lines. Line 180: `system: [".ai-engineering/state/**", ".ai-engineering/learnings/**"]`.
- `src/ai_engineering/installer/phases/governance.py` — 150 lines. `_TEAM_OWNED = "contexts/team/"` at line 29. `_classify()` at lines 125-149 handles install/fresh/repair modes.

### Patterns to Follow
- CONSTITUTION.md at `.ai-engineering/` root — same visibility level as proposed LESSONS.md.
- Ownership entries in defaults.py follow pattern: `(path_glob, OwnershipLevel, FrameworkUpdatePolicy)`.

### Dependencies Map
- 45 files reference `contexts/team/lessons` across CLAUDE.md, GEMINI.md, AGENTS.md, 4 IDE ai-onboard skills, templates, tests.
- ai-learn SKILL.md is the only writer to learnings/index.jsonl.
- governance.py reads `_TEAM_OWNED` constant to classify files during install.

### Risks
- 45 file references must ALL be updated atomically to avoid broken references.
- Template files in `src/ai_engineering/templates/project/` must also be updated.
- governance.py migration logic must handle: old path exists + new path missing → move file.
