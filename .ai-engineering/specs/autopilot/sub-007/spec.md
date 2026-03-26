---
id: sub-007
parent: spec-080
title: "Deep Documentation /ai-docs"
status: planning
files: [".claude/skills/ai-docs/SKILL.md", ".claude/skills/ai-docs/handlers/changelog.md", ".claude/skills/ai-docs/handlers/readme.md", ".claude/skills/ai-docs/handlers/solution-intent-init.md", ".claude/skills/ai-docs/handlers/solution-intent-sync.md", ".claude/skills/ai-docs/handlers/solution-intent-validate.md", ".claude/skills/ai-docs/handlers/docs-portal.md", ".claude/skills/ai-docs/handlers/docs-quality-gate.md", ".claude/skills/ai-pr/SKILL.md", ".claude/skills/ai-commit/SKILL.md", ".claude/skills/ai-solution-intent/SKILL.md", ".ai-engineering/manifest.yml"]
depends_on: []
---

# Sub-Spec 007: Deep Documentation /ai-docs

## Scope
Create /ai-docs skill with 7 handlers (changelog, readme, solution-intent-init, solution-intent-sync, solution-intent-validate, docs-portal, docs-quality-gate) absorbing ai-solution-intent. Modify ai-pr to dispatch 5 documentation subagents in parallel. Remove ai-solution-intent as independent skill. Solution-intent-sync changes from surgical-only to diff-aware rewrite. Docs-portal handles external repos (clone/PR, default branch detection, pending PR reference). Quality gate verifies all outputs reflect semantic changes.

## Exploration

### Current State Analysis

**ai-solution-intent (being absorbed)**: 1 SKILL.md + 3 handlers (init.md, sync.md, validate.md). Registered in manifest.yml as `ai-solution-intent: { type: enterprise, tags: [documentation] }`. Exists in 3 IDE mirrors: `.claude/skills/ai-solution-intent/`, `.github/skills/ai-solution-intent/`, `.agents/skills/solution-intent/`. Also exists in 3 template mirrors under `src/ai_engineering/templates/project/`. Total: 4 files x 6 locations = 24 files to delete.

**ai-write handlers reusable as base**: `handlers/changelog.md` (43 lines) covers Keep a Changelog format, commit classification, user-facing language transforms, quality checks. `handlers/docs.md` (60 lines) covers Divio doc types, README structure, README Update Mode (recursive scan), API docs, guides, ADR. Both provide solid foundations but need strengthening for the new ai-docs versions -- the new changelog handler needs semantic diff reading (not just commit-based), and the new readme handler needs diff-aware section targeting (not just recursive scan).

**ai-pr documentation dispatch (current)**: Step 6.5 is a "doc gate verification" safety net checking CHANGELOG.md is staged. Step 6.7 invokes `/ai-solution-intent sync` conditionally when architecture files change. Both are sequential, single-skill calls. The new design replaces steps 6.5 and 6.7 with a parallel 5-subagent dispatch.

**ai-commit documentation gate (step 5)**: Classifies scope into 3 tiers (CHANGELOG+README, CHANGELOG only, None) based on staged change type. References `documentation.external_portal` from manifest.yml. The new ai-docs handlers take over the actual documentation writing, but ai-commit step 5 scope classification remains -- it determines WHAT needs updating, ai-docs handlers determine HOW.

**manifest.yml documentation section**: Has `documentation.auto_update` flags (readme, changelog, solution_intent) and `documentation.external_portal` (enabled, source, update_method). These flags serve as the gate -- ai-docs handlers check them before executing.

### Key Behavioral Changes

1. **solution-intent-sync**: Current sync.md has "Surgical only -- update specific fields/tables, never rewrite paragraphs" as a hard rule plus "TBD sections -- do NOT fill TBD sections during sync." The new handler removes the surgical restriction, enabling diff-aware rewrite of misaligned prose sections. The TBD policy and user-content preservation rules remain.

2. **ai-pr parallel dispatch**: Current sequential flow (step 5 in commit -> step 6.5 verify -> step 6.7 solution-intent) becomes a parallel 5-subagent dispatch. The quality gate subagent (5th) runs after subagents 1-4 complete, making the pattern 4-parallel + 1-sequential.

3. **docs-portal**: Entirely new handler. Reads `documentation.external_portal` from manifest.yml. Handles local directory (pull, update, commit, push/PR) and remote URL (clone to temp, update, PR). Detects default branch via `git symbolic-ref refs/remotes/origin/HEAD`. On PR failure, cleans up branches and references failure in the source PR body.

4. **docs-quality-gate**: Entirely new handler. Reads the diff, reads all doc outputs from subagents 1-4, produces a checklist mapping each changed function/class/module to its documentation update. Zero uncovered items is the pass criterion.

### Blast Radius (21 files reference ai-solution-intent)

**Delete (24 files across 6 directories)**:
- `.claude/skills/ai-solution-intent/` (SKILL.md + 3 handlers)
- `.github/skills/ai-solution-intent/` (SKILL.md + 3 handlers)
- `.agents/skills/solution-intent/` (SKILL.md + 3 handlers)
- `src/ai_engineering/templates/project/.claude/skills/ai-solution-intent/` (SKILL.md + 3 handlers)
- `src/ai_engineering/templates/project/.github/skills/ai-solution-intent/` (SKILL.md + 3 handlers)
- `src/ai_engineering/templates/project/.agents/skills/solution-intent/` (SKILL.md + 3 handlers)

**Create (8 files + mirrors)**:
- `.claude/skills/ai-docs/SKILL.md` (router skill)
- `.claude/skills/ai-docs/handlers/` (7 handlers: changelog.md, readme.md, solution-intent-init.md, solution-intent-sync.md, solution-intent-validate.md, docs-portal.md, docs-quality-gate.md)
- Mirror to `.github/skills/ai-docs/` (SKILL.md + 7 handlers)
- Mirror to `.agents/skills/docs/` (SKILL.md + 7 handlers)
- Mirror to `src/ai_engineering/templates/project/` for all 3 IDE surfaces (SKILL.md + 7 handlers x 3)
- Total new files: 8 x 6 = 48 files

**Modify**:
- `.claude/skills/ai-pr/SKILL.md` -- replace steps 6.5 + 6.7 with parallel 5-subagent dispatch
- `.github/skills/ai-pr/SKILL.md` -- same change, GitHub Copilot path references
- `.agents/skills/pr/SKILL.md` -- same change, Codex/Gemini path references
- `src/ai_engineering/templates/project/.claude/skills/ai-pr/SKILL.md` -- template mirror
- `src/ai_engineering/templates/project/.github/skills/ai-pr/SKILL.md` -- template mirror
- `src/ai_engineering/templates/project/.agents/skills/pr/SKILL.md` -- template mirror
- `.ai-engineering/manifest.yml` -- remove ai-solution-intent from registry, add ai-docs
- `src/ai_engineering/templates/.ai-engineering/manifest.yml` -- same registry change
- `CLAUDE.md` -- update Enterprise skill group (solution-intent -> docs), Effort Levels table
- `.ai-engineering/README.md` -- update skill table (solution-intent -> docs)
- `src/ai_engineering/templates/.ai-engineering/README.md` -- template mirror

### Confidence Assessment

| Area | Confidence | Notes |
|------|-----------|-------|
| Solution-intent handler migration | HIGH | Direct content copy with sync behavior change |
| Changelog handler | HIGH | Strengthened version of ai-write changelog.md |
| README handler | HIGH | Strengthened version of ai-write docs.md README section |
| ai-pr parallel dispatch | HIGH | Clear insertion point (steps 6.5 + 6.7), well-defined subagent pattern |
| docs-portal handler | MEDIUM | New behavior, git operations with error handling branches |
| docs-quality-gate handler | MEDIUM | New concept -- semantic diff coverage verification |
| Mirror maintenance | HIGH | Mechanical -- same content, adjusted path references |
| ai-solution-intent deletion | HIGH | Full directory listing confirmed, grep found all 21 referencing files |
