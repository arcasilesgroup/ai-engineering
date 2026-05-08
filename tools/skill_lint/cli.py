"""``skill_lint`` CLI — ``--check`` and ``--baseline`` modes.

Hot-path budget per D-127-08: ``--check`` over the current 50-skill
surface must complete in ≤200 ms parallel walk. Implementation guard:
``ThreadPoolExecutor(max_workers=8)`` in the FS scanner, no
third-party deps, single regex pass for frontmatter.

Exit codes (per plan T-E.3):

* ``0`` — no Grade D, ≤2 Grade C entries.
* ``1`` — at least one Grade D.
* ``2`` — more than 2 Grade C entries.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from skill_app.lint_agents import LintAgentsUseCase
from skill_app.lint_skills import LintSkillsUseCase
from skill_infra.fs_scanner import FilesystemAgentScanner, FilesystemSkillScanner
from skill_infra.markdown_reporter import MarkdownReporter
from skill_lint.checks.pair_aware import check_pair_consistency

_DEFAULT_SKILLS_ROOT = Path(".claude/skills")
_DEFAULT_AGENTS_ROOT = Path(".claude/agents")


def _exit_code(grade_counts: dict[str, int]) -> int:
    if grade_counts.get("D", 0) > 0:
        return 1
    if grade_counts.get("C", 0) > 2:
        return 2
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill_lint",
        description=("Conformance lint for SKILL.md and agent .md files (spec-127 M1 rubric)."),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Lint and exit non-zero on Grade D or >2 Grade C.",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Print the Markdown baseline report to stdout.",
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=_DEFAULT_SKILLS_ROOT,
        help="Path to the skills directory (default: .claude/skills).",
    )
    parser.add_argument(
        "--agents-root",
        type=Path,
        default=_DEFAULT_AGENTS_ROOT,
        help="Path to the agents directory (default: .claude/agents).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.check and not args.baseline:
        parser.print_help()
        return 0

    started = time.perf_counter()

    skill_scanner = FilesystemSkillScanner(args.skills_root)
    agent_scanner = FilesystemAgentScanner(args.agents_root, args.skills_root)

    skills_report = LintSkillsUseCase(skill_scanner).run()
    agents_report = LintAgentsUseCase(agent_scanner).run()
    # Brief §22.5: pair-aware checks. Advisory-grade by default — aggregate
    # severity counts surface in the summary line so operators see them
    # without the gate hard-failing the legacy surface (gates added in
    # follow-up wave once the §22.3 caps are met).
    pair_results = check_pair_consistency(args.skills_root, args.agents_root)

    elapsed_ms = (time.perf_counter() - started) * 1000.0

    if args.baseline:
        reporter = MarkdownReporter()
        sys.stdout.write(
            reporter.render_baseline(
                skills_report=skills_report,
                agents_report=agents_report,
                elapsed_ms=elapsed_ms,
            )
        )
        sys.stdout.write("\n")

    if args.check:
        # Pair-aware severity counts (advisory): surface so operators
        # see the §22.5 picture without changing exit-code semantics.
        pair_counts: dict[str, int] = {}
        for _slug, result in pair_results:
            pair_counts[result.severity] = pair_counts.get(result.severity, 0) + 1
        # Print a one-line summary so CI logs surface the result.
        sys.stdout.write(
            "skill_lint: skills "
            f"A={skills_report.summary.get('A', 0)} "
            f"B={skills_report.summary.get('B', 0)} "
            f"C={skills_report.summary.get('C', 0)} "
            f"D={skills_report.summary.get('D', 0)} "
            f"| pairs "
            f"OK={pair_counts.get('OK', 0)} "
            f"INFO={pair_counts.get('INFO', 0)} "
            f"MINOR={pair_counts.get('MINOR', 0)} "
            f"MAJOR={pair_counts.get('MAJOR', 0)} "
            f"({elapsed_ms:.1f} ms)\n"
        )
        return _exit_code(skills_report.summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
