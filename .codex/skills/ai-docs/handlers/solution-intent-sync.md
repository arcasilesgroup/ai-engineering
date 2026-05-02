# Handler: solution-intent-sync

## Purpose

Diff-aware update of `docs/solution-intent.md` based on current project state. Compares document content against project reality section-by-section and rewrites any section where content is misaligned. Preserves user-authored content that is still accurate.

## Pre-conditions

1. Read `.ai-engineering/manifest.yml` -- check `documentation.auto_update.solution_intent`.
2. If `false`, skip silently and report "solution intent auto-update disabled".

## Trigger Table

| Trigger | Sections Affected | Source |
|---------|-------------------|--------|
| Spec closure (done.md created) | 7.2 epic status, 7.4 active spec | spec lifecycle |
| Release completion | 7.1 roadmap, 7.3 KPIs | release skill |
| Stack add/remove | 3.1 stack & architecture | manifest.yml |
| Security scan delta | 5.4 hardening checklist, 7.3 KPIs | verify agent |
| Decision store update | 2.2 if domain-relevant | decision-store.json |
| Skill/agent add/remove | 2.2 AI Ecosystem, 6.4 scalability | manifest.yml |
| Quality gate change | 6.1 quality gates, 2.3 NFRs | manifest.yml |

## Procedure

### 1. Read current document

Load `docs/solution-intent.md`. If file does not exist, report "no solution intent found -- run `/ai-docs solution-intent-init` first" and stop.

### 2. Gather current project state

Collect authoritative data from ALL sources:
- `.ai-engineering/manifest.yml` -- stack/skill/agent counts, quality gates, tooling, providers
- `.ai-engineering/state/decision-store.json` -- active decisions, risk acceptances
- `.ai-engineering/specs/spec.md` -- current spec status
- Recent spec closures (done.md files)
- `.codex/skills/` -- actual skill count and categories
- `.codex/agents/internal/` -- actual agent count
- Source code structure (`src/`) -- module layout, CLI commands
- Quality/security tool outputs if available

### 3. Compare section-by-section

For each of the 7 sections and their subsections:
1. Read the section content from the document
2. Compare against the authoritative project state gathered in step 2
3. Classify each section as: CURRENT (no changes needed), STALE (content misaligned with project state), or TBD (intentionally unpopulated)

### 4. Rewrite misaligned sections

For each STALE section:
1. Rewrite the section content to reflect current project state
2. Update tables with current data (counts, statuses, versions)
3. Update Mermaid diagrams if the underlying data changed (e.g., new module in architecture)
4. Rewrite prose paragraphs if they describe outdated state (not limited to field/table updates)
5. Preserve user-authored content that is still accurate
6. Update `Last Review: YYYY-MM-DD` in document header

### 5. Stage

`git add docs/solution-intent.md`

### 6. Report

List sections updated with before/after summary. Report sections that were CURRENT (unchanged) and TBD (skipped).

## Rules

- **Diff-aware rewrite** -- compare document content against project state and rewrite any section where content is misaligned. Not limited to surgical field/table updates; prose that describes outdated state is also rewritten.
- **Preserve user content** -- if a section has been manually edited and the content is still accurate, keep it. Only rewrite what is stale.
- **Idempotent** -- running sync twice with no project state changes produces no diff.
- **Diagrams** -- update Mermaid diagrams if the underlying data changed (e.g., new module in architecture).
- **TBD sections** -- do NOT fill TBD sections during sync. Only init or user can populate those.
