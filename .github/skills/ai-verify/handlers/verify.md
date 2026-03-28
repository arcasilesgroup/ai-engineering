# Handler: Verify

## Purpose

Run evidence-first verification through a stable specialist surface. `normal` is the default profile and covers every specialist through 2 fixed macro-agents. `--full` keeps the same specialist coverage but dispatches one specialist per agent.

## Specialist Surface

| Specialist | What it verifies | `normal` runner |
|------------|------------------|-----------------|
| `governance` | integrity, ownership, compliance | `macro-agent-1` |
| `security` | secrets, dependency risk, security tooling | `macro-agent-1` |
| `architecture` | cycles, boundary drift, structural issues | `macro-agent-1` |
| `quality` | lint, duplication, code-quality gates | `macro-agent-2` |
| `performance` | benchmark/perf evidence, hotspot signals | `macro-agent-2` |
| `a11y` | UI accessibility applicability and checks | `macro-agent-2` |
| `feature` | active spec/plan completeness and handoff readiness | `macro-agent-2` |

## Procedure

### Step 0: Load contexts

Follow `.ai-engineering/contexts/step-zero-protocol.md`. Load `.ai-engineering/contexts/evidence-protocol.md` before making claims.

### Step 1: Select profile

- Default to `normal`.
- Use `--full` only when the caller explicitly wants maximum decomposition.
- Direct specialist modes stay callable without `platform`.

### Step 2: Collect evidence

Run the deterministic tools each specialist owns. If a specialist does not apply to the target project, emit `not applicable` or `low signal` explicitly instead of pretending the lens did not run.

### Step 3: Aggregate by specialist

- Preserve original specialist attribution in both text and JSON output.
- `platform` combines all specialist findings into one scored report.
- `verify` does **not** run a separate finding validator stage.

### Step 4: Report

Emit:

- overall score and verdict
- profile used (`normal` or `full`)
- specialist summaries in stable order
- findings grouped by original specialist

## Constraints

- Evidence before claims.
- No work-item writes.
- No confidence bonuses, dismissed-findings sections, or aspirational scoring claims the runtime cannot prove.
