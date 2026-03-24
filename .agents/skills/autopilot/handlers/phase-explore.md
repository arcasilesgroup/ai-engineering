# Handler: Deep Explore

## Purpose

Dispatch Agent(Explore) x N in parallel to gather deep codebase context for each sub-spec before implementation begins. Enriches every sub-spec with architectural context so that build agents receive full situational awareness on first attempt.

## Prerequisites

- Phase Split is complete
- Sub-spec files exist at `specs/autopilot/sub-NNN.md`
- Each sub-spec contains a `files:` list and `## Scope` section

## Procedure

### Step 1 -- Load Sub-Specs

1. Glob `specs/autopilot/sub-*.md` to discover all sub-spec files.
2. For each sub-spec, extract:
   - `files:` list (files to create or modify)
   - `## Scope` section content
   - Sub-spec number (NNN from filename)
3. If no sub-specs found: STOP. Report: "No sub-specs found. Run phase-split first."

### Step 2 -- Dispatch Explorers

For each sub-spec, launch Agent(Explore) with `run_in_background: true` using this prompt:

```
Gather implementation context for sub-spec NNN.

**Files to create/modify:**
{files list from sub-spec}

**Sub-spec scope:**
{scope section from sub-spec}

Explore the codebase to understand:
1. Full context of files that will be modified (read them entirely)
2. Existing patterns for similar functionality nearby
3. Callers and importers of functions that will change
4. Reusable utilities, helpers, and conventions in scope
5. Test patterns used in this area of the codebase

Time-box: 2-3 minutes.

Output: structured context report with absolute file paths and patterns found.
```

All N explorers run in parallel. Do NOT wait for one to finish before launching the next.

### Step 3 -- Collect and Enrich

Wait for all explorers to complete. For each explorer result:

1. Read the explorer output.
2. Append an `## Architectural Context` section to the corresponding sub-spec file containing:
   - **Patterns found**: design patterns, naming conventions, structural idioms in scope
   - **Dependencies mapped**: import chains, coupling points, callers of modified functions
   - **Utilities to reuse**: existing helpers, shared modules, test fixtures available
   - **Key files read**: absolute paths with one-line annotations
3. Write the enriched sub-spec back to disk.

### Step 4 -- Validate Enrichment

For each sub-spec file:

1. Confirm `## Architectural Context` section exists and is non-empty.
2. Reject placeholder content -- if any section contains only "TODO", "TBD", or "N/A", re-dispatch a single explorer for that sub-spec with a narrower prompt.
3. After re-dispatch (max 1 retry per sub-spec), if context is still empty: mark the sub-spec with `context: partial` and proceed. Do not block the pipeline.

## Output

- Every sub-spec file enriched with `## Architectural Context`
- Exploration summary appended to `specs/autopilot/exploration.md`
- Pipeline ready to proceed to Phase 2 (Execute Loop)

## Failure Modes

| Condition | Action |
|-----------|--------|
| Explorer times out | Mark sub-spec `context: partial`, proceed |
| Explorer returns empty output | Retry once with narrower scope |
| All explorers fail | STOP. Report: "Exploration failed for all sub-specs." |
| Sub-spec file missing after split | STOP. Report: "Sub-spec NNN missing. Re-run phase-split." |
