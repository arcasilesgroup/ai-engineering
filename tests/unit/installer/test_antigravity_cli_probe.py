"""Tests for Antigravity CLI runtime diagnostics."""

from __future__ import annotations

import subprocess

from ai_engineering.installer.antigravity import find_agy_binary, probe_agy_cli


def test_find_agy_binary_prefers_posix_binary() -> None:
    def which(name: str) -> str | None:
        return {"agy": "/usr/local/bin/agy", "agy.exe": "C:/agy.exe"}.get(name)

    assert find_agy_binary(which=which) == "/usr/local/bin/agy"


def test_find_agy_binary_falls_back_to_windows_binary() -> None:
    def which(name: str) -> str | None:
        return {"agy.exe": "C:/tools/agy.exe"}.get(name)

    assert find_agy_binary(which=which) == "C:/tools/agy.exe"


def test_probe_agy_cli_missing_binary_is_fail_soft() -> None:
    result = probe_agy_cli(which=lambda _name: None)

    assert result.available is False
    assert result.binary is None
    assert result.version is None
    assert "not found" in result.reason


def test_probe_agy_cli_returns_version_when_available() -> None:
    def which(name: str) -> str | None:
        return "/opt/bin/agy" if name == "agy" else None

    def run(*_args, **_kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["agy", "--version"], 0, stdout="agy 2.0.1\n")

    result = probe_agy_cli(which=which, run=run)

    assert result.available is True
    assert result.binary == "/opt/bin/agy"
    assert result.version == "agy 2.0.1"


def test_probe_agy_cli_command_failure_is_fail_soft() -> None:
    def which(name: str) -> str | None:
        return "/opt/bin/agy" if name == "agy" else None

    def run(*_args, **_kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["agy", "--version"], 2, stderr="not ready\n")

    result = probe_agy_cli(which=which, run=run)

    assert result.available is False
    assert result.binary == "/opt/bin/agy"
    assert result.version == "not ready"
    assert "status 2" in result.reason
