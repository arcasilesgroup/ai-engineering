"""spec-201 sub-001 T-3.1/T-3.2: top-level scripts append a *chained* event.

Two stand-alone scripts under `.ai-engineering/scripts/` write straight
into `framework-events.ndjson`:

* `runtime_rotate._emit_event` appended with **no lock and no pointer** —
  an unlocked raw append that lands between a chained writer's pointer
  computation and its write, which is what produced the live breaks;
* `spec_lifecycle._append_event` takes the events lock but never stamped
  a pointer, leaving pointer-less `framework_operation` rows behind.

Both must now follow the one contract every other writer on this file
follows (`state/observability.py::_append_framework_events_locked`):
stamp `prev_event_hash` **inside** `artifact_lock(root,
"framework-events")`. Tests assert the on-disk verdict via
`verify_audit_chain` so the scripts stay free to change how they do it.

Neither script may import `ai_engineering` — both run under the host
`#!/usr/bin/env python3` shebang and must stay stdlib-only.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

from ai_engineering.state.audit_chain import verify_audit_chain

_SCRIPTS = Path(__file__).resolve().parents[3] / ".ai-engineering" / "scripts"
_RUNTIME_ROTATE = _SCRIPTS / "runtime_rotate.py"
_SPEC_LIFECYCLE = _SCRIPTS / "spec_lifecycle.py"
_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


def _load(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    mod = importlib.util.module_from_spec(spec)
    # ``@dataclass`` resolves string annotations through ``sys.modules``,
    # so the module must be registered before it executes.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _events_path(root: Path) -> Path:
    path = root / _EVENTS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _entries(root: Path) -> list[dict]:
    text = _events_path(root).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _seed_anchor(root: Path) -> None:
    """Write one pre-existing chained event so the next append must point at it."""
    anchor = {
        "kind": "framework_operation",
        "timestamp": "2026-07-27T00:00:00Z",
        "detail": {"operation": "anchor"},
        "prev_event_hash": None,
    }
    _events_path(root).write_text(json.dumps(anchor, sort_keys=True) + "\n", encoding="utf-8")


# ── runtime_rotate ───────────────────────────────────────────────────────


def test_runtime_rotate_stamps_a_pointer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The rotation summary event must carry a chain pointer."""
    mod = _load("rr_chain", _RUNTIME_ROTATE)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    _seed_anchor(tmp_path)

    mod._emit_event({"tool_outputs": {"deleted": 0}})

    entries = _entries(tmp_path)
    assert len(entries) == 2
    assert "prev_event_hash" in entries[1]
    assert entries[1]["prev_event_hash"] is not None


def test_runtime_rotate_append_keeps_the_chain_verifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load("rr_chain_verify", _RUNTIME_ROTATE)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    _seed_anchor(tmp_path)

    mod._emit_event({"tool_outputs": {"deleted": 0}})
    mod._emit_event({"tool_outputs": {"deleted": 1}})

    verdict = verify_audit_chain(_events_path(tmp_path), mode="ndjson")
    assert verdict.ok, verdict.first_break_reason
    assert verdict.entries_checked == 3


def test_runtime_rotate_anchors_on_an_empty_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first event on a fresh repo anchors at ``None``, not at a hash."""
    mod = _load("rr_chain_anchor", _RUNTIME_ROTATE)
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    mod._emit_event({"tool_outputs": {"deleted": 0}})

    entries = _entries(tmp_path)
    assert entries[0]["prev_event_hash"] is None


def test_runtime_rotate_takes_the_events_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The append holds ``artifact_lock(root, "framework-events")``.

    Without the lock the pointer read and the write straddle any other
    writer's append — the exact race that broke the live ledger.
    """
    mod = _load("rr_chain_lock", _RUNTIME_ROTATE)
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    mod._emit_event({"tool_outputs": {"deleted": 0}})

    assert (tmp_path / ".ai-engineering" / "state" / "locks" / "framework-events.lock").exists()


# ── spec_lifecycle ───────────────────────────────────────────────────────


def test_spec_lifecycle_stamps_a_pointer(tmp_path: Path) -> None:
    """``framework_operation`` rows must stop landing pointer-less."""
    mod = _load("sl_chain", _SPEC_LIFECYCLE)
    _seed_anchor(tmp_path)

    mod._append_event(tmp_path, "start_new", {"spec_id": "spec-201"})

    entries = _entries(tmp_path)
    assert len(entries) == 2
    assert entries[1].get("prev_event_hash") is not None


def test_spec_lifecycle_append_keeps_the_chain_verifiable(tmp_path: Path) -> None:
    mod = _load("sl_chain_verify", _SPEC_LIFECYCLE)
    _seed_anchor(tmp_path)

    mod._append_event(tmp_path, "start_new", {"spec_id": "spec-201"})
    mod._append_event(tmp_path, "mark_shipped", {"spec_id": "spec-201"})

    verdict = verify_audit_chain(_events_path(tmp_path), mode="ndjson")
    assert verdict.ok, verdict.first_break_reason
    assert verdict.entries_checked == 3


def test_both_writers_interleave_without_breaking_the_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two different writers on one ledger must still produce one chain."""
    rotate = _load("rr_chain_mix", _RUNTIME_ROTATE)
    lifecycle = _load("sl_chain_mix", _SPEC_LIFECYCLE)
    monkeypatch.setattr(rotate, "ROOT", tmp_path)

    rotate._emit_event({"tool_outputs": {"deleted": 0}})
    lifecycle._append_event(tmp_path, "start_new", {"spec_id": "spec-201"})
    rotate._emit_event({"tool_outputs": {"deleted": 2}})

    verdict = verify_audit_chain(_events_path(tmp_path), mode="ndjson")
    assert verdict.ok, verdict.first_break_reason
    assert verdict.entries_checked == 3


# ── stdlib-only guard ────────────────────────────────────────────────────


@pytest.mark.parametrize("script", [_RUNTIME_ROTATE, _SPEC_LIFECYCLE])
def test_scripts_stay_stdlib_only(script: Path) -> None:
    """Neither script may import ``ai_engineering``: they run stdlib-only."""
    tree = ast.parse(script.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            assert not name.startswith("ai_engineering"), (
                f"{script.name} imports {name!r}; these scripts run under the host "
                "`#!/usr/bin/env python3` and must stay stdlib-only."
            )
