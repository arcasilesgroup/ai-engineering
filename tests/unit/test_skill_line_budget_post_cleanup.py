"""Phase 5 GREEN: post-cleanup line-budget contract for 47 SKILL.md files (spec-106 G-5).

Asserts that the restatement-cleanup mechanical sweep removes >=400 lines
across ``.claude/skills/ai-*/SKILL.md`` without weakening contract content
(the sweep targets only restatements of CLAUDE.md Don't rules / framework
conventions per spec-106 D-106-05). The baseline was captured in Phase 5
T-5.1 via ``wc -l .claude/skills/ai-*/SKILL.md`` and recorded as
``BASELINE_LINES`` below.

TDD CONSTRAINT: this file is IMMUTABLE once Phase 5 T-5.1 records the
baseline -- BASELINE_LINES, the cut target, and the assertion must NOT be
edited downward to make implementation easier. Skill markdown is the
load-bearing surface for non-Claude IDEs (Codex/Gemini do not auto-load
CLAUDE.md), so the line-budget contract guards genuine adoption friction.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

# Phase 5 T-5.1 contract: pre-sweep snapshot total of
# `wc -l .claude/skills/ai-*/SKILL.md` recorded 2026-04-27.
BASELINE_LINES: int = 5736
TARGET_REDUCTION = 400

# Skills added AFTER the spec-106 P5 baseline. Their lines are excluded from
# the cleanup contract because the contract targets restatement removal in
# the original 47 skills, not net cap on framework surface. Each entry must
# be a skill folder name under .claude/skills/. Adding a new skill here
# requires a corresponding new spec that justifies the addition.
SKILLS_ADDED_POST_BASELINE: tuple[str, ...] = (
    "ai-mcp-sentinel",  # spec-107 D-107-08 (Capa 3 LLM cold-path skill)
)

# Functional additions to existing skills AFTER the spec-106 P5 baseline.
# These represent NEW required content, not restatement that should have
# been swept. Format: skill_name -> (spec_ref, lines_added_estimate).
# Each entry must reference an approved spec decision; this map is itself
# audit evidence that the line count grew for legitimate functional reasons.
FUNCTIONAL_ADDITIONS_POST_BASELINE: dict[str, tuple[str, int]] = {
    # spec-107 D-107-04 added Checks 6 (agent naming consistency cross-IDE),
    # 7 (GEMINI.md skill count freshness), 8 (generic instruction-file
    # count scan) to /ai-platform-audit. These are new functional checks,
    # not restatement. ~60 lines of new content.
    "ai-platform-audit": ("spec-107 D-107-04", 65),
}


def _total_skill_lines() -> int:
    """Sum line counts across every .claude/skills/ai-*/SKILL.md file."""
    return sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in SKILLS_DIR.glob("ai-*/SKILL.md")
    )


def _post_baseline_skill_lines() -> int:
    """Sum line counts for skills added AFTER the spec-106 P5 baseline."""
    total = 0
    for skill_name in SKILLS_ADDED_POST_BASELINE:
        path = SKILLS_DIR / skill_name / "SKILL.md"
        if path.is_file():
            total += len(path.read_text(encoding="utf-8").splitlines())
    return total


def _functional_additions_lines() -> int:
    """Sum estimated lines from functional additions to existing skills."""
    return sum(lines for _spec, lines in FUNCTIONAL_ADDITIONS_POST_BASELINE.values())


def test_post_cleanup_total_lines_under_baseline_minus_400() -> None:
    """Sweep must drop >=400 lines net across the original 47 SKILL.md files.

    Phase 5 T-5.1 records ``BASELINE_LINES`` from the pre-sweep snapshot.
    Phase 5 T-5.3..T-5.6 sweep batches a-d / e-l / m-s / t-z. T-5.7
    re-measures and T-5.9 confirms the >=400 line cut budget here.

    spec-107 added new skills (``ai-mcp-sentinel`` per D-107-08); their
    lines are excluded via ``SKILLS_ADDED_POST_BASELINE`` because the
    cleanup contract targets restatement removal in the original 47
    skills, not a net cap on the framework surface.
    """
    raw_actual = _total_skill_lines()
    new_skill_overhead = _post_baseline_skill_lines()
    functional_overhead = _functional_additions_lines()
    actual_against_baseline = raw_actual - new_skill_overhead - functional_overhead
    target = BASELINE_LINES - TARGET_REDUCTION
    assert actual_against_baseline <= target, (
        f"Cleanup-equivalent SKILL.md line count {actual_against_baseline} "
        f"(raw {raw_actual} minus {new_skill_overhead} from new skills "
        f"{SKILLS_ADDED_POST_BASELINE} minus {functional_overhead} from "
        f"functional additions {list(FUNCTIONAL_ADDITIONS_POST_BASELINE.keys())}) "
        f"exceeds spec-106 G-5 target of {target} (baseline {BASELINE_LINES} "
        f"minus >={TARGET_REDUCTION} cuts). Phase 5 sweep must remove "
        "restatement of CLAUDE.md Don't rules without weakening any required "
        "contract section."
    )
