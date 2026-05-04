# Proposed: `.claude/skills/ai-eval-gate/SKILL.md`

T-4.1 produced this skill body. Auto-mode harness denied autonomous writes into `.claude/skills/` (the dispatch surface is protected from harness self-modification). Apply this content to `.claude/skills/ai-eval-gate/SKILL.md` during a maintainer review pass and run `uv run ai-eng sync-mirrors` to propagate to `.gemini/`, `.codex/`, `.github/` and the matching `src/ai_engineering/templates/project/<ide>/skills/ai-eval-gate/SKILL.md` install templates.

The runtime engine is already landed at `src/ai_engineering/eval/gate.py`; the SKILL.md below is the user-facing trigger that dispatches the engine.

---

```markdown
---
name: ai-eval-gate
description: "Eval gate that reads thresholds from manifest.yml and runs scenario packs against the deliverable. Modes: check (compute current run vs threshold), report (markdown verdict for human review), enforce (exit 0 GO / 1 NO_GO; CONDITIONAL exits 0 with logged warning). Wired into /ai-pr pre-merge and /ai-release-gate as the 9th dimension."
effort: medium
model: sonnet
color: orange
tools: [Bash, Read]
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

`enforcement: advisory` makes the gate informational — it computes and emits all telemetry but always exits 0. Use during the initial roll-out window; flip to `blocking` once scenarios are seeded and pass rates are stable.

## Behaviour

1. Load the manifest evaluation config via `ai_engineering.eval.thresholds.load_evaluation_config`.
2. For each pack in `evaluation.scenario_packs`, load the pack JSON, derive the baseline (pack-embedded `baseline.pass_at_k`), and run `ai_engineering.eval.runner.run_scenario_pack` against the configured trial runner.
3. Aggregate per-pack scorecards. Worst verdict wins (`NO_GO` > `CONDITIONAL` > `GO`).
4. Emit one `eval_gated` event per gate run with `detail.verdict`, `detail.regression_delta_vs_baseline`, `detail.failed_scenarios`. Every per-scenario trial also emits a `scenario_executed` event.
5. Return the verdict JSON or markdown depending on mode.

## /ai-pr integration

Insert a call to `ai-eval-gate enforce` between `/ai-verify` and `gh pr create`. Block merge on NO_GO. Honour `--skip-eval-gate` only when the user explicitly passes it, and audit the bypass:

```yaml
# /ai-pr internal sequence
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

Add as the 9th dimension alongside coverage, security, tests, lint, dependencies, types, docs, packaging. The verdict aggregation in release-gate already handles N dimensions; the integration is a single dispatch line.

## SKILL invocation contract

```bash
# Local check
$CLAUDE_PROJECT_DIR/.claude/skills/ai-eval-gate/run.sh check

# Pre-merge enforce (blocks PR)
$CLAUDE_PROJECT_DIR/.claude/skills/ai-eval-gate/run.sh enforce

# Skip with audit (PR-only escape hatch)
$CLAUDE_PROJECT_DIR/.claude/skills/ai-eval-gate/run.sh enforce --skip --reason "scenarios pending"
```

The `run.sh` shim invokes the Python engine:

```bash
#!/usr/bin/env bash
set -euo pipefail
mode="${1:-check}"
shift || true
exec uv run python -c "
import sys
from pathlib import Path
from ai_engineering.eval.gate import mode_check, mode_enforce, mode_report, filesystem_trial_runner, to_json
from ai_engineering.eval.thresholds import load_evaluation_config

root = Path('${CLAUDE_PROJECT_DIR:-.}').resolve()
runner = filesystem_trial_runner(root)
mode = '$mode'

if mode == 'check':
    print(to_json_check := __import__('json').dumps(mode_check(root, trial_runner=runner), indent=2))
elif mode == 'report':
    print(mode_report(root, trial_runner=runner))
elif mode == 'enforce':
    skip = '--skip' in sys.argv
    reason = None
    if '--reason' in sys.argv:
        reason = sys.argv[sys.argv.index('--reason') + 1]
    code, _ = mode_enforce(root, trial_runner=runner, skip=skip, skip_reason=reason)
    sys.exit(code)
else:
    print(f'unknown mode: {mode}', file=sys.stderr)
    sys.exit(2)
" "$@"
```

## Dependencies

- `ai-evaluator` agent — agent body proposal at `.ai-engineering/specs/spec-119-progress/proposed-ai-evaluator-agent.md`. The skill works without the agent because it dispatches the engine directly; the agent is the kernel-Stage-0 dispatch path.
- `ai_engineering.eval.gate` (Python module — already landed under `src/ai_engineering/eval/gate.py`).
- `manifest.yml` `evaluation:` section — landed under spec-119 Phase 1.
- `.ai-engineering/evals/baseline.json` — landed with three seed scenarios.
```

## Why deferred

Auto-mode harness protected `.claude/skills/` from autonomous self-modification. The runtime engine is already importable, tested, and runs end-to-end (`tests/unit/eval/test_gate_smoke_canonical.py` proves it against the seed baseline). The SKILL.md is the dispatch surface; once landed, no other change is required.
