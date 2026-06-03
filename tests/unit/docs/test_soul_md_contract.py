"""SOUL.md content contract (spec-164 D-164-08 / D-164-09)."""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SOUL_MD = REPO_ROOT / "SOUL.md"

FORBIDDEN_TOKENS = ("Claude", "Anthropic", "principal hierarchy")
PII_PATTERNS = (
    r"/Users/[a-z][a-z0-9_-]+/",
    r"/home/(?!runner/)[a-z][a-z0-9_-]+/",
    r"C:\\Users\\[A-Za-z][A-Za-z0-9_-]+\\",
)
REQUIRED = (
    "Pragmatic Helpfulness",
    "Honest & Direct",
    "Collaborative Partner",
    "Learn & Grow",
    "judgment layer",
)


@pytest.mark.unit
def test_soul_md_exists() -> None:
    assert SOUL_MD.exists(), "SOUL.md missing at repo root (D-164-04)"


@pytest.mark.unit
def test_soul_md_headers_ascii_no_emoji() -> None:
    """D-164-09: value headers are ASCII (no emoji glyphs)."""
    for lineno, line in enumerate(SOUL_MD.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            try:
                line.encode("ascii")
            except UnicodeEncodeError as exc:
                raise AssertionError(f"SOUL.md:{lineno} non-ASCII header: {line!r}") from exc


@pytest.mark.unit
def test_soul_md_model_agnostic() -> None:
    """D-164-08: no Claude/Anthropic-specific framing (multi-IDE doc)."""
    text = SOUL_MD.read_text(encoding="utf-8")
    for token in FORBIDDEN_TOKENS:
        assert token not in text, f"SOUL.md forbidden token: {token!r}"


@pytest.mark.unit
def test_soul_md_anonymous() -> None:
    text = SOUL_MD.read_text(encoding="utf-8")
    for pattern in PII_PATTERNS:
        assert re.search(pattern, text) is None, f"SOUL.md PII pattern: {pattern!r}"


@pytest.mark.unit
def test_soul_md_carries_the_four_values() -> None:
    text = SOUL_MD.read_text(encoding="utf-8")
    for needle in REQUIRED:
        assert needle in text, f"SOUL.md missing required content: {needle!r}"


@pytest.mark.unit
def test_soul_md_line_cap() -> None:
    """Loaded every session via §0 Bootstrap — stays <=1 page."""
    n = len(SOUL_MD.read_text(encoding="utf-8").splitlines())
    assert n <= 80, f"SOUL.md exceeds 80-line cap; got {n}"
