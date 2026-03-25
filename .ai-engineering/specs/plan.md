---
total: 13
completed: 13
---

# Plan: spec-076 Autopilot Sub-Spec Quality Parity and Dispatch Quality+Deliver Phases

## Pipeline: full
## Phases: 4
## Tasks: 13 (build: 12, verify: 1)

### Phase 1: Autopilot Handler Modernization
**Gate**: All 7 handlers reference `sub-NNN/spec.md` + `sub-NNN/plan.md`; plan sections use `- [ ] T-N.K` checkbox format; no handler references `sub-NNN.md` as a flat file.

- [x] T-1.1: Update `phase-decompose.md` -- change shell schema to create `sub-NNN/` subdirectories with `spec.md` (frontmatter + Scope) and `plan.md` (frontmatter + Plan placeholder + Self-Report placeholder) shells. Update manifest format to reference subdirectory paths. Update output section and examples. (agent: build)
- [x] T-1.2: Update `phase-deep-plan.md` -- agents enrich `sub-NNN/spec.md` with Exploration section and `sub-NNN/plan.md` with checkbox-formatted tasks (`- [ ] T-N.K` with Files + Done condition). Update prerequisites, agent prompt template, gate criteria, and output section. (agent: build)
- [x] T-1.3: Update `phase-orchestrate.md` -- change Step 1 to read `sub-NNN/plan.md` for exports/imports/files instead of `sub-NNN.md`. Update directory glob from `specs/autopilot/sub-*.md` to `specs/autopilot/sub-*/plan.md`. Update examples. DAG logic unchanged. (agent: build)
- [x] T-1.4: Update `phase-implement.md` -- Agent(Build) prompt references `sub-NNN/spec.md` for scope context and `sub-NNN/plan.md` for task list. After completing each task, agent marks `- [x]` in plan.md. Self-Report written to plan.md (not spec.md). Update agent prompt template, Self-Report instructions, and output section. (agent: build)
- [x] T-1.5: Update `phase-quality.md` -- change Self-Report source from `sub-NNN.md` to `sub-NNN/plan.md`. Update prerequisites table, Step 2b cross-reference instructions, and Step 2d fix agent context references. (agent: build)
- [x] T-1.6: Update `phase-deliver.md` -- change Step 1 glob from `sub-*.md` to `sub-*/plan.md` for Self-Reports. Update Step 3 cleanup to `rm -rf specs/autopilot/` (already handles subdirectories). Update prerequisites and output section. (agent: build)
- [x] T-1.7: Update autopilot `SKILL.md` -- update Process Step 1 (`sub-NNN/spec.md` + `sub-NNN/plan.md`), Step 2 (enrich both files), Step 4 (mark checkboxes), Step 6 (cleanup subdirectories). Verify Handler Dispatch Table, Thin Orchestrator section, and Integration section are still accurate. (agent: build)

### Phase 2: Legacy Cleanup + Dispatch Handlers
**Gate**: 5 legacy handlers deleted. Dispatch has `handlers/quality.md` and `handlers/deliver.md`. All three are structurally complete.

- [x] T-2.1: Delete 5 legacy v1 handlers -- `phase-execute.md`, `phase-explore.md`, `phase-split.md`, `phase-verify.md`, `phase-pr.md`. Confirmed dead code: not in SKILL.md Handler Dispatch Table, not referenced by any active handler. (agent: build)
- [x] T-2.2: Create `ai-dispatch/handlers/quality.md` -- Dispatch quality check handler. Dispatch Agent(Verify) + Agent(Review) in parallel on `git diff main...HEAD`. Unified severity mapping. Pass condition: 0 blockers + 0 criticals + 0 highs. Fix cycle: dispatch Agent(Build) per finding, commit fixes, retry. Max 2 rounds. Round 2 with blockers: STOP and escalate. Thin orchestrator: reads ai-verify/SKILL.md and ai-review/SKILL.md at dispatch time. Document what dispatch quality does NOT check (no Guard, no decision-store, no ownership). (agent: build)
- [x] T-2.3: Create `ai-dispatch/handlers/deliver.md` -- Dispatch deliver handler. Follow ai-pr SKILL.md starting from Step 7 (pre-push checks). Steps 0-6 only if unstaged changes exist. PR body includes simplified quality report (severity counts, rounds, changeset scope). No Self-Reports, no Integrity Report. Enable auto-complete with squash merge. Watch-and-fix loop per ai-pr. Thin orchestrator: reads ai-pr/SKILL.md at dispatch time. (agent: build)
- [x] T-2.4: Update `ai-dispatch/SKILL.md` -- add Phase 3 (Quality Check) and Phase 4 (Deliver) to Process. Remove `/ai-commit` transition from Integration section. Add ai-verify, ai-review, ai-pr to "Calls" list. Define `--resume` behavior for Phases 3-4 (all tasks DONE but no PR → resume Phase 3; quality passed but no PR → resume Phase 4). Update Two-Stage Review section to clarify it is per-task; new Phase 3 is full-changeset. (agent: build) [depends on T-2.2, T-2.3]

### Phase 3: Mirror Sync
**Gate**: All IDE mirrors updated. New dispatch handler mirrors exist.

- [x] T-3.1: Run `sync_command_mirrors.py` for ai-autopilot and ai-dispatch. Verify new mirrors created for `ai-dispatch/handlers/quality.md` and `ai-dispatch/handlers/deliver.md` in `.github/prompts/` and `.agents/skills/`. If script does not create new file mirrors, create them manually. (agent: build) [depends on Phase 1, Phase 2]

### Phase 4: Verification
**Gate**: All 18 ACs pass.

- [x] T-4.1: Verify all acceptance criteria -- AC15 (grep for flat `sub-NNN.md` in autopilot handlers), AC16 (legacy files deleted), AC17 (dispatch Integration section), AC18 (dispatch resume). Spot-check AC1-AC14 by reading modified files. Report pass/fail per AC. (agent: verify) [depends on Phase 3]
