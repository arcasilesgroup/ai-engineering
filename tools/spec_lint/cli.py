"""``spec_lint`` CLI — validates ``.ai-engineering/specs/spec.md``.

Runs the five schema checks (frontmatter, sections, decisions, non_goals,
references) against a target spec file and prints a single info-line
summary. Hot-path budget per spec-131 R-131-13: ≤500 ms per invocation
(CI tolerance 25 % → 625 ms hard ceiling).

Exit codes:

* ``0`` — zero BLOCKER results (ADVISORY warnings allowed).
* ``1`` — at least one BLOCKER (missing required frontmatter, missing
  required section, malformed decision ID, empty Non-Goals,
  malformed reference).
* ``2`` — argument-parse error or file-not-found (argparse default).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from spec_lint.checks.decisions import check_decisions
from spec_lint.checks.frontmatter import check_frontmatter
from spec_lint.checks.non_goals import check_non_goals
from spec_lint.checks.plan import check_plan
from spec_lint.checks.references import check_references
from spec_lint.checks.sections import check_sections

_DEFAULT_SPEC_PATH = Path(".ai-engineering/specs/spec.md")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spec_lint",
        description=(
            "Schema validator for .ai-engineering/specs/spec.md (spec-131 S7 enforcement surface)."
        ),
    )
    parser.add_argument(
        "spec_path",
        type=Path,
        nargs="?",
        default=_DEFAULT_SPEC_PATH,
        help="Path to the spec.md file (default: .ai-engineering/specs/spec.md).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Lint and exit non-zero on any BLOCKER result.",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Print every check result line-by-line (advisory output mode).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress summary line when BLOCKERS=0 and ADVISORIES=0.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.check and not args.baseline:
        parser.print_help()
        return 0

    spec_path: Path = args.spec_path
    if not spec_path.is_file():
        sys.stderr.write(f"spec_lint: file not found: {spec_path}\n")
        return 2

    started = time.perf_counter()

    # Run every check; each returns ``list[CheckResult]``. Order is
    # deterministic so CI logs read top-to-bottom: frontmatter →
    # sections → decisions → non_goals → references.
    results = []
    results.extend(check_frontmatter(spec_path))
    results.extend(check_sections(spec_path))
    results.extend(check_decisions(spec_path))
    results.extend(check_non_goals(spec_path))
    results.extend(check_references(spec_path))
    results.extend(check_plan(spec_path))

    elapsed_ms = (time.perf_counter() - started) * 1000.0

    blockers = [r for r in results if r.severity == "BLOCKER"]
    advisories = [r for r in results if r.severity == "ADVISORY"]

    if args.baseline:
        for result in results:
            sys.stdout.write(f"[{result.severity}] {result.check_name}: {result.reason}\n")

    quiet_ok = args.quiet and not blockers and not advisories
    if args.check and not quiet_ok:
        sys.stdout.write(
            "spec_lint: 6/6 checks "
            f"(BLOCKERS={len(blockers)} "
            f"ADVISORIES={len(advisories)}, "
            f"file={spec_path}, "
            f"T={elapsed_ms:.1f}ms)\n"
        )
        for result in blockers:
            sys.stdout.write(f"  BLOCKER {result.check_name}: {result.reason}\n")
        for result in advisories:
            sys.stdout.write(f"  ADVISORY {result.check_name}: {result.reason}\n")

    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
