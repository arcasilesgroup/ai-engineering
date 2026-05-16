"""Regression: the shared ``--consolidate-spec`` action is wired across
``/ai-repo-tidy``, ``/ai-pr``, and ``/ai-brainstorm`` (spec-131 sub-002,
Phase F).

The shared handler lives at
``.claude/skills/_shared/consolidate-spec.md`` and is the single source of
truth for the action. The three callers reference the handler and accept
the ``--consolidate-spec`` flag.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SHARED_HANDLER = REPO_ROOT / ".claude" / "skills" / "_shared" / "consolidate-spec.md"
CALLER_SKILLS = (
    REPO_ROOT / ".claude" / "skills" / "ai-repo-tidy" / "SKILL.md",
    REPO_ROOT / ".claude" / "skills" / "ai-pr" / "SKILL.md",
    REPO_ROOT / ".claude" / "skills" / "ai-brainstorm" / "SKILL.md",
)


def test_shared_handler_exists() -> None:
    assert SHARED_HANDLER.exists(), (
        "Shared handler at .claude/skills/_shared/consolidate-spec.md must "
        "exist (spec-131 sub-002 Phase F)."
    )


def test_shared_handler_declares_purpose_and_callers() -> None:
    if not SHARED_HANDLER.exists():
        pytest.skip("Shared handler missing -- covered by test_shared_handler_exists.")
    text = SHARED_HANDLER.read_text()
    assert "--consolidate-spec" in text, "Handler must document the --consolidate-spec CLI surface."
    assert "spec_lifecycle.py" in text, (
        "Handler must reference the load-bearing spec_lifecycle.py entry point."
    )
    # Must list all three callers.
    for caller in ("ai-repo-tidy", "ai-pr", "ai-brainstorm"):
        assert caller in text, f"Handler must list {caller} as a caller."


@pytest.mark.parametrize("path", CALLER_SKILLS, ids=[p.parent.name for p in CALLER_SKILLS])
def test_caller_references_shared_handler(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"Caller skill not found at {path}")
    text = path.read_text()
    assert "--consolidate-spec" in text, (
        f"{path.parent.name} must wire the --consolidate-spec flag (spec-131 sub-002)."
    )
    assert "_shared/consolidate-spec.md" in text, (
        f"{path.parent.name} must reference _shared/consolidate-spec.md (DRY §10.4)."
    )
