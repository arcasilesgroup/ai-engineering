# Spec 012: Skills Taxonomy — Plan

## Approach

Single-session reorganization of skills directory structure. No code changes required — pure content restructuring with cross-reference updates.

## Phases

### Phase 1: Directory restructuring

- Create new category directories: `dev/`, `review/`, `docs/`, `govern/`, `quality/`
- Move and rename skill files from `swe/`, `lifecycle/`, `validation/`
- Merge `pr-creation.md` into `workflows/pr.md`
- Rename verbose files (`dependency-update` -> `deps-update`, `architecture-analysis` -> `architecture`, `python-mastery` -> `python-patterns`)

### Phase 2: Cross-reference updates

- Update all 40 `.claude/commands/` wrappers to point to new paths
- Update CLAUDE.md, AGENTS.md, codex.md, copilot-instructions.md skill sections
- Update manifest.yml skill counters and category listing

### Phase 3: Template sync

- Mirror all changes to `templates/` directory
- Verify canonical ↔ template sync via validator

## Risk Assessment

- **Low risk**: no code changes, only content restructuring
- **Rollback**: git revert of single commit restores prior structure
