"""Unit tests for ai_engineering.cli_commands.sync module."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

import ai_engineering.cli_commands.sync as sync_module

pytestmark = pytest.mark.unit


def _create_sync_script(root: Path) -> Path:
    script = root / "scripts" / "sync_command_mirrors.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("print('ok')\n", encoding="utf-8")
    return script


def test_missing_script_json_mode_emits_structured_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sync_module, "resolve_project_root", lambda _: tmp_path)
    monkeypatch.setattr(sync_module, "is_json_mode", lambda: True)

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(sync_module, "emit_error", lambda **kwargs: calls.append(kwargs))

    with pytest.raises(typer.Exit) as exc:
        sync_module.sync_cmd()

    assert exc.value.exit_code == 1
    assert len(calls) == 1
    assert calls[0]["code"] == "SCRIPT_NOT_FOUND"
    assert "sync_command_mirrors.py" in str(calls[0]["message"])


def test_missing_script_non_json_writes_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sync_module, "resolve_project_root", lambda _: tmp_path)
    monkeypatch.setattr(sync_module, "is_json_mode", lambda: False)

    output: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        sync_module.typer,
        "echo",
        lambda msg, err=False: output.append((str(msg), bool(err))),
    )

    with pytest.raises(typer.Exit) as exc:
        sync_module.sync_cmd()

    assert exc.value.exit_code == 1
    assert output
    assert "sync script not found" in output[0][0]
    assert output[0][1] is True


def test_success_non_json_runs_check_and_verbose_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    script = _create_sync_script(tmp_path)

    monkeypatch.setattr(sync_module, "resolve_project_root", lambda _: tmp_path)
    monkeypatch.setattr(sync_module, "is_json_mode", lambda: False)

    actions: list[str] = []
    monkeypatch.setattr(
        sync_module, "spinner", lambda action: actions.append(action) or nullcontext()
    )

    calls: dict[str, object] = {}

    def fake_run(cmd: list[str], *, capture_output: bool, text: bool, cwd: str) -> SimpleNamespace:
        calls["cmd"] = cmd
        calls["capture_output"] = capture_output
        calls["text"] = text
        calls["cwd"] = cwd
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sync_module.subprocess, "run", fake_run)

    headers: list[tuple[str, str, str]] = []
    status: list[tuple[str, str, str]] = []
    monkeypatch.setattr(sync_module, "result_header", lambda *args: headers.append(args))
    monkeypatch.setattr(sync_module, "status_line", lambda *args: status.append(args))

    sync_module.sync_cmd(check=True, verbose=True)

    assert actions == ["Checking mirror sync..."]
    assert calls["cmd"] == [sync_module.sys.executable, str(script), "--check", "--verbose"]
    assert calls["cwd"] == str(tmp_path)
    assert calls["capture_output"] is True
    assert calls["text"] is True
    assert headers == [("Sync", "PASS", str(tmp_path))]
    assert status == [("ok", "Mirrors", "in sync")]


def test_success_json_mode_emits_success_envelope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _create_sync_script(tmp_path)

    monkeypatch.setattr(sync_module, "resolve_project_root", lambda _: tmp_path)
    monkeypatch.setattr(sync_module, "is_json_mode", lambda: True)
    monkeypatch.setattr(sync_module, "spinner", lambda _action: nullcontext())
    monkeypatch.setattr(
        sync_module.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(sync_module, "emit_success", lambda *args: calls.append(args))

    sync_module.sync_cmd(check=False)

    assert len(calls) == 1
    assert calls[0][0] == "ai-eng sync"
    assert calls[0][1] == {"status": "in_sync", "check": False}
    next_actions = calls[0][2]
    assert len(next_actions) == 1
    assert next_actions[0].command == "ai-eng validate"


def test_drift_non_json_reports_stdout_and_next_step(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _create_sync_script(tmp_path)

    monkeypatch.setattr(sync_module, "resolve_project_root", lambda _: tmp_path)
    monkeypatch.setattr(sync_module, "is_json_mode", lambda: False)
    monkeypatch.setattr(sync_module, "spinner", lambda _action: nullcontext())
    monkeypatch.setattr(
        sync_module.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=1, stdout="drift details", stderr=""),
    )

    headers: list[tuple[str, str, str]] = []
    statuses: list[tuple[str, str, str]] = []
    next_calls: list[list[tuple[str, str]]] = []
    stderr: list[tuple[str, bool]] = []

    monkeypatch.setattr(sync_module, "result_header", lambda *args: headers.append(args))
    monkeypatch.setattr(sync_module, "status_line", lambda *args: statuses.append(args))
    monkeypatch.setattr(sync_module, "suggest_next", lambda items: next_calls.append(items))
    monkeypatch.setattr(
        sync_module.typer,
        "echo",
        lambda msg, err=False: stderr.append((str(msg), bool(err))),
    )

    with pytest.raises(typer.Exit) as exc:
        sync_module.sync_cmd(check=True)

    assert exc.value.exit_code == 1
    assert headers == [("Sync", "FAIL", str(tmp_path))]
    assert statuses == [("fail", "Mirrors", "drift detected")]
    assert stderr == [("drift details", True)]
    assert next_calls == [[("ai-eng sync", "Apply sync to fix drift")]]


def test_drift_json_mode_emits_drift_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _create_sync_script(tmp_path)

    monkeypatch.setattr(sync_module, "resolve_project_root", lambda _: tmp_path)
    monkeypatch.setattr(sync_module, "is_json_mode", lambda: True)
    monkeypatch.setattr(sync_module, "spinner", lambda _action: nullcontext())
    monkeypatch.setattr(
        sync_module.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=1, stdout="", stderr=""),
    )

    errors: list[dict[str, object]] = []
    monkeypatch.setattr(sync_module, "emit_error", lambda **kwargs: errors.append(kwargs))

    with pytest.raises(typer.Exit) as exc:
        sync_module.sync_cmd(check=True)

    assert exc.value.exit_code == 1
    assert len(errors) == 1
    assert errors[0]["code"] == "DRIFT"


def test_validation_failure_non_json_echoes_stderr_and_stdout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _create_sync_script(tmp_path)

    monkeypatch.setattr(sync_module, "resolve_project_root", lambda _: tmp_path)
    monkeypatch.setattr(sync_module, "is_json_mode", lambda: False)
    monkeypatch.setattr(sync_module, "spinner", lambda _action: nullcontext())
    monkeypatch.setattr(
        sync_module.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=2, stdout="stdout text", stderr="stderr text"),
    )

    headers: list[tuple[str, str, str]] = []
    statuses: list[tuple[str, str, str]] = []
    output: list[tuple[str, bool]] = []
    monkeypatch.setattr(sync_module, "result_header", lambda *args: headers.append(args))
    monkeypatch.setattr(sync_module, "status_line", lambda *args: statuses.append(args))
    monkeypatch.setattr(
        sync_module.typer,
        "echo",
        lambda msg, err=False: output.append((str(msg), bool(err))),
    )

    with pytest.raises(typer.Exit) as exc:
        sync_module.sync_cmd(verbose=True)

    assert exc.value.exit_code == 1
    assert headers == [("Sync", "FAIL", str(tmp_path))]
    assert statuses == [("fail", "Canonical validation", "failed")]
    assert ("stderr text", True) in output
    assert ("stdout text", True) in output


def test_validation_failure_json_mode_emits_validation_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _create_sync_script(tmp_path)

    monkeypatch.setattr(sync_module, "resolve_project_root", lambda _: tmp_path)
    monkeypatch.setattr(sync_module, "is_json_mode", lambda: True)
    monkeypatch.setattr(sync_module, "spinner", lambda _action: nullcontext())
    monkeypatch.setattr(
        sync_module.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=42, stdout="", stderr=""),
    )

    errors: list[dict[str, object]] = []
    monkeypatch.setattr(sync_module, "emit_error", lambda **kwargs: errors.append(kwargs))

    with pytest.raises(typer.Exit) as exc:
        sync_module.sync_cmd()

    assert exc.value.exit_code == 1
    assert len(errors) == 1
    assert errors[0]["code"] == "VALIDATION_ERROR"
