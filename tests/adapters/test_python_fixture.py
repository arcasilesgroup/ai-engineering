"""Python adapter fixture (sub-008 T-8.10.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

_ADAPTER = Path(__file__).resolve().parents[2] / ".ai-engineering" / "adapters" / "python"


def test_conventions_names_ruff() -> None:
    """`ruff` is the canonical linter/formatter."""
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "ruff" in text, "Python conventions must require ruff."


def test_conventions_names_mypy_or_pyright() -> None:
    """A type checker is named."""
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert ("mypy" in text) or ("pyright" in text), "Python conventions must name a type checker."


def test_tdd_harness_names_pytest() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "pytest" in text


def test_security_floor_names_pydantic_or_validator() -> None:
    text = (_ADAPTER / "security_floor.md").read_text(encoding="utf-8").lower()
    assert ("pydantic" in text) or ("attrs" in text)


def test_examples_count_minimum_two() -> None:
    examples = sorted((_ADAPTER / "examples").glob("*.md"))
    assert len(examples) >= 2


@pytest.mark.parametrize("name", ["django-view.md", "fastapi-endpoint.md"])
def test_canonical_examples_present(name: str) -> None:
    assert (_ADAPTER / "examples" / name).is_file()


def test_conventions_source_header_pins_actual_sha() -> None:
    first_line = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").splitlines()[0]
    for marker in ("TBD", "PLACEHOLDER", "FIXME", "XXX"):
        assert marker not in first_line
