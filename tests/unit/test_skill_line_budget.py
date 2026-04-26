"""SKILL.md line-budget assertions for spec-104 Phase 7 verbosity reduction.

Spec: spec-104 D-104-07 (verbosity reduction conservadora) and G-6 (≥30% / ≥160
lines net reduction across the three skill files in scope).

Pre-spec-104 baseline (verified 2026-04-26):

    .claude/skills/ai-commit/SKILL.md          126 lines
    .claude/skills/ai-pr/SKILL.md              221 lines
    .claude/skills/ai-pr/handlers/watch.md     185 lines
    ----------------------------------------------------
    combined                                   532 lines

Phase 7 targets (cuts validated against D-104-07 surgical edits + surrounding
boilerplate trim) require:

    ai-commit/SKILL.md      <=115 lines  (>=11 line cut)
    ai-pr/SKILL.md          <=180 lines  (>=41 line cut)
    ai-pr/handlers/watch.md <=175 lines  (>=10 line cut)
    combined                <=372 lines  (>=160 line cut total per G-6)

These tests are RED today (current line counts exceed every target). After the
Phase 7 cuts they go GREEN and act as a regression guard against future drift.

TDD CONSTRAINT: this file is IMMUTABLE once written -- test names, targets and
asserts must NOT be edited to make implementation easier. Skill markdown is the
load-bearing surface for non-Claude IDEs (Codex/Gemini do not auto-load
CLAUDE.md), so the line-budget contract guards genuine adoption friction.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

AI_COMMIT_SKILL = REPO_ROOT / ".claude" / "skills" / "ai-commit" / "SKILL.md"
AI_PR_SKILL = REPO_ROOT / ".claude" / "skills" / "ai-pr" / "SKILL.md"
WATCH_HANDLER = REPO_ROOT / ".claude" / "skills" / "ai-pr" / "handlers" / "watch.md"


def _line_count(path: Path) -> int:
    """Count lines the way `wc -l` does on the canonical skill files.

    Uses ``splitlines()`` so a trailing newline does not inflate the count and
    so the assertion matches what humans see when running ``wc -l`` locally.
    """
    return len(path.read_text(encoding="utf-8").splitlines())


def test_ai_commit_skill_under_115_lines() -> None:
    """ai-commit/SKILL.md must shrink from 126 to <=115 lines (Phase 7).

    Conservative cut target: D-104-07 removes the 10-line Common Mistakes
    duplicate (lines 110-119) and replaces it with a one-line pointer to
    CLAUDE.md, plus surrounding boilerplate trim. Net >=11 line reduction.
    """
    assert AI_COMMIT_SKILL.exists(), f"missing skill file: {AI_COMMIT_SKILL}"
    actual = _line_count(AI_COMMIT_SKILL)
    assert actual <= 115, (
        f"ai-commit/SKILL.md line count {actual} exceeds Phase 7 target of 115. "
        f"Spec-104 D-104-07 requires removing the duplicated Common Mistakes "
        f"block (vs CLAUDE.md Don't section) and trimming orphan boilerplate."
    )


def test_ai_pr_skill_under_180_lines() -> None:
    """ai-pr/SKILL.md must shrink from 221 to <=180 lines (Phase 7).

    Cuts mandated by D-104-07: stack-detection block (lines 53-63, -11), Common
    Mistakes anti-patterns consolidated into watch.md (lines 199-205, -22), and
    surrounding boilerplate trim. Net >=41 line reduction.
    """
    assert AI_PR_SKILL.exists(), f"missing skill file: {AI_PR_SKILL}"
    actual = _line_count(AI_PR_SKILL)
    assert actual <= 180, (
        f"ai-pr/SKILL.md line count {actual} exceeds Phase 7 target of 180. "
        f"Spec-104 D-104-07 requires removing the stack-detection duplicate "
        f"(now lives in contexts/languages/) and consolidating anti-patterns "
        f"into handlers/watch.md to drop >=41 lines."
    )


def test_watch_md_under_175_lines() -> None:
    """ai-pr/handlers/watch.md must shrink from 185 to <=175 lines (Phase 7).

    The Behavioral negatives + Anti-patterns sections currently overlap with
    ai-pr/SKILL.md; consolidating them in a single canonical location plus
    boilerplate trim yields >=10 line reduction without losing contract content.
    """
    assert WATCH_HANDLER.exists(), f"missing skill file: {WATCH_HANDLER}"
    actual = _line_count(WATCH_HANDLER)
    assert actual <= 175, (
        f"handlers/watch.md line count {actual} exceeds Phase 7 target of 175. "
        f"Spec-104 D-104-07 consolidates the duplicated behavioral-negatives "
        f"section here, but the trim must still produce a net >=10 line drop."
    )


def test_combined_skill_lines_under_372() -> None:
    """Combined budget enforces G-6: 532 baseline - >=160 cuts -> <=372 lines.

    Acts as a global ceiling so individual files cannot trade lines among
    themselves to hide regressions: the combined ceiling matches the spec-level
    goal G-6 (>=30% net reduction across the three files in scope).
    """
    for path in (AI_COMMIT_SKILL, AI_PR_SKILL, WATCH_HANDLER):
        assert path.exists(), f"missing skill file: {path}"
    combined = _line_count(AI_COMMIT_SKILL) + _line_count(AI_PR_SKILL) + _line_count(WATCH_HANDLER)
    assert combined <= 372, (
        f"Combined skill line count {combined} exceeds spec-104 G-6 target of "
        f"372 (baseline 532 minus >=160 cuts). Phase 7 must remove duplicated "
        f"content across ai-commit/SKILL.md, ai-pr/SKILL.md, and "
        f"handlers/watch.md without weakening any required contract section."
    )
