"""Phase 5 RED: post-cleanup line-budget contract for 47 SKILL.md files (spec-106 G-5).

Asserts that the restatement-cleanup mechanical sweep removes >=400 lines
across ``.claude/skills/ai-*/SKILL.md`` without weakening contract content
(the sweep targets only restatements of CLAUDE.md Don't rules / framework
conventions per spec-106 D-106-05). The exact baseline is captured in
Phase 5 T-5.1 via ``wc -l .claude/skills/ai-*/SKILL.md`` and recorded as
``BASELINE_LINES`` below.

Marked ``spec_106_red``: excluded from the default CI run until Phase 5
T-5.1 measures the baseline and the sweep delivers the >=400 line drop.
T-5.10 unmarks this file once the GREEN budget is met.

TDD CONSTRAINT: this file is IMMUTABLE once Phase 5 T-5.1 records the
baseline -- BASELINE_LINES, the cut target, and the assertion must NOT be
edited downward to make implementation easier. Skill markdown is the
load-bearing surface for non-Claude IDEs (Codex/Gemini do not auto-load
CLAUDE.md), so the line-budget contract guards genuine adoption friction.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

# Phase 5 T-5.1 contract: capture `wc -l .claude/skills/ai-*/SKILL.md` total
# at sweep start and replace this placeholder. Until then the constant is
# `None` so the deferred-import guard fires inside the test body.
BASELINE_LINES: int | None = None
TARGET_REDUCTION = 400


def _total_skill_lines() -> int:
    """Sum line counts across every .claude/skills/ai-*/SKILL.md file."""
    return sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in SKILLS_DIR.glob("ai-*/SKILL.md")
    )


@pytest.mark.spec_106_red
def test_post_cleanup_total_lines_under_baseline_minus_400() -> None:
    """Sweep must drop >=400 lines net across the 47 SKILL.md files.

    Phase 5 T-5.1 records ``BASELINE_LINES`` from the pre-sweep snapshot.
    Phase 5 T-5.3..T-5.6 sweep batches a-d / e-l / m-s / t-z. T-5.7
    re-measures and T-5.9 confirms the >=400 line cut budget here.
    """
    if BASELINE_LINES is None:
        raise NotImplementedError(
            "spec-106 Phase 5 T-5.1 must record BASELINE_LINES (current "
            "total of `wc -l .claude/skills/ai-*/SKILL.md`). T-4.6 ships "
            "this file as a RED skeleton; the constant lands in Phase 5."
        )
    actual = _total_skill_lines()
    target = BASELINE_LINES - TARGET_REDUCTION
    assert actual <= target, (
        f"Combined SKILL.md line count {actual} exceeds spec-106 G-5 target "
        f"of {target} (baseline {BASELINE_LINES} minus >={TARGET_REDUCTION} "
        "cuts). Phase 5 sweep must remove restatement of CLAUDE.md Don't "
        "rules without weakening any required contract section."
    )
