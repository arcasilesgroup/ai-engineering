#!/usr/bin/env python3
"""Enforce OPA policy coverage threshold (spec-123 D-123-20 / T-4.3).

Runs ``opa test --coverage --format=json .ai-engineering/policies/`` and
asserts that overall + per-policy line coverage stays at or above the
configured threshold (default 90%). Failure exits non-zero so CI can
block the merge.

Why a separate script:

* Keeps the CI workflow YAML small and grep-able.
* Lets a developer reproduce the gate locally with ``python3
  scripts/check_opa_coverage.py``.
* Centralises the per-policy filter logic — test rego files
  (``*_test.rego``) are excluded because their helpers are 100%-covered
  by definition and would mask thin policy coverage if rolled in.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 90.0
DEFAULT_POLICIES_DIR = Path(".ai-engineering/policies")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--policies-dir",
        type=Path,
        default=DEFAULT_POLICIES_DIR,
        help="Path to the OPA bundle directory (default: %(default)s).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Minimum percentage line coverage per policy (default: %(default)s).",
    )
    return parser.parse_args(argv)


def _run_opa_coverage(policies_dir: Path) -> dict:
    if shutil.which("opa") is None:
        sys.stderr.write(
            "ERROR: opa binary not on PATH. Install via setup-opa or "
            "https://www.openpolicyagent.org/docs/latest/#1-download-opa\n"
        )
        raise SystemExit(2)
    proc = subprocess.run(
        [
            "opa",
            "test",
            "--coverage",
            "--format=json",
            str(policies_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in (0,):
        # opa test exits 1 when a test fails -- surface stderr+stdout
        # and abort so CI fails loudly rather than silently allowing.
        sys.stderr.write(f"opa test failed (rc={proc.returncode}):\n{proc.stderr}\n")
        sys.stderr.write(proc.stdout)
        raise SystemExit(proc.returncode or 1)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"opa coverage output is not valid JSON: {exc}\n")
        sys.stderr.write(proc.stdout)
        raise SystemExit(1) from exc


def _filter_policy_files(files: dict[str, dict]) -> dict[str, dict]:
    """Keep only ``*.rego`` source files, excluding ``*_test.rego``."""
    return {
        path: data
        for path, data in files.items()
        if path.endswith(".rego") and not path.endswith("_test.rego")
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    coverage = _run_opa_coverage(args.policies_dir)
    overall = coverage.get("coverage")
    per_file = _filter_policy_files(coverage.get("files", {}))

    print(f"OPA coverage report ({args.policies_dir})")
    print(f"  overall: {overall:.2f}%")
    failures: list[str] = []
    for path, data in sorted(per_file.items()):
        pct = data.get("coverage", 0.0)
        marker = "PASS" if pct >= args.threshold else "FAIL"
        print(f"  [{marker}] {path}: {pct:.2f}%")
        if pct < args.threshold:
            failures.append(f"{path}: {pct:.2f}% < {args.threshold:.2f}%")

    if overall is None or overall < args.threshold:
        failures.append(
            f"overall: {overall if overall is not None else 'missing'} < {args.threshold:.2f}%"
        )

    if failures:
        sys.stderr.write("\nOPA coverage gate failed:\n")
        for line in failures:
            sys.stderr.write(f"  - {line}\n")
        return 1
    print(f"\nOK: all policies meet ≥{args.threshold:.0f}% coverage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
