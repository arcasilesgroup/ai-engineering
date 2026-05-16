"""Tests for stack overrides inventory (spec-133 D-133-12)."""

from __future__ import annotations

from pathlib import Path

import pytest

_OVERRIDES = Path(".ai-engineering/overrides")

_EXPECTED_STACKS = {
    "python",
    "typescript",
    "go",
    "rust",
    "java",
    "csharp",
    "kotlin",
    "swift",
    "php",
    "ruby",
    "flutter",
    "react-native",
}
_REQUIRED_FILES = {"conventions.md", "security_floor.md", "tdd_harness.md"}


def test_overrides_has_all_12_stacks() -> None:
    actual = {p.name for p in _OVERRIDES.iterdir() if p.is_dir() and not p.name.startswith("_")}
    assert actual == _EXPECTED_STACKS, (
        f"Expected 12 stacks; got {len(actual)}. Diff: "
        f"missing={_EXPECTED_STACKS - actual}, extra={actual - _EXPECTED_STACKS}"
    )


@pytest.mark.parametrize("stack", sorted(_EXPECTED_STACKS))
def test_each_stack_has_required_files(stack: str) -> None:
    stack_dir = _OVERRIDES / stack
    for required in _REQUIRED_FILES:
        assert (stack_dir / required).is_file(), f"missing {stack}/{required}"


def test_shared_sql_md_exists() -> None:
    assert (_OVERRIDES / "_shared" / "sql.md").is_file()


def test_t1_stacks_present() -> None:
    """T1 stacks (8): python, typescript, go, rust, java, csharp, kotlin, swift."""
    t1 = {"python", "typescript", "go", "rust", "java", "csharp", "kotlin", "swift"}
    for stack in t1:
        assert (_OVERRIDES / stack).is_dir(), f"T1 stack {stack} missing"


def test_t2_stacks_present() -> None:
    """T2 stacks (4): php, ruby, flutter, react-native."""
    t2 = {"php", "ruby", "flutter", "react-native"}
    for stack in t2:
        assert (_OVERRIDES / stack).is_dir(), f"T2 stack {stack} missing"


def test_excluded_stacks_absent() -> None:
    """Per non-goals: dart, javascript, elixir not present as standalone."""
    for excluded in ("dart", "javascript", "elixir"):
        assert not (_OVERRIDES / excluded).is_dir(), f"excluded stack {excluded} present"
