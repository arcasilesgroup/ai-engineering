"""spec-147 G1 T-1.11/1.12: hook failures must be VISIBLE (or fail closed).

Four hooks previously swallowed failures into silent ``exit 0``:

* ``auto-format.py`` — ``contextlib.suppress(Exception)`` on the
  re-stage primitive. A formatter that rewrote the file but failed to
  re-stage left the index silently inconsistent.
* ``runtime-stop.py`` — checkpoint / resume writes "degrade silently",
  so ``/ai-start`` could resume from a stale or absent checkpoint with
  no signal.
* ``mcp-health.py`` — ``bare except Exception: pass`` on state persist,
  so a corrupt / unwritable health file silently lost backoff state.
* ``no-verify-guard.py`` — returned ``False`` (allow) when ``shlex``
  could not parse the command, so a malformed-quoting ``git commit
  --no-verify`` slipped through the deny rule.

The first three are NOT security gates: they emit a visible
``hookSpecificOutput`` warning (non-blocking) so the failure is at least
observable. The last IS a security boundary on untrusted input: it now
fails CLOSED (blocks) on a parse error.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"


def _load_hook(module_name: str, filename: str, monkeypatch: pytest.MonkeyPatch):
    sys.modules.pop(module_name, None)
    monkeypatch.syspath_prepend(str(HOOKS_DIR))
    spec = importlib.util.spec_from_file_location(module_name, HOOKS_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


# ── auto-format: re-stage failure is visible ─────────────────────────────


@pytest.fixture
def autoformat(monkeypatch: pytest.MonkeyPatch):
    return _load_hook("aieng_autoformat_failloud", "auto-format.py", monkeypatch)


def test_autoformat_restage_failure_returns_warning(
    autoformat, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the re-stage primitive raises, the helper must surface a warning
    string instead of swallowing it (visible, non-blocking)."""

    def _boom(*_a, **_k):
        raise RuntimeError("git index locked")

    # Force a non-empty staged set so the re-stage path is actually reached,
    # then make the re-stage itself blow up.
    monkeypatch.setattr(autoformat, "capture_staged_set", lambda _root: {"a.py"})
    monkeypatch.setattr(autoformat, "restage_intersection", _boom)

    warning = autoformat._maybe_restage_after_format(project)

    assert warning is not None
    assert "re-stage" in warning.lower() or "restage" in warning.lower()


def test_autoformat_clean_restage_returns_none(
    autoformat, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The happy path emits no warning."""
    monkeypatch.setattr(autoformat, "capture_staged_set", lambda _root: {"a.py"})
    monkeypatch.setattr(autoformat, "restage_intersection", lambda _root, _s: None)

    assert autoformat._maybe_restage_after_format(project) is None


# ── runtime-stop: checkpoint write failure is visible ────────────────────


@pytest.fixture
def rstop(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AIENG_RALPH_MAX_RETRIES", "3")
    return _load_hook("aieng_runtime_stop_failloud", "runtime-stop.py", monkeypatch)


def test_runtime_stop_checkpoint_failure_returns_warning(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A checkpoint write that fails must surface a warning, not vanish."""

    def _boom(*_a, **_k):
        raise OSError("disk full")

    warning = rstop._safe_write_checkpoint(project, {"schemaVersion": "1.0"}, writer=_boom)

    assert warning is not None
    assert "checkpoint" in warning.lower()


def test_runtime_stop_checkpoint_success_returns_none(rstop, project: Path) -> None:
    written: dict = {}

    def _writer(path: Path, payload: dict) -> None:
        written["path"] = path
        written["payload"] = payload

    warning = rstop._safe_write_checkpoint(project, {"schemaVersion": "1.0"}, writer=_writer)

    assert warning is None
    assert written["payload"] == {"schemaVersion": "1.0"}


# ── mcp-health: state persist failure is visible ─────────────────────────


@pytest.fixture
def mcp(monkeypatch: pytest.MonkeyPatch):
    return _load_hook("aieng_mcp_health_failloud", "mcp-health.py", monkeypatch)


def test_mcp_health_state_persist_failure_returns_warning(
    mcp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed state write must report a warning so lost backoff state is
    observable, instead of ``except Exception: pass``."""

    def _boom(*_a, **_k):
        raise OSError("permission denied")

    monkeypatch.setattr(mcp, "_STATE_FILE", Path("/nonexistent-root/mcp-health.json"))
    monkeypatch.setattr(mcp.json, "dump", _boom)

    warning = mcp._save_state({"version": 1, "servers": {}})

    assert warning is not None
    assert "state" in warning.lower()


def test_mcp_health_state_persist_success_returns_none(
    mcp, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mcp, "_STATE_FILE", tmp_path / "state" / "mcp-health.json")

    warning = mcp._save_state({"version": 1, "servers": {}})

    assert warning is None
    assert (tmp_path / "state" / "mcp-health.json").is_file()


# ── no-verify-guard: parse error fails CLOSED (blocks) ───────────────────


@pytest.fixture
def nvg(monkeypatch: pytest.MonkeyPatch):
    return _load_hook("aieng_no_verify_guard_failloud", "no-verify-guard.py", monkeypatch)


def test_no_verify_guard_blocks_unparseable_command(nvg) -> None:
    """Malformed quoting must be treated as a deny condition (fail closed):
    we cannot prove the command is NOT a ``--no-verify`` bypass, so refuse."""
    # Unterminated single quote -> shlex.split raises ValueError.
    assert nvg._is_no_verify_attempt("git commit --no-verify -m 'unterminated") is True


def test_no_verify_guard_allows_well_formed_safe_command(nvg) -> None:
    """A well-formed command that is not a git --no-verify bypass passes."""
    assert nvg._is_no_verify_attempt("git status") is False
    assert nvg._is_no_verify_attempt("python3 -c \"print('--no-verify')\"") is False


def test_no_verify_guard_still_blocks_real_attempt(nvg) -> None:
    """The original deny contract still holds for a genuine attempt."""
    assert nvg._is_no_verify_attempt("git commit --no-verify -m x") is True
