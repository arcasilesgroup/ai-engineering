"""exception --skip "<reason>" — one design exception, granted by a person.

The bypass is deliberate, loud and human-only. It demands a confirmation on a real
keyboard, which the agent does not have, and that is the whole gate. Every concession
emits an event, and `report digest` lists them by name: a guard you bypass three times is a
guard to fix or delete, and the report says so.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from ai_engineering import outcome, paths

WINDOW_SECONDS = 900


def _matches(path: Path, grant: dict[str, object]) -> bool:
    try:
        return json.loads(path.read_text(encoding="utf-8")) == grant
    except (OSError, UnicodeError, ValueError):
        return False


def main(argv: list[str]) -> outcome.Result:
    parser = argparse.ArgumentParser(prog="ai-eng exception")
    parser.add_argument(
        "--skip", required=True, metavar="REASON", help="why this change does not need a plan"
    )
    parser.add_argument("--guard", default="design_gate", choices=["design_gate", "loop_guard"])
    args = parser.parse_args(argv)

    if not sys.stdin.isatty():
        print("  a bypass is a person's decision, and there is no keyboard here. Nothing granted.")
        return outcome.result("INCOMPLETE")
    print(f"  This grants ONE bypass of {args.guard}, for 15 minutes, recorded against your name.")
    print(f"  Reason: {args.skip}")
    if input("  Type yes to grant it › ").strip().lower() != "yes":
        print("  nothing granted.")
        return outcome.result("CANCELLED")

    grant = {"guard": args.guard, "reason": args.skip, "expires": time.time() + WINDOW_SECONDS}
    path = paths.home() / "cache" / "bypass.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(grant), encoding="utf-8")
    except OSError:
        print("  INCOMPLETE: the one-time exception could not be written. Nothing granted.")
        return outcome.result("INCOMPLETE")
    if not _matches(path, grant):
        print("  INCOMPLETE: the one-time exception could not be verified. Nothing granted.")
        return outcome.result("INCOMPLETE")
    paths.load("_emit").emit(args.guard, "bypassed", reason=args.skip, granted="by a person")
    if not _matches(path, grant):
        print("  INCOMPLETE: the one-time exception could not be verified. Nothing granted.")
        return outcome.result("INCOMPLETE")
    print(f"  ✓ granted. The next {args.guard} block passes, once, and the record says why.")
    return outcome.result("PASS")
