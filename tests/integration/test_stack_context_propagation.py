"""Integration tests for the Phase-0 stack-context resolver (spec-139 M3).

The resolver replaces the N redundant ``manifest.yml`` reads that used
to fire once per dispatched agent (each triggering an 8-hook cascade).
These tests defend the four contracts spelled out in the M3 brief:

1. Resolver produces a dict with the canonical keys (``stacks``,
   ``test_command``, ``format_command``, ``lint_command``).
2. The call is idempotent — two invocations return equivalent dicts.
3. Missing / unreadable ``manifest.yml`` returns a degraded default
   instead of crashing (fail-open contract).
4. :func:`write_stack_context` produces valid JSON at the documented
   runtime path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.autopilot import stack_context as sc

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_PYTHON_MANIFEST = """\
schema_version: "2.0"
framework_version: "0.4.0"
name: ai-engineering
version: "1.0.0"

providers:
  vcs: github
  stacks: [python]

quality:
  coverage: 80
"""

_POLYGLOT_MANIFEST = """\
schema_version: "2.0"

providers:
  vcs: github
  stacks:
    - python
    - typescript
    - rust
"""

_NO_STACKS_MANIFEST = """\
schema_version: "2.0"

providers:
  vcs: github

quality:
  coverage: 80
"""


@pytest.fixture()
def manifest_python(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.yml"
    path.write_text(_PYTHON_MANIFEST, encoding="utf-8")
    return path


@pytest.fixture()
def manifest_polyglot(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.yml"
    path.write_text(_POLYGLOT_MANIFEST, encoding="utf-8")
    return path


@pytest.fixture()
def manifest_no_stacks(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.yml"
    path.write_text(_NO_STACKS_MANIFEST, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Contract 1 — schema shape
# ---------------------------------------------------------------------------


def test_resolve_stack_context_returns_canonical_keys(manifest_python: Path) -> None:
    """The dict carries the four keys downstream dispatchers expect."""
    ctx = sc.resolve_stack_context(manifest_python)

    # Every key documented in phase-deep-plan.md § Step 0 is present.
    assert "stacks" in ctx
    assert "test_command" in ctx
    assert "format_command" in ctx
    assert "lint_command" in ctx

    # Types match the dispatch-prompt JSON shape.
    assert isinstance(ctx["stacks"], list)
    assert isinstance(ctx["test_command"], dict)
    assert isinstance(ctx["format_command"], dict)
    assert isinstance(ctx["lint_command"], dict)


def test_resolve_stack_context_python_default_commands(manifest_python: Path) -> None:
    """The python default uses the venv-anchored ruff/pytest invocations."""
    ctx = sc.resolve_stack_context(manifest_python)

    assert ctx["stacks"] == ["python"]
    assert ctx["test_command"]["python"].endswith("pytest")
    assert "ruff" in ctx["format_command"]["python"]
    assert "ruff" in ctx["lint_command"]["python"]
    assert ctx["degraded"] is False


def test_resolve_stack_context_polyglot_emits_one_entry_per_stack(
    manifest_polyglot: Path,
) -> None:
    """A 3-stack manifest yields three keyed command tables."""
    ctx = sc.resolve_stack_context(manifest_polyglot)

    assert ctx["stacks"] == ["python", "typescript", "rust"]
    for stack in ("python", "typescript", "rust"):
        assert stack in ctx["test_command"]
        assert stack in ctx["format_command"]
        assert stack in ctx["lint_command"]
    # Rust must hit the canonical clippy/fmt commands so build agents
    # do not have to re-read the override file.
    assert "cargo" in ctx["test_command"]["rust"]
    assert "clippy" in ctx["lint_command"]["rust"]


# ---------------------------------------------------------------------------
# Contract 2 — idempotency
# ---------------------------------------------------------------------------


def test_resolve_stack_context_idempotent(manifest_python: Path) -> None:
    """Two calls return equivalent dicts (same keys, same values)."""
    first = sc.resolve_stack_context(manifest_python)
    second = sc.resolve_stack_context(manifest_python)

    assert first == second
    # Independent objects so callers cannot mutate the cache by accident.
    assert first is not second


# ---------------------------------------------------------------------------
# Contract 3 — fail-open degraded default
# ---------------------------------------------------------------------------


def test_resolve_stack_context_missing_manifest_returns_degraded_default(
    tmp_path: Path,
) -> None:
    """When manifest.yml is absent, return the documented degraded default."""
    missing = tmp_path / "does-not-exist.yml"

    ctx = sc.resolve_stack_context(missing)

    assert ctx["stacks"] == []
    assert ctx["test_command"] == {}
    assert ctx["format_command"] == {}
    assert ctx["lint_command"] == {}
    assert ctx["degraded"] is True


def test_resolve_stack_context_manifest_without_stacks_returns_degraded(
    manifest_no_stacks: Path,
) -> None:
    """A valid manifest with no ``providers.stacks`` still degrades cleanly."""
    ctx = sc.resolve_stack_context(manifest_no_stacks)

    assert ctx["stacks"] == []
    assert ctx["degraded"] is True


def test_resolve_stack_context_unreadable_manifest_does_not_crash(
    tmp_path: Path,
) -> None:
    """Passing a directory (read raises) still produces the degraded default."""
    a_directory = tmp_path / "not-a-file"
    a_directory.mkdir()

    ctx = sc.resolve_stack_context(a_directory)

    assert ctx["degraded"] is True
    assert ctx["stacks"] == []


# ---------------------------------------------------------------------------
# Contract 4 — write_stack_context produces valid JSON
# ---------------------------------------------------------------------------


def test_write_stack_context_emits_valid_json(
    manifest_python: Path,
    tmp_path: Path,
) -> None:
    """The resolved JSON round-trips through json.loads with sorted keys."""
    ctx = sc.resolve_stack_context(manifest_python)
    runtime_dir = tmp_path / "runtime"

    target = sc.write_stack_context(ctx, active="spec-139-test", runtime_dir=runtime_dir)

    assert target.exists()
    assert target.parent.name == "spec-139-test"
    assert target.name == "stack-context.json"

    parsed = json.loads(target.read_text(encoding="utf-8"))
    assert parsed["stacks"] == ["python"]
    assert "python" in parsed["test_command"]


def test_write_stack_context_sorts_keys_for_byte_stability(
    manifest_polyglot: Path,
    tmp_path: Path,
) -> None:
    """Two writes of equivalent contexts produce byte-identical files."""
    ctx_a = sc.resolve_stack_context(manifest_polyglot)
    ctx_b = sc.resolve_stack_context(manifest_polyglot)

    runtime_dir = tmp_path / "runtime"
    path_a = sc.write_stack_context(ctx_a, active="run-a", runtime_dir=runtime_dir)
    path_b = sc.write_stack_context(ctx_b, active="run-b", runtime_dir=runtime_dir)

    # Bytes must match — proves sort_keys=True is in effect so the
    # dispatch-prompt serialisation is cache-friendly.
    assert path_a.read_bytes() == path_b.read_bytes()


def test_write_stack_context_creates_runtime_subdir(
    manifest_python: Path,
    tmp_path: Path,
) -> None:
    """Missing parent dirs are created on first write."""
    ctx = sc.resolve_stack_context(manifest_python)
    runtime_dir = tmp_path / "fresh" / "runtime" / "autopilot"
    assert not runtime_dir.exists()

    target = sc.write_stack_context(ctx, active="spec-deep", runtime_dir=runtime_dir)

    assert target.exists()
    assert target.is_file()
