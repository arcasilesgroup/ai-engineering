"""spec-158 D-158-12 / AC14 — Stop hooks honor ``stop_hook_active``.

When Claude Code is already in a Stop-hook continuation it sets
``stop_hook_active: true`` on the payload. A Stop hook that re-runs its work
and re-emits a ``decision: block`` would loop until the engine's cap (the
observed "9x block"). Each Stop/SubagentStop hook must release the turn —
exit cleanly, run no convergence, emit no block — when the flag is set.

The hooks live outside the importable package tree, so each is loaded by file
path and its ``get_hook_context`` is monkeypatched with a fake context whose
payload carries ``stop_hook_active: true``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HOOK_DIR = Path(__file__).resolve().parents[3] / ".ai-engineering" / "scripts" / "hooks"

# (filename, event_name) for every Stop/SubagentStop hook.
_STOP_HOOKS = [
    ("runtime-stop.py", "Stop"),
    ("memory-stop.py", "Stop"),
    ("instinct-extract.py", "Stop"),
    ("runtime-subagent-stop.py", "SubagentStop"),
]


def _load(filename: str, monkeypatch: pytest.MonkeyPatch):
    """Load a hook module fresh by file path."""
    monkeypatch.syspath_prepend(str(HOOK_DIR))
    mod_name = f"aieng_stopguard_{filename.replace('-', '_').removesuffix('.py')}"
    sys.modules.pop(mod_name, None)
    spec = importlib.util.spec_from_file_location(mod_name, HOOK_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def _fake_ctx(event_name: str, project_root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        event_name=event_name,
        data={"stop_hook_active": True, "hook_event_name": event_name},
        project_root=project_root,
        session_id="sess-test",
        agent_kind="main",
        engine="claude_code",
    )


@pytest.mark.parametrize(("filename", "event_name"), _STOP_HOOKS, ids=[h[0] for h in _STOP_HOOKS])
def test_stop_hook_active_releases_without_block(
    filename: str,
    event_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)
    mod = _load(filename, monkeypatch)
    monkeypatch.setattr(mod, "get_hook_context", lambda: _fake_ctx(event_name, tmp_path))

    # runtime-stop is the only hook that runs convergence; if the guard works it
    # must NOT be reached. Make a call an immediate, loud failure.
    if hasattr(mod, "check_convergence"):

        def _boom(*_a: object, **_k: object) -> None:
            raise AssertionError("check_convergence must not run when stop_hook_active is true")

        monkeypatch.setattr(mod, "check_convergence", _boom)

    # Must return cleanly (no SystemExit, no convergence, no exception).
    mod.main()

    out = capsys.readouterr().out
    assert '"decision": "block"' not in out
    assert '"decision":"block"' not in out
