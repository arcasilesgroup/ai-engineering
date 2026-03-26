---
id: sub-008
parent: spec-080
title: "Work Item Lifecycle"
status: ready
files: [".claude/skills/ai-board-discover/SKILL.md", ".claude/skills/ai-board-sync/SKILL.md", ".claude/skills/ai-brainstorm/SKILL.md", ".claude/skills/ai-dispatch/SKILL.md", ".claude/skills/ai-pr/SKILL.md", ".claude/skills/ai-onboard/SKILL.md", ".ai-engineering/manifest.yml", ".ai-engineering/schemas/manifest.schema.json"]
depends_on: []
confidence: 0.90
---

# Sub-Spec 008: Work Item Lifecycle

## Scope

Create /ai-board-discover skill for LLM-assisted post-install discovery of board configuration (process template, states, custom fields, GitHub Projects v2 columns, docs URLs, CI/CD standards URLs). Create /ai-board-sync skill for operational work item state updates at each lifecycle phase (refinement, ready, in_progress, in_review, done). Extend manifest.yml schema with state_mapping, process_template, custom_fields, github_project sections. Modify ai-brainstorm (refinement/ready transitions), ai-dispatch (in_progress), ai-pr (in_review). GitHub Projects v2 first option, labels fallback. Remove "set during install" comments from manifest. Update ai-onboard to load board config.

## Exploration

### Current State

**manifest.yml `work_items` section** (lines 33-45):
- Has `provider` (github | azure_devops), provider-specific config blocks, and `hierarchy` (close rules per type).
- The `github` sub-object has `team_label` and an optional `project` field, but no state mapping, no process template, no custom fields, and no github_project column/field IDs.
- The `cicd.standards_url` field (line 73) has a "set during install or edit manually" comment -- the only such comment remaining in the manifest.

**manifest.schema.json `work_items`** (lines 62-109):
- Schema allows `provider`, `azure_devops` (area_path, iteration_path), `github` (team_label, project), `hierarchy` (feature/user_story/task/bug close rules).
- `additionalProperties: false` on every sub-object -- new fields like `state_mapping`, `process_template`, `custom_fields`, `github_project` will need schema additions.
- The schema does NOT currently validate work_items as required at the top level.

**Existing GitHub Projects v2 integration** (scripts/):
- `scripts/work_items_backfill.py` -- uses `gh project item-edit` with GraphQL for project item IDs, single-select fields (priority, size, status), date fields, number fields, and issue types. References `work_items.sources[].type == "github-projects"` with `project_id`, `fields`, `priority_options`, `size_options`, `status_options`.
- `scripts/work_items_validate.py` -- uses `gh project item-list` to fetch items, validates required fields (Priority, Size, Status) and warn fields (Estimate, Start Date, Target Date).
- **Gap**: the backfill script references a `work_items.sources` array structure that does NOT exist in the current manifest.yml. This is a one-off script with its own config (`work_items_backfill.yml`). The scripts are operational tooling, not skill-level artifacts. /ai-board-discover needs to write the canonical manifest fields that these scripts could later consume.

**ai-brainstorm (SKILL.md, lines 26-33)**:
- Step 1 already reads manifest.yml `work_items` section for active provider and team config.
- Fetches work item via `gh issue view` (GitHub) or `az boards work-item show` (ADO).
- Walks hierarchy: Feature -> User Story -> Tasks.
- Uses standard and custom fields from the platform.
- **Insertion point for board-sync**: after step 1 (work item fetched -> `refinement` state), and after step 4 (spec written -> `ready` state).

**ai-brainstorm interrogate handler (lines 21-31)**:
- Step 1.5 reads work item title, description, acceptance criteria, child items, all standard/custom fields.
- Maps fields to KNOWN/ASSUMED categories.
- **No changes needed here** -- interrogate.md consumes what brainstorm provides; the board-sync call goes in the parent SKILL.md, not the handler.

**ai-dispatch (SKILL.md, lines 23-33)**:
- Step 1 loads plan, step 2 loads decisions, step 3 builds DAG, step 4 executes phases.
- **Insertion point**: between step 2 (load decisions) and step 3 (build DAG) -- this is when implementation "starts" and `in_progress` should be set.
- Alternative: at the start of step 4a (first subagent dispatch). The spec-080 says "implementation starts" so between step 2 and step 3 is cleaner.

**ai-pr (SKILL.md)**:
- Step 7.5 reads manifest work_items and spec refs.
- Step 8.5 adds close keywords per hierarchy rule.
- **Insertion point for board-sync (`in_review`)**: after step 9 (commit and push) but before step 10 (detect VCS provider). Or after step 12 (PR created). After PR creation (step 12) is semantically correct -- the item enters "in review" when a PR exists.

**ai-onboard (SKILL.md, lines 25-30)**:
- Step 2 loads active context: spec.md, plan.md, decision-store.json, lessons.md.
- **Gap**: does NOT load manifest.yml work_items config, board config, or state_mapping.
- **Insertion point**: add a sub-step to step 2 that reads manifest.yml work_items section and reports board configuration status in step 3's summary.

**ai-sprint / ai-standup (Pre-conditions)**:
- Both already read manifest.yml work_items section and use provider-specific queries.
- They will naturally benefit from the new state_mapping fields without modification (they already read "all standard and custom fields the platform provides").

### Mirror Surfaces

Three mirror surfaces must receive copies of new/modified skills:
1. `.github/skills/ai-<name>/` -- Copilot mirror (exists for brainstorm, dispatch, pr, onboard)
2. `.agents/skills/<name>/` -- Codex/Gemini mirror (exists for brainstorm, dispatch, pr, onboard; note: no `ai-` prefix in directory names)
3. `src/ai_engineering/templates/project/.claude/skills/ai-<name>/` -- template mirror (exists for brainstorm, dispatch, pr, onboard)

New skills (ai-board-discover, ai-board-sync) need directories created in all 4 surfaces (Claude Code + 3 mirrors).

### Provider Strategy

**GitHub Projects v2 (primary)**:
- Use `gh project item-list` to discover fields and columns.
- Use `gh project item-edit` to update status field (single-select) on work items.
- Field IDs and option IDs are project-specific -- board-discover caches them in manifest.yml `github_project` section.
- GraphQL needed for: getting project item ID from issue number, discovering field schemas.

**GitHub Labels (fallback)**:
- If no Projects v2 configured: use labels like `status:refinement`, `status:in-progress`, etc.
- Use `gh issue edit --add-label / --remove-label` for state transitions.
- Simpler but less rich -- no custom fields, no board view.

**Azure DevOps**:
- Use `az boards work-item update --state <state>` for transitions.
- Process template discovery via `az boards work-item type list` and `az boards process get`.
- Custom fields via `az boards work-item show --expand all`.

### Design Decisions

1. **board-sync is fail-open**: logs warning and continues if provider CLI fails. Never blocks the main skill workflow.
2. **board-discover writes atomically**: builds complete config in memory, writes to manifest only when all discovery succeeds. Partial failure means no write (manifest retains previous state).
3. **State mapping is provider-agnostic**: `state_mapping` section maps lifecycle phases to provider-specific values. Skills call board-sync with lifecycle phase names (`refinement`, `ready`, etc.), not provider-specific state names.
4. **Custom fields are round-tripped**: board-discover reads available custom fields and stores them. board-sync can read and update them per transition.
5. **No new manifest comments**: remove the existing "set during install" comment on cicd.standards_url. New fields use descriptive YAML keys with no inline comments about setup method.

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GitHub Projects v2 GraphQL API changes field ID format | Low | Medium | Discovery caches IDs; re-run /ai-board-discover to refresh |
| Provider CLI not authenticated when board-sync runs | Medium | Low | Fail-open design; log warning with remediation hint |
| State names differ across process templates | Medium | Low | state_mapping abstraction layer; board-discover populates correct values per template |
| Teams without Projects v2 or ADO boards | Medium | Low | Labels fallback for GitHub; board-sync becomes no-op if no board config |
| Custom field IDs change after board reorganization | Low | Low | Re-run /ai-board-discover; stale IDs produce failed updates caught by fail-open |
