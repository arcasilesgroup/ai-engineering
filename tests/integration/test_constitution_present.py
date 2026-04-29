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


def test_each_article_has_at_least_one_numbered_rule() -> None:
    """Each Article body in CONSTITUTION.md contains at least one ``1.`` rule.

    Asserts:
    1. ``CONSTITUTION.md`` is present at the repository root.
    2. For every article heading ``^## Article (I|...|X) —`` matched, the
       article body (text from that heading up to the next ``## Article``
       heading or end of file) contains at least one line starting with
       the literal numbered-rule marker ``1.`` (i.e. ``^1\\.`` per line).
    """
    assert CONSTITUTION_PATH.is_file(), (
        f"CONSTITUTION.md must exist at repo root: {CONSTITUTION_PATH}. "
        "Generate it via /ai-constitution per spec-110 G-1."
    )

    content = CONSTITUTION_PATH.read_text(encoding="utf-8")
    numbered_rule_re = re.compile(r"^1\.", re.MULTILINE)

    # Collect (roman, start, end) spans for each article body so we can
    # check rules on a per-article basis.
    matches = list(ARTICLE_HEADING_RE.finditer(content))
    assert matches, (
        "CONSTITUTION.md does not contain any '## Article (I|...|X) —' "
        "headings; cannot validate numbered rules per article."
    )

    articles_without_rule: list[str] = []
    for index, match in enumerate(matches):
        roman = match.group(1)
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        body = content[body_start:body_end]
        if not numbered_rule_re.search(body):
            articles_without_rule.append(roman)

    assert not articles_without_rule, (
        "Each Article body in CONSTITUTION.md must contain at least one "
        f"numbered rule starting with '1.'. Articles missing a '1.' rule: "
        f"{articles_without_rule}."
    )
