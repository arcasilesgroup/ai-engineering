"""C# adapter fixture (sub-008 T-8.10.cs)."""

from __future__ import annotations

from pathlib import Path

import pytest

_ADAPTER = Path(__file__).resolve().parents[2] / ".ai-engineering" / "adapters" / "csharp"


def test_conventions_names_dotnet_format() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "dotnet format" in text


def test_conventions_names_nullable_reference_types() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "nullable" in text


def test_tdd_harness_names_xunit() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "xunit" in text


def test_tdd_harness_names_inlinedata() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "inlinedata" in text or "[theory]" in text


def test_security_floor_names_iconfiguration() -> None:
    text = (_ADAPTER / "security_floor.md").read_text(encoding="utf-8").lower()
    assert "iconfiguration" in text


def test_security_floor_names_vulnerable_check() -> None:
    text = (_ADAPTER / "security_floor.md").read_text(encoding="utf-8").lower()
    assert "vulnerable" in text


def test_examples_count_minimum_two() -> None:
    examples = sorted((_ADAPTER / "examples").glob("*.md"))
    assert len(examples) >= 2


@pytest.mark.parametrize("name", ["minimal-api.md", "record-test.md"])
def test_canonical_examples_present(name: str) -> None:
    assert (_ADAPTER / "examples" / name).is_file()


def test_conventions_source_header_pins_actual_sha() -> None:
    first_line = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").splitlines()[0]
    for marker in ("TBD", "PLACEHOLDER", "FIXME", "XXX"):
        assert marker not in first_line
