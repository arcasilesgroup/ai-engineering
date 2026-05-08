"""Kotlin adapter fixture (sub-008 T-8.10.kt)."""

from __future__ import annotations

from pathlib import Path

import pytest

_ADAPTER = Path(__file__).resolve().parents[2] / ".ai-engineering" / "adapters" / "kotlin"


def test_conventions_names_ktlint() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "ktlint" in text


def test_conventions_names_detekt() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "detekt" in text


def test_conventions_names_data_class() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "data class" in text


def test_tdd_harness_names_junit5() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "junit 5" in text or "junit5" in text or "junit.jupiter" in text


def test_tdd_harness_names_kotest() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "kotest" in text


def test_security_floor_names_keystore() -> None:
    text = (_ADAPTER / "security_floor.md").read_text(encoding="utf-8").lower()
    assert "keystore" in text


def test_security_floor_names_masvs() -> None:
    text = (_ADAPTER / "security_floor.md").read_text(encoding="utf-8").lower()
    assert "masvs" in text or "owasp" in text


def test_examples_count_minimum_two() -> None:
    examples = sorted((_ADAPTER / "examples").glob("*.md"))
    assert len(examples) >= 2


@pytest.mark.parametrize("name", ["sealed-class.md", "compose-vm.md"])
def test_canonical_examples_present(name: str) -> None:
    assert (_ADAPTER / "examples" / name).is_file()


def test_conventions_source_header_pins_actual_sha() -> None:
    first_line = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").splitlines()[0]
    for marker in ("TBD", "PLACEHOLDER", "FIXME", "XXX"):
        assert marker not in first_line
