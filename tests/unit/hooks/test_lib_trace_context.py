"""Tests for `.ai-engineering/scripts/hooks/_lib/trace_context.py` (spec-120 T-A4).

Two contracts under test:

  1. **Byte-for-byte parity with pkg side**: given identical inputs (same
     trace_id, same span_stack), the file produced by the `_lib` mirror
     must equal the file produced by `ai_engineering.state.trace_context`.
     We blank out `updatedAt` (a wall-clock field) before comparing because
     two writes always run a few nanoseconds apart.

  2. **Stdlib-only**: the `_lib` module imports nothing from
     `ai_engineering.*`. We confirm via AST scan that no `import` /
     `from … import` statement references the package; this catches
     copy-paste regressions where a developer accidentally re-imports the
     pkg helper into the hook-side module.

The `_lib` module is loaded under a fresh module name (not on the
package import path) so the test doesn't pollute `sys.modules` for
sibling tests.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LIB_TRACE_CONTEXT_PATH = (
    REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "trace_context.py"
)


@pytest.fixture
def lib_tc():
    """Load the stdlib-only mirror as `aieng_lib_trace_context`.

    Loaded fresh for every test so module-level state cannot leak.
    """
    sys.modules.pop("aieng_lib_trace_context", None)
    spec = importlib.util.spec_from_file_location("aieng_lib_trace_context", LIB_TRACE_CONTEXT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_lib_trace_context"] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Stdlib-only contract
# ---------------------------------------------------------------------------


def test_lib_no_pkg_imports() -> None:
    """The `_lib` module must not import from `ai_engineering.*`.

    Hooks run pre-pip-install in fresh checkouts and pre-commit
    contexts -- any pkg import would crash the hook. We scan the AST
    so the test is independent of import-time side effects.
    """
    source = LIB_TRACE_CONTEXT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("ai_engineering"):
                    offenders.append(f"import {alias.name}")
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("ai_engineering")
        ):
            offenders.append(f"from {node.module} import ...")
    assert offenders == [], (
        f"_lib/trace_context.py must not import from ai_engineering.*; found: {offenders}"
    )


def test_lib_module_attributes_have_no_pkg_origin(lib_tc) -> None:
    """No top-level callable in the module declares a pkg `__module__`."""
    for name in dir(lib_tc):
        if name.startswith("_"):
            continue
        obj = getattr(lib_tc, name)
        origin = getattr(obj, "__module__", "")
        if isinstance(origin, str) and origin.startswith("ai_engineering"):
            raise AssertionError(
                f"{name!r} on _lib.trace_context resolves to pkg origin {origin!r}"
            )


# ---------------------------------------------------------------------------
# Byte-for-byte parity with pkg side
# ---------------------------------------------------------------------------


def _strip_volatile_fields(payload: dict) -> dict:
    """Remove fields that depend on wall clock so we can compare bodies."""
    cleaned = dict(payload)
    cleaned.pop("updatedAt", None)
    return cleaned


def test_lib_mirror_byte_for_byte_with_pkg(tmp_path: Path, lib_tc) -> None:
    """Same inputs into both modules => identical canonical-JSON bodies.

    Compares the file content with `updatedAt` stripped (it's a wall-clock
    field -- two writes always differ by nanoseconds). All other bytes
    must match exactly: same key order (sort_keys=True), same separators,
    same value types.
    """
    from ai_engineering.state import trace_context as pkg_tc

    pkg_root = tmp_path / "pkg"
    lib_root = tmp_path / "lib"
    pkg_root.mkdir()
    lib_root.mkdir()

    payload = {
        "traceId": "0123456789abcdef0123456789abcdef",
        "span_stack": ["aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb"],
    }

    pkg_tc.write_trace_context(pkg_root, dict(payload))
    lib_tc.write_trace_context(lib_root, dict(payload))

    pkg_file = pkg_tc.trace_context_path(pkg_root)
    lib_file = lib_tc.trace_context_path(lib_root)

    pkg_dict = json.loads(pkg_file.read_text(encoding="utf-8"))
    lib_dict = json.loads(lib_file.read_text(encoding="utf-8"))

    # Strip `updatedAt` -- only volatile field. Everything else must match.
    pkg_canonical = json.dumps(
        _strip_volatile_fields(pkg_dict),
        sort_keys=True,
        separators=(",", ":"),
    )
    lib_canonical = json.dumps(
        _strip_volatile_fields(lib_dict),
        sort_keys=True,
        separators=(",", ":"),
    )
    assert pkg_canonical == lib_canonical, (
        f"pkg and _lib produced different bodies:\n  pkg: {pkg_canonical}\n  lib: {lib_canonical}"
    )


def test_lib_id_generation_shapes(lib_tc) -> None:
    """`_lib` IDs match pkg shape constraints: 32-hex / 16-hex."""
    trace_id = lib_tc.new_trace_id()
    assert isinstance(trace_id, str) and len(trace_id) == 32
    assert all(c in "0123456789abcdef" for c in trace_id)

    span_id = lib_tc.new_span_id()
    assert isinstance(span_id, str) and len(span_id) == 16
    assert all(c in "0123456789abcdef" for c in span_id)


def test_lib_push_pop_round_trip(tmp_path: Path, lib_tc) -> None:
    """LIFO order, missing-file => fresh-context branch, empty-stack => None."""
    lib_tc.push_span(tmp_path, "1111111111111111")
    lib_tc.push_span(tmp_path, "2222222222222222")
    lib_tc.push_span(tmp_path, "3333333333333333")

    assert lib_tc.pop_span(tmp_path) == "3333333333333333"
    assert lib_tc.pop_span(tmp_path) == "2222222222222222"
    assert lib_tc.pop_span(tmp_path) == "1111111111111111"
    assert lib_tc.pop_span(tmp_path) is None


def test_lib_corruption_writes_stdlib_framework_error(tmp_path: Path, lib_tc) -> None:
    """`_lib` corruption fallback writes a `framework_error` NDJSON line.

    Critical: the line must validate against the canonical event schema
    (the pkg-side validator) so downstream consumers (audit_chain reader,
    schema validator) treat hook-emitted errors uniformly.
    """
    from ai_engineering.state.event_schema import validate_event_schema

    path = lib_tc.trace_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-valid-json{", encoding="utf-8")

    out = lib_tc.read_trace_context(tmp_path)
    assert out is None

    events_path = tmp_path / lib_tc.FRAMEWORK_EVENTS_REL
    assert events_path.exists()
    lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["kind"] == "framework_error"
    assert parsed["component"] == "state.trace_context"
    assert parsed["detail"]["error_code"] == "trace_context_corrupted"
    # Round-trips through the canonical schema validator.
    assert validate_event_schema(parsed) is True


def test_lib_current_trace_context_does_not_persist(tmp_path: Path, lib_tc) -> None:
    """`_lib` mirrors the pkg side: read path is side-effect-free."""
    trace_id, parent = lib_tc.current_trace_context(tmp_path)
    assert isinstance(trace_id, str) and len(trace_id) == 32
    assert parent is None
    assert not lib_tc.trace_context_path(tmp_path).exists()


def test_lib_clear_removes_file(tmp_path: Path, lib_tc) -> None:
    """clear_trace_context idempotent (handles missing-file case)."""
    lib_tc.write_trace_context(
        tmp_path,
        {"traceId": lib_tc.new_trace_id(), "span_stack": []},
    )
    path = lib_tc.trace_context_path(tmp_path)
    assert path.exists()
    lib_tc.clear_trace_context(tmp_path)
    assert not path.exists()
    # Second call is a no-op.
    lib_tc.clear_trace_context(tmp_path)
    assert not path.exists()


def test_lib_atomic_write_no_tmp_leftover(tmp_path: Path, lib_tc) -> None:
    """No `.tmp` siblings remain after a successful write on the `_lib` side."""
    lib_tc.write_trace_context(
        tmp_path,
        {"traceId": lib_tc.new_trace_id(), "span_stack": []},
    )
    runtime_dir = tmp_path / ".ai-engineering" / "state" / "runtime"
    leftovers = [p for p in runtime_dir.iterdir() if p.suffix == ".tmp" or ".tmp" in p.name]
    assert leftovers == [], f"unexpected leftover tmp files: {leftovers}"
