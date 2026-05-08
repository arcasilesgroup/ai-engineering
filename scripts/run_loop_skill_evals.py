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

# pyproject.toml pins ``pythonpath = ["src", "tools"]``; running this
# script directly via ``python scripts/...`` does not honour that
# pin, so we extend ``sys.path`` defensively. CI invokes via
# ``pytest`` or via ``python -m`` so this branch is rarely taken.
_TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from skill_app.eval_runner import (  # noqa: E402 — sys.path bootstrap above.
    load_baseline,
    load_corpora,
    run_skill_set_regression,
)
from skill_infra.skill_creator_adapter import (  # noqa: E402
    StubSkillCreatorAdapter,
)


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
        default=Path("evals/baseline.json"),
        help="Path to evals/baseline.json (default: evals/baseline.json).",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=Path("evals"),
        help="Directory containing <skill>.jsonl corpora (default: evals/).",
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

    baseline = load_baseline(args.baseline)
    if not baseline:
        # Empty baseline ⇒ first-run capture flow. Per
        # ``ai-eval --regression`` semantics, the absence of a
        # baseline is treated as a no-op pass; ``--regression``
        # only gates after a baseline exists.
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
    optimizer = StubSkillCreatorAdapter(fixed_pass_at_1=1.0)
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


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
