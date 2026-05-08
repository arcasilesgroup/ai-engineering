"""Deterministic adapter router (sub-008 T-8.11).

Tests the pure function ``resolve_adapter(task_path, spec_stack) -> Path``
in ``tools/skill_app/deterministic_router.py``. The router must:

1. Resolve all 7 supported stacks via explicit ``spec_stack`` argument.
2. Infer the stack from a file path's extension when ``spec_stack`` is
   ``None`` (e.g. ``foo.ts`` → typescript, ``bar.py`` → python, etc.).
3. Raise ``UnknownStackError`` when neither argument lets it pick a
   stack (no extension match, no explicit hint).
4. Run under 50 ms p95 — measured with ``time.perf_counter`` over a
   warm-loop of 1000 calls.
5. Return a real ``Path`` rooted at ``.ai-engineering/adapters/<stack>``.

The test imports from ``skill_app.deterministic_router`` (the
distribution-package form per ``pyproject.toml`` ``pythonpath`` setting),
so the router must live at ``tools/skill_app/deterministic_router.py``
to satisfy hex layering (D-127-09).
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from skill_app.deterministic_router import UnknownStackError, resolve_adapter

_REPO_ROOT = Path(__file__).resolve().parents[3]
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

# Mapping from canonical extension → stack name. Per sub-008 the router
# only needs to support these — ``ai-build`` agent surfaces the
# ``spec_stack`` argument for everything else.
_EXT_FIXTURES: tuple[tuple[str, str], ...] = (
    ("foo.ts", "typescript"),
    ("foo.tsx", "typescript"),
    ("foo.py", "python"),
    ("foo.go", "go"),
    ("foo.rs", "rust"),
    ("foo.swift", "swift"),
    ("foo.cs", "csharp"),
    ("foo.kt", "kotlin"),
)


@pytest.mark.parametrize("stack", _STACKS)
def test_resolves_via_explicit_spec_stack(stack: str) -> None:
    """``spec_stack`` wins over path inference for every supported stack."""
    result = resolve_adapter(Path("README.md"), spec_stack=stack)
    expected = _ADAPTERS_ROOT / stack
    assert result == expected


@pytest.mark.parametrize("path,expected_stack", _EXT_FIXTURES)
def test_infers_from_path_extension(path: str, expected_stack: str) -> None:
    """When ``spec_stack`` is None, the path's extension picks the stack."""
    result = resolve_adapter(Path(path), spec_stack=None)
    assert result == _ADAPTERS_ROOT / expected_stack


@pytest.mark.parametrize("path,expected_stack", _EXT_FIXTURES)
def test_explicit_stack_overrides_path_extension(path: str, expected_stack: str) -> None:
    """``spec_stack`` always overrides whatever the path implies."""
    # Pick a different stack to ensure precedence. We rotate through the
    # _STACKS tuple so we never accidentally pick the same one.
    other_stack = _STACKS[(_STACKS.index(expected_stack) + 1) % len(_STACKS)]
    result = resolve_adapter(Path(path), spec_stack=other_stack)
    assert result == _ADAPTERS_ROOT / other_stack


def test_raises_when_neither_input_resolves() -> None:
    """No spec_stack, no inference → UnknownStackError."""
    with pytest.raises(UnknownStackError):
        resolve_adapter(Path("README.md"), spec_stack=None)


def test_raises_for_unsupported_explicit_stack() -> None:
    """An unknown ``spec_stack`` value also raises UnknownStackError."""
    with pytest.raises(UnknownStackError):
        resolve_adapter(Path("foo.py"), spec_stack="haskell")


def test_returns_path_inside_adapters_root() -> None:
    """Returned path is rooted at .ai-engineering/adapters/."""
    result = resolve_adapter(Path("foo.py"), spec_stack=None)
    assert result.is_relative_to(_ADAPTERS_ROOT)


def test_returned_directory_exists_on_disk() -> None:
    """For each known stack the returned dir must exist (matches scaffolding)."""
    for stack in _STACKS:
        result = resolve_adapter(Path("anything"), spec_stack=stack)
        assert result.is_dir(), f"adapter dir not on disk for stack {stack}"


def test_router_is_pure_no_side_effects() -> None:
    """Calling the router twice yields the same result; nothing mutates."""
    a = resolve_adapter(Path("foo.py"), spec_stack=None)
    b = resolve_adapter(Path("foo.py"), spec_stack=None)
    assert a == b


def test_router_p95_under_50ms() -> None:
    """1000 calls; p95 latency under 50 ms (router hot-path budget)."""
    samples: list[float] = []
    for _ in range(1000):
        t0 = time.perf_counter()
        resolve_adapter(Path("foo.py"), spec_stack=None)
        samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    p95 = samples[int(len(samples) * 0.95)]
    assert p95 < 50.0, f"router p95 = {p95:.3f} ms, budget 50 ms"
