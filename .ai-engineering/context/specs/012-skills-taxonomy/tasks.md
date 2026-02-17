# Spec 012: Skills Taxonomy — Tasks

## Phase 1: Directory Restructuring

- [x] Create `dev/` category (6 skills from `swe/`)
- [x] Create `review/` category (3 skills from `swe/`)
- [x] Create `docs/` category (4 skills from `swe/`)
- [x] Rename `lifecycle/` to `govern/` (9 skills)
- [x] Absorb `validation/` into `quality/` (3 skills)
- [x] Merge `pr-creation.md` into `workflows/pr.md`
- [x] Rename `dependency-update.md` to `deps-update.md`
- [x] Rename `architecture-analysis.md` to `architecture.md`
- [x] Rename `python-mastery.md` to `python-patterns.md`
- [x] Remove empty old category directories

## Phase 2: Cross-Reference Updates

- [x] Update 40 `.claude/commands/` wrappers
- [x] Update CLAUDE.md skill section
- [x] Update AGENTS.md skill section
- [x] Update codex.md skill section
- [x] Update copilot-instructions.md skill section
- [x] Update manifest.yml counters (33 -> 32 skills, 6 -> 7 categories)

## Phase 3: Template Sync

- [x] Mirror skill files to `templates/.ai-engineering/skills/`
- [x] Mirror command wrappers to `templates/project/.claude/commands/`
- [x] Mirror instruction files to `templates/project/`
- [x] Run `ai-eng validate` — all 6 categories pass
