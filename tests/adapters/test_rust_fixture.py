"""Rust adapter fixture (sub-008 T-8.10.rs)."""

from __future__ import annotations

from pathlib import Path

import pytest

_ADAPTER = Path(__file__).resolve().parents[2] / ".ai-engineering" / "adapters" / "rust"


def test_conventions_names_clippy() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "clippy" in text


def test_conventions_names_cargo_fmt() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "cargo fmt" in text


def test_tdd_harness_names_cargo_test() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "cargo test" in text


def test_tdd_harness_cfg_test_pattern() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "cfg(test)" in text


def test_security_floor_names_cargo_audit() -> None:
    text = (_ADAPTER / "security_floor.md").read_text(encoding="utf-8").lower()
    assert "cargo audit" in text


def test_examples_count_minimum_two() -> None:
    examples = sorted((_ADAPTER / "examples").glob("*.md"))
    assert len(examples) >= 2


@pytest.mark.parametrize("name", ["result-fn.md", "trait-impl.md"])
def test_canonical_examples_present(name: str) -> None:
    assert (_ADAPTER / "examples" / name).is_file()


def test_conventions_source_header_pins_actual_sha() -> None:
    first_line = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").splitlines()[0]
    for marker in ("TBD", "PLACEHOLDER", "FIXME", "XXX"):
        assert marker not in first_line
