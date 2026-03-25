---
id: spec-076
title: "Autopilot Sub-Spec Quality Parity and Dispatch Quality+Deliver Phases"
status: draft
created: 2026-03-25
refs: []
---

# spec-076: Autopilot Sub-Spec Quality Parity and Dispatch Quality+Deliver Phases

## Problem

### 1. Autopilot sub-plans lack progress tracking

Phase 2 (Deep Plan) handler specifies `### T-N.K` task format but no checkboxes. In practice, agents produce `### Step N` headers instead. This means:
- No checkbox tracking during Phase 4 implementation
- Sub-plans are not treated as first-class plans like `plan.md`
- Progress is invisible -- only manifest status (planned/implemented/blocked) is tracked

### 2. Autopilot sub-specs are monolithic files

Each `sub-NNN.md` mixes four concerns with different lifecycles:
- **Scope** (Phase 1) -- requirements contract
- **Exploration** (Phase 2) -- codebase analysis
- **Plan** (Phase 2) -- task list
- **Self-Report** (Phase 4) -- implementation evidence

This violates the spec/plan separation that the framework enforces at the top level (`spec.md` / `plan.md`). Sub-specs are not treated as complete spec+plan pairs, degrading quality assurance.

### 3. ai-dispatch lacks quality and delivery phases

Dispatch's Two-Stage Review (per-task spec compliance + code quality) never evaluates the full changeset as a unit. After all tasks complete, dispatch transitions to `/ai-commit` without:
- Running quality tools on the complete changeset
- Creating a PR with review context
- Any final quality gate

This is a gap: autopilot has Phase 5 (quality loop) and Phase 6 (deliver via PR), but dispatch -- the more commonly used execution skill -- has neither.

## Solution

### Group 1: Autopilot Sub-Spec Split

Split each `sub-NNN.md` into a subdirectory with two files:

```
specs/autopilot/sub-NNN/spec.md   # Scope + Exploration
specs/autopilot/sub-NNN/plan.md   # Plan (checkboxes) + Self-Report
```

**spec.md** contains:
- Frontmatter (id, parent, title, status, files, depends_on)
- `## Scope` -- requirements extracted from parent spec
- `## Exploration` -- codebase analysis (Existing Files, Patterns, Dependencies, Risks)

**plan.md** contains:
- Frontmatter (total, completed task counts)
- `## Plan` with simplified checkbox format:
  ```markdown
  exports: [modules/classes this sub-spec creates]
  imports: [modules/classes expected from other sub-specs]

  - [ ] T-N.1: [task title]
    - **Files**: [paths]
    - **Done**: [verifiable condition]
  - [ ] T-N.2: [task title]
    - **Files**: [paths]
    - **Done**: [verifiable condition]
  ```
- `## Self-Report` (populated by Phase 4 Agent(Build))

No phases, no gates, no agent assignments in the sub-plan. The Agent(Build) executes all tasks sequentially. The real quality gate is Phase 5.

### Group 2: Dispatch Quality + Deliver Phases

Add two new phases to ai-dispatch after task execution:

**Phase 3: Quality Check** (new handler `handlers/quality.md`):
- Dispatch Agent(Verify) + Agent(Review) in parallel on full changeset (`git diff main...HEAD`)
- Consolidate findings with unified severity mapping
- If clean (0 blockers + 0 criticals + 0 highs): proceed to Phase 4
- If issues remain: dispatch fix agents, commit, retry
- Max 2 rounds total. Round 2 with blockers: STOP and escalate
- No Agent(Guard) -- guard is for multi-sub-spec governance, not relevant for dispatch-scale work

**Dispatch quality does NOT check** (by design):
- Decision-store constraint violations (no Agent(Guard))
- Expired risk acceptances, ownership violations, framework integrity drift
- Users working on governance-sensitive changes must run `/ai-governance` separately

**Phase 4: Deliver** (new handler `handlers/deliver.md`):
- Follow ai-pr SKILL.md starting from Step 7 (pre-push checks). Steps 0-6 (commit pipeline) run only if unstaged changes exist (quality report files, manifest updates). Dispatch commits changes per-task and per-quality-round, so the commit pipeline is typically unnecessary.
- PR body includes simplified quality report: final severity counts, rounds executed, changeset scope
- No Self-Reports, no Integrity Report (dispatch has no sub-specs)
- Enable auto-complete with squash merge
- Enter watch-and-fix loop per ai-pr

**Removed transition**: dispatch no longer transitions to `/ai-commit`. Delivery is always via PR through ai-pr.

### Handler Impact Matrix

| Handler | Change Type |
|---------|-------------|
| `ai-autopilot/handlers/phase-decompose.md` | Modified: create `sub-NNN/` directories with spec.md + plan.md shells |
| `ai-autopilot/handlers/phase-deep-plan.md` | Modified: enrich both files; plan with checkbox format |
| `ai-autopilot/handlers/phase-implement.md` | Modified: mark checkboxes in plan.md, write Self-Report to plan.md |
| `ai-autopilot/handlers/phase-quality.md` | Modified: update file paths for subdirectory structure |
| `ai-autopilot/handlers/phase-deliver.md` | Modified: update globs and cleanup for subdirectories |
| `ai-autopilot/handlers/phase-orchestrate.md` | Modified: update file paths in glob and plan extraction |
| `ai-autopilot/SKILL.md` | Modified: update Process steps 1, 2, 4, 6 to reference `sub-NNN/` structure |
| ~~phase-execute.md~~ | Deleted (legacy v1 handler) |
| ~~phase-explore.md~~ | Deleted (legacy v1 handler) |
| ~~phase-split.md~~ | Deleted (legacy v1 handler) |
| ~~phase-verify.md~~ | Deleted (legacy v1 handler) |
| ~~phase-pr.md~~ | Deleted (legacy v1 handler) |
| `ai-dispatch/SKILL.md` | Modified: add quality+deliver phases, remove `/ai-commit` transition |
| `ai-dispatch/handlers/quality.md` | **NEW**: Verify+Review parallel, max 2 rounds, fix cycle |
| `ai-dispatch/handlers/deliver.md` | **NEW**: ai-pr with simplified quality report |

## Scope

### In Scope

1. Update `phase-decompose.md`: create `sub-NNN/` subdirectories with `spec.md` + `plan.md` shell files
2. Update `phase-deep-plan.md`: enrich `sub-NNN/spec.md` with Exploration, enrich `sub-NNN/plan.md` with checkbox-formatted tasks
3. Update `phase-implement.md`: mark checkboxes `- [x]` as tasks complete, write Self-Report to `plan.md`
4. Update `phase-quality.md`: update glob patterns from `sub-NNN.md` to `sub-NNN/spec.md` + `sub-NNN/plan.md`
5. Update `phase-deliver.md`: update globs, update cleanup logic for subdirectory structure
6. Update `phase-orchestrate.md`: update glob patterns and file references from `sub-NNN.md` to `sub-NNN/spec.md` + `sub-NNN/plan.md` (DAG logic unchanged, only paths)
7. Update autopilot `SKILL.md`: update Process steps 1, 2, 4, 6 to reference `sub-NNN/` structure; verify Thin Orchestrator and Integration sections remain accurate
8. Delete 5 legacy v1 handlers: `phase-execute.md`, `phase-explore.md`, `phase-split.md`, `phase-verify.md`, `phase-pr.md` (not in Handler Dispatch Table, dead code)
9. Create `ai-dispatch/handlers/quality.md`: Verify+Review parallel, max 2 rounds, fix cycle
10. Create `ai-dispatch/handlers/deliver.md`: ai-pr with simplified quality report
11. Update `ai-dispatch/SKILL.md`: add Phases 3+4, remove `/ai-commit` transition, update Integration section (add ai-verify, ai-review, ai-pr to "Calls"), update process flow
12. Define dispatch `--resume` behavior for Phases 3-4: if all tasks DONE but quality not passed, resume at Phase 3; if quality passed but PR not created, resume at Phase 4
13. Update `phase-decompose.md` manifest format: reflect subdirectory paths in file references
14. Update IDE mirrors via `sync_command_mirrors.py` for both modified skills

### Out of Scope

- Changing Phase 3 (Orchestrate) DAG construction logic (only file path references updated)
- Changing Phase 5 quality agents, severity mapping, or round limits for autopilot
- Adding Self-Reports to dispatch (dispatch has no sub-spec decomposition)
- Adding Agent(Guard) to dispatch quality check (guard is for multi-sub-spec governance)
- Modifying ai-verify, ai-review, or ai-pr SKILL.md files (consumed as-is by both skills)
- Modifying ai-commit SKILL.md (remains usable standalone, just no longer called by dispatch)
- Changing the content or structure of Exploration or Self-Report sections (only file location changes)

## Acceptance Criteria

- [ ] AC1: Phase 1 creates `specs/autopilot/sub-NNN/spec.md` and `specs/autopilot/sub-NNN/plan.md` for each concern
- [ ] AC2: `sub-NNN/plan.md` uses `- [ ] T-N.K` checkbox format for all tasks
- [ ] AC3: Phase 4 Agent(Build) marks checkboxes `- [x]` in `plan.md` as tasks complete
- [ ] AC4: Phase 4 Agent(Build) writes `## Self-Report` to `sub-NNN/plan.md`
- [ ] AC5: Phase 2 populates `sub-NNN/spec.md` with `## Exploration` section (Existing Files + Patterns mandatory)
- [ ] AC6: Phase 2 populates `sub-NNN/plan.md` with checkbox-formatted tasks including `exports:`/`imports:` declarations
- [ ] AC7: Phase 5 reads Self-Reports from `sub-NNN/plan.md` for cross-reference against quality findings
- [ ] AC8: Phase 6 cleanup deletes `specs/autopilot/` including all subdirectories
- [ ] AC9: `--resume` correctly identifies pipeline state from new directory structure
- [ ] AC10: ai-dispatch runs Verify+Review in parallel on full changeset after all tasks complete
- [ ] AC11: ai-dispatch quality check blocks delivery when blockers, criticals, or highs remain
- [ ] AC12: ai-dispatch fix cycle runs max 2 rounds before escalating
- [ ] AC13: ai-dispatch delivers via ai-pr after quality passes (not `/ai-commit`)
- [ ] AC14: ai-dispatch SKILL.md does not reference `/ai-commit` as a transition target
- [ ] AC15: No handler in `ai-autopilot/handlers/` references `sub-NNN.md` as a flat file path
- [x] AC16: Legacy handlers (phase-execute, phase-explore, phase-split, phase-verify, phase-pr) are deleted
- [ ] AC17: ai-dispatch SKILL.md Integration section lists ai-verify, ai-review, and ai-pr as called skills
- [ ] AC18: ai-dispatch `--resume` re-enters at Phase 3 if all tasks are DONE but no PR exists

## Files Modified

| File | Change |
|------|--------|
| `.claude/skills/ai-autopilot/handlers/phase-decompose.md` | Create `sub-NNN/` directories with `spec.md` + `plan.md` shells |
| `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md` | Enrich both files; plan with checkbox format |
| `.claude/skills/ai-autopilot/handlers/phase-implement.md` | Mark checkboxes, write Self-Report to `plan.md` |
| `.claude/skills/ai-autopilot/handlers/phase-quality.md` | Update file paths for new structure |
| `.claude/skills/ai-autopilot/handlers/phase-deliver.md` | Update globs, cleanup for subdirectories |
| `.claude/skills/ai-autopilot/handlers/phase-orchestrate.md` | Update file paths in glob and plan extraction |
| `.claude/skills/ai-autopilot/SKILL.md` | Update Process steps and structure references |
| ~~phase-execute.md~~ | **DELETED** (legacy v1 handler) |
| ~~phase-explore.md~~ | **DELETED** (legacy v1 handler) |
| ~~phase-split.md~~ | **DELETED** (legacy v1 handler) |
| ~~phase-verify.md~~ | **DELETED** (legacy v1 handler) |
| ~~phase-pr.md~~ | **DELETED** (legacy v1 handler) |
| `.claude/skills/ai-dispatch/SKILL.md` | Add quality+deliver phases, remove `/ai-commit` transition |
| `.claude/skills/ai-dispatch/handlers/quality.md` | **NEW**: Verify+Review, max 2 rounds, fix cycle |
| `.claude/skills/ai-dispatch/handlers/deliver.md` | **NEW**: ai-pr with simplified quality report |

## Assumptions

- ai-pr SKILL.md is stable and usable by both autopilot and dispatch without modification
- Agent(Build) can reliably mark checkboxes in plan files via Edit tool on markdown
- Subdirectory structure does not break existing glob patterns outside autopilot handlers
- Two quality rounds is sufficient for dispatch-scale changes (typically <3 concerns, <10 files)
- Removing `/ai-commit` transition from dispatch does not affect users who invoke `/ai-commit` directly
- Dispatch-scale work (typically <3 concerns) does not require governance verification during quality check; users can invoke `/ai-governance` directly for governance-sensitive changes
- `sync_command_mirrors.py` creates new mirror files for new handlers (not just updates existing ones); if it only syncs existing files, manual mirror creation is needed for dispatch handlers

## Risks

| Risk | Mitigation |
|------|-----------|
| Agents may not reliably mark checkboxes | Explicit instruction in handler: "After completing T-N.K, edit plan.md to mark `- [x] T-N.K`" |
| Subdirectory structure increases Phase 1 file creation | Mechanical overhead only: 2 Write calls per concern instead of 1 |
| Dispatch quality adds latency to small changes | Proportionate: 2 agents, 2 max rounds vs autopilot's 3 agents, 3 rounds |
| `/ai-commit` standalone usage confusion | ai-commit remains available as standalone skill; only dispatch stops calling it |
| Resume protocol must handle new directory structure | Resume reads manifest (unchanged location); manifest references `sub-NNN/` paths instead of `sub-NNN.md` |
| sync_command_mirrors.py may not create mirrors for NEW handler files | Verify script behavior for new files during implementation; add manual mirror creation if needed |
| Dispatch deliver re-runs commit pipeline unnecessarily | Deliver starts from ai-pr Step 7 by default; Steps 0-6 only if unstaged changes exist |

## Dependencies

- Must execute after spec-074 and spec-075 complete (no file overlap, but uses current autopilot format)
- No external dependencies
