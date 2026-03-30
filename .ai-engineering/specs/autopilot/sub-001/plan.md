---
total: 6
completed: 4
---

# Plan: sub-001 LESSONS.md Consolidation

## Plan

exports: [".ai-engineering/LESSONS.md (new canonical path)", "defaults.py APPEND_ONLY ownership entry"]
imports: []

- [x] T-1.1: Move lessons.md to new location
  - **Files**: `.ai-engineering/contexts/team/lessons.md`, `.ai-engineering/LESSONS.md`
  - **Done**: `git mv .ai-engineering/contexts/team/lessons.md .ai-engineering/LESSONS.md` succeeds; old path gone, new path has 211 lines intact

- [x] T-1.2: Delete learnings/ directory and clean manifest.yml
  - **Files**: `.ai-engineering/learnings/index.jsonl`, `.ai-engineering/learnings/`, `.ai-engineering/manifest.yml`
  - **Done**: `learnings/` directory deleted; manifest.yml line 180 ownership.system list no longer references `learnings/**`

- [x] T-1.3: Add APPEND_ONLY ownership rule to defaults.py
  - **Files**: `src/ai_engineering/state/defaults.py`
  - **Done**: `_DEFAULT_OWNERSHIP_PATHS` contains `(".ai-engineering/LESSONS.md", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.APPEND_ONLY)`; existing `contexts/team/**` DENY entry stays for other team files

- [x] T-1.4: Add migration logic to governance.py installer
  - **Files**: `src/ai_engineering/installer/phases/governance.py`
  - **Done**: On INSTALL/REPAIR: if old path exists and new path missing, move file. Template source updated to `.ai-engineering/LESSONS.md`. `_classify()` handles new path correctly.

- [ ] T-1.5: Refactor /ai-learn SKILL.md (canonical .claude/ copy)
  - **Files**: `.claude/skills/ai-learn/SKILL.md`
  - **Done**: Step 0 removed (no learnings/ init). `single <pr>` appends lesson in Context/Learning/Rule format to `.ai-engineering/LESSONS.md`. `batch` tracks via `lastAnalyzedAt` frontmatter + git log. `apply` mode removed. Quick reference updated.

- [ ] T-1.6: Update template LESSONS.md location
  - **Files**: `src/ai_engineering/templates/.ai-engineering/contexts/team/lessons.md`, `src/ai_engineering/templates/.ai-engineering/LESSONS.md`
  - **Done**: Template seed file moved from `templates/.ai-engineering/contexts/team/lessons.md` to `templates/.ai-engineering/LESSONS.md`. Old template file deleted.

### Confidence
- **Level**: high
- **Assumptions**: git mv preserves content and history. APPEND_ONLY policy is already implemented in the framework (not a new policy type).
- **Unknowns**: Whether any CI/CD scripts reference the old path (not found in exploration).

## Self-Report
[EMPTY -- populated by Phase 4]
