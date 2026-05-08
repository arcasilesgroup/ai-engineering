"""Swift adapter fixture (sub-008 T-8.10.sw)."""

from __future__ import annotations

from pathlib import Path

import pytest

_ADAPTER = Path(__file__).resolve().parents[2] / ".ai-engineering" / "adapters" / "swift"


def test_conventions_names_swiftlint() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "swiftlint" in text


def test_conventions_names_swiftpm() -> None:
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert "swiftpm" in text or "swift build" in text


def test_tdd_harness_names_xctest() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "xctest" in text


def test_tdd_harness_names_swift_test() -> None:
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "swift test" in text


def test_security_floor_names_keychain() -> None:
    text = (_ADAPTER / "security_floor.md").read_text(encoding="utf-8").lower()
    assert "keychain" in text


def test_security_floor_names_ats() -> None:
    text = (_ADAPTER / "security_floor.md").read_text(encoding="utf-8").lower()
    assert "ats" in text or "app transport security" in text


def test_examples_count_minimum_two() -> None:
    examples = sorted((_ADAPTER / "examples").glob("*.md"))
    assert len(examples) >= 2


@pytest.mark.parametrize("name", ["value-type-xctest.md", "swiftui-view.md"])
def test_canonical_examples_present(name: str) -> None:
    assert (_ADAPTER / "examples" / name).is_file()


def test_conventions_source_header_pins_actual_sha() -> None:
    first_line = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").splitlines()[0]
    for marker in ("TBD", "PLACEHOLDER", "FIXME", "XXX"):
        assert marker not in first_line
