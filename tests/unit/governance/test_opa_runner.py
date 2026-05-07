"""Tests for ``governance.opa_runner`` (spec-122 Phase C, T-3.6).

Subprocess-mocked unit tests covering:

(a) successful allow verdict (data.allow returns true)
(b) deny with messages (data.deny returns set of strings)
(c) missing binary -> OpaError
(d) timeout escalation -> OpaError
(e) malformed JSON output -> OpaError
(f) bundle path forwarding
(g) version() parses Version: line
(h) which() / available() memoisation contract
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from ai_engineering.governance import opa_runner


@pytest.fixture(autouse=True)
def _reset_path_cache() -> Any:
    """Each test starts AND ends with a clean which() cache.

    Tests in this file ``monkeypatch.setattr(opa_runner.shutil, "which", ...)``
    which propagates into ``opa_runner.which()``'s memoisation and leaks
    across test files (the cache is module-level state in
    ``opa_runner``). Resetting on teardown keeps neighbouring suites
    such as ``test_policy_engine`` clean.
    """
    opa_runner.reset_path_cache()
    yield
    opa_runner.reset_path_cache()


# ---------------------------------------------------------------------------
# (a) allow verdict
# ---------------------------------------------------------------------------


def test_evaluate_returns_allow_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")

    fake_stdout = json.dumps(
        {"result": [{"expressions": [{"value": True, "text": "data.x.allow"}]}]},
    )

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout=fake_stdout, stderr=""
        )

    monkeypatch.setattr(opa_runner.subprocess, "run", fake_run)

    result = opa_runner.evaluate("data.x.allow", {"k": "v"})
    assert result.allow is True
    assert result.deny_messages == []
    assert result.raw["result"][0]["expressions"][0]["value"] is True


# ---------------------------------------------------------------------------
# (b) deny with messages
# ---------------------------------------------------------------------------


def test_evaluate_returns_deny_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")

    fake_stdout = json.dumps(
        {
            "result": [
                {
                    "expressions": [
                        {
                            "value": ["push to protected branch denied"],
                            "text": "data.branch_protection.deny",
                        },
                    ],
                },
            ],
        },
    )

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout=fake_stdout, stderr=""
        )

    monkeypatch.setattr(opa_runner.subprocess, "run", fake_run)

    result = opa_runner.evaluate("data.branch_protection.deny", {"branch": "main"})
    assert result.allow is False
    assert result.deny_messages == ["push to protected branch denied"]


def test_evaluate_deny_empty_set_yields_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")

    fake_stdout = json.dumps(
        {"result": [{"expressions": [{"value": [], "text": "data.x.deny"}]}]},
    )

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout=fake_stdout, stderr=""
        )

    monkeypatch.setattr(opa_runner.subprocess, "run", fake_run)

    result = opa_runner.evaluate("data.x.deny", {})
    assert result.allow is False  # empty deny is not affirmative allow
    assert result.deny_messages == []


# ---------------------------------------------------------------------------
# (c) missing binary
# ---------------------------------------------------------------------------


def test_evaluate_raises_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: None)
    with pytest.raises(opa_runner.OpaError, match="opa not installed"):
        opa_runner.evaluate("data.x.allow", {})


def test_version_raises_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: None)
    with pytest.raises(opa_runner.OpaError, match="opa not installed"):
        opa_runner.version()


# ---------------------------------------------------------------------------
# (d) timeout escalation
# ---------------------------------------------------------------------------


def test_evaluate_raises_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="opa eval", timeout=1.0)

    monkeypatch.setattr(opa_runner.subprocess, "run", fake_run)

    with pytest.raises(opa_runner.OpaError, match="timed out"):
        opa_runner.evaluate("data.x.allow", {}, timeout=1.0)


# ---------------------------------------------------------------------------
# (e) malformed JSON
# ---------------------------------------------------------------------------


def test_evaluate_raises_on_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="not json",
            stderr="",
        )

    monkeypatch.setattr(opa_runner.subprocess, "run", fake_run)

    with pytest.raises(opa_runner.OpaError, match="malformed JSON"):
        opa_runner.evaluate("data.x.allow", {})


def test_evaluate_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="some error",
        )

    monkeypatch.setattr(opa_runner.subprocess, "run", fake_run)

    with pytest.raises(opa_runner.OpaError, match="exited with code 1"):
        opa_runner.evaluate("data.x.allow", {})


# ---------------------------------------------------------------------------
# (f) bundle path forwarding
# ---------------------------------------------------------------------------


def test_evaluate_forwards_bundle_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")
    captured: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["argv"] = args[0]
        captured["input"] = kwargs.get("input")
        fake_stdout = json.dumps({"result": [{"expressions": [{"value": True}]}]})
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout=fake_stdout, stderr=""
        )

    monkeypatch.setattr(opa_runner.subprocess, "run", fake_run)

    opa_runner.evaluate("data.x.allow", {"k": 1}, bundle_path=Path("/tmp/custom-bundle"))

    argv = captured["argv"]
    assert "--bundle" in argv
    assert "/tmp/custom-bundle" in argv
    assert "--stdin-input" in argv
    assert "--format" in argv
    assert "json" in argv
    # input piped as JSON stdin payload
    assert json.loads(captured["input"]) == {"k": 1}


def test_evaluate_default_bundle_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")
    captured: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["argv"] = args[0]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps({"result": [{"expressions": [{"value": True}]}]}),
            stderr="",
        )

    monkeypatch.setattr(opa_runner.subprocess, "run", fake_run)

    opa_runner.evaluate("data.x.allow", None)
    assert str(opa_runner.DEFAULT_BUNDLE_PATH) in captured["argv"]


# ---------------------------------------------------------------------------
# (g) version() parsing
# ---------------------------------------------------------------------------


def test_version_parses_version_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="Version: 1.16.1\nGo Version: go1.26.2\n",
            stderr="",
        )

    monkeypatch.setattr(opa_runner.subprocess, "run", fake_run)
    assert opa_runner.version() == "1.16.1"


def test_version_raises_when_line_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="something else entirely\n",
            stderr="",
        )

    monkeypatch.setattr(opa_runner.subprocess, "run", fake_run)
    with pytest.raises(opa_runner.OpaError, match="missing 'Version:'"):
        opa_runner.version()


# ---------------------------------------------------------------------------
# (h) memoisation contract
# ---------------------------------------------------------------------------


def test_which_memoises_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def fake_which(_: str) -> str | None:
        calls["count"] += 1
        return "/fake/opa"

    monkeypatch.setattr(opa_runner.shutil, "which", fake_which)
    assert opa_runner.which() == "/fake/opa"
    assert opa_runner.which() == "/fake/opa"
    assert opa_runner.which() == "/fake/opa"
    assert calls["count"] == 1, "shutil.which must be called exactly once"


def test_available_reflects_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: "/fake/opa")
    assert opa_runner.available() is True

    opa_runner.reset_path_cache()
    monkeypatch.setattr(opa_runner.shutil, "which", lambda _: None)
    assert opa_runner.available() is False
