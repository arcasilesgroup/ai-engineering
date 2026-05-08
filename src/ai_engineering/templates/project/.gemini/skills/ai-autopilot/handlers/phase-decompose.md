# Handler: Phase 1 -- DECOMPOSE

## Purpose

Take an approved spec and decompose it into N independent concerns, each becoming a sub-spec shell. Fast and shallow -- produces the skeleton that Phase 2 (Deep Plan) enriches. This phase is read-only analysis: no code changes, no builds, no tests.

## Inputs

| Source | What to extract |
|--------|----------------|
| `.ai-engineering/specs/spec.md` | Full approved spec -- requirements, scope, constraints, acceptance criteria |
| `state/state.db.decisions` | Architectural decisions and constraints that bound decomposition |

## Procedure

### Step 1 -- Extract Concerns

Read the spec end-to-end. Identify N independent concerns. A concern is a coherent unit of work: a module, a feature area, a configuration surface, or a data domain.

Heuristics for concern boundaries:
- Different files or directories touched
- Different runtime behavior (CLI vs library vs config)
- Independent testability (can be verified without other concerns)
- Separate domain concepts (auth vs storage vs UI)

Each concern gets a short title (3-6 words) and a 2-3 sentence scope statement extracted from the parent spec.

### Step 2 -- Minimum Concern Guard

If N < 3: **ABORT**. Report to orchestrator:

```
DECOMPOSE ABORTED: Spec has N concerns -- below autopilot threshold (3).
Recommendation: Use /ai-build for direct execution.
```

This is a hard gate. Do not proceed. Do not attempt to split concerns further to meet the threshold -- that produces artificial granularity.

### Step 3 -- Write Sub-Spec Shells

For each concern, create a directory `.ai-engineering/runtime/autopilot/sub-NNN/` containing two files:

**`.ai-engineering/runtime/autopilot/sub-NNN/spec.md`** (Shell Schema):

```markdown
---
id: sub-NNN
parent: spec-XXX
title: "Concern title"
status: planning
files: []
depends_on: []
---

# Sub-Spec NNN: [title]

## Scope
[2-3 sentences from parent spec describing this concern]

## Exploration
[EMPTY -- populated by Phase 2]
```

**`.ai-engineering/runtime/autopilot/sub-NNN/plan.md`**:

```markdown
---
total: 0
completed: 0
---

# Plan: sub-NNN [title]

## Plan
[EMPTY -- populated by Phase 2]

## Self-Report
[EMPTY -- populated by Phase 4]
```

Rules:
- Number sub-spec directories sequentially: `sub-001/`, `sub-002/`, ..., `sub-NNN/`
- The `parent`, `files`, and `depends_on` fields live in `spec.md` frontmatter. The `files` field is a best guess based on spec mentions and project conventions. Phase 2 agents refine it after codebase exploration.
- The `plan.md` frontmatter tracks `total` and `completed` task counts (both start at 0, updated by later phases).
- The `parent` field references the spec ID (e.g., `spec-065`)
- Scope text must trace back to specific sections of the parent spec. Do not invent requirements.

### Step 4 -- Write Manifest

Write `.ai-engineering/runtime/autopilot/manifest.md` with the full sub-spec list. All statuses start as `planning`.

Format:

```markdown
# Autopilot Manifest: spec-XXX

## Split Strategy
[1 sentence: by-domain, by-layer, by-feature, by-dependency, or hybrid -- explain the rationale]

## Sub-Specs

| # | Title | Status | Depends On | Files (best guess) |
|---|-------|--------|------------|---------------------|
| sub-001/ | [title] | planning | None | `path/a`, `path/b` |
| sub-002/ | [title] | planning | None | `path/c` |
| sub-003/ | [title] | planning | sub-001 | `path/d`, `path/e` |

## Totals
- Sub-specs: N
- Dependency chain depth: M
```

Dependency rules:
- Default to `None` (independent) unless there is an obvious data or API dependency between concerns
- Keep the dependency graph as shallow as possible -- deep chains reduce parallelism in Phase 4
- Dependencies are refined in Phase 3 (Orchestrate) after full plan analysis

### Step 5 -- Validate Coverage

Walk every section and requirement of the parent spec. Confirm each maps to at least one sub-spec's `spec.md` scope. Build a traceability check:

```
Spec Section -> Sub-Spec(s)
------------------------------
Section A    -> sub-001, sub-003
Section B    -> sub-002
Section C    -> sub-004
...
```

**Orphan detection**: if any spec section or requirement does not map to a sub-spec, reassign it to the most relevant existing sub-spec. Update that sub-spec's `spec.md` Scope and `files` field.

If orphans remain after 2 reassignment attempts: **STOP**. Report the orphan requirements to the orchestrator for human review.

## Output

Artifacts written:
- N sub-spec directories at `.ai-engineering/runtime/autopilot/sub-001/` through `.ai-engineering/runtime/autopilot/sub-NNN/` (each containing `spec.md` and `plan.md`)
- Execution manifest at `.ai-engineering/runtime/autopilot/manifest.md`

Report to orchestrator:
```
DECOMPOSE COMPLETE
- Concerns identified: N
- Split strategy: [strategy]
- Coverage validation: PASSED (all spec sections mapped)
- Dependency depth: M
- Ready for Phase 2: DEEP PLAN
```

## Failure Modes

| Condition | Action |
|-----------|--------|
| Spec is placeholder or draft (no real requirements) | STOP. Report: "No approved spec. Run `/ai-brainstorm` first." |
| < 3 concerns extracted | ABORT. Report concern count and recommend `/ai-build`. |
| Orphan requirements after 2 reassignment attempts | STOP. Report orphan list with spec section references for human review. |
| Spec references external systems not in the repo | Flag as constraint in manifest. Do not block -- Phase 2 agents will assess feasibility. |
| Ambiguous scope boundaries between concerns | Prefer larger concerns over artificial splits. Note the ambiguity in the manifest for Phase 3 resolution. |
