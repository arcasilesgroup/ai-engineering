"""Mock tests asserting each NDJSON writer uses the lock primitive (spec-126 T-3.2).

Three hook-side writers append to ``framework-events.ndjson`` and must
all wrap the ``prev_event_hash`` compute + ``f.write`` in a
``with_lock_retry(project_root, "framework-events")`` context (so two
concurrent writers cannot observe the same prev value and append
duplicate-pointer entries):

1. ``_lib/observability.py:append_framework_event``
2. ``_lib/hook-common.py:emit_event``
3. ``_lib/trace_context.py:_emit_corruption_event``

Each test patches ``with_lock_retry`` to a context-manager spy, invokes
the writer with a synthetic event, and asserts the spy was entered
exactly once with ``lock_name == "framework-events"``.

These tests are RED until T-3.3 / T-3.4 / T-3.5 land.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks"


@pytest.fixture
def hooks_path(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Make ``_lib.*`` importable; clear any cached modules."""
    monkeypatch.syspath_prepend(str(_HOOKS_DIR))
    for mod_name in list(sys.modules):
        if mod_name == "_lib" or mod_name.startswith("_lib."):
            del sys.modules[mod_name]
    return _HOOKS_DIR


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state" / "locks").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _install_spy(monkeypatch: pytest.MonkeyPatch, calls: list[tuple]):
    """Replace ``_lib.locked_append.with_lock_retry`` with a context-manager spy."""
    import _lib.locked_append as la_mod

    @contextmanager
    def spy(project_root, lock_name, **kwargs):
        calls.append((Path(project_root), lock_name, kwargs))
        yield True

    monkeypatch.setattr(la_mod, "with_lock_retry", spy)


def _load_hook_common(hooks_path: Path):
    """Load ``_lib/hook-common.py`` (filename has hyphen → load by spec)."""
    file_path = hooks_path / "_lib" / "hook-common.py"
    spec = importlib.util.spec_from_file_location("_lib.hook_common", str(file_path))
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        msg = "could not load _lib.hook-common"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_lib.hook_common"] = module
    spec.loader.exec_module(module)
    return module


def _valid_event(project_root: Path) -> dict:
    return {
        "schemaVersion": "1.0",
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": project_root.name,
        "engine": "claude_code",
        "kind": "skill_invoked",
        "outcome": "success",
        "component": "hook.test_lock_usage",
        "correlationId": uuid4().hex,
        "detail": {"skill": "ai-test"},
    }


def test_observability_append_framework_event_uses_lock(
    hooks_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``append_framework_event`` must enter ``with_lock_retry`` with the framework-events lock."""
    obs = importlib.import_module("_lib.observability")
    calls: list[tuple] = []
    _install_spy(monkeypatch, calls)

    obs.append_framework_event(project_root, _valid_event(project_root))

    assert len(calls) == 1, f"expected exactly one with_lock_retry entry, got {len(calls)}"
    entered_root, lock_name, _kwargs = calls[0]
    assert entered_root == project_root
    assert lock_name == "framework-events"


def test_hook_common_emit_event_uses_lock(
    hooks_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``hook-common.emit_event`` must enter ``with_lock_retry`` with the framework-events lock."""
    hook_common = _load_hook_common(hooks_path)

    calls: list[tuple] = []
    _install_spy(monkeypatch, calls)

    result = hook_common.emit_event(project_root, _valid_event(project_root))

    assert result is True, "emit_event should accept a well-formed event"
    assert len(calls) == 1, f"expected exactly one with_lock_retry entry, got {len(calls)}"
    entered_root, lock_name, _kwargs = calls[0]
    assert entered_root == project_root
    assert lock_name == "framework-events"


def test_trace_context_corruption_logger_uses_lock(
    hooks_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Corruption logger must enter ``with_lock_retry`` with the framework-events lock."""
    tc = importlib.import_module("_lib.trace_context")

    calls: list[tuple] = []
    _install_spy(monkeypatch, calls)

    tc._emit_corruption_event(project_root, "synthetic corruption summary for test")

    assert len(calls) == 1, f"expected exactly one with_lock_retry entry, got {len(calls)}"
    entered_root, lock_name, _kwargs = calls[0]
    assert entered_root == project_root
    assert lock_name == "framework-events"
