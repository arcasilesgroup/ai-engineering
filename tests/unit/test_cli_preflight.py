"""RED tests for CLI bootstrap preflight behavior in spec-102."""

from __future__ import annotations

import importlib
import runpy
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest


def test_cli_module_runs_preflight_before_create_app(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []
    fake_preflight = ModuleType("ai_engineering.cli_preflight")

    def _preflight_check() -> None:
        order.append("preflight")

    fake_preflight.preflight_check = _preflight_check
    monkeypatch.setitem(sys.modules, "ai_engineering.cli_preflight", fake_preflight)

    def _create_app() -> object:
        order.append("create_app")
        return object()

    with patch("ai_engineering.cli_factory.create_app", side_effect=_create_app):
        runpy.run_module("ai_engineering.cli", run_name="ai_engineering.cli")

    assert order == ["preflight", "create_app"]


def test_preflight_fails_fast_for_unsupported_python(monkeypatch: pytest.MonkeyPatch) -> None:
    cli_preflight = importlib.import_module("ai_engineering.cli_preflight")
    fatal_messages: list[str] = []

    monkeypatch.setattr(cli_preflight.sys, "version_info", (3, 10, 12), raising=False)
    monkeypatch.setattr(
        cli_preflight,
        "_emit_fatal",
        lambda message: fatal_messages.append(message),
        raising=False,
    )

    with pytest.raises(SystemExit):
        cli_preflight.preflight_check()

    assert fatal_messages
    assert "3.11" in fatal_messages[0]


def test_preflight_attempts_packaging_repair_for_broken_dependency_closure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli_preflight = importlib.import_module("ai_engineering.cli_preflight")
    repair_calls: list[str] = []

    monkeypatch.setattr(cli_preflight, "_validate_python_version", lambda: None, raising=False)
    monkeypatch.setattr(cli_preflight, "_validate_interpreter", lambda: None, raising=False)

    def _raise_broken_closure() -> None:
        raise ImportError("typer/click incompatibility")

    monkeypatch.setattr(
        cli_preflight,
        "_validate_dependency_closure",
        _raise_broken_closure,
        raising=False,
    )
    monkeypatch.setattr(
        cli_preflight,
        "_classify_failure",
        lambda exc, context=None: "packaging",
        raising=False,
    )
    monkeypatch.setattr(
        cli_preflight,
        "_attempt_packaging_repair",
        lambda exc: repair_calls.append(str(exc)) or True,
        raising=False,
    )

    cli_preflight.preflight_check()

    assert repair_calls == ["typer/click incompatibility"]


def test_attempt_packaging_repair_reinstalls_broken_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli_preflight = importlib.import_module("ai_engineering.cli_preflight")
    dependency_closure = importlib.import_module("ai_engineering.doctor.dependency_closure")
    commands: list[list[str]] = []
    violation = dependency_closure.ClosureViolation(
        package="typer",
        dependency="click",
        required_specifier=">=8.2.1",
        actual_version="8.1.8",
    )
    validations = [[violation], []]

    monkeypatch.setattr(
        cli_preflight,
        "validate_framework_dependency_closure",
        lambda: validations.pop(0),
        raising=False,
    )
    monkeypatch.setattr(cli_preflight, "_find_repo_root", lambda path: Path("/repo"), raising=False)
    monkeypatch.setattr(cli_preflight.shutil, "which", lambda cmd: "uv", raising=False)

    def _run(cmd: list[str], **_: object) -> object:
        commands.append(cmd)
        return object()

    monkeypatch.setattr(cli_preflight.subprocess, "run", _run, raising=False)

    repaired = cli_preflight._attempt_packaging_repair(ImportError("broken closure"))

    assert repaired is True
    assert commands == [["uv", "sync", "--dev"]]


def test_attempt_packaging_repair_returns_false_when_environment_is_not_repairable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli_preflight = importlib.import_module("ai_engineering.cli_preflight")
    dependency_closure = importlib.import_module("ai_engineering.doctor.dependency_closure")
    violation = dependency_closure.ClosureViolation(
        package="typer",
        dependency="click",
        required_specifier=">=8.2.1",
        actual_version="8.1.8",
    )

    monkeypatch.setattr(
        cli_preflight,
        "validate_framework_dependency_closure",
        lambda: [violation],
        raising=False,
    )
    monkeypatch.setattr(cli_preflight, "_find_repo_root", lambda path: None, raising=False)

    assert cli_preflight._attempt_packaging_repair(ImportError("broken closure")) is False


def test_render_fatal_message_for_packaging_failure_includes_manual_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli_preflight = importlib.import_module("ai_engineering.cli_preflight")

    monkeypatch.setattr(cli_preflight, "_find_repo_root", lambda path: None, raising=False)

    message = cli_preflight._render_fatal_message(
        ImportError("typer requires click>=8.2.1 but found 8.1.8"),
        "packaging",
    )

    assert "Automatic repair is not supported in this environment" in message
