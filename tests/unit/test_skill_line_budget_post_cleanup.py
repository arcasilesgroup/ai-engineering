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


def _total_skill_lines() -> int:
    """Sum line counts across every .claude/skills/ai-*/SKILL.md file."""
    return sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in SKILLS_DIR.glob("ai-*/SKILL.md")
    )


def test_post_cleanup_total_lines_under_baseline_minus_400() -> None:
    """Sweep must drop >=400 lines net across the 47 SKILL.md files.

    Phase 5 T-5.1 records ``BASELINE_LINES`` from the pre-sweep snapshot.
    Phase 5 T-5.3..T-5.6 sweep batches a-d / e-l / m-s / t-z. T-5.7
    re-measures and T-5.9 confirms the >=400 line cut budget here.
    """
    actual = _total_skill_lines()
    target = BASELINE_LINES - TARGET_REDUCTION
    assert actual <= target, (
        f"Combined SKILL.md line count {actual} exceeds spec-106 G-5 target "
        f"of {target} (baseline {BASELINE_LINES} minus >={TARGET_REDUCTION} "
        "cuts). Phase 5 sweep must remove restatement of CLAUDE.md Don't "
        "rules without weakening any required contract section."
    )
