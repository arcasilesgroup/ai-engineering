# Handler: Phase 2 -- DEEP PLAN

## Purpose

Dispatch N parallel agents (one per sub-spec) to deep-explore the codebase and write detailed, implementation-ready plans. Each agent enriches its sub-spec with architectural context, ordered tasks, and exports/imports declarations. This is where plan quality is built -- implementation quality depends on it.

## Prerequisites

- Phase 1 (DECOMPOSE) is complete.
- Sub-spec directories exist at `specs/autopilot/sub-NNN/` with `spec.md` (Scope + `files:` frontmatter) and `plan.md` (Plan placeholder).
- Manifest exists at `specs/autopilot/manifest.md` with all sub-spec statuses set to `planning`.
- Parent spec is available at `specs/spec.md`.
- Decision store is loaded from `state/decision-store.json`.

## Procedure

### Step 1: Load Sub-Specs

1. Glob `specs/autopilot/sub-*/spec.md`. Collect the full list of sub-spec directories.
2. For each `sub-NNN/spec.md`, extract:
   - `id` from frontmatter (e.g., `sub-001`)
   - `title` from frontmatter
   - `files:` list from frontmatter (Phase 1 best-guess file list)
   - `## Scope` section content
3. Verify all sub-specs are in `planning` status in the manifest. Skip any that are not.
4. Build a dispatch list: one entry per sub-spec with its content and metadata.

### Step 2: Dispatch Agent(Explore+Plan) Per Sub-Spec

Dispatch all agents in parallel using `run_in_background: true`. Each agent receives a self-contained prompt with:

- The full sub-spec content (frontmatter + scope)
- The parent spec's relevant section for this concern
- Decision-store constraints that apply to this sub-spec's scope
- Stack contexts from `contexts/languages/` and `contexts/frameworks/`

Each agent executes the following five-step procedure:

#### 2a. Deep Explore

Read every file mentioned in the sub-spec's `files:` frontmatter. For each file:

- Summarize current state: key exports, public API surface, line count.
- Map imports: what does this file import, and who imports it.
- Map callers: trace usages from other modules.
- Identify test fixtures that cover this file.

Then read analogous implementations in the codebase -- files that solve a similar problem or follow the pattern this sub-spec should replicate.

#### 2b. Write Exploration Section

Populate `## Exploration` in `sub-NNN/spec.md` with the following required subsections:

```markdown
## Exploration

### Existing Files
[For each file in scope: path, summary of current state, key exports, line count.
If file does not exist yet, note "NEW FILE" with the module it belongs to.]

### Patterns to Follow
[Identify the exemplar file in the codebase that this sub-spec should replicate.
State what pattern to follow and why. Include file path and key structural elements.]

### Dependencies Map
[Import chains relevant to this sub-spec. What this code imports, what imports it.
External dependencies. Shared utilities.]

### Risks
[Discovered constraints, edge cases, or unknowns. Breaking changes to existing callers.
Assumptions that need validation. Missing test coverage.]
```

"Existing Files" and "Patterns to Follow" are mandatory. "Dependencies Map" and "Risks" are mandatory but may be brief if the sub-spec is self-contained.

#### 2c. Write Plan Section

Populate `## Plan` in `sub-NNN/plan.md` with ordered tasks using simplified checkbox format:

```markdown
## Plan

exports: [list of modules/classes/functions this sub-spec creates or exposes]
imports: [list of modules/classes/functions this sub-spec expects from other sub-specs]

- [ ] T-N.1: [Task title]
  - **Files**: [list of file paths]
  - **Done**: [verifiable condition]
- [ ] T-N.2: [Task title]
  - **Files**: [list of file paths]
  - **Done**: [verifiable condition]
```

Requirements for the plan:
- Minimum 2 tasks per sub-spec. No upper limit.
- Every task MUST have explicit file paths and a verifiable done condition.
- TDD pairs: where tests are needed, the test task precedes the implementation task.
- `exports:` declares modules, classes, or functions this sub-spec creates that other sub-specs may consume. Phase 3 uses these for DAG construction.
- `imports:` declares what this sub-spec expects from other sub-specs. Can be empty (`imports: []`) if there are no cross-sub-spec dependencies.
- Task IDs use the pattern `T-N.K` where N is the sub-spec number and K is the task sequence (e.g., T-3.1, T-3.2 for sub-003).

#### 2d. Refine File List

Update `sub-NNN/spec.md` frontmatter `files:` field with the actual files discovered during exploration. This replaces Phase 1's best-guess list with a verified, complete list. Add files that were discovered during exploration but not in the original list. Remove files that turned out to be irrelevant.

#### 2e. Self-Assess

Append a brief assessment to `sub-NNN/plan.md` (after Plan, before Self-Report placeholder):

```markdown
### Confidence
- **Level**: high | medium | low
- **Assumptions**: [List any assumptions made during exploration]
- **Unknowns**: [List anything that could not be determined from the codebase]
```

Confidence criteria:
- **high**: all files read, patterns clear, no ambiguity in scope, done conditions are objective.
- **medium**: most files read, some assumptions about behavior or API contracts, minor unknowns.
- **low**: key files missing or inaccessible, significant assumptions, scope may need revision.

### Step 3: Collect Results

Wait for all dispatched agents to complete. For each agent:

1. Verify the sub-spec file was written (non-empty).
2. Read the enriched sub-spec content.
3. Record the outcome: success, timeout, crash, or empty output.

### Step 4: Validate Gate Criteria

For each sub-spec that completed successfully, validate the gate (see Gate section below). Track pass/fail per sub-spec.

If a sub-spec fails gate validation despite the agent completing (e.g., missing required subsections, fewer than 2 tasks, no exports/imports declaration), treat it as a failed agent and proceed to failure handling.

### Step 5: Update Manifest

For each sub-spec:

- If gate passed: update status in manifest to `planned`.
- If gate failed or agent failed: follow Failure Modes procedure. After retries, mark surviving failures as `plan-failed`.

Write a summary line to the manifest:

```markdown
## Deep Plan Summary
- Planned: N of M sub-specs
- Failed: K sub-specs [list IDs]
- Confidence distribution: X high, Y medium, Z low
```

## Output

- N enriched sub-spec directories at `specs/autopilot/sub-NNN/`:
  - `spec.md` containing populated `## Exploration` and updated `files:` frontmatter reflecting actual discovered files.
  - `plan.md` containing `## Plan` with checkbox-formatted tasks, `exports:`/`imports:` declarations, and confidence assessment.
- Updated manifest with `planned` or `plan-failed` statuses.
- Summary report: N planned, M failed, confidence distribution.

## Gate

All of the following must pass for each sub-spec to be marked `planned`:

1. **Exploration completeness**: `sub-NNN/spec.md` contains `## Exploration` that is non-empty and includes at least the "Existing Files" and "Patterns to Follow" subsections with substantive content (not placeholders or TODOs).
2. **Plan minimum tasks**: `sub-NNN/plan.md` contains at least 2 checkbox items matching `- [ ] T-N.K`, each with explicit `**Files**:` paths and a `**Done**:` condition.
3. **Dependency declarations**: `sub-NNN/plan.md` declares both `exports:` and `imports:` in the Plan section. Either can be an empty list (`[]`) if there are no cross-sub-spec dependencies, but the declaration must be present.

## Failure Modes

### Single Agent Failure (timeout, crash, empty output, gate fail)

1. **First attempt fails**: retry once with a narrower prompt. The retry prompt:
   - Reduces scope to the sub-spec's `## Scope` section only (drops parent spec context).
   - Explicitly names the missing sections: "You must produce ## Exploration with 'Existing Files' and 'Patterns to Follow' subsections, and ## Plan with at least 2 tasks containing file paths and done conditions."
   - Keeps `files:` frontmatter and decision-store constraints.
2. **Second attempt fails**: mark the sub-spec as `plan-failed` in manifest. Do not retry again.

### All Agents Fail

If every sub-spec is `plan-failed` after retries: **halt the pipeline**. Report:

```
HALT: Deep planning failed for all sub-specs.
None of the N agents produced a valid plan.
Pipeline cannot proceed to Phase 3 (Orchestrate).
Review the parent spec for clarity and scope issues.
```

### Partial Failure (some succeed, some fail)

The orchestrator evaluates the failed sub-specs against the parent spec:

1. Read the parent spec's requirements.
2. For each `plan-failed` sub-spec, determine if its scope covers critical or optional requirements.
3. **If failed sub-specs cover critical parent spec requirements**: halt the pipeline. Report which critical scope is unplannable and why.
4. **If failed sub-specs cover only optional or low-priority scope**: proceed to Phase 3 with the successful subset. Report the gap:

```
PARTIAL: N of M sub-specs planned successfully.
Proceeding without: [list of plan-failed sub-spec IDs and titles].
Gap: [description of scope not covered].
```

### Criticality Assessment Criteria

A sub-spec is **critical** if any of the following apply:
- It implements a requirement marked as mandatory or blocking in the parent spec.
- Other sub-specs declare an `imports:` dependency on modules it would `exports:`.
- Its scope covers the primary deliverable of the parent spec.

A sub-spec is **optional** if:
- It covers ancillary concerns (tests-only, docs-only, CI config, mirror updates).
- No other sub-spec depends on its exports.
- The parent spec can be considered partially delivered without it.
