"""spec-119 /ai-eval-gate Python entry point.

Invoked by run.sh; does the actual gate dispatch through the
ai_engineering.eval engine. Kept as a sibling of SKILL.md so the
skill is self-contained and the shell shim stays pattern-free.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from ai_engineering.eval.gate import (
    filesystem_trial_runner,
    mode_check,
    mode_enforce,
    mode_report,
    to_json,
)
from ai_engineering.eval.thresholds import load_evaluation_config


def _project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(raw).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-eval-gate")
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "report", "enforce"],
    )
    parser.add_argument("--skip", action="store_true")
    parser.add_argument("--reason", default=None)
    args = parser.parse_args(argv)

    root = _project_root()
    cfg = load_evaluation_config(root / ".ai-engineering" / "manifest.yml")
    runner = filesystem_trial_runner(root)

    if args.mode == "check":
        payload = mode_check(root, trial_runner=runner, config=cfg)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.mode == "report":
        print(mode_report(root, trial_runner=runner, config=cfg))
        return 0
    if args.mode == "enforce":
        code, outcome = mode_enforce(
            root,
            trial_runner=runner,
            config=cfg,
            skip=args.skip,
            skip_reason=args.reason,
        )
        print(to_json(outcome))
        return code
    print(f"unknown mode: {args.mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
