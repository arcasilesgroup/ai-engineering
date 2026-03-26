# Handler: Phase 3 -- ORCHESTRATE

## Purpose

Analyze all N enriched sub-spec plans together, detect file overlaps and import dependencies, construct an execution DAG with wave assignments, and resolve conflicts. This phase prevents merge conflicts during Phase 4 and ensures correct execution ordering. It is read-only analysis on sub-spec files -- no code changes, no builds.

## Prerequisites

Phase 2 (Deep Plan) complete. All non-failed sub-specs have enriched `## Exploration` sections (in `sub-NNN/spec.md`) and `## Plan` sections (in `sub-NNN/plan.md`). Each plan declares `exports:` and `imports:` lists -- Phase 3 uses these structured declarations for DAG construction, not code analysis.

Required state:
- `specs/autopilot/manifest.md` exists with sub-spec list and statuses
- Non-failed sub-specs (`planning` or `planned`) have non-empty `## Plan` sections in their `sub-NNN/plan.md`
- Sub-specs marked `plan-failed` are excluded from DAG construction

## Procedure

### Step 1 -- Extract Declarations

Read all non-failed sub-spec directories from `specs/autopilot/sub-*/`. For each sub-spec, extract:

1. **files**: the `files:` list from `sub-NNN/spec.md` frontmatter (refined by Phase 2)
2. **exports**: the `exports:` declarations from `sub-NNN/plan.md` `## Plan` section (modules, classes, or functions this sub-spec creates)
3. **imports**: the `imports:` declarations from `sub-NNN/plan.md` `## Plan` section (modules, classes, or functions this sub-spec expects from other sub-specs)

Build a lookup table:

```
sub-001: files=[a.py, b.py], exports=[ModuleA, func_x], imports=[]
sub-002: files=[c.py, d.py], exports=[ServiceB],        imports=[ModuleA]
sub-003: files=[e.py],       exports=[HelperC],          imports=[]
```

**Missing declarations**: if a sub-spec lacks `exports:` or `imports:` declarations, treat it as having no cross-sub-spec dependencies (isolated). Log a warning:

```
WARNING: sub-NNN missing exports/imports declarations -- treated as isolated.
```

### Step 2 -- Build File-Overlap Matrix

For each pair of sub-specs (i, j) where i < j, check if they share any file paths. A file path is shared when both sub-specs list it in their `files:` frontmatter (create or modify the same path).

Record overlaps as undirected edges:

```
File Overlaps:
  sub-001 <-> sub-004  (shared: src/installer/service.py)
  sub-002 <-> sub-005  (shared: src/installer/merge.py, src/installer/phases/__init__.py)
```

Sub-spec pairs with zero shared files have no file-overlap edge.

### Step 3 -- Build Import-Chain Graph

Using declared `exports:` and `imports:`, check if sub-spec A exports a symbol that sub-spec B imports. This uses the structured declarations from Phase 2 -- it does NOT parse or analyze source code.

Record import dependencies as directed edges (A -> B means B depends on A, so A must complete before B):

```
Import Chains:
  sub-001 -> sub-002  (sub-002 imports ModuleA from sub-001)
  sub-001 -> sub-005  (sub-005 imports func_x from sub-001)
```

If sub-spec B imports a symbol not exported by any sub-spec, it is an external dependency (outside autopilot scope). Ignore it -- no edge created.

### Step 4 -- Construct DAG

Combine file-overlap edges and import-chain edges into a single dependency graph. Apply topological sort to assign wave numbers:

**Rules**:
- Sub-specs with zero file overlaps AND zero import chains with each other can be assigned to the same wave (parallel execution is safe).
- Sub-specs with a file overlap or import dependency must be serialized (the dependent waits for the dependency to complete).
- For file overlaps (undirected), serialize by sub-spec number (lower number goes first).
- For import chains (directed), the exporter executes before the importer.

**Wave assignment via topological sort**:
- Wave 1: sub-specs with zero incoming edges (no dependencies on other sub-specs)
- Wave 2: sub-specs whose dependencies are all in Wave 1
- Wave 3: sub-specs whose dependencies are all in Wave 1 or Wave 2
- Continue until all sub-specs are assigned.

### Step 5 -- Handle Unresolvable Conflicts

A conflict is unresolvable when two sub-specs must modify the same function within the same file -- not just the same file, but the same logical unit. Ordering alone cannot prevent a merge conflict at the function level.

**Resolution**: merge the conflicting sub-specs into a single sub-spec.

1. Create a new sub-spec that combines the scopes, plans, and file lists of both
2. Preserve the lower sub-spec number (e.g., merge sub-003 into sub-001 -> result is sub-001)
3. Remove the higher-numbered sub-spec from the manifest
4. Update the merged sub-spec's `spec.md` (combined Scope, Exploration, files frontmatter) and `plan.md` (combined Plan, exports/imports)
5. Re-check the DAG edges for the merged sub-spec (it inherits all edges of both originals)
6. Log the merge with rationale:

```
MERGE: sub-003 merged into sub-001
Reason: both modify detect_phase() in src/installer/phases/detect.py
Combined work units: 7
```

If a merge produces a sub-spec with more than 7 work units, consider splitting differently: extract the conflicting function into its own sub-spec, or reorder tasks so the conflict is localized. Max 2 attempts at resolution before escalating to the orchestrator.

### Step 6 -- Write DAG to Manifest

Append the `## Execution DAG` section to `specs/autopilot/manifest.md`:

```markdown
## Execution DAG

Wave 1 (parallel): sub-001, sub-003, sub-005
Wave 2 (parallel, after Wave 1): sub-002, sub-004
Wave 3 (serial, after Wave 2): sub-006

### Dependency Edges
- sub-001 -> sub-002 (imports: ModuleA)
- sub-001 -> sub-004 (file overlap: service.py)
- sub-003 -> sub-006 (imports: HelperC)
```

Wave labels:
- `(parallel)` when the wave contains 2+ sub-specs
- `(serial, after Wave N)` when the wave contains exactly 1 sub-spec
- `(parallel, after Wave N)` when the wave contains 2+ sub-specs and follows another wave

### Step 7 -- Validate DAG

Run two validation checks:

1. **Acyclicity**: verify the DAG has no cycles. A cycle means A depends on B and B depends on A (directly or transitively). If a cycle is detected, see Failure Modes below.

2. **Complete coverage**: every non-failed sub-spec must have a wave assignment. If any sub-spec is unassigned, it was missed during graph construction -- reassign it. Sub-specs with no edges default to Wave 1.

## Output

Artifacts written:
- Updated `specs/autopilot/manifest.md` with `## Execution DAG` section
- Updated sub-spec `spec.md` and `plan.md` files (only if merges occurred in Step 5)

Report to orchestrator:

```
ORCHESTRATE COMPLETE
- Sub-specs analyzed: N (M excluded as plan-failed)
- File overlaps detected: X pairs
- Import chains detected: Y edges
- Merges performed: Z (details: ...)
- DAG waves: W
- Wave distribution: Wave 1 = A sub-specs, Wave 2 = B sub-specs, ...
- Fully serial: yes/no
- Ready for Phase 4: IMPLEMENT
```

## Failure Modes

| Condition | Action |
|-----------|--------|
| Cyclic dependency detected | Attempt to break by merging the cycle participants into one sub-spec. If the merged sub-spec exceeds 7 work units, split differently and rebuild the DAG. Max 2 attempts. If unresolved, escalate to user with the cycle graph. |
| Sub-spec missing `exports:`/`imports:` declarations | Treat as isolated (no cross-sub-spec dependencies). Log warning. Do not block. |
| All sub-specs must be serial (fully serial DAG) | Proceed normally. This is an expected DAG shape for tightly coupled specs, not a failure. Phase 2 deep-plan work is still valuable even without parallelism. |
| Merge produces sub-spec with >7 work units | Attempt to split the conflicting function into its own sub-spec (max 2 attempts). If still >7, proceed with the large sub-spec and note it in the report. |
| No sub-specs remain after excluding `plan-failed` | STOP. Report: "All sub-specs failed planning. Pipeline cannot continue." Escalate to user. |
| File overlap between 3+ sub-specs on the same path | Merge all sub-specs that share that file into one. Apply the same merge protocol as Step 5. |
