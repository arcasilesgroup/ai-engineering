"""RED skeleton for spec-105 Phase 7 -- skill forward-refs resolved.

Covers G-13: ``/ai-commit`` and ``/ai-pr`` SKILL.md and handler files no
longer reference ``ai-eng risk accept-all (spec-105)`` as a forward
placeholder. After Phase 7 (T-7.5 / T-7.6 / T-7.7 / T-7.8) the
forward-ref text ``(spec-105)`` MUST be absent from every file under
``.claude/skills/ai-commit/`` and ``.claude/skills/ai-pr/``.

Status: RED -- the SKILL.md updates land in Phase 7.
Marker: ``@pytest.mark.spec_105_red`` -- excluded by default CI run.
Will be unmarked in Phase 7 (T-7.17).

Lesson: deferred filesystem walk inside the test function keeps pytest
collection green even when the skills directory is partially populated
during in-progress migrations.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.spec_105_red


_FORWARD_REF_NEEDLE = "(spec-105)"
_SKILL_DIRS = (
    ".claude/skills/ai-commit",
    ".claude/skills/ai-pr",
)


def _repo_root() -> Path:
    """Walk up from this test file to the repo root."""
    here = Path(__file__).resolve()
    # tests/unit/test_skill_forward_refs_resolved.py -> repo root is parent.parent.parent
    return here.parent.parent.parent


def test_no_forward_refs_in_ai_commit() -> None:
    """No file under .claude/skills/ai-commit/ contains ``(spec-105)``."""
    root = _repo_root()
    skill_dir = root / _SKILL_DIRS[0]
    if not skill_dir.exists():
        pytest.fail(f"missing skill directory: {skill_dir}")
    offenders: list[Path] = []
    for path in skill_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _FORWARD_REF_NEEDLE in text:
            offenders.append(path)
    assert offenders == [], (
        f"forward-ref {_FORWARD_REF_NEEDLE!r} still present in: "
        f"{[str(p.relative_to(root)) for p in offenders]}"
    )


def test_no_forward_refs_in_ai_pr() -> None:
    """No file under .claude/skills/ai-pr/ contains ``(spec-105)``."""
    root = _repo_root()
    skill_dir = root / _SKILL_DIRS[1]
    if not skill_dir.exists():
        pytest.fail(f"missing skill directory: {skill_dir}")
    offenders: list[Path] = []
    for path in skill_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _FORWARD_REF_NEEDLE in text:
            offenders.append(path)
    assert offenders == [], (
        f"forward-ref {_FORWARD_REF_NEEDLE!r} still present in: "
        f"{[str(p.relative_to(root)) for p in offenders]}"
    )
