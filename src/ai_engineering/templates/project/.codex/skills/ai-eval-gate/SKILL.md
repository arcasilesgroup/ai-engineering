---
name: ai-eval-gate
description: "Eval gate that reads thresholds from manifest.yml and runs scenario packs against the deliverable. Modes: check (compute current run vs threshold), report (markdown verdict for human review), enforce (exit 0 GO / 1 NO_GO; CONDITIONAL exits 0 with logged warning). Wired into /ai-pr pre-merge and /ai-release-gate as the 9th dimension."
model: sonnet
effort: medium
color: orange
tools: [Bash, Read]
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-eval-gate/SKILL.md
edit_policy: generated-do-not-edit
---


# Eval Gate

## Purpose

Block merge / deploy when behavioural pass@k or hallucination rate fails the manifest-declared thresholds. The Generator (`ai-build`) writes code; the Evaluator (`ai-evaluator`) replays scenario packs; this skill aggregates verdicts across packs and returns a binary GO / NO_GO signal that consumers (`/ai-pr`, `/ai-release-gate`) act on.

## Modes

| Mode | What it does | Exit code |
|---|---|---|
| `check` | Run the gate; print JSON outcome to stdout | always 0 |
| `report` | Run the gate; print markdown verdict to stdout | always 0 |
| `enforce` | Run the gate; print verdict; exit 1 on NO_GO when enforcement is `blocking` | 0 GO/CONDITIONAL/SKIPPED, 1 NO_GO |

## Manifest contract

Reads `.ai-engineering/manifest.yml` `evaluation:` section (spec-119 D-119-04):

```yaml
evaluation:
  pass_at_k:
    k: 5
    threshold: 0.8
  hallucination_rate:
    max: 0.1
  regression_tolerance: 0.05
  scenario_packs:
    - .ai-engineering/evals/baseline.json
  enforcement: blocking  # or 'advisory'
```

`enforcement: advisory` makes the gate informational -- it computes and emits all telemetry but always exits 0. Use during the initial roll-out window; flip to `blocking` once scenarios are seeded and pass rates are stable.

## Behaviour

1. Load the manifest evaluation config via `ai_engineering.eval.thresholds.load_evaluation_config`.
2. For each pack in `evaluation.scenario_packs`, load the pack JSON, derive the baseline (pack-embedded `baseline.pass_at_k`), and run `ai_engineering.eval.runner.run_scenario_pack` against the configured trial runner.
3. Aggregate per-pack scorecards. Worst verdict wins (`NO_GO` > `CONDITIONAL` > `GO`).
4. Emit one `eval_gated` event per gate run with `detail.verdict`, `detail.regression_delta_vs_baseline`, `detail.failed_scenarios`. Every per-scenario trial also emits a `scenario_executed` event.
5. Return the verdict JSON or markdown depending on mode.

## Invocation

```bash
$CLAUDE_PROJECT_DIR/.codex/skills/ai-eval-gate/run.sh check
$CLAUDE_PROJECT_DIR/.codex/skills/ai-eval-gate/run.sh report
$CLAUDE_PROJECT_DIR/.codex/skills/ai-eval-gate/run.sh enforce
$CLAUDE_PROJECT_DIR/.codex/skills/ai-eval-gate/run.sh enforce --skip --reason "scenarios pending"
```

The `run.sh` shim invokes `_entry.py` (a Python entry script sibling) which dispatches into the Python engine in `src/ai_engineering/eval/gate.py`. Both files live next to this SKILL.md so the skill is self-contained.

## /ai-pr integration

`/ai-pr` calls `ai-eval-gate enforce` between `/ai-verify` and `gh pr create`. Block merge on NO_GO. Honour `--skip-eval-gate` only when the user explicitly passes it, and the skip path emits an audit event:

```yaml
- run: /ai-verify
- run: /ai-eval-gate enforce
  on_failure:
    if: arg.skip_eval_gate
    emit:
      kind: eval_run
      detail:
        operation: eval_gated
        verdict: SKIPPED
        reason: user_skip_via_pr_flag
- run: gh pr create
```

## /ai-release-gate integration

Added as the 9th dimension alongside coverage, security, tests, lint, dependencies, types, docs, packaging. The verdict aggregation in release-gate handles N dimensions; this is a single dispatch line that contributes the eval verdict.

## Common Mistakes

- Running enforce on `pre-commit` or `pre-push`: the eval gate is for CI / PR-time, not the local hot path. Pre-commit budgets are reserved for ms-scale work; eval gate runs N x k trials per pack.
- Treating `CONDITIONAL` as a soft failure: it is a soft pass with surfaced regression delta. Consumers must surface but not block.
- Skipping the gate without `--skip-eval-gate` audit logging. Bypasses must be traceable; never silence the gate by removing it from the `/ai-pr` sequence.
- Authoring scenario packs with non-deterministic graders in v1. LLM graders are follow-up work and would need their own bias / calibration spec.

## Integration

- **Called by**: `/ai-pr` (pre-merge), `/ai-release-gate` (9th dimension), maintainers directly via the run.sh shim, CI pipelines.
- **Calls**: `ai-evaluator` agent (when invoked via Agent tool), the Python engine in `src/ai_engineering/eval/gate.py` (when invoked via run.sh).
- **Telemetry**: every run emits an `eval_gated` event; per-scenario trials emit `scenario_executed`; `pass_at_k_computed` and `hallucination_rate_computed` are emitted before the verdict.

## References

- Skill source of truth: `.codex/skills/ai-eval-gate/SKILL.md`
- Engine: `src/ai_engineering/eval/gate.py`
- Manifest contract: `.ai-engineering/manifest.yml` `evaluation:` section
- Schema: `.ai-engineering/schemas/audit-event.schema.json` (`$defs/detail_eval_run`)
- Spec: `.ai-engineering/specs/spec-119-evaluation-layer.md`
- Plan: `.ai-engineering/specs/plan-119-evaluation-layer.md`
