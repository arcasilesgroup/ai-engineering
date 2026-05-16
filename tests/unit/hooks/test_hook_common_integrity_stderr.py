"""Tests for the integrity-violation stderr fix (spec-131 sub-004 T-4.C).

`_lib/hook-common.py:526-529` previously emitted ``sys.exit(2)`` on
enforce-mode integrity mismatch without writing to stderr first. Operators
saw an empty deny with no actionable signal AND could not distinguish from
the injection-deny exit code 2. The fix:

* Write a one-line ``[hook-integrity]`` reason + a remediation hint
  (``regenerate-hooks-manifest.py``) to stderr before exiting.
* Use exit code ``3`` so operators can tell integrity drift apart from
  injection deny (2).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_COMMON_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "hook-common.py"


@pytest.fixture
def hc(monkeypatch: pytest.MonkeyPatch):
    """Load ``_lib/hook-common.py`` under a fresh module name."""
    sys.modules.pop("aieng_lib_hook_common_integrity", None)
    spec = importlib.util.spec_from_file_location(
        "aieng_lib_hook_common_integrity", HOOK_COMMON_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_lib_hook_common_integrity"] = module
    spec.loader.exec_module(module)
    return module


def test_enforce_mode_integrity_failure_exits_3(
    hc, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Enforce-mode mismatch must exit 3 and write a stderr reason."""

    # Force enforce mode + force the integrity check to fail.
    def _fail(*args, **kwargs):
        return False, "sha256 mismatch (expected aaaaaaaaaaaa…, got bbbbbbbbbbbb…)", "enforce"

    monkeypatch.setattr(hc, "_verify_caller_integrity", _fail)
    monkeypatch.setattr(hc, "_emit_integrity_violation", lambda **kw: None)

    def _main():  # pragma: no cover - reached after exit if regression
        return None

    with pytest.raises(SystemExit) as exc_info:
        hc.run_hook_safe(
            _main,
            component="hook.test",
            hook_kind="pre-tool-use",
            script_path=Path("/tmp/fake-hook.py"),
        )
    assert exc_info.value.code == 3

    captured = capsys.readouterr()
    assert "[hook-integrity]" in captured.err
    assert "regenerate-hooks-manifest.py" in captured.err


def test_enforce_mode_writes_reason_line(
    hc, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The first stderr line must carry the specific reason for the failure."""

    def _fail(*args, **kwargs):
        return False, "hook foo not enrolled in hooks-manifest.json", "enforce"

    monkeypatch.setattr(hc, "_verify_caller_integrity", _fail)
    monkeypatch.setattr(hc, "_emit_integrity_violation", lambda **kw: None)

    with pytest.raises(SystemExit):
        hc.run_hook_safe(
            lambda: None,
            component="hook.test",
            hook_kind="pre-tool-use",
            script_path=Path("/tmp/fake-hook.py"),
        )
    captured = capsys.readouterr()
    assert "not enrolled" in captured.err


def test_warn_mode_does_not_block(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    """Warn mode keeps the hook running (existing semantics) — no SystemExit(3)."""

    def _warn(*args, **kwargs):
        return True, "sha256 mismatch", "warn"

    monkeypatch.setattr(hc, "_verify_caller_integrity", _warn)
    monkeypatch.setattr(hc, "_emit_integrity_violation", lambda **kw: None)
    monkeypatch.setattr(hc, "_emit_hook_heartbeat", lambda **kw: None)

    with pytest.raises(SystemExit) as exc_info:
        hc.run_hook_safe(
            lambda: None,
            component="hook.test",
            hook_kind="pre-tool-use",
            script_path=Path("/tmp/fake-hook.py"),
        )
    # run_hook_safe always exits — but with code 0 on success in warn mode.
    assert exc_info.value.code == 0


def test_healthy_path_does_not_emit_stderr(
    hc, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No integrity violation -> no stderr noise."""

    def _ok(*args, **kwargs):
        return True, None, "warn"

    monkeypatch.setattr(hc, "_verify_caller_integrity", _ok)
    monkeypatch.setattr(hc, "_emit_hook_heartbeat", lambda **kw: None)

    with pytest.raises(SystemExit) as exc_info:
        hc.run_hook_safe(
            lambda: None,
            component="hook.test",
            hook_kind="pre-tool-use",
            script_path=Path("/tmp/fake-hook.py"),
        )
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "[hook-integrity]" not in captured.err
