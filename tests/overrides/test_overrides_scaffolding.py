"""Overrides scaffolding contract test (spec-128 T-009 RED).

Each of the 7 supported stacks under ``.ai-engineering/overrides/`` must
ship the ``ai-build`` agent's runtime artifacts:

1. ``conventions.md`` opening with a source-revision pin so we can detect
   drift against an upstream canonical source.
2. ``tdd_harness.md`` describing the test runner and TDD pattern (≥30
   lines so it has substantive content, not a placeholder).
3. ``security_floor.md`` describing the language-specific security
   minimum (≥30 lines, same rationale).
4. ``examples/`` with at least two ``*.md`` files showing realistic
   patterns the agent can lift into prose.

Header pin format (post spec-128): ``<!-- source: <stack> overrides v<N> -->``.
The previous ``contexts/languages/<stack>.md`` source path is gone after
spec-128 D-128-03 (hard delete of training-redundant content).

This test starts RED:
- ``.ai-engineering/overrides/`` does not yet exist (still ``adapters/``).
- The header pin format references the deleted ``contexts/languages/`` path.

Turns GREEN once Phase 5 renames ``adapters/`` → ``overrides/`` (T-024)
and Phase 6 updates the source-pin headers (T-025).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OVERRIDES_ROOT = _REPO_ROOT / ".ai-engineering" / "overrides"

_STACKS: tuple[str, ...] = (
    "typescript",
    "python",
    "go",
    "rust",
    "swift",
    "csharp",
    "kotlin",
)

# spec-128 source-pin format: <!-- source: <stack> overrides v<N> -->
# (Replaces the old contexts/languages/<stack>.md @ <sha> pin since
# D-128-03 deletes that source.)
_HEADER_RE = re.compile(r"<!--\s*source:\s*(?P<stack>[a-z]+)\s+overrides\s+v(?P<version>\d+)\s*-->")


@pytest.mark.parametrize("stack", _STACKS)
def test_overrides_directory_exists(stack: str) -> None:
    """Each supported stack has its own overrides directory."""
    stack_dir = _OVERRIDES_ROOT / stack
    assert stack_dir.is_dir(), (
        f"overrides directory missing: {stack_dir.relative_to(_REPO_ROOT)}. "
        f"Expected per spec-128 D-128-09 - 7 stacks x project-specific deltas."
    )


@pytest.mark.parametrize("stack", _STACKS)
def test_conventions_has_source_pin(stack: str) -> None:
    """``conventions.md`` opens with the spec-128 source-revision header."""
    conventions = _OVERRIDES_ROOT / stack / "conventions.md"
    assert conventions.is_file(), f"missing: {conventions.relative_to(_REPO_ROOT)}"
    first_line = conventions.read_text(encoding="utf-8").splitlines()[0]
    match = _HEADER_RE.match(first_line)
    assert match is not None, (
        f"{conventions.relative_to(_REPO_ROOT)} first line must be "
        f"'<!-- source: {stack} overrides v<N> -->'; got: {first_line!r}"
    )
    assert match.group("stack") == stack, (
        f"source pin stack mismatch in {conventions.relative_to(_REPO_ROOT)}: "
        f"expected {stack}, got {match.group('stack')}"
    )


@pytest.mark.parametrize("stack", _STACKS)
def test_tdd_harness_substantive(stack: str) -> None:
    """``tdd_harness.md`` has substantive content (≥30 non-blank lines)."""
    harness = _OVERRIDES_ROOT / stack / "tdd_harness.md"
    assert harness.is_file(), f"missing: {harness.relative_to(_REPO_ROOT)}"
    non_blank = [ln for ln in harness.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(non_blank) >= 30, (
        f"{harness.relative_to(_REPO_ROOT)} too short: {len(non_blank)} non-blank lines, "
        f"required ≥30. Overrides prose must teach the runtime, not just name it."
    )


@pytest.mark.parametrize("stack", _STACKS)
def test_security_floor_substantive(stack: str) -> None:
    """``security_floor.md`` has substantive content (≥30 non-blank lines)."""
    floor = _OVERRIDES_ROOT / stack / "security_floor.md"
    assert floor.is_file(), f"missing: {floor.relative_to(_REPO_ROOT)}"
    non_blank = [ln for ln in floor.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(non_blank) >= 30, (
        f"{floor.relative_to(_REPO_ROOT)} too short: {len(non_blank)} non-blank lines, "
        f"required ≥30."
    )


@pytest.mark.parametrize("stack", _STACKS)
def test_examples_has_minimum_two(stack: str) -> None:
    """``examples/`` ships at least two markdown files."""
    examples_dir = _OVERRIDES_ROOT / stack / "examples"
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
    assert _OVERRIDES_ROOT.is_dir(), f"overrides root missing: {_OVERRIDES_ROOT}"
    on_disk = {p.name for p in _OVERRIDES_ROOT.iterdir() if p.is_dir() and p.name != "_shared"}
    expected = set(_STACKS)
    assert expected.issubset(on_disk), (
        f"missing override dirs: {sorted(expected - on_disk)}. spec-128 D-128-09 requires all 7 stacks."
    )


def test_shared_directory_exists() -> None:
    """spec-128 D-128-10: ``overrides/_shared/`` exists for cross-cutting refs."""
    shared = _OVERRIDES_ROOT / "_shared"
    assert shared.is_dir(), (
        f"shared directory missing: {shared.relative_to(_REPO_ROOT)}. "
        f"spec-128 D-128-10 requires _shared/ for cross-cutting content "
        f"(compliance-trace, observability shared-framework, execution-kernel team)."
    )
