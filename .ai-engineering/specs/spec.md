---
id: spec-065
title: "Autopilot v2: Parallel Intelligence, DAG Execution, Quality Convergence"
status: approved
created: 2026-03-24
refs: [DEC-023]
---

# spec-065: Autopilot v2

## Problem

The current `/ai-autopilot` (v1) has structural defects that undermine autonomous execution quality:

1. **Shallow exploration**: Sub-specs are created by a single orchestrator in one pass. The explore phase populates `exploration.md` but evidence from spec-064 shows it was never written — sub-specs executed without architectural context, leading to implementation drift.

2. **Sequential execution**: Sub-specs execute one-by-one. A 7-sub-spec pipeline runs 7 serial agents. Independent sub-specs that could run in parallel are forced to wait.

3. **Single-shot verify**: Each sub-spec gets one verify pass with one retry. There is no quality convergence loop — if verify fails twice, the pipeline halts. There is no guard or review pass. Issues that require iterative refinement (lint, type errors, integration bugs) cannot be resolved.

4. **No orchestration awareness**: File ownership is declared statically in the manifest. There is no analysis of the N plans together to detect import chains, shared modules, or execution order conflicts before implementation starts.

5. **Zero transparency**: The only output is PASS/FAIL per sub-spec. There is no disclosure of what is real vs. aspirational, what is stubbed, what was invented by the agent, or what was hallucinated. The user sees a PR but cannot assess the integrity of the implementation without reading every line.

6. **Frontmatter state drift**: Sub-spec files are never updated to `complete` after execution. The manifest is the authority but the sub-spec files contradict it. State lives in two places and diverges.

## Solution

Rewrite `/ai-autopilot` as a **6-phase linear pipeline** with parallel intelligence gathering, DAG-driven execution, and a quality convergence loop:

```
Phase 1: DECOMPOSE    -- Split spec into N concerns
Phase 2: DEEP PLAN    -- N parallel agents: explore + sub-spec + plan (per concern)
Phase 3: ORCHESTRATE   -- Analyze N plans, build DAG, resolve conflicts
Phase 4: IMPLEMENT     -- Agents execute per DAG (parallel where safe, serial where dependent)
Phase 5: QUALITY LOOP  -- verify + guard + review on full changeset, fix, iterate (max 3 rounds)
Phase 6: DELIVER       -- Transparency report + /ai-pr
```

Key design principles:
- **Single approval gate**: user approves the parent spec (DEC-023). Everything else is automatic. Next human gate is the PR (CI).
- **Parallel intelligence, not parallel guessing**: N agents each do deep codebase research before writing their plan. Implementation quality depends on plan quality.
- **DAG-driven execution**: the orchestration phase detects file overlaps and dependency chains across N plans. Independent sub-specs execute in parallel waves. Dependent sub-specs serialize.
- **Quality convergence**: the full changeset is verified, reviewed, and governance-checked as a unit. Fixes iterate up to 3 rounds. Remaining issues are reported, not hidden.
- **Radical transparency**: every agent self-reports what it built, stubbed, assumed, or invented. An independent audit classifies the full changeset. The PR body contains the complete integrity report.

## Scope

### In Scope

**A) SKILL.md Rewrite**

1. Rewrite `.claude/skills/ai-autopilot/SKILL.md` from scratch. New 6-phase pipeline. Remove all references to the v1 flow (split+explore combined, sequential execute, single verify).
2. Update skill description and argument-hint in frontmatter to reflect v2 semantics.

**B) Handler Rewrite (clean-sheet)**

3. Delete all existing handlers in `.claude/skills/ai-autopilot/handlers/`. Replace with:
   - `handlers/phase-decompose.md` -- Split parent spec into N concerns
   - `handlers/phase-deep-plan.md` -- N parallel agents: explore + sub-spec + plan
   - `handlers/phase-orchestrate.md` -- DAG construction from N plans
   - `handlers/phase-implement.md` -- DAG-driven parallel/serial execution
   - `handlers/phase-quality.md` -- Convergence loop: verify + guard + review
   - `handlers/phase-deliver.md` -- Transparency report + PR delivery

**C) Agent File Update**

4. Update `.claude/agents/ai-autopilot.md` to reflect the new 6-phase pipeline, updated capabilities, and new handler dispatch table.

**D) Manifest Schema Update**

5. Redesign the `specs/autopilot/manifest.md` schema:
   - Add `dag:` section with wave assignments and dependency edges
   - Add `transparency:` section for consolidated integrity report
   - Single source of truth for sub-spec status (manifest only -- no frontmatter `status:` field in sub-spec files)
   - Add `quality_rounds:` tracking section

**E) Sub-Spec Schema Update**

6. Redesign sub-spec file schema:
   - Remove `status:` from frontmatter (manifest is authority)
   - Add `self_report:` section template for implementation agents
   - Add `plan:` section with detailed tasks (no separate plan file per sub-spec)
   - Add `exploration:` section (populated by deep-plan agent, not a separate file)

**F) Transparency Protocol**

7. Define the transparency classification schema:
   - `real` -- implemented and verified, backed by tests or evidence
   - `aspirational` -- implemented but not fully tested or relying on unverified assumptions
   - `stub` -- placeholder implementation, marked with TODO or raises NotImplementedError
   - `failing` -- implemented but tests/lint/type checks fail on it
   - `invented` -- agent created something not specified (new helper, utility, pattern)
   - `hallucinated` -- agent referenced something that does not exist (phantom import, non-existent API)
8. Each implementation agent includes a `## Self-Report` section in its output with entries per file/function.
9. Phase 5 (quality loop) produces an independent `## Audit Report` that cross-references self-reports against evidence.
10. Phase 6 (deliver) consolidates both into the PR body `## Integrity Report`.

**G) Mirror Updates**

11. Update Copilot prompt mirror: `.github/prompts/ai-autopilot.prompt.md`
12. Update Codex/Gemini mirror: `.agents/skills/ai-autopilot/SKILL.md`

### Out of Scope

- Changes to `/ai-verify`, `/ai-review`, `/ai-commit`, `/ai-pr` skill logic or `Agent(Guard)` agent logic (they are consumed as-is)
- Changes to agent files other than `ai-autopilot.md`
- Python CLI code changes (the autopilot is a prompt-based orchestrator, not a CLI command)
- Changes to the current spec-064 autopilot state (sub-001 through sub-007)
- New telemetry event infrastructure (v2 emits new phase events using the existing hook system -- no new telemetry code)

## Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | 6-phase linear pipeline | Each phase has a clear input/output contract. Linear progression is debuggable. Parallelism happens WITHIN phases (2 and 4), not between them. |
| D2 | Parallel deep-plan agents (Phase 2) | v1's single-pass split produced shallow sub-specs. N agents each doing deep explore + plan produces higher-quality implementation instructions. |
| D3 | DAG-based orchestration (Phase 3) | Static file ownership in v1 was declared by the orchestrator, not validated. Phase 3 analyzes actual file references across all plans and builds a real dependency graph. |
| D4 | Quality convergence loop (Phase 5) | v1 verified per sub-spec with 1 retry. v2 verifies the full changeset with verify+guard+review and iterates up to 3 rounds. This catches cross-sub-spec integration issues. |
| D5 | Transparency protocol with 6 classifications | Agents hallucinate. The only defense is forced self-disclosure plus independent audit. Users see exactly what they're merging. |
| D6 | Manifest as single state authority | v1 had status in both manifest and sub-spec frontmatter, causing drift. v2 removes status from sub-spec frontmatter entirely. |
| D7 | Spec-only prerequisite (no plan.md) | The N deep-plan agents create their own plans. Requiring a pre-existing plan.md is redundant and constraining. |
| D8 | Embedded exploration (no separate exploration.md) | v1 defined exploration.md but it was never written in practice. v2 embeds exploration findings directly in each sub-spec's `## Exploration` section. |
| D9 | Max 3 quality rounds | Unbounded loops risk infinite compute. 3 rounds is enough for convergence in practice. After 3, remaining issues are reported, not hidden. |
| D10 | Clean-sheet handler rewrite | v1 handlers accumulated assumptions (sequential execution, single verify, no transparency). Refactoring would preserve those assumptions. Clean-sheet eliminates them. |

## Phase Details

### Phase 1: DECOMPOSE

**Input**: Approved `specs/spec.md`
**Output**: N sub-spec shells in `specs/autopilot/sub-NNN.md` + `specs/autopilot/manifest.md`

1. Read `specs/spec.md` and `state/decision-store.json`
2. Extract N independent concerns from the spec (each concern = a coherent unit of work: a module, a feature area, a config surface)
3. **Minimum concern guard**: if decomposition produces fewer than 3 concerns, abort and recommend `/ai-dispatch` instead. Log: "Spec has N concerns -- below autopilot threshold (3). Use /ai-dispatch."
4. Write sub-spec shell files using the **Shell Schema** below
5. Write manifest.md with sub-spec list, all status `planning`
6. Validate: every spec section maps to at least one sub-spec. No orphan requirements.

This phase is fast and shallow. It produces the skeleton that Phase 2 enriches.

**Sub-Spec Shell Schema** (Phase 1 output, Phase 2 input):

```markdown
---
id: sub-NNN
parent: spec-XXX
title: "Concern title"
files: []  # best guess -- Phase 2 refines
---

# Sub-Spec NNN: [title]

## Scope
[2-3 sentences from parent spec]

## Exploration
[EMPTY -- populated by Phase 2]

## Plan
[EMPTY -- populated by Phase 2]

## Self-Report
[EMPTY -- populated by Phase 4]
```

### Phase 2: DEEP PLAN (N agents, parallel)

**Input**: N sub-spec shells from Phase 1
**Output**: N fully-enriched sub-spec files with exploration + detailed plan

For each sub-spec, dispatch Agent(Explore + Plan) in parallel:

1. **Deep explore**: read every file mentioned in the sub-spec's scope. Map imports, callers, patterns, test fixtures. Read analogous implementations in the codebase.
2. **Write exploration section**: populate `## Exploration` with: existing files summary, patterns to follow, dependency map, risks discovered.
3. **Write detailed plan**: populate `## Plan` with: ordered tasks (T-N.1, T-N.2...), each with description, files, done condition. TDD pairs where tests are needed.
4. **Refine file list**: update sub-spec's `files:` frontmatter with the actual files discovered during exploration.
5. **Self-assess**: agent reports confidence (high/medium/low) and flags any assumptions or unknowns.

**Gate** (all must pass):
- Every sub-spec has non-empty `## Exploration` with at least "Existing Files" and "Patterns to Follow" subsections
- Every sub-spec has non-empty `## Plan` with at least 2 tasks, each with explicit file paths and done conditions
- Every plan declares `exports:` (modules/classes/functions it creates) and `imports:` (what it expects from other sub-specs) -- Phase 3 uses these for DAG construction

**Failure handling**: if a deep-plan agent fails (timeout, crash, empty output), retry once. If second attempt fails, mark sub-spec as `plan-failed` in manifest. If all agents fail, halt pipeline. If some succeed and some fail, the orchestrator evaluates: if failed sub-specs cover critical parent spec requirements, halt. If they cover optional/low-priority scope, proceed with the successful subset and report the gap.

### Phase 3: ORCHESTRATE

**Input**: N enriched sub-specs with plans
**Output**: DAG with wave assignments in `manifest.md`

1. Read all N sub-spec files. Extract file lists and `exports:`/`imports:` declarations from each.
2. Build file-overlap matrix: for each pair of sub-specs, check if they share files (create/modify the same path).
3. Build import-chain graph: using declared `exports:` and `imports:`, check if sub-spec A exports a module that sub-spec B imports. This uses structured declarations from Phase 2, not code analysis.
4. Construct DAG:
   - Sub-specs with zero overlap and zero import chains → same wave (parallel)
   - Sub-specs with overlap or import dependency → sequential (dependent waits for dependency)
5. Assign wave numbers: Wave 1 = no dependencies, Wave 2 = depends on Wave 1 only, etc.
6. Write DAG to manifest.md `## Execution DAG` section:
   ```
   Wave 1 (parallel): sub-001, sub-003, sub-005
   Wave 2 (parallel, after Wave 1): sub-002, sub-004
   Wave 3 (serial, after Wave 2): sub-006
   ```
7. Validate: DAG is acyclic. Every sub-spec has a wave assignment.

If conflicts cannot be resolved by ordering alone (e.g., two sub-specs must modify the same function), merge those sub-specs into one. Log the merge with rationale.

**Fully serial DAG**: if the DAG degenerates to one sub-spec per wave (every pair has dependencies), this is expected for tightly coupled specs. Execution proceeds normally -- Phase 2 deep-plan work is still valuable even without parallelism.

### Phase 4: IMPLEMENT (DAG-driven)

**Input**: Orchestrated manifest with wave assignments
**Output**: All sub-specs implemented and committed

For each wave in order:

1. Dispatch Agent(Build) per sub-spec in the wave (parallel within wave)
2. Each build agent receives:
   - The full sub-spec content (scope, exploration, plan, files)
   - Decision-store constraints
   - Stack standards from `contexts/languages/` and `contexts/frameworks/`
   - Explicit file boundaries: "Do NOT modify files outside your scope"
3. Each build agent executes its plan tasks in order
4. Each build agent writes a `## Self-Report` section at the end of the sub-spec file:
   ```markdown
   ## Self-Report
   | File/Function | Classification | Notes |
   |---------------|----------------|-------|
   | phases/detect.py:DetectPhase | real | Full implementation, tested |
   | phases/tools.py:check_auth() | stub | Returns True always, needs real impl |
   | merge.py:validate_schema() | invented | Not in spec, added for safety |
   ```
5. After all agents in the wave complete: commit the wave
   ```
   git add [files from all sub-specs in this wave]
   git commit -m "spec-NNN: wave W -- [sub-spec titles]"
   ```
6. Update manifest: mark wave sub-specs as `implemented`
7. Proceed to next wave

If a build agent fails (cannot complete its plan): mark sub-spec as `blocked` in manifest, continue with remaining sub-specs in the wave.

**Cascade blocking**: if sub-spec X is blocked, all sub-specs in later waves that depend on X (via DAG edges) are automatically marked `cascade-blocked` without attempting execution. This prevents wasted compute and misleading error reports. The Integrity Report includes a "Blocked / Undelivered" section listing all blocked and cascade-blocked sub-specs with their scope.

### Phase 5: QUALITY LOOP (max 3 rounds)

**Input**: Full changeset (all waves committed)
**Output**: Clean changeset or detailed report of remaining issues

For each round (1 to 3):

**5a. Assess** -- dispatch 3 agents in parallel:
- Agent(Verify) in `platform` mode -- runs all 7 scan modes on the changeset
- Agent(Guard) in `advise` mode -- governance check against decision-store
- Agent(Review) -- 8-agent parallel review on the full diff

**5b. Consolidate findings**:
- Collect all findings from verify + guard + review
- Map to unified severity scale:
  - Verify findings: use severity as-is (blocker, critical, high, medium, low)
  - Guard findings: `concern` → high, `warn` → medium, `info` → low
  - Review findings: use severity as-is (agents use the same scale)
- Cross-reference against implementation self-reports (Phase 4)
- Produce consolidated findings list

**Partial changeset handling**: if Phase 4 produced blocked sub-specs, Phase 5 verifies only the implemented subset. The Integrity Report notes which scope was not delivered.

**5c. Evaluate**:
- If 0 blockers + 0 criticals + 0 highs → PASS. Proceed to Phase 6.
- If round < 3 and issues remain → proceed to 5d (fix)
- If round = 3 and issues remain:
  - If blockers remain → STOP. Do NOT create PR. Report blockers and escalate to user.
  - If only criticals/highs remain → proceed to Phase 6 with issues documented in Integrity Report. PR is created but flagged.

**5d. Fix** -- for each blocker/critical/high finding:
- Dispatch Agent(Build) with: the finding, the affected file, the sub-spec context
- Build agent fixes the issue and updates the self-report
- Commit fixes: `spec-NNN: quality round R -- fix [category]`
- Return to 5a for next round

### Phase 6: DELIVER

**Input**: Implemented changeset (clean or with documented remaining issues)
**Output**: PR with transparency report

**6a. Transparency Report**:
1. Read all sub-spec `## Self-Report` sections (from implementation agents)
2. Read the quality loop's consolidated findings (from Phase 5 audit)
3. Produce `## Integrity Report`:
   ```markdown
   ## Integrity Report

   ### Summary
   - Real: N files/functions (fully implemented and verified)
   - Aspirational: N (implemented, not fully tested)
   - Stub: N (placeholder, needs completion)
   - Failing: N (implemented but failing checks)
   - Invented: N (not in spec, added by agents)
   - Hallucinated: N (referenced non-existent things -- fixed or flagged)

   ### Quality Convergence
   - Rounds: N/3
   - Final state: CLEAN | N remaining issues (severity breakdown)

   ### Details
   [Full table: file, function, classification, evidence, notes]
   ```

**6b. Deliver PR**:
1. Follow `/ai-pr` SKILL.md in full (steps 0-14)
2. PR body includes the Integrity Report as a dedicated section
3. PR body includes sub-spec completion table
4. Enable auto-complete with squash merge
5. Enter watch-and-fix loop (unless `--no-watch`)

### Resume Protocol

When invoked with `--resume`, the pipeline reads `specs/autopilot/manifest.md` and re-enters at the correct point:

1. Read manifest. Determine pipeline state from sub-spec statuses and phase markers.
2. **If all sub-specs are `planning`**: Phase 2 never completed. Re-enter at Phase 2.
3. **If DAG section is missing**: Phase 3 never completed. Re-enter at Phase 3.
4. **If some waves are `implemented` and others are not**: Re-enter Phase 4 at the first incomplete wave. Skip completed waves.
5. **If all waves are `implemented` but no quality rounds recorded**: Re-enter at Phase 5.
6. **If quality rounds exist but pipeline stopped (blockers after round 3)**: Re-enter at Phase 5 for another attempt (resets round counter).
7. **If quality passed but PR not created**: Re-enter at Phase 6.

Resume never re-executes completed phases. Manifest is the single source of truth for resume decisions.

**6c. Cleanup**:
1. Delete `specs/autopilot/` directory
2. Clear `specs/spec.md` and `specs/plan.md` with placeholders
3. Add to `specs/_history.md`
4. Verify cleanup (lesson from spec-056: re-read files after clearing)
5. Commit: `chore: clear autopilot state after spec-NNN delivery`

## Acceptance Criteria

### Pipeline
- [ ] AC1: `/ai-autopilot` with an approved spec executes all 6 phases without requiring user approval between phases
- [ ] AC2: Phase 2 dispatches N agents in parallel (one per sub-spec), not sequentially
- [ ] AC3: Phase 3 produces a valid acyclic DAG with wave assignments
- [ ] AC4: Phase 4 executes waves in order -- parallel within wave, serial between waves
- [ ] AC5: Phase 5 runs verify + guard + review in parallel, iterates up to 3 rounds

### Quality Convergence
- [ ] AC6: Quality loop exits on round where 0 blockers + 0 criticals + 0 highs
- [ ] AC7: Quality loop stops after 3 rounds and reports remaining issues (does not halt silently). After 3 rounds: blockers prevent PR creation; remaining criticals/highs are documented in the Integrity Report and the PR is created but flagged
- [ ] AC8: Fix agents in Phase 5 produce new commits (not amends) with descriptive messages

### Transparency
- [ ] AC9: Every implementation agent writes a `## Self-Report` section with per-file classifications
- [ ] AC10: Phase 5 audit cross-references self-reports against verify/review evidence
- [ ] AC11: PR body contains `## Integrity Report` with the 6-category classification summary
- [ ] AC12: Stubs, inventions, and hallucinations are explicitly listed -- nothing is hidden

### Orchestration
- [ ] AC13: Phase 3 detects file overlaps between sub-specs and serializes conflicting sub-specs
- [ ] AC14: Phase 3 detects import chains via declared `exports:`/`imports:` in sub-spec plans and orders accordingly
- [ ] AC15: Sub-specs with zero overlaps and zero import chains are assigned to the same wave (parallel)
- [ ] AC16: Phase 3 merges sub-specs with unresolvable file conflicts into a single sub-spec and logs the merge
- [ ] AC17: Phase 5 consolidation maps guard advisory severities (concern/warn/info) to the unified severity scale (high/medium/low)
- [ ] AC18: Phase 1 aborts with recommendation for `/ai-dispatch` if spec decomposes into fewer than 3 concerns

### State Management
- [ ] AC19: Manifest.md is the single source of truth for sub-spec status (no `status:` in sub-spec frontmatter)
- [ ] AC20: Exploration findings are embedded in sub-spec files (no separate exploration.md)
- [ ] AC21: Plan is embedded in sub-spec files (no separate sub-NNN-plan.md files)

### Governance
- [ ] AC22: No approval required between phases (DEC-023: invocation is approval)
- [ ] AC23: If quality loop exhausts 3 rounds with blockers remaining, pipeline stops (does not create a PR with known blockers)
- [ ] AC24: Spec cleanup (clear spec.md, plan.md, add to _history.md) is verified post-execution

### Recovery
- [ ] AC25: `--resume` reads manifest, identifies last completed phase/wave, re-enters pipeline at the correct point (see Resume Protocol)
- [ ] AC26: Blocked sub-specs (build failure) do not prevent other sub-specs in the same wave from completing

### Failure Handling
- [ ] AC27: If a Phase 2 deep-plan agent fails after 1 retry, sub-spec is marked `plan-failed` in manifest
- [ ] AC28: If Phase 4 produces blocked sub-specs, the Integrity Report includes a "Blocked / Undelivered" section
- [ ] AC29: Blocked sub-specs in Wave N cascade-block dependent sub-specs in later waves without attempting execution

### Compatibility
- [ ] AC30: `/ai-autopilot` continues to consume `/ai-verify`, `/ai-review`, `/ai-commit`, `/ai-pr` skills and `Agent(Guard)` advisory as-is (no changes to those skills or agent)
- [ ] AC31: Telemetry events from v1 are preserved (autopilot.started, .subspec_complete, .done, etc.)
- [ ] AC32: IDE mirrors (Copilot, Codex/Gemini) updated to reflect v2
- [ ] AC33: New telemetry events emitted for v2-specific phases: `autopilot.decompose_complete`, `autopilot.deep_plan_complete`, `autopilot.dag_built`, `autopilot.quality_round`

## Assumptions

- ASSUMPTION: Agent(Build) dispatched in parallel within a wave will not conflict if Phase 3 correctly assigns file-disjoint sub-specs to the same wave
- ASSUMPTION: The verify `platform` mode covers all quality dimensions needed for the convergence loop (lint, types, tests, security, governance)
- ASSUMPTION: 3 rounds of quality fixes is sufficient for convergence in typical specs (5-10 sub-specs, 20-50 files)
- ASSUMPTION: DEC-023's "2-retry limit" applies to phase-level failures (e.g., Phase 2 agent crash). Phase 5 quality rounds (max 3) are a different mechanism -- iterative fix cycles on the assembled changeset, not failure retries

## Risks

| Risk | Mitigation |
|------|-----------|
| N parallel deep-plan agents consume significant compute | Phase 1 decompose is lightweight and fast. Phase 2 agents are time-boxed. For specs with >10 sub-specs, consider batching into groups of 5. |
| DAG construction in Phase 3 misses a dependency | Phase 5 quality loop catches integration failures. Fix agents can resolve in subsequent rounds. |
| Self-report dishonesty (agent claims "real" for a stub) | Independent audit in Phase 5 cross-references self-reports against verify evidence. Discrepancies are flagged. |
| Quality loop does not converge in 3 rounds | After 3 rounds, remaining issues are reported in the Integrity Report. The PR is NOT created if blockers remain (AC20). |
| Parallel build agents in Phase 4 write to shared state files (.ai-engineering/) | Sub-spec file boundaries enforced per build agent prompt. Manifest updates are orchestrator-only (not delegated to build agents). |
| PR body too large with full Integrity Report | Summary section with counts at top. Details collapsible or linked to sub-spec files. |

## Breaking Changes

- **plan.md no longer required**: v1 required both `spec.md` and `plan.md` before invocation. v2 requires only an approved `spec.md`. Existing `plan.md` files are ignored -- Phase 2 agents generate their own plans. Users who run `/ai-plan` before `/ai-autopilot` will find their plan unused.
- **Sub-spec file schema changed**: v2 sub-specs have no `status:` frontmatter, and include `## Exploration`, `## Plan`, and `## Self-Report` sections. v1 sub-specs with `status:` frontmatter are not compatible.
- **exploration.md removed**: v1 defined a separate `exploration.md` file. v2 embeds exploration in each sub-spec. The file is no longer created.
- **Handler files renamed**: all 5 v1 handlers are deleted and replaced with 6 new handlers. Any external references to v1 handler filenames will break.

## Dependencies

- DEC-023 (invocation-as-approval) is the governance foundation -- no changes needed
- `/ai-verify` platform mode must work as documented (7-mode aggregation)
- `/ai-review` 8-agent dispatch must work as documented
- `/ai-pr` step 8 spec operations (sub-steps 5-8: add to _history.md, clear spec.md, clear plan.md, stage) must execute correctly (known failure mode per lessons.md)
- Agent(Build), Agent(Verify), Agent(Guard), Agent(Review), Agent(Explore) must be dispatchable as subagent_type in the Agent tool

## Files Changed

| Action | Path | Notes |
|--------|------|-------|
| rewrite | `.claude/skills/ai-autopilot/SKILL.md` | Clean-sheet, 6-phase pipeline |
| delete | `.claude/skills/ai-autopilot/handlers/phase-split.md` | Replaced by phase-decompose.md |
| delete | `.claude/skills/ai-autopilot/handlers/phase-explore.md` | Merged into phase-deep-plan.md |
| delete | `.claude/skills/ai-autopilot/handlers/phase-execute.md` | Replaced by phase-implement.md |
| delete | `.claude/skills/ai-autopilot/handlers/phase-verify.md` | Replaced by phase-quality.md |
| delete | `.claude/skills/ai-autopilot/handlers/phase-pr.md` | Replaced by phase-deliver.md |
| create | `.claude/skills/ai-autopilot/handlers/phase-decompose.md` | Phase 1 handler |
| create | `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md` | Phase 2 handler |
| create | `.claude/skills/ai-autopilot/handlers/phase-orchestrate.md` | Phase 3 handler (new) |
| create | `.claude/skills/ai-autopilot/handlers/phase-implement.md` | Phase 4 handler |
| create | `.claude/skills/ai-autopilot/handlers/phase-quality.md` | Phase 5 handler (new) |
| create | `.claude/skills/ai-autopilot/handlers/phase-deliver.md` | Phase 6 handler |
| rewrite | `.claude/agents/ai-autopilot.md` | Updated pipeline, capabilities, dispatch table |
| update | `.github/prompts/ai-autopilot.prompt.md` | Copilot mirror |
| update | `.agents/skills/ai-autopilot/SKILL.md` | Codex/Gemini mirror |
