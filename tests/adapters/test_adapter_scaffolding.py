"""Adapter scaffolding contract test (sub-008 T-8.1).

Each of the 7 supported stacks under ``.ai-engineering/adapters/`` must
ship four artifacts the ``ai-build`` agent loads at runtime:

1. ``conventions.md`` opening with a source-revision pin so we can detect
   drift against the upstream ``contexts/languages/<stack>.md`` source.
2. ``tdd_harness.md`` describing the test runner and TDD pattern (≥30
   lines so it has substantive content, not a placeholder).
3. ``security_floor.md`` describing the language-specific security
   minimum (≥30 lines, same rationale).
4. ``examples/`` with at least two ``*.md`` files showing realistic
   patterns the agent can lift into prose.

The header pin format is locked: ``<!-- source: contexts/languages/<stack>.md @ <sha> -->``.
``<sha>`` is asserted to match a 40-char hex SHA, not a placeholder.

This test must FAIL before any adapter is written (RED) and turn GREEN
once all 7 stacks ship the four artifacts.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADAPTERS_ROOT = _REPO_ROOT / ".ai-engineering" / "adapters"

_STACKS: tuple[str, ...] = (
    "typescript",
    "python",
    "go",
    "rust",
    "swift",
    "csharp",
    "kotlin",
)

# Source-pin format: <!-- source: contexts/languages/<stack>.md @ <40-hex sha> -->
_HEADER_RE = re.compile(
    r"<!--\s*source:\s*contexts/languages/(?P<stack>[a-z]+)\.md\s*@\s*(?P<sha>[0-9a-f]{40})\s*-->"
)


@pytest.mark.parametrize("stack", _STACKS)
def test_adapter_directory_exists(stack: str) -> None:
    """Each supported stack has its own adapter directory."""
    stack_dir = _ADAPTERS_ROOT / stack
    assert stack_dir.is_dir(), (
        f"adapter directory missing: {stack_dir.relative_to(_REPO_ROOT)}. "
        f"Expected per sub-008 D-127-06 — 7 stacks × adapter prose."
    )


@pytest.mark.parametrize("stack", _STACKS)
def test_conventions_has_source_pin(stack: str) -> None:
    """``conventions.md`` opens with the canonical source-revision header."""
    conventions = _ADAPTERS_ROOT / stack / "conventions.md"
    assert conventions.is_file(), f"missing: {conventions.relative_to(_REPO_ROOT)}"
    first_line = conventions.read_text(encoding="utf-8").splitlines()[0]
    match = _HEADER_RE.match(first_line)
    assert match is not None, (
        f"{conventions.relative_to(_REPO_ROOT)} first line must be "
        f"'<!-- source: contexts/languages/{stack}.md @ <sha> -->'; got: {first_line!r}"
    )
    assert match.group("stack") == stack, (
        f"source pin stack mismatch in {conventions.relative_to(_REPO_ROOT)}: "
        f"expected {stack}, got {match.group('stack')}"
    )


@pytest.mark.parametrize("stack", _STACKS)
def test_tdd_harness_substantive(stack: str) -> None:
    """``tdd_harness.md`` has substantive content (≥30 non-blank lines)."""
    harness = _ADAPTERS_ROOT / stack / "tdd_harness.md"
    assert harness.is_file(), f"missing: {harness.relative_to(_REPO_ROOT)}"
    non_blank = [ln for ln in harness.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(non_blank) >= 30, (
        f"{harness.relative_to(_REPO_ROOT)} too short: {len(non_blank)} non-blank lines, "
        f"required ≥30. Adapter prose must teach the runtime, not just name it."
    )


@pytest.mark.parametrize("stack", _STACKS)
def test_security_floor_substantive(stack: str) -> None:
    """``security_floor.md`` has substantive content (≥30 non-blank lines)."""
    floor = _ADAPTERS_ROOT / stack / "security_floor.md"
    assert floor.is_file(), f"missing: {floor.relative_to(_REPO_ROOT)}"
    non_blank = [ln for ln in floor.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(non_blank) >= 30, (
        f"{floor.relative_to(_REPO_ROOT)} too short: {len(non_blank)} non-blank lines, "
        f"required ≥30."
    )


@pytest.mark.parametrize("stack", _STACKS)
def test_examples_has_minimum_two(stack: str) -> None:
    """``examples/`` ships at least two markdown files."""
    examples_dir = _ADAPTERS_ROOT / stack / "examples"
    assert examples_dir.is_dir(), (
        f"examples directory missing: {examples_dir.relative_to(_REPO_ROOT)}"
    )
    examples = sorted(examples_dir.glob("*.md"))
    assert len(examples) >= 2, (
        f"{examples_dir.relative_to(_REPO_ROOT)} has {len(examples)} examples, "
        f"required ≥2 for representative coverage."
    )


def test_seven_stacks_total() -> None:
    """Vacuous-pass guard: 7 supported stacks materialised on disk."""
    assert _ADAPTERS_ROOT.is_dir(), f"adapters root missing: {_ADAPTERS_ROOT}"
    on_disk = {p.name for p in _ADAPTERS_ROOT.iterdir() if p.is_dir()}
    expected = set(_STACKS)
    assert expected.issubset(on_disk), (
        f"missing adapter dirs: {sorted(expected - on_disk)}. D-127-06 requires all 7 stacks."
    )
