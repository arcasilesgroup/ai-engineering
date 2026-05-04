"""Pin the Ralph reinjection default-enabled behaviour (P0.3 / 2026-05-04 gap closure).

Before the harness gap audit, ``_RALPH_BLOCK_ENABLED`` defaulted to False —
the ``decision: block`` reinjection path was unreachable in production
unless ``AIENG_RALPH_BLOCK=1`` was set. ~200 lines of dead code. The flip
enables reinjection by default; opt-out is via ``AIENG_RALPH_BLOCK=0``
or the broader ``AIENG_RALPH_DISABLED=1`` escape.

Companion to ``test_runtime_stop_ralph.py`` which exercises the
behavioural contract via fake convergence results. This file pins the
flag-resolution invariants so a future revert lands a CI failure.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RUNTIME_STOP_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-stop.py"


def _load_runtime_stop_fresh(monkeypatch: pytest.MonkeyPatch):
    """Re-import runtime-stop.py with a clean module-level env snapshot.

    The flag is captured at module load time, so each test that needs a
    different env must reload the module via importlib.
    """
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_runtime_stop_default", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_stop_default", RUNTIME_STOP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_runtime_stop_default"] = module
    spec.loader.exec_module(module)
    return module


def test_default_block_enabled_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """No env vars set → reinjection is enabled. New default after the
    2026-05-04 harness audit identified this as P0.3."""
    monkeypatch.delenv("AIENG_RALPH_BLOCK", raising=False)
    monkeypatch.delenv("AIENG_RALPH_DISABLED", raising=False)
    mod = _load_runtime_stop_fresh(monkeypatch)
    assert mod._RALPH_BLOCK_ENABLED is True
    assert mod._RALPH_DISABLED is False


def test_explicit_block_zero_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    """``AIENG_RALPH_BLOCK=0`` opts out of reinjection. The escape hatch
    documented in the runtime-stop docstring."""
    monkeypatch.setenv("AIENG_RALPH_BLOCK", "0")
    monkeypatch.delenv("AIENG_RALPH_DISABLED", raising=False)
    mod = _load_runtime_stop_fresh(monkeypatch)
    assert mod._RALPH_BLOCK_ENABLED is False


def test_explicit_block_one_keeps_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """The explicit on-switch must keep working for forward compat."""
    monkeypatch.setenv("AIENG_RALPH_BLOCK", "1")
    monkeypatch.delenv("AIENG_RALPH_DISABLED", raising=False)
    mod = _load_runtime_stop_fresh(monkeypatch)
    assert mod._RALPH_BLOCK_ENABLED is True


def test_ralph_disabled_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    """``AIENG_RALPH_DISABLED=1`` is the broader escape; it short-circuits
    convergence entirely so neither telemetry nor reinjection runs."""
    monkeypatch.setenv("AIENG_RALPH_DISABLED", "1")
    monkeypatch.delenv("AIENG_RALPH_BLOCK", raising=False)
    mod = _load_runtime_stop_fresh(monkeypatch)
    assert mod._RALPH_DISABLED is True


def test_block_default_documented_in_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drift guard: the comment block above _RALPH_BLOCK_ENABLED must
    mention the new default. If you flip the default again, update the
    comment first so the source-of-truth stays self-consistent."""
    text = RUNTIME_STOP_PATH.read_text(encoding="utf-8")
    assert "Reinjection is enabled by default" in text, (
        "Drift: runtime-stop.py docstring no longer matches the flag default."
    )
    assert 'AIENG_RALPH_BLOCK", "1"' in text, (
        "Drift: the .get() default in _RALPH_BLOCK_ENABLED is no longer '1'."
    )
