# spec-119 — Evals Directory

Scenario packs that the `ai-evaluator` agent and `/ai-eval-gate` skill replay against the deliverable to compute pass@k and detect regression vs baseline.

## Layout

| Path | Purpose | Tracked? |
|---|---|---|
| `baseline.json` | Aggregate baseline + seed scenarios | committed |
| `scenarios/` | Per-skill or per-feature scenario packs | committed |
| `runs/` | Per-machine run logs and ad-hoc observations | gitignored |

## Pack schema

```json
{
  "version": "1",
  "baseline": {"pass_at_k": 0.85},
  "scenarios": [
    {
      "id": "scn-NN",
      "k": 5,
      "grader": "deterministic.exact_match",
      "metadata": {
        "description": "...",
        "expected_path": "...",
        "expected_content_substring": "...",
        "forbidden_path": "..."
      }
    }
  ]
}
```

## Authoring contract

- `id` is a stable identifier; do not renumber.
- `k` defaults to `manifest.evaluation.pass_at_k.k` when omitted.
- `grader` references one of the deterministic grader IDs registered with the runner. v1 ships `filesystem_trial_runner` (matches `metadata.expected_path` / `expected_content_substring` / `forbidden_path`); LLM graders are follow-up work.
- `baseline.pass_at_k` reflects the last accepted run's pass@k; update only via `/ai-eval --regression --update-baseline` after explicit human review.

## Adding a new pack

1. Add the pack to `scenarios/<feature-name>.json`.
2. Reference it from `manifest.yml` under `evaluation.scenario_packs`.
3. Run `ai-eng eval-gate check` (CLI wiring lands with the SKILL.md activation per spec-119 Phase 4).
4. Once a passing run exists, set `baseline.pass_at_k` to the observed value.
