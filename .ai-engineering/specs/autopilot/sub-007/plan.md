---
total: 7
completed: 7
---

# Plan: sub-007 Deep Documentation /ai-docs

## Plan

### T-7.1 Create ai-docs SKILL.md router
- [x] **Files**: `.claude/skills/ai-docs/SKILL.md`
- **Done**: SKILL.md exists with frontmatter (name: ai-docs, effort: high, tags: [documentation, architecture, governance]), routing table for 7 handlers (changelog, readme, solution-intent-init, solution-intent-sync, solution-intent-validate, docs-portal, docs-quality-gate), When to Use section, Quick Reference, Integration section listing ai-pr as caller and manifest.yml auto_update flags as gate, Governance Notes carried from ai-solution-intent (visual priority, TBD policy, ownership)

### T-7.2 Create 7 ai-docs handlers
- [x] **Files**: `.claude/skills/ai-docs/handlers/changelog.md`, `.claude/skills/ai-docs/handlers/readme.md`, `.claude/skills/ai-docs/handlers/solution-intent-init.md`, `.claude/skills/ai-docs/handlers/solution-intent-sync.md`, `.claude/skills/ai-docs/handlers/solution-intent-validate.md`, `.claude/skills/ai-docs/handlers/docs-portal.md`, `.claude/skills/ai-docs/handlers/docs-quality-gate.md`
- **Done**:
  - `changelog.md`: Strengthened from ai-write changelog.md -- adds semantic diff reading (read full git diff, not just commit messages), classification by user impact, Keep a Changelog format, quality rejection rules. Checks `documentation.auto_update.changelog` flag before executing.
  - `readme.md`: Strengthened from ai-write docs.md README section -- adds diff-aware section targeting (identify which README sections are affected by the diff, update only those), recursive README scan from existing handler, Divio structure rules. Checks `documentation.auto_update.readme` flag.
  - `solution-intent-init.md`: Direct migration from ai-solution-intent handlers/init.md -- full 7-section scaffold procedure, deep audit source table, prerequisite `/ai-explore` audit, visual priority governance notes. No behavioral changes.
  - `solution-intent-sync.md`: Migration from ai-solution-intent handlers/sync.md with key behavioral change -- removes "Surgical only" rule, adds diff-aware rewrite: (1) read current document, (2) gather current project state from all sources (manifest, decision-store, specs, tools), (3) compare document content against project state section-by-section, (4) rewrite any section where content is misaligned (not limited to field/table updates), (5) preserve user-authored content that is still accurate, (6) TBD policy unchanged (do NOT fill TBD sections during sync). Trigger table and idempotency rules preserved. Checks `documentation.auto_update.solution_intent` flag.
  - `solution-intent-validate.md`: Direct migration from ai-solution-intent handlers/validate.md -- completeness check per 7 sections (29 subsections), freshness check (30-day WARNING, 60-day CRITICAL), consistency cross-reference against manifest/decision-store/spec, scorecard output. No behavioral changes.
  - `docs-portal.md`: New handler. Reads `documentation.external_portal` from manifest.yml. If `enabled: false`, skip silently. If enabled: (1) determine source type (local path vs remote URL), (2) for local: detect default branch via `git symbolic-ref refs/remotes/origin/HEAD`, `git pull`, update docs, commit, create PR or push based on `update_method`, (3) for remote URL: `git clone` to temp directory, create feature branch, update docs, create PR, (4) on PR creation failure: clean up local branches, add comment to our PR body with link and failure reason, (5) on success: add cross-reference to our PR body noting docs PR number. Never leave orphaned branches in external repos.
  - `docs-quality-gate.md`: New handler. Runs after subagents 1-4 complete. (1) Read the full staged diff, (2) extract every semantic change (new functions, modified signatures, renamed classes, deleted modules, changed behavior), (3) read all documentation outputs from subagents 1-4 (CHANGELOG entries, README changes, solution-intent updates, portal updates), (4) produce a coverage checklist mapping each semantic change to its documentation update, (5) flag any uncovered changes, (6) pass criterion: zero uncovered items. Report format: table with columns [Change, Type, Covered By, Status].

### T-7.3 Modify ai-pr to dispatch 5 documentation subagents in parallel
- [x] **Files**: `.claude/skills/ai-pr/SKILL.md` + 5 mirrors
- **Done**: Steps 6.5 (doc gate verification) and 6.7 (solution intent sync) replaced with new step 6.5 "Documentation subagent dispatch" across all 6 mirrors: `.claude/`, `.github/`, `.agents/`, and all 3 template mirrors. Integration section updated to reference ai-docs. References updated from ai-write to ai-docs.

### T-7.4 Delete ai-solution-intent skill across all surfaces
- [x] **Files**: DELETE `.claude/skills/ai-solution-intent/`, DELETE `.github/skills/ai-solution-intent/`, DELETE `.agents/skills/solution-intent/`, DELETE template mirrors
- **Done**: All 24 files across 6 directories deleted via `git rm -r`. No residual references to ai-solution-intent in any SKILL.md, manifest.yml, CLAUDE.md, or README.md.

### T-7.5 Mirror ai-docs to all IDE surfaces and templates
- [x] **Files**: `.github/skills/ai-docs/SKILL.md` + 7 handlers, `.agents/skills/docs/SKILL.md` + 7 handlers, template mirrors
- **Done**: ai-docs SKILL.md + 7 handlers mirrored to 5 additional locations: `.github/skills/ai-docs/`, `.agents/skills/docs/`, and all 3 template directories. Each mirror has platform-appropriate path references. All 6 ai-pr mirrors updated with parallel dispatch changes.

### T-7.6 Update manifest.yml skill registry
- [x] **Files**: `.ai-engineering/manifest.yml`, `src/ai_engineering/templates/.ai-engineering/manifest.yml`
- **Done**: `ai-solution-intent` entry replaced with `ai-docs: { type: enterprise, tags: [documentation, architecture, governance] }` in both project and template manifests.

### T-7.7 Update CLAUDE.md and README.md references
- [x] **Files**: `CLAUDE.md`, `src/ai_engineering/templates/project/CLAUDE.md`, `.ai-engineering/README.md`, `src/ai_engineering/templates/.ai-engineering/README.md`
- **Done**: CLAUDE.md Enterprise skill group: `solution-intent` replaced with `docs`. Effort Levels table: `solution-intent` replaced with `docs` in high row. Both project and template CLAUDE.md updated. README.md skill table: `/ai-solution-intent` row replaced with `/ai-docs | Project documentation lifecycle (changelog, readme, solution-intent, external portal)` in both project and template README.md.

## Self-Report

**Status**: COMPLETE

**Created** (48 files):
- `.claude/skills/ai-docs/SKILL.md` + 7 handlers (8 files)
- `.github/skills/ai-docs/SKILL.md` + 7 handlers (8 files)
- `.agents/skills/docs/SKILL.md` + 7 handlers (8 files)
- `src/ai_engineering/templates/project/.claude/skills/ai-docs/SKILL.md` + 7 handlers (8 files)
- `src/ai_engineering/templates/project/.github/skills/ai-docs/SKILL.md` + 7 handlers (8 files)
- `src/ai_engineering/templates/project/.agents/skills/docs/SKILL.md` + 7 handlers (8 files)

**Deleted** (24 files via `git rm -r`):
- `.claude/skills/ai-solution-intent/` (SKILL.md + 3 handlers)
- `.github/skills/ai-solution-intent/` (SKILL.md + 3 handlers)
- `.agents/skills/solution-intent/` (SKILL.md + 3 handlers)
- `src/ai_engineering/templates/project/.claude/skills/ai-solution-intent/` (SKILL.md + 3 handlers)
- `src/ai_engineering/templates/project/.github/skills/ai-solution-intent/` (SKILL.md + 3 handlers)
- `src/ai_engineering/templates/project/.agents/skills/solution-intent/` (SKILL.md + 3 handlers)

**Modified** (12 files):
- `.claude/skills/ai-pr/SKILL.md` -- steps 6.5/6.7 replaced with parallel dispatch, references updated
- `.github/skills/ai-pr/SKILL.md` -- same changes
- `.agents/skills/pr/SKILL.md` -- same changes
- `src/ai_engineering/templates/project/.claude/skills/ai-pr/SKILL.md` -- same changes (via cp)
- `src/ai_engineering/templates/project/.github/skills/ai-pr/SKILL.md` -- same changes
- `src/ai_engineering/templates/project/.agents/skills/pr/SKILL.md` -- same changes
- `.ai-engineering/manifest.yml` -- ai-solution-intent replaced with ai-docs
- `src/ai_engineering/templates/.ai-engineering/manifest.yml` -- same
- `CLAUDE.md` -- Enterprise group and Effort Levels updated
- `src/ai_engineering/templates/project/CLAUDE.md` -- same
- `.ai-engineering/README.md` -- skill table updated
- `src/ai_engineering/templates/.ai-engineering/README.md` -- same

**Key behavioral changes delivered**:
- solution-intent-sync: removed "Surgical only" restriction, now does diff-aware rewrite of misaligned prose
- ai-pr: sequential doc gate + solution-intent sync replaced with parallel 5-subagent dispatch
- Two new handlers: docs-portal (external repo PR flow) and docs-quality-gate (semantic coverage verification)
