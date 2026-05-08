"""Go adapter fixture (sub-008 T-8.10.go)."""

from __future__ import annotations

from pathlib import Path

import pytest

_ADAPTER = Path(__file__).resolve().parents[2] / ".ai-engineering" / "adapters" / "go"


def test_conventions_names_gofmt() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "gofmt" in text


def test_conventions_names_golangci() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "golangci-lint" in text


def test_tdd_harness_names_go_test() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "go test" in text


def test_tdd_harness_table_driven() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "table-driven" in text or "table driven" in text


def test_security_floor_names_govulncheck() -> None:
    text = (_ADAPTER / "security_floor.md").read_text(encoding="utf-8").lower()
    assert "govulncheck" in text


def test_examples_count_minimum_two() -> None:
    examples = sorted((_ADAPTER / "examples").glob("*.md"))
    assert len(examples) >= 2


@pytest.mark.parametrize("name", ["http-handler.md", "table-test.md"])
def test_canonical_examples_present(name: str) -> None:
    assert (_ADAPTER / "examples" / name).is_file()


def test_conventions_source_header_pins_actual_sha() -> None:
    first_line = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").splitlines()[0]
    for marker in ("TBD", "PLACEHOLDER", "FIXME", "XXX"):
        assert marker not in first_line
