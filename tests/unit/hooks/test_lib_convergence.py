"""Tests for ``_lib/convergence.py`` — the Ralph Loop convergence checker.

Convergence is the gate that decides whether the Stop hook reinjects
``additionalContext`` for another loop iteration or releases the
session. The contract this suite pins:

* **Success path.** All checks exit 0 → ``ConvergenceResult.converged
  is True`` and ``failures == []``.
* **Failure-collection.** Each failing check appends ONE entry to
  ``failures`` with a human-readable reason.
* **Missing tools.** :func:`shutil.which` returning ``None`` means
  the tool is skipped silently — never a failure.
* **Timeout.** ``subprocess.TimeoutExpired`` becomes a failure entry
  (the loop must see it; the alternative — silent skip — would mask
  hung test suites).
* **fast vs full mode.** ``fast=True`` skips the full pytest run.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LIB_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "convergence.py"


@pytest.fixture
def conv(monkeypatch: pytest.MonkeyPatch):
    """Load the convergence module fresh per test (monkey-safe)."""
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_convergence_lib", None)
    spec = importlib.util.spec_from_file_location("aieng_convergence_lib", LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_convergence_lib"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _python_project(tmp_path: Path) -> None:
    """Mark ``tmp_path`` as a Python project (spec-158 D-158-11).

    Convergence now runs the Python lint+test tools ONLY in a Python project
    (marker file present). Existing tests exercise ruff/pytest against
    ``tmp_path``, so a ``pyproject.toml`` marker keeps them meaningful. Tests
    that need a NON-Python project use a marker-less subdirectory instead.
    """
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 't'\n", encoding="utf-8")


class _CompletedProcStub:
    """Minimal stand-in for ``subprocess.CompletedProcess``."""

    def __init__(
        self,
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _stub_run(rc_by_arg0: dict[str, _CompletedProcStub]):
    """Build a ``subprocess.run`` replacement that dispatches on ``cmd[0]``.

    Falls back to a generic exit-0 stub for any binary not in the map
    so peripheral commands (e.g. ``git``) never accidentally trip a test.
    """
    default = _CompletedProcStub(returncode=0)

    def _run(cmd, **_kwargs):
        head = cmd[0] if cmd else ""
        # Match by the *script* invocation too, for ANY interpreter — incl.
        # ``sys.executable`` (spec-158 D-158-10): "<interp> -m pytest …".
        if len(cmd) > 2 and cmd[1] == "-m":
            key = f"{head} -m {cmd[2]}"
            if key in rc_by_arg0:
                return rc_by_arg0[key]
            # Try the generic module key too (e.g. "pytest").
            if cmd[2] in rc_by_arg0:
                return rc_by_arg0[cmd[2]]
        return rc_by_arg0.get(head, default)

    return _run


def test_converged_when_no_checks_fail(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")
    monkeypatch.setattr(
        conv.subprocess,
        "run",
        _stub_run(
            {
                "ruff": _CompletedProcStub(returncode=0),
                "pytest": _CompletedProcStub(returncode=0),
                "git": _CompletedProcStub(returncode=0),
            }
        ),
    )
    result = conv.check_convergence(tmp_path, fast=True)
    assert result.converged is True
    assert result.failures == []


def test_failures_collected_from_ruff(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")
    monkeypatch.setattr(
        conv.subprocess,
        "run",
        _stub_run(
            {
                "ruff": _CompletedProcStub(returncode=1, stderr="found 3 issues\n"),
                "pytest": _CompletedProcStub(returncode=0),
                "git": _CompletedProcStub(returncode=0),
            }
        ),
    )
    result = conv.check_convergence(tmp_path, fast=True)
    assert result.converged is False
    assert any("ruff check" in f for f in result.failures)
    assert any("found 3 issues" in f for f in result.failures)


def test_failures_collected_from_pytest(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")
    monkeypatch.setattr(
        conv.subprocess,
        "run",
        _stub_run(
            {
                "ruff": _CompletedProcStub(returncode=0),
                "pytest": _CompletedProcStub(returncode=1, stderr="ImportError: bad module\n"),
                "git": _CompletedProcStub(returncode=0),
            }
        ),
    )
    result = conv.check_convergence(tmp_path, fast=True)
    assert result.converged is False
    assert any("pytest collect" in f for f in result.failures)


def test_missing_tools_skipped_silently(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``shutil.which`` returning None for ruff must produce zero failures."""
    monkeypatch.setattr(
        conv.shutil,
        "which",
        lambda name: None if name == "ruff" else f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        conv.subprocess,
        "run",
        _stub_run(
            {
                "pytest": _CompletedProcStub(returncode=0),
                "git": _CompletedProcStub(returncode=0),
            }
        ),
    )
    result = conv.check_convergence(tmp_path, fast=True)
    # ruff missing ≠ failure; pytest collect succeeded → converged.
    assert result.converged is True
    assert result.failures == []


def test_timeout_treated_as_failure(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")

    def _run(cmd, **_kwargs):
        if cmd and cmd[0] == "ruff":
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=5)
        return _CompletedProcStub(returncode=0)

    monkeypatch.setattr(conv.subprocess, "run", _run)
    result = conv.check_convergence(tmp_path, fast=True)
    assert result.converged is False
    assert any("ruff check" in f and "timeout" in f for f in result.failures)


def test_fast_vs_full_mode(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``fast=True`` runs collect-only; ``fast=False`` adds the full pytest run."""
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")
    calls: list[list[str]] = []

    def _run(cmd, **_kwargs):
        calls.append(list(cmd))
        return _CompletedProcStub(returncode=0)

    monkeypatch.setattr(conv.subprocess, "run", _run)

    # Fast: should NOT include "-x --tb=no" pytest run.
    calls.clear()
    fast_result = conv.check_convergence(tmp_path, fast=True)
    fast_pytest_cmds = [c for c in calls if "pytest" in c]
    assert any("--collect-only" in c for c in fast_pytest_cmds)
    assert not any("-x" in c for c in fast_pytest_cmds)
    assert fast_result.converged is True

    # Full: collect-only AND a -x run.
    calls.clear()
    full_result = conv.check_convergence(tmp_path, fast=False)
    full_pytest_cmds = [c for c in calls if "pytest" in c]
    assert any("--collect-only" in c for c in full_pytest_cmds)
    assert any("-x" in c for c in full_pytest_cmds)
    # ``ruff format --check`` is a "full mode" extra.
    assert any(c[:3] == ["ruff", "format", "--check"] for c in calls)
    assert full_result.converged is True


def test_pytest_exit_5_no_tests_is_not_a_failure(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pytest exit 5 ('no tests collected') is fail-open: nothing to verify."""
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")
    monkeypatch.setattr(
        conv.subprocess,
        "run",
        _stub_run(
            {
                "ruff": _CompletedProcStub(returncode=0),
                "pytest": _CompletedProcStub(returncode=5),
                "git": _CompletedProcStub(returncode=0),
            }
        ),
    )
    result = conv.check_convergence(tmp_path, fast=True)
    assert result.converged is True
    assert result.failures == []


def test_filenotfound_treated_as_failure_when_tool_advertised_present(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``shutil.which`` lied; subsequent ``run`` raises FileNotFoundError.

    This is the race condition where the binary was uninstalled between
    probe and call. Surfacing it as a failure beats silent skip.
    """
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")

    def _run(cmd, **_kwargs):
        if cmd and cmd[0] == "ruff":
            raise FileNotFoundError("ruff vanished")
        return _CompletedProcStub(returncode=0)

    monkeypatch.setattr(conv.subprocess, "run", _run)
    result = conv.check_convergence(tmp_path, fast=True)
    assert result.converged is False
    assert any("ruff check" in f for f in result.failures)


def test_duration_ms_populated(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")
    monkeypatch.setattr(
        conv.subprocess,
        "run",
        _stub_run(
            {
                "ruff": _CompletedProcStub(returncode=0),
                "pytest": _CompletedProcStub(returncode=0),
                "git": _CompletedProcStub(returncode=0),
            }
        ),
    )
    result = conv.check_convergence(tmp_path, fast=True)
    assert result.duration_ms >= 0
    # Frozen dataclass — mutability must be rejected.
    with pytest.raises(Exception):  # noqa: B017
        result.duration_ms = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# spec-158 concern C — stack-aware convergence under the resolved interpreter
# ---------------------------------------------------------------------------


def test_pytest_runs_under_resolved_interpreter(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-158-10/AC12: the pytest checks spawn ``sys.executable``, never a bare
    PATH ``python``/``python3`` that may belong to another environment."""
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")
    calls: list[list[str]] = []

    def _run(cmd, **_kwargs):
        calls.append(list(cmd))
        return _CompletedProcStub(returncode=0)

    monkeypatch.setattr(conv.subprocess, "run", _run)
    conv.check_convergence(tmp_path, fast=False)

    pytest_cmds = [c for c in calls if "pytest" in c]
    assert pytest_cmds, "expected at least one pytest invocation in a Python project"
    for c in pytest_cmds:
        assert c[0] == sys.executable, f"pytest must run under sys.executable, got {c[0]!r}"
        assert c[0] not in ("python", "python3")


def test_non_python_project_skips_python_tools(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-158-11/AC13: a non-Python project (no marker) runs NO Python verifier,
    so a TypeScript-only repo never trips a false convergence failure."""
    ts_repo = tmp_path / "ts_repo"
    ts_repo.mkdir()
    (ts_repo / "package.json").write_text('{"name":"x"}', encoding="utf-8")
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")
    calls: list[list[str]] = []

    def _run(cmd, **_kwargs):
        calls.append(list(cmd))
        # Even if invoked, pretend everything fails — must not matter (skipped).
        return _CompletedProcStub(returncode=1, stderr="should never run")

    monkeypatch.setattr(conv.subprocess, "run", _run)
    result = conv.check_convergence(ts_repo, fast=False)

    assert result.converged is True
    assert result.failures == []
    assert not any("pytest" in c for c in calls), "pytest must not run in a TS repo"
    assert not any(c and c[0] == "ruff" for c in calls), "ruff must not run in a TS repo"


def test_pytest_runner_absent_is_fail_open(
    conv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-158-11/AC13: a Python project whose interpreter lacks the test runner
    fails OPEN (nothing to verify), NOT a convergence failure that blocks Stop."""
    monkeypatch.setattr(conv.shutil, "which", lambda _name: f"/usr/bin/{_name}")
    monkeypatch.setattr(
        conv.subprocess,
        "run",
        _stub_run(
            {
                "ruff": _CompletedProcStub(returncode=0),
                "pytest": _CompletedProcStub(returncode=1, stderr="No module named pytest\n"),
                "git": _CompletedProcStub(returncode=0),
            }
        ),
    )
    result = conv.check_convergence(tmp_path, fast=True)
    assert result.converged is True
    assert result.failures == []
