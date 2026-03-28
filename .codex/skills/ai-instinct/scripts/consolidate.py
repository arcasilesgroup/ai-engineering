#!/usr/bin/env python3
"""consolidate.py -- Read instinct context and report observation counts.

Usage:
    python3 consolidate.py [--context PATH] [--observations PATH]

Reads the instinct context file and observations stream, then prints
a summary of observation counts per supported pattern family.

Cross-platform: Python 3.9+, no external dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Supported pattern families for instinct v1
SUPPORTED_FAMILIES = ("toolSequences", "errorRecoveries", "skillAgentPreferences")

DEFAULT_CONTEXT = Path(".ai-engineering/instincts/context.md")
DEFAULT_OBSERVATIONS = Path(".ai-engineering/state/instinct-observations.ndjson")


def count_observations(observations_path: Path) -> Counter[str]:
    """Count observations per pattern family from the NDJSON stream."""
    counts: Counter[str] = Counter()
    if not observations_path.exists():
        return counts
    with observations_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                family = entry.get("family", "unknown")
                counts[family] += 1
            except json.JSONDecodeError:
                counts["_malformed"] += 1
    return counts


def check_context(context_path: Path) -> dict[str, object]:
    """Check whether the instinct context file exists and its size."""
    if not context_path.exists():
        return {"exists": False, "lines": 0}
    text = context_path.read_text(encoding="utf-8")
    lines = text.strip().splitlines()
    return {"exists": True, "lines": len(lines)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Instinct consolidation summary")
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    args = parser.parse_args()

    # Context status
    ctx = check_context(args.context)
    if ctx["exists"]:
        print(f"Context: {args.context} ({ctx['lines']} lines)")
    else:
        print(f"Context: {args.context} (not found)")

    # Observation counts
    counts = count_observations(args.observations)
    total = sum(counts.values())
    print(f"\nObservations: {total} total from {args.observations}")

    if total == 0:
        print("  (no observations recorded yet)")
        return

    for family in SUPPORTED_FAMILIES:
        count = counts.get(family, 0)
        print(f"  {family}: {count}")

    # Report unsupported families if any
    unsupported = {k: v for k, v in counts.items() if k not in SUPPORTED_FAMILIES}
    if unsupported:
        print("\n  Unsupported families (will be ignored):")
        for family, count in sorted(unsupported.items()):
            print(f"    {family}: {count}")


if __name__ == "__main__":
    sys.exit(main() or 0)
