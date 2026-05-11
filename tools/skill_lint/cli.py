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
from skill_lint.checks.effort import check_all_skills as check_effort_all
from skill_lint.checks.effort import load_policy as load_dispatch_policy
from skill_lint.checks.md_mirror import check_md_mirror_consistency
from skill_lint.checks.naming import check_naming
from skill_lint.checks.pair_aware import check_pair_consistency
from skill_lint.checks.principles import check_principles_citations

_DEFAULT_SKILLS_ROOT = Path(".claude/skills")
_DEFAULT_AGENTS_ROOT = Path(".claude/agents")
_DEFAULT_REPO_ROOT = Path(".")
_DEFAULT_HOOKS_ROOT = Path(".ai-engineering/scripts/hooks")
_DEFAULT_SCHEDULED_ROOT = Path(".ai-engineering/scripts/scheduled")
_DEFAULT_POLICY_PATH = Path("docs/model-dispatch-policy.md")


def _exit_code(
    grade_counts: dict[str, int],
    md_mirror_results: list | None = None,
    principles_results: list | None = None,
    effort_results: list | None = None,
) -> int:
    """Map grade counts + extra-check severities to a CLI exit code.

    Existing semantics (spec-127): exit 1 on Grade D; exit 2 on >2 Grade C.

    spec-131 S1 additions:
      * Any CRITICAL from ``md_mirror`` → exit 1 (canonical-payload drift
        is a hard fail; D-131-03 / D-131-14).
      * ``principles`` ships in ADVISORY mode for sub-001 (R-1.6
        mitigation): every severity surfaces in the summary line but
        never drives exit code. S6 SKILL audit upgrades MAJOR to
        blocking once every shipped SKILL.md emits the "Principles
        applied" line via the patch-ready ``/ai-plan`` output.

    spec-131 S3 (sub-003) addition:
      * Any MAJOR / CRITICAL from ``effort`` → exit 1 (D-131-08).
        ``model_tier`` MINORs stay advisory during the R-131-09 grace
        window — they surface in the summary but do not block.
    """
    # principles_results intentionally consumed for signature parity;
    # advisory-only in sub-001 (R-1.6).
    _ = principles_results
    if grade_counts.get("D", 0) > 0:
        return 1
    if md_mirror_results and any(
        getattr(r, "severity", "OK") == "CRITICAL" for r in md_mirror_results
    ):
        return 1
    if effort_results and any(
        getattr(r, "severity", "OK") in ("MAJOR", "CRITICAL") for _path, r in effort_results
    ):
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
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_DEFAULT_REPO_ROOT,
        help="Path to the repo root for md_mirror checks (default: .).",
    )
    parser.add_argument(
        "--hooks-root",
        type=Path,
        default=_DEFAULT_HOOKS_ROOT,
        help="Path to the hooks directory for naming R2/R3/R5 (default: .ai-engineering/scripts/hooks).",
    )
    parser.add_argument(
        "--scheduled-root",
        type=Path,
        default=_DEFAULT_SCHEDULED_ROOT,
        help="Path to the scheduled directory for naming R4/R5 (default: .ai-engineering/scripts/scheduled).",
    )
    parser.add_argument(
        "--policy-path",
        type=Path,
        default=_DEFAULT_POLICY_PATH,
        help="Path to docs/model-dispatch-policy.md (default: docs/model-dispatch-policy.md).",
    )
    parser.add_argument(
        "--enforce-tier",
        action="store_true",
        help="Promote `model_tier:` violations from MINOR to MAJOR (flip after R-131-09 grace).",
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
    # spec-131 S1: md_mirror + principles checks (D-131-03 / D-131-04 / R-1.6).
    # md_mirror CRITICAL drives exit 1; principles MAJOR drives exit 1
    # (MINOR is advisory per R-1.6 — upgraded in S6).
    md_mirror_results = check_md_mirror_consistency(args.repo_root)
    principles_results = check_principles_citations(args.skills_root)
    # spec-131 sub-006: brief §2.5 R1-R5 naming lint. Advisory in this
    # sub-spec — naming MAJORs do NOT alter exit-code semantics until
    # spec-132 closes the D-131-10 legacy renames. Counts surface in
    # the one-line summary so operators see the picture.
    naming_results = check_naming(
        args.skills_root,
        args.agents_root,
        args.hooks_root,
        args.scheduled_root,
    )
    # spec-131 S3 (sub-003): effort + model_tier frontmatter contract.
    # MAJOR (effort_declared, policy mismatch) blocks; model_tier MINOR
    # stays advisory during the R-131-09 grace window.
    dispatch_policy = load_dispatch_policy(args.policy_path)
    effort_results = check_effort_all(
        args.skills_root,
        dispatch_policy,
        enforce_tier=args.enforce_tier,
    )

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
        # spec-131 S1: md_mirror + principles counters.
        md_mirror_status = "OK" if all(r.severity == "OK" for r in md_mirror_results) else "FAIL"
        principles_counts: dict[str, int] = {}
        for _path, result in principles_results:
            principles_counts[result.severity] = principles_counts.get(result.severity, 0) + 1
        # spec-131 sub-006: naming R1-R5 counters.
        naming_counts: dict[str, int] = {}
        for _path, result in naming_results:
            naming_counts[result.severity] = naming_counts.get(result.severity, 0) + 1
        # spec-131 S3 (sub-003): effort + model_tier counters.
        effort_counts: dict[str, int] = {}
        for _path, result in effort_results:
            effort_counts[result.severity] = effort_counts.get(result.severity, 0) + 1
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
            f"| md_mirror={md_mirror_status} "
            f"| principles "
            f"OK={principles_counts.get('OK', 0)} "
            f"MINOR={principles_counts.get('MINOR', 0)} "
            f"MAJOR={principles_counts.get('MAJOR', 0)} "
            f"| naming "
            f"OK={naming_counts.get('OK', 0)} "
            f"INFO={naming_counts.get('INFO', 0)} "
            f"MINOR={naming_counts.get('MINOR', 0)} "
            f"MAJOR={naming_counts.get('MAJOR', 0)} "
            f"| effort "
            f"OK={effort_counts.get('OK', 0)} "
            f"MINOR={effort_counts.get('MINOR', 0)} "
            f"MAJOR={effort_counts.get('MAJOR', 0)} "
            f"({elapsed_ms:.1f} ms)\n"
        )
        return _exit_code(
            skills_report.summary,
            md_mirror_results=md_mirror_results,
            principles_results=principles_results,
            effort_results=effort_results,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
