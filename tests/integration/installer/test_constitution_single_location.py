"""CI invariant: only ONE CONSTITUTION.md ships to a consumer install.

spec-132 D-132-14: the source-repo `.ai-engineering/CONSTITUTION.md`
stub and the template `.ai-engineering/CONSTITUTION.md` stub are
both deleted. The installer ships the project-charter template to the
consumer root only -- never to `.ai-engineering/`.

This test exercises the installer copy path directly (no subprocess
fork). It calls ``copy_project_templates`` on a tmp_path target and
asserts the post-copy filesystem shape: exactly one
``CONSTITUTION.md`` (at the consumer root), zero copies under
``.ai-engineering/``.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.installer.templates import copy_project_templates


def test_only_root_constitution_ships(tmp_path: Path) -> None:
    """spec-132 D-132-14: a fresh install produces ONE CONSTITUTION.md."""
    target = tmp_path / "consumer"
    target.mkdir()

    copy_project_templates(target, surfaces=["claude-code"], vcs_provider="github")

    matches = sorted(target.rglob("CONSTITUTION.md"))
    assert len(matches) == 1, (
        "Expected exactly one CONSTITUTION.md per install; found:\n"
        + "\n".join(str(p.relative_to(target)) for p in matches)
    )
    assert matches[0] == target / "CONSTITUTION.md", (
        f"CONSTITUTION.md should live at the root, found at {matches[0]}"
    )


def test_no_ai_engineering_constitution_stub(tmp_path: Path) -> None:
    """spec-132 D-132-14: no stub under .ai-engineering/."""
    target = tmp_path / "consumer"
    target.mkdir()

    copy_project_templates(target, surfaces=["claude-code"], vcs_provider="github")

    stub = target / ".ai-engineering" / "CONSTITUTION.md"
    assert not stub.exists(), (
        "Legacy .ai-engineering/CONSTITUTION.md stub must not be shipped (spec-132 D-132-14)"
    )
