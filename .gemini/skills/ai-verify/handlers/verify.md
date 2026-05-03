# Handler: Verify

## Purpose

Run evidence-first verification through a specialist surface. Dispatches agents
via the `Agent` tool for real context isolation. `normal` is the default profile.
`--full` dispatches one specialist per agent.

## Specialist Surface

| Specialist | Agent | What it verifies | `normal` runner |
|------------|-------|------------------|-----------------|
| `deterministic` | `verify-deterministic.md` | security, quality, deps, tests | runs first (alone) |
| `governance` | `verifier-governance.md` | integrity, ownership, compliance | `macro-agent-2` |
| `architecture` | `verifier-architecture.md` | cycles, boundary drift, alignment | `macro-agent-2` |
| `feature` | `verifier-feature.md` | spec/plan completeness, handoff | `macro-agent-2` |

## Procedure

### Step 0: Load Stack Contexts

Follow `.ai-engineering/contexts/stack-context.md`.
Load `.ai-engineering/contexts/evidence-protocol.md` before making claims.

### Step 1: Select profile

- Default to `normal`.
- Use `--full` only when the caller explicitly wants maximum decomposition.
- Direct specialist modes stay callable without `platform`.

### Step 2: Dispatch deterministic agent via Agent tool

Dispatch `verify-deterministic.md` via the **Agent** tool:

```
Agent prompt: "You are the deterministic verification agent.
Read and follow .gemini/agents/verify-deterministic.md
Execute all tool-driven checks against the current codebase.
Read .ai-engineering/state/decision-store.json for accepted exceptions.
Produce structured YAML output."
```

Wait for deterministic results before dispatching LLM judgment agents.

### Step 3: Dispatch LLM judgment agents via Agent tool

**Normal mode** -- Dispatch 1 macro-agent with all 3 LLM specialists:

```
Agent prompt: "You are verifying this codebase with these specialist lenses:
governance, architecture, feature.
[deterministic evidence from Step 2]
Read and follow these agent files:
.gemini/agents/verifier-governance.md
.gemini/agents/verifier-architecture.md
.gemini/agents/verifier-feature.md
Produce findings in YAML format attributed by original specialist."
```

**Full mode** -- Dispatch 3 individual agents in parallel:

```
For each specialist (governance, architecture, feature):
Agent prompt: "You are the [specialist] verification agent.
[deterministic evidence from Step 2]
Read and follow .gemini/agents/verifier-[specialist].md
Produce findings in YAML format."
```

### Step 4: Aggregate by specialist

- Preserve original specialist attribution in both text and YAML output.
- `platform` combines all specialist findings into one scored report.
- `verify` does **not** run a separate finding validator stage.

If a specialist does not apply, emit `not_applicable` explicitly.

### Step 5: Report

Emit:

- Overall score and verdict
- Profile used (`normal` or `full`)
- Specialist summaries in stable order
- Findings grouped by original specialist
- Gate check against thresholds

## Constraints

- Evidence before claims.
- No work-item writes.
- No confidence bonuses or aspirational scoring claims the runtime cannot prove.
- All specialists dispatched via Agent tool, not read inline.
