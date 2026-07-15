"""Coarse top-level-name-presence floor for the CLI reference doc.

spec-183 Goal 4 / R-183-04: the canonical ``cli-reference.md`` must document
every non-hidden top-level command/group registered on the ``ai-eng`` app so a
human can trust it as the authoritative surface index. This is a lightweight,
deterministic floor: it only asserts that each visible top-level *name* appears
somewhere in the doc (as a whole word). It intentionally does not enforce
subcommand-level completeness -- that would be brittle -- but it guards against
the doc silently going stale when top-level verbs are added or removed.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer

from ai_engineering.cli_factory import create_app

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CANONICAL = _REPO_ROOT / ".ai-engineering" / "reference" / "cli-reference.md"
_TEMPLATE = (
    _REPO_ROOT
    / "src"
    / "ai_engineering"
    / "templates"
    / ".ai-engineering"
    / "reference"
    / "cli-reference.md"
)


def _visible_top_level_names() -> list[str]:
    """Return non-hidden top-level command/group names on the root app."""
    command = typer.main.get_command(create_app())
    commands = getattr(command, "commands", {})
    return sorted(name for name, sub in commands.items() if not getattr(sub, "hidden", False))


def _missing_names(doc_text: str, names: list[str]) -> list[str]:
    return [name for name in names if not re.search(rf"\b{re.escape(name)}\b", doc_text)]


def test_canonical_documents_every_visible_top_level_name() -> None:
    names = _visible_top_level_names()
    assert names, "expected at least one visible top-level command"
    text = _CANONICAL.read_text(encoding="utf-8")
    missing = _missing_names(text, names)
    assert not missing, f"cli-reference.md is missing these visible top-level commands: {missing}"


def test_template_mirror_documents_every_visible_top_level_name() -> None:
    names = _visible_top_level_names()
    text = _TEMPLATE.read_text(encoding="utf-8")
    missing = _missing_names(text, names)
    assert not missing, (
        f"template cli-reference.md is missing these visible top-level commands: {missing}"
    )
