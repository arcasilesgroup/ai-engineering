#!/usr/bin/env python3
"""``run_loop_skill_evals.py`` — sub-007 M6 CLI skeleton.

Pilot scope (per ``sub-007/spec.md``): wire the regression-gate path
end-to-end with a deterministic stub optimizer. Full corpus rollout
(736 cases over 46 skills, operator manual review) is deferred — see
``sub-007/plan.md`` Self-Report.

Usage::

    python scripts/run_loop_skill_evals.py --skill all --regression \\
        --baseline evals/baseline.json --corpus-root evals/

Exit codes
----------

- ``0`` — gate passed (no regressions above threshold).
- ``1`` — gate failed (at least one skill dropped > threshold).
- ``2`` — operational error (missing baseline, malformed corpora).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_eval_dependencies() -> tuple[object, object, object, object]:
    """Load tools-only dependencies for direct script execution.

    ``python scripts/run_loop_skill_evals.py`` does not honour pytest's
    configured ``pythonpath``. Keeping the narrowly-scoped bootstrap here
    leaves module imports deterministic for all normal package entry points.
    """
    tools_root = Path(__file__).resolve().parents[1] / "tools"
    if str(tools_root) not in sys.path:
        sys.path.insert(0, str(tools_root))

    from skill_app.eval_runner import load_baseline, load_corpora, run_skill_set_regression
    from skill_infra.skill_creator_adapter import StubSkillCreatorAdapter

    return load_baseline, load_corpora, run_skill_set_regression, StubSkillCreatorAdapter


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run skill-set evals and gate against a captured baseline."
    )
    parser.add_argument(
        "--skill",
        default="all",
        help="Skill name to evaluate, or 'all' (default).",
    )
    parser.add_argument(
        "--regression",
        action="store_true",
        help="Fail the run on >threshold pass@1 drop vs baseline.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(".ai-engineering/evals/baseline.json"),
        help="Path to baseline.json (default: .ai-engineering/evals/baseline.json).",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=Path(".ai-engineering/evals"),
        help="Directory containing <skill>.jsonl corpora (default: .ai-engineering/evals/).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write the JSON regression report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    load_baseline, load_corpora, run_skill_set_regression, stub_adapter = _load_eval_dependencies()

    baseline = load_baseline(args.baseline)
    if not baseline:
        if args.regression:
            # spec-136 D-136-07: fail-loud when the operator explicitly
            # asked for the regression gate but the baseline contract is
            # missing. Silent green here masked broken CI gates pre-spec-136.
            print(
                f"missing baseline at {args.baseline} but --regression was requested; "
                "the regression gate has no contract to evaluate against. Capture a "
                "baseline first (drop --regression on the first run).",
                file=sys.stderr,
            )
            return 2
        # First-run capture flow preserved when --regression is NOT set.
        print(
            f"no baseline at {args.baseline} — skipping regression gate (first-run capture).",
            file=sys.stderr,
        )
        return 0

    if args.skill != "all":
        baseline = tuple(entry for entry in baseline if entry.skill == args.skill)
        if not baseline:
            print(
                f"skill {args.skill!r} not present in baseline; nothing to evaluate.",
                file=sys.stderr,
            )
            return 0

    corpora = load_corpora(args.corpus_root)
    optimizer = stub_adapter(fixed_pass_at_1=1.0)
    report = run_skill_set_regression(
        optimizer=optimizer,
        baseline=baseline,
        corpora=corpora,
    )

    payload = json.dumps(report.to_dict(), indent=2, sort_keys=True)
    if args.out is not None:
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)

    if args.regression and report.failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
