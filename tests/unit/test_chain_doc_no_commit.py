"""Regression: canonical chain doc reads
``/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`` and never references
``/ai-commit`` inside the canonical chain string (spec-131 D-131-07).

Files asserted:

* ``src/ai_engineering/templates/project/CANONICAL.md`` (canonical template)
* ``AGENTS.md``
* ``CLAUDE.md``
* ``.github/copilot-instructions.md``

CANONICAL.md is the source-of-truth template; if Wave 1 has not landed it,
the assertion against CANONICAL.md is logged but skipped (do not fail the
suite). The active mirrors must always pass.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CANONICAL = REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / "CANONICAL.md"
MIRRORS = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / ".github" / "copilot-instructions.md",
)

CHAIN_EXPECTED = "/ai-brainstorm → /ai-plan → /ai-build → /ai-pr"
# Old chain string forbidden in the canonical chain block.
CHAIN_FORBIDDEN_RE = re.compile(
    r"/ai-build\s*→\s*/ai-verify\s*→\s*/ai-review\s*→\s*/ai-commit\s*→\s*/ai-pr"
)


def _has_expected_chain(text: str) -> bool:
    return CHAIN_EXPECTED in text


def _has_forbidden_chain(text: str) -> bool:
    return bool(CHAIN_FORBIDDEN_RE.search(text))


@pytest.mark.parametrize("path", MIRRORS, ids=[p.name for p in MIRRORS])
def test_mirror_contains_expected_chain(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"Mirror not found at {path}")
    text = path.read_text(encoding="utf-8")
    assert _has_expected_chain(text), (
        f"{path.relative_to(REPO_ROOT)} must contain the canonical chain "
        f"'{CHAIN_EXPECTED}' (spec-131 D-131-07)."
    )


@pytest.mark.parametrize("path", MIRRORS, ids=[p.name for p in MIRRORS])
def test_mirror_omits_old_chain_with_commit(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"Mirror not found at {path}")
    text = path.read_text(encoding="utf-8")
    assert not _has_forbidden_chain(text), (
        f"{path.relative_to(REPO_ROOT)} must not embed the legacy chain "
        f"containing /ai-commit (spec-131 D-131-07)."
    )


def test_canonical_template_contains_expected_chain() -> None:
    if not CANONICAL.exists():
        pytest.skip(
            "CANONICAL.md template not found -- sub-001 wave 1 has not "
            "materialised it yet. Mirror assertions still apply."
        )
    text = CANONICAL.read_text(encoding="utf-8")
    assert _has_expected_chain(text), (
        "CANONICAL.md must contain the canonical chain string (spec-131 D-131-07)."
    )
    assert not _has_forbidden_chain(text), (
        "CANONICAL.md must not embed the legacy chain with /ai-commit."
    )
