"""Tests for stack-drift CLI middleware (spec-133 D-133-23, D-133-24)."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import pytest

_AI_ENG = "ai-eng"


def _write_manifest(root: Path, stacks: list[str]) -> None:
    """Helper: write a manifest with given stacks."""
    (root / ".ai-engineering").mkdir(parents=True, exist_ok=True)
    yml = root / ".ai-engineering" / "manifest.yml"
    yml.write_text(
        "schema_version: '2.0'\n"
        "framework_version: '0.4.0'\n"
        "name: test\n"
        "providers:\n"
        f"  stacks: [{', '.join(stacks)}]\n"
        "  vcs: github\n",
        encoding="utf-8",
    )


def test_middleware_silent_when_no_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_manifest(tmp_path, ["python"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

    from ai_engineering.cli_factory import _stack_drift_middleware

    monkeypatch.chdir(tmp_path)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        _stack_drift_middleware("status")
    assert "stack drift" not in err.getvalue()


def test_middleware_emits_warning_on_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_manifest(tmp_path, ["python"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'rs'\nversion = '0.1.0'\n")

    from ai_engineering.cli_factory import _stack_drift_middleware

    monkeypatch.chdir(tmp_path)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        _stack_drift_middleware("status")
    assert "stack drift" in err.getvalue().lower()
    assert "rust" in err.getvalue()


def test_middleware_blocks_in_strict_mode_for_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_manifest(tmp_path, ["python"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'rs'\nversion = '0.1.0'\n")

    import typer

    from ai_engineering.cli_factory import _stack_drift_middleware

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIENG_STACK_DRIFT_STRICT", "1")
    with pytest.raises(typer.Exit) as excinfo:
        _stack_drift_middleware("commit")
    assert excinfo.value.exit_code == 78


def test_middleware_exempts_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_manifest(tmp_path, ["python"])
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'rs'\nversion = '0.1.0'\n")

    from ai_engineering.cli_factory import _stack_drift_middleware

    monkeypatch.chdir(tmp_path)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        _stack_drift_middleware("install")
    assert err.getvalue() == ""


def test_middleware_silent_in_greenfield(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No stack markers = nothing to drift against."""
    _write_manifest(tmp_path, ["python"])

    from ai_engineering.cli_factory import _stack_drift_middleware

    monkeypatch.chdir(tmp_path)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        _stack_drift_middleware("status")
    assert "stack drift" not in err.getvalue().lower()


def test_middleware_strict_warn_only_for_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Strict mode warns but doesn't block read-only commands."""
    _write_manifest(tmp_path, ["python"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'rs'\nversion = '0.1.0'\n")

    from ai_engineering.cli_factory import _stack_drift_middleware

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIENG_STACK_DRIFT_STRICT", "1")
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        _stack_drift_middleware("status")
    assert "stack drift" in err.getvalue().lower()
