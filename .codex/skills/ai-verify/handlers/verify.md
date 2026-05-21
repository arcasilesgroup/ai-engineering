# Handler: Verify

## Purpose

Run evidence-first verification through a specialist surface. Dispatches agents
via the `Agent` tool for real context isolation. `normal` is the default profile.
`--full` dispatches one specialist per agent.

## Specialist Surface

Spec-140 W3 collapsed the verifier roster from 4 to 2. `verifier-governance` + `verifier-feature` merged into `verifier-acceptance`. `verifier-architecture`'s heuristics moved to `/ai-advise` (advisory non-blocking).

| Specialist | Agent | What it verifies | `normal` runner |
|------------|-------|------------------|-----------------|
| `deterministic` | `verifier-deterministic.md` | security, quality, deps, tests | runs first (alone) |
| `acceptance` | `verifier-acceptance.md` | spec/plan completeness, handoff, integrity, ownership, compliance, gate enforcement | `macro-agent-2` |

## Procedure

### Step 0: Load Stack Contexts

Apply stack overrides: read `.ai-engineering/manifest.yml` `providers.stacks` and load `.ai-engineering/overrides/<stack>/conventions.md` for each stack.
Run the IRRV protocol before making claims: per claim, identify command → run → capture output + exit code → classify CONFIRMED or REFUTED.

### Step 1: Select profile

- Default to `normal`.
- Use `--full` only when the caller explicitly wants maximum decomposition.
- Direct specialist modes stay callable without `platform`.

### Step 2: Dispatch deterministic agent via Agent tool

Dispatch `verifier-deterministic.md` via the **Agent** tool:

```
Agent prompt: "You are the deterministic verification agent.
Read and follow .codex/agents/verifier-deterministic.md
Execute all tool-driven checks against the current codebase.
Query decision-store.json (via `ai-eng decision list`) for accepted exceptions.
Produce structured YAML output."
```

Wait for deterministic results before dispatching LLM judgment agents.

### Step 3: Dispatch LLM judgment agent via Agent tool

**Normal mode** -- Dispatch the single acceptance specialist (covers both feature + governance lenses post-W3):

```
Agent prompt: "You are the acceptance verification specialist.
[deterministic evidence from Step 2]
Read and follow .codex/agents/verifier-acceptance.md
Cover both lenses (feature + governance) and produce findings in YAML
format with `lens: feature|governance` attribution preserved per finding."
```

**Full mode** -- Same single dispatch; `--full` no longer fans out beyond
deterministic + acceptance because the post-W3 roster has only those two
specialists. Architecture concerns route to `/ai-advise drift` for
advisory non-blocking signal.

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
