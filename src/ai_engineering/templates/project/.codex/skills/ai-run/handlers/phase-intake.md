# Handler: Phase 1 -- INTAKE AND BASELINE EXPLORE

## Purpose

Create or resume the run, fetch source work items, and build the architectural baseline that all later planning depends on.

## Inputs

- Invocation arguments (`github`, `azure`, or `markdown`)
- `.ai-engineering/manifest.yml`
- `.codex/agents/ai-explore.md`
- `references/run-manifest.md`
- `references/provider-matrix.md`

## Procedure

### Step 1 -- Resolve source provider

Pick the intake flow from the invocation:

- `github` -> GitHub Issues and optional GitHub Projects metadata
- `azure` -> Azure Boards work items and relations
- `markdown` -> local task-list document

Use `work_items.provider` from `.ai-engineering/manifest.yml` for lifecycle policy, but do not treat it as the only valid source. `ai-run` may normalize from one provider and deliver through another.

### Step 2 -- Create run state

Create the run-state tree described in `references/run-manifest.md`:

```text
.ai-engineering/runs/<run-id>/
  manifest.md
  items/<item-id>/
```

Initialize `manifest.md` with:

- run id
- invocation
- source provider
- mode (`single-item` or `multi-item`)
- initial status `intake`

### Step 3 -- Gather source inventory

Fetch all candidate work items and record the raw source inventory in the run manifest.

Provider-specific expectations:

- GitHub: title, body, labels, comments, linked PRs, issue refs, project metadata
- Azure Boards: title, description, type, state, relations, parent/child links, board fields
- Markdown: checkbox state, heading path, inline refs, local file path

### Step 4 -- Baseline exploration is mandatory

Before item enrichment or DAG planning:

1. Read `.codex/agents/ai-explore.md`.
2. Dispatch a repository-wide baseline exploration pass.
3. Capture:
   - architecture map
   - coupling hot spots
   - shared configs and manifests
   - root-level governance surfaces
   - migration and generated-file zones
   - likely conflict clusters

Persist the summary into the run manifest under `baseline_exploration`.

### Step 5 -- Normalize and enrich

Normalize every candidate item to the shared schema:

```text
{ id, type, source, source_ref, title, description, acceptance_criteria,
  dependencies, close_policy, risk_level, predicted_write_surface,
  shared_artifacts, children[] }
```

Enrichment must use both source metadata and baseline exploration evidence.

### Step 6 -- Initial triage

Classify each item:

- `ready` -> enough context to plan
- `needs_deepening` -> requires scoped exploration
- `blocked` -> missing external dependency or unsafe ambiguity
- `deferred` -> should wait for another item or later wave

## Gate

Phase 1 passes only when:

- run manifest exists
- source inventory is recorded
- baseline exploration is recorded
- every item has a normalized status

## Failure Modes

| Condition | Action |
|-----------|--------|
| Source provider auth fails | Stop with a blocker report. |
| Baseline exploration fails twice | Stop. Do not plan from issue metadata alone. |
| Source inventory is empty | Report and stop. |
