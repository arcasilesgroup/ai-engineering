# Handler: sync

## Purpose

Surgical update of specific sections based on project changes. Never rewrites the entire document. Never deletes user-authored content.

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

1. **Read current document** -- load `docs/solution-intent.md`.

2. **Detect changes** -- compare current project state against document content:
   - Parse manifest.yml for stack/skill/agent counts
   - Parse decision-store.json for active decisions
   - Check specs/spec.md for current spec
   - Check recent spec closures (done.md files)
   - Run quality/security tools if available for fresh data

3. **Apply updates** -- for each affected section:
   - Read existing section content
   - Merge new data (update tables, status fields, counts, diagrams)
   - Preserve all user-authored text and custom content
   - Update `Last Review: YYYY-MM-DD` in header

4. **Stage** -- `git add docs/solution-intent.md`.

5. **Report** -- list sections updated with before/after summary.

## Rules

- **Surgical only** -- update specific fields/tables, never rewrite paragraphs
- **Preserve user content** -- if a section has been manually edited, merge carefully
- **Idempotent** -- running sync twice with no changes produces no diff
- **Diagrams** -- update Mermaid diagrams if the underlying data changed (e.g., new module in architecture)
- **TBD sections** -- do NOT fill TBD sections during sync. Only init or user can populate those.
