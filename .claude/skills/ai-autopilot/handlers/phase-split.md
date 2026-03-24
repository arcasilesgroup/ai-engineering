# Handler: Split + Explore

## Purpose

Take a large approved spec and decompose it into N focused sub-specs (max 3-5 tasks each), then enrich each with deep codebase exploration. Every sub-spec must be independently implementable by a fresh-context agent that reads only the sub-spec file and the referenced source files.

## Inputs

- `specs/spec.md` -- the approved parent spec
- `specs/plan.md` -- the task breakdown (if exists)
- `state/decision-store.json` -- active constraints

## Procedure

### Step 1 -- Analyze the Spec

Read `specs/spec.md` end-to-end. Extract:

1. **Work units**: every discrete implementation item (a file to create, a file to modify, a config entry to add, a test to write). Number them sequentially: W-001, W-002, ...
2. **Dependency edges**: for each work unit, note which other work units it reads from, writes to, or imports. Record as `W-003 -> W-007` (003 must complete before 007).
3. **File manifest**: for each work unit, list every file it will create or modify. One work unit may touch multiple files; one file must belong to exactly one work unit.

If `specs/plan.md` exists and has checkable items, cross-reference. Every plan item must map to at least one work unit. Flag orphans.

### Step 2 -- Determine Split Strategy

Evaluate three grouping strategies against the work units:

| Strategy | Rule | Best when |
|----------|------|-----------|
| **By domain** | Group by functional area (contexts, skills, handlers, config, tests) | Spec spans multiple system layers |
| **By dependency** | Group items that form a dependency chain together | Spec has deep sequential dependencies |
| **By file scope** | Group items that touch the same files or directories | Spec modifies many files with clear ownership boundaries |

Choose the strategy that minimizes cross-sub-spec file conflicts. If two strategies tie, prefer by-dependency -- it produces the most predictable execution order.

Document the choice and reasoning in one line:
```
Split strategy: [by-domain|by-dependency|by-file-scope] -- [one sentence why]
```

### Step 3 -- Form Groups

Apply the chosen strategy. Assign each work unit to exactly one group.

**Hard constraints:**
- Each group has 3-5 work units (split large groups, merge small ones)
- No file appears in more than one group
- Dependency edges between groups flow in one direction (no cycles)
- Groups are numbered in execution order: group 1 has no dependencies on later groups

**Soft preferences:**
- Keep related tests in the same group as their implementation
- Keep config/registry updates in the group that creates the thing being registered
- If a file is read by multiple groups but written by one, assign it to the writer

### Step 4 -- Generate Sub-Specs

Create `specs/autopilot/` directory. For each group, write `specs/autopilot/sub-NNN.md`:

```markdown
---
id: sub-NNN
parent: spec-XXX
title: "Sub-spec title"
status: pending
files:
  - path/to/file-1.ext
  - path/to/file-2.ext
depends_on: []
---

# Sub-Spec NNN: [title]

## Scope

[2-3 sentences: what this sub-spec implements from the parent spec. Reference parent spec sections by name.]

## Work Units

- W-XXX: [description]
- W-YYY: [description]

## Files

| Action | Path | Notes |
|--------|------|-------|
| create | path/to/new-file.ext | [what it contains] |
| modify | path/to/existing.ext | [what changes] |

## Acceptance Criteria

- [ ] [Testable criterion -- one per work unit minimum]
- [ ] [Additional criteria from parent spec that apply to this sub-spec]

## Dependencies

[Which sub-specs must complete before this one, or "None -- first in sequence."]

## Architectural Context

[Populated by Step 5. Left blank during generation.]
```

Number sub-specs with zero-padded three-digit IDs: sub-001, sub-002, ... sub-NNN.

### Step 5 -- Deep Explore

For each sub-spec, dispatch an Agent(Explore) in parallel. Each explorer receives:

**Prompt**: "Read sub-spec `specs/autopilot/sub-NNN.md`. For every file listed in the Files table:"

1. **If the file exists**: read it. Summarize its current structure (exports, classes, key functions). Note the patterns it follows (naming conventions, import style, error handling).
2. **If the file will be created**: find the closest existing analog in the codebase. Read it. Document the pattern to replicate.
3. **Map dependencies**: for each file, find who imports it (`Grep` for the module name) and what it imports. List direct dependents.
4. **Identify patterns**: read one existing file of the same type (e.g., if creating a handler, read an existing handler). Extract the template: frontmatter schema, section order, tone, line count range.
5. **Check for conflicts**: verify no other sub-spec lists the same files. If conflict found, report it -- do not resolve.

Each explorer appends its findings to the sub-spec's `## Architectural Context` section:

```markdown
## Architectural Context

### Existing Files
- `path/to/file.ext`: [summary of current state, key exports, line count]

### Patterns to Follow
- [Pattern name]: [file that exemplifies it] -- [what to replicate]

### Dependencies Map
- `module.name` imported by: [list of importers]
- `module.name` imports: [list of dependencies]

### Risks
- [Any discovered constraint or conflict]
```

### Step 6 -- Validate

Run these checks. All must pass before proceeding.

1. **Existence**: every `specs/autopilot/sub-NNN.md` file exists and has >30 lines
2. **Coverage**: every work unit (W-XXX) from Step 1 appears in exactly one sub-spec
3. **No overlap**: no file path appears in the Files table of more than one sub-spec
4. **Valid DAG**: sub-spec dependency order contains no cycles (if sub-002 depends on sub-001, sub-001 must not depend on sub-002 or any successor of sub-002)
5. **Enriched**: every sub-spec has a non-empty `## Architectural Context` section

If any check fails:
- Overlap or coverage gap: reassign the conflicting work unit and regenerate affected sub-specs
- Cycle: reorder groups to break the cycle
- Missing context: re-run the explorer for that sub-spec
- Max 2 fix attempts. If still failing after 2: STOP and report the validation failures to the orchestrator

## Output

```
specs/autopilot/sub-001.md
specs/autopilot/sub-002.md
...
specs/autopilot/sub-NNN.md
```

Report to orchestrator:
```
Split complete.
- Strategy: [chosen strategy]
- Sub-specs: N
- Work units: M (distributed across N sub-specs)
- Estimated complexity: [low|medium|high] per sub-spec
- Dependency chain depth: D (longest path through the DAG)
- Validation: all 5 checks passed
```

## Anti-Patterns

- Generating sub-specs without reading the parent spec first (always start from spec.md)
- Splitting too fine (1-2 work units per sub-spec creates overhead without value)
- Splitting too coarse (6+ work units defeats the purpose of splitting)
- Assigning the same file to multiple sub-specs (guaranteed merge conflicts)
- Skipping the explore phase (agents without context hallucinate file paths and APIs)
- Hand-waving acceptance criteria (every criterion must be verifiable by a command or assertion)
- Creating circular dependencies between sub-specs (makes sequential execution impossible)
