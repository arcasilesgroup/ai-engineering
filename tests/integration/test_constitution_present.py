"""RED-phase test for spec-110 G-1 — CONSTITUTION.md presence and structure.

Spec acceptance criterion (G-1):
    CONSTITUTION.md exists in root del proyecto con 10 artículos
    numerados (I-X) generados vía ``/ai-constitution``. Verificable por
    ``tests/integration/test_constitution_present.py::test_constitution_has_all_articles``
    que valida presencia de cada Article I-X y que cada uno tenga al
    menos un ``1.`` numbered rule.

Status: RED (CONSTITUTION.md does not yet exist at repo root). The
``/ai-constitution`` skill produces the document in a subsequent task.
This test deliberately fails now to drive the GREEN phase.
"""

from __future__ import annotations

import re
from pathlib import Path

# Repo root: tests/integration/<this file> → up 3 levels.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONSTITUTION_PATH = REPO_ROOT / "CONSTITUTION.md"

ARTICLE_HEADING_RE = re.compile(
    r"^## Article (I|II|III|IV|V|VI|VII|VIII|IX|X) —",
    re.MULTILINE,
)
EXPECTED_ARTICLES = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")


def test_constitution_has_all_articles() -> None:
    """CONSTITUTION.md exists at repo root with all 10 articles I-X.

    Asserts:
    1. ``CONSTITUTION.md`` is present at the repository root.
    2. Each of the 10 articles (I-X) appears as a level-2 heading
       matching ``^## Article (I|II|...|X) —`` (em-dash, not hyphen).
    3. Exactly 10 article headings are matched (no duplicates, no extras).
    """
    assert CONSTITUTION_PATH.is_file(), (
        f"CONSTITUTION.md must exist at repo root: {CONSTITUTION_PATH}. "
        "Generate it via /ai-constitution per spec-110 G-1."
    )

    content = CONSTITUTION_PATH.read_text(encoding="utf-8")
    matched_articles = ARTICLE_HEADING_RE.findall(content)

    assert len(matched_articles) == 10, (
        f"CONSTITUTION.md must contain exactly 10 article headings "
        f"(pattern '^## Article (I|II|...|X) —'). "
        f"Found {len(matched_articles)}: {matched_articles}"
    )

    missing = [roman for roman in EXPECTED_ARTICLES if roman not in matched_articles]
    assert not missing, (
        f"CONSTITUTION.md is missing article headings for: {missing}. "
        f"Expected all of {list(EXPECTED_ARTICLES)}; found {matched_articles}."
    )
