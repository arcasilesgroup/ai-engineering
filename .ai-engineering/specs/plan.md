# Plan: spec-065 Autopilot v2

## Pipeline: standard
## Phases: 4
## Tasks: 14 (build: 11, verify: 3)

---

### Phase 1: Foundation
**Gate**: New SKILL.md exists with 6-phase structure. All 5 old handlers deleted. `$ARGUMENTS` as last line.

- [x] T-1.1: Delete the 5 v1 handler files from `.claude/skills/ai-autopilot/handlers/` -- phase-split.md, phase-explore.md, phase-execute.md, phase-verify.md, phase-pr.md (agent: build) -- done: `ls handlers/` shows 0 files
- [x] T-1.2: Write new `.claude/skills/ai-autopilot/SKILL.md` from scratch (agent: build, blocked by T-1.1) -- done: file exists with all required sections, ends with `$ARGUMENTS`
  - Frontmatter: name, description (updated for v2), effort:max, argument-hint (`'implement spec-NNN'|--resume|--no-watch`), tags
  - `## Purpose`: autonomous execution, 6-phase pipeline, single approval gate
  - `## When to Use` / `## When NOT to Use`: >= 3 concerns for autopilot, <3 use /ai-dispatch
  - `## Process`: Step 0 (Load+Validate, spec-only prerequisite per D7, no plan.md required), Steps 1-6 each referencing `handlers/phase-*.md`
  - `## Handler Dispatch Table`: 6 rows mapping phase to handler to agent pattern
  - `## Flags`: --resume (Resume Protocol), --no-watch (skip PR watch loop)
  - `## Thin Orchestrator Principle`: reads other skills' SKILL.md, embeds into subagent prompts
  - `## Governance`: DEC-023 invocation-as-approval
  - `## Failure Recovery` table: 6 scenarios (Phase 2 agent fail, blocked sub-spec, cascade block, quality loop exhausted, final blockers, mid-pipeline crash)
  - `## Telemetry`: v1 events preserved + v2 events (decompose_complete, deep_plan_complete, dag_built, quality_round)
  - `## Quick Reference`, `## Common Mistakes`, `## Integration`
  - `$ARGUMENTS` as last line

### Phase 2: Handlers (T-2.1 through T-2.6 are independent -- parallelize all 6)
**Gate**: All 6 handlers exist in `handlers/`. Each >50 lines. Each follows pattern: `# Handler: [Name]`, `## Purpose`, `## Inputs`/`## Prerequisites`, `## Procedure` with `### Step N`, `## Output`, `## Failure Modes`/`## Gate`.

- [x] T-2.1: Write `handlers/phase-decompose.md` -- Phase 1: DECOMPOSE (agent: build, blocked by T-1.2) -- done: file exists with Shell Schema template, minimum 3 concern guard
  - Spec source: lines 129-166
  - Must include: read spec + decision-store, extract N concerns, minimum 3 concern guard (abort → recommend /ai-dispatch), Shell Schema template (full markdown with frontmatter: id, parent, title, files + sections: Scope, Exploration [EMPTY], Plan [EMPTY], Self-Report [EMPTY]), write manifest with `planning` status, validate no orphan requirements
  - Output: N sub-spec shells + manifest.md
  - Failure modes: spec is placeholder, <3 concerns, orphan requirements

- [x] T-2.2: Write `handlers/phase-deep-plan.md` -- Phase 2: DEEP PLAN (agent: build, blocked by T-1.2) -- done: file exists with parallel dispatch, exports/imports gate, failure handling
  - Spec source: lines 168-186
  - Must include: dispatch Agent(Explore+Plan) per sub-spec in parallel (use `run_in_background: true`), 5-step procedure (deep explore, write Exploration with "Existing Files" + "Patterns to Follow" subsections, write Plan with ordered tasks T-N.1/T-N.2 including file paths + done conditions + exports:/imports: declarations, refine file list, self-assess confidence), gate criteria (all 3 checks), failure handling (retry once, `plan-failed` status, subset evaluation for critical vs optional scope)
  - Output: N enriched sub-spec files
  - Failure modes: agent timeout, empty output, all agents fail

- [x] T-2.3: Write `handlers/phase-orchestrate.md` -- Phase 3: ORCHESTRATE (agent: build, blocked by T-1.2) -- done: file exists with DAG algorithm, merge logic, wave format
  - Spec source: lines 188-210
  - Must include: read N sub-specs + extract file lists + exports/imports, build file-overlap matrix (pairwise path comparison), build import-chain graph (from structured exports/imports declarations, NOT code analysis), construct DAG (zero overlap+zero chains → same wave, overlap or dependency → sequential), assign wave numbers, write DAG to manifest `## Execution DAG` section (format: `Wave N (parallel): sub-001, sub-003`), validate acyclicity, merge logic for unresolvable conflicts (log rationale), note on fully-serial DAG being expected for tightly coupled specs
  - Output: DAG with wave assignments in manifest.md
  - Failure modes: cyclic dependency detected, merge required

- [x] T-2.4: Write `handlers/phase-implement.md` -- Phase 4: IMPLEMENT (agent: build, blocked by T-1.2) -- done: file exists with Self-Report template, cascade blocking, wave commit protocol
  - Spec source: lines 212-245
  - Must include: iterate waves in DAG order, dispatch Agent(Build) per sub-spec in wave (parallel), context injection (sub-spec content, decision-store, stack standards from `contexts/languages/` + `contexts/frameworks/`, file boundaries: "Do NOT modify files outside your scope"), Self-Report section template (6 classifications: real/aspirational/stub/failing/invented/hallucinated, table format: File/Function | Classification | Notes), wave commit protocol (`spec-NNN: wave W -- [titles]`), manifest update to `implemented`, cascade blocking protocol (blocked → mark dependents as `cascade-blocked` without execution)
  - Output: committed waves, updated manifest
  - Failure modes: build agent fails, cascade blocking triggered

- [x] T-2.5: Write `handlers/phase-quality.md` -- Phase 5: QUALITY LOOP (agent: build, blocked by T-1.2) -- done: file exists with severity mapping, 3-round loop, partial changeset handling
  - Spec source: lines 247-281
  - Must include: 3-round max loop, step 5a (dispatch 3 agents parallel: Agent(Verify) `platform` mode referencing `.claude/skills/ai-verify/SKILL.md`, Agent(Guard) `advise` mode, Agent(Review) 8-agent referencing `.claude/skills/ai-review/SKILL.md`), step 5b (consolidation with severity mapping table: verify as-is, guard concern→high / warn→medium / info→low, review as-is; cross-reference against Self-Reports), partial changeset handling (blocked sub-specs → verify implemented subset only, note gaps), step 5c (evaluation: 0 B+C+H → PASS, round<3 → fix, round=3 + blockers → STOP no PR, round=3 + only C/H → Phase 6 flagged), step 5d (fix dispatch: Agent(Build) per finding, commit `spec-NNN: quality round R -- fix [category]`)
  - Output: clean changeset or documented remaining issues
  - Failure modes: quality loop exhausted with blockers, all 3 agents fail

- [x] T-2.6: Write `handlers/phase-deliver.md` -- Phase 6: DELIVER + Resume Protocol (agent: build, blocked by T-1.2) -- done: file exists with Integrity Report template, Resume Protocol 7 re-entry points, cleanup verification
  - Spec source: lines 283-337
  - Must include: 6a Transparency Report (read all Self-Reports, read quality loop findings, produce Integrity Report with 3 sections: Summary with 6-category counts, Quality Convergence with rounds + final state, Details table with file/function/classification/evidence/notes; if blocked sub-specs exist add "Blocked / Undelivered" section), 6b deliver PR (reference `.claude/skills/ai-pr/SKILL.md` -- thin orchestrator, do NOT duplicate steps; include Integrity Report + sub-spec completion table in PR body; auto-complete squash; watch-and-fix unless --no-watch), Resume Protocol (7 re-entry points based on manifest state: all planning→Phase 2, no DAG→Phase 3, partial waves→Phase 4, all implemented no quality→Phase 5, quality stopped→Phase 5 reset, quality passed no PR→Phase 6), 6c cleanup (delete autopilot/, clear spec.md + plan.md with placeholders, add to _history.md, VERIFY cleanup by re-reading files per lessons.md, commit `chore: clear autopilot state after spec-NNN delivery`)
  - Output: PR with Integrity Report, cleaned state
  - Failure modes: PR creation fails, cleanup not verified

### Phase 3: Agent + Mirrors
**Gate**: Agent file updated with 6-phase state machine. `sync_command_mirrors.py --check` reports zero drift. All mirrors regenerated.

- [x] T-3.1: Rewrite `.claude/agents/ai-autopilot.md` (agent: build, blocked by T-2.6) -- done: file exists with 6-phase state machine, no v1 references
  - Frontmatter: name: ai-autopilot, description (v2), model: opus, color: purple, tools: [Read, Glob, Grep, Bash]
  - Body sections (follow existing agent pattern from other agents):
    - Identity: thin orchestrator, never writes code
    - Mandate: execute approved specs autonomously via 6-phase pipeline
    - Capabilities: 6 phases listed with 1-line description each
    - Subagent Orchestration: dispatch patterns for Agent(Explore), Agent(Build), Agent(Verify), Agent(Guard), Agent(Review) -- when each is used, what they receive
    - Behavior: 6 numbered phases with key actions per phase
    - State Machine table: states (loading, decomposing, deep-planning, orchestrating, implementing, quality-looping, delivering, done, halted) with transitions
    - Self-Challenge Protocol: after each phase, question own output before proceeding
    - Referenced Skills table: ai-verify, ai-review, ai-pr, ai-commit, ai-dispatch (read at runtime)
    - Boundaries: never write code, never skip phases, never bypass quality loop
    - Escalation Protocol: when to halt and report to user
  - No v1 references (no "phase-split", "exploration.md", "sequential execute")

- [x] T-3.2: Run `python scripts/sync_command_mirrors.py` to regenerate all mirrors (agent: build, blocked by T-3.1) -- done: script exits 0
- [x] T-3.3: Verify mirror sync and cross-references (agent: verify, blocked by T-3.2) -- done: zero drift, all handler references resolve
  - Run `python scripts/sync_command_mirrors.py --check` — must exit 0
  - Verify `.github/prompts/ai-autopilot.prompt.md` contains all 6 handlers inlined
  - Verify `.agents/skills/autopilot/handlers/` has 6 handler files

### Phase 4: Verification
**Gate**: All 33 ACs addressed. Zero v1 remnants. All skill path references resolve.

- [x] T-4.1: Verify no v1 remnants and all cross-references resolve (agent: verify, blocked by T-3.3) -- done: zero v1 matches, all skill paths exist, 6 handlers confirmed
  - Grep `.claude/skills/ai-autopilot/` + `.claude/agents/ai-autopilot.md` for v1 terms: "exploration.md", "phase-split", "phase-execute", "sub-NNN-plan.md", "Step 2a", "Step 2b" — zero matches expected
  - Grep all 6 handlers for `.claude/skills/ai-` references — confirm each target SKILL.md exists on disk
  - `ls .claude/skills/ai-autopilot/handlers/` — exactly 6 files: phase-decompose.md, phase-deep-plan.md, phase-orchestrate.md, phase-implement.md, phase-quality.md, phase-deliver.md
  - Spot-check: SKILL.md Handler Dispatch Table has 6 rows matching the 6 handler filenames

- [x] T-4.2: AC coverage sweep (agent: verify, blocked by T-4.1) -- done: all 33 ACs mapped to file content
  - For each AC (1-33), identify which file addresses it (SKILL.md, handler, or agent)
  - Flag any AC not covered by any file — must be 0 uncovered
  - Produce AC→file mapping table as verification evidence

---

## Agent Assignments Summary

| Agent | Tasks | Purpose |
|-------|-------|---------|
| build | 11 | Delete old handlers, write SKILL.md, write 6 handlers, write agent, run sync |
| verify | 3 | Mirror sync check, v1 remnant scan, AC coverage sweep |

## Dependencies

```
T-1.1 → T-1.2
              ↘
               T-2.1 ┐
               T-2.2 ┤
               T-2.3 ┤ (all 6 parallel)
               T-2.4 ┤
               T-2.5 ┤
               T-2.6 ┘
                     ↓
               T-3.1 → T-3.2 → T-3.3
                                   ↓
                        T-4.1 → T-4.2
```

Phase 2 tasks are fully parallel (6 independent handler files).
Phase 3 requires all Phase 2 tasks complete (agent file references all handlers).
Phase 4 is final verification.

## Files Modified

| File | Phase | Action |
|------|-------|--------|
| `.claude/skills/ai-autopilot/handlers/phase-split.md` | 1 | delete |
| `.claude/skills/ai-autopilot/handlers/phase-explore.md` | 1 | delete |
| `.claude/skills/ai-autopilot/handlers/phase-execute.md` | 1 | delete |
| `.claude/skills/ai-autopilot/handlers/phase-verify.md` | 1 | delete |
| `.claude/skills/ai-autopilot/handlers/phase-pr.md` | 1 | delete |
| `.claude/skills/ai-autopilot/SKILL.md` | 1 | rewrite |
| `.claude/skills/ai-autopilot/handlers/phase-decompose.md` | 2 | create |
| `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md` | 2 | create |
| `.claude/skills/ai-autopilot/handlers/phase-orchestrate.md` | 2 | create |
| `.claude/skills/ai-autopilot/handlers/phase-implement.md` | 2 | create |
| `.claude/skills/ai-autopilot/handlers/phase-quality.md` | 2 | create |
| `.claude/skills/ai-autopilot/handlers/phase-deliver.md` | 2 | create |
| `.claude/agents/ai-autopilot.md` | 3 | rewrite |

## Auto-generated (via sync, NOT manually edited)

| File | Source |
|------|--------|
| `.github/prompts/ai-autopilot.prompt.md` | sync from SKILL.md + 6 handlers (flattened) |
| `.github/agents/autopilot.agent.md` | sync from ai-autopilot.md + AGENT_METADATA |
| `.agents/skills/autopilot/SKILL.md` | sync from SKILL.md |
| `.agents/skills/autopilot/handlers/*.md` (6 files) | sync from handlers/ |
| `.agents/agents/ai-autopilot.md` | sync from ai-autopilot.md |
| `templates/project/.claude/skills/ai-autopilot/` | sync from canonical |
| `templates/project/.claude/agents/ai-autopilot.md` | sync from canonical |
| `templates/project/prompts/ai-autopilot.prompt.md` | sync from canonical |
| `templates/project/agents/autopilot.agent.md` | sync from canonical |
