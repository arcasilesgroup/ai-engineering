"""Tests for stack-drift CLI middleware (spec-133 D-133-23, D-133-24)."""

from __future__ import annotations

import os
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


def test_middleware_silent_when_no_drift(tmp_path: Path) -> None:
    _write_manifest(tmp_path, ["python"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    # No-drift scenario: invoking middleware directly should not emit warning
    # The middleware itself is the unit under test.
    import contextlib

    # Capture stderr
    import io

    from ai_engineering.cli_factory import _stack_drift_middleware

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        # Provide root by chdir
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            _stack_drift_middleware("status")
        finally:
            os.chdir(cwd)
    assert "stack drift" not in err.getvalue()


def test_middleware_emits_warning_on_drift(tmp_path: Path) -> None:
    _write_manifest(tmp_path, ["python"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'rs'\nversion = '0.1.0'\n")

    import contextlib
    import io

    from ai_engineering.cli_factory import _stack_drift_middleware

    err = io.StringIO()
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        with contextlib.redirect_stderr(err):
            _stack_drift_middleware("status")
    finally:
        os.chdir(cwd)
    assert "stack drift" in err.getvalue().lower()
    assert "rust" in err.getvalue()


def test_middleware_blocks_in_strict_mode_for_commit(tmp_path: Path) -> None:
    _write_manifest(tmp_path, ["python"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'rs'\nversion = '0.1.0'\n")

    import typer

    from ai_engineering.cli_factory import _stack_drift_middleware

    cwd = os.getcwd()
    os.environ["AIENG_STACK_DRIFT_STRICT"] = "1"
    try:
        os.chdir(tmp_path)
        with pytest.raises(typer.Exit) as excinfo:
            _stack_drift_middleware("commit")
        assert excinfo.value.exit_code == 78
    finally:
        os.chdir(cwd)
        del os.environ["AIENG_STACK_DRIFT_STRICT"]


def test_middleware_exempts_install(tmp_path: Path) -> None:
    _write_manifest(tmp_path, ["python"])
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'rs'\nversion = '0.1.0'\n")

    import contextlib
    import io

    from ai_engineering.cli_factory import _stack_drift_middleware

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            _stack_drift_middleware("install")
        assert err.getvalue() == ""
    finally:
        os.chdir(cwd)


def test_middleware_silent_in_greenfield(tmp_path: Path) -> None:
    """No stack markers = nothing to drift against."""
    _write_manifest(tmp_path, ["python"])
    import contextlib
    import io

    from ai_engineering.cli_factory import _stack_drift_middleware

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            _stack_drift_middleware("status")
        # No project markers => detected is empty => no drift
        assert "stack drift" not in err.getvalue().lower()
    finally:
        os.chdir(cwd)


def test_middleware_strict_warn_only_for_status(tmp_path: Path) -> None:
    """Strict mode warns but doesn't block read-only commands."""
    _write_manifest(tmp_path, ["python"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'rs'\nversion = '0.1.0'\n")

    import contextlib
    import io

    from ai_engineering.cli_factory import _stack_drift_middleware

    cwd = os.getcwd()
    os.environ["AIENG_STACK_DRIFT_STRICT"] = "1"
    try:
        os.chdir(tmp_path)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            # Non-blocking command — should warn, not raise
            _stack_drift_middleware("status")
        assert "stack drift" in err.getvalue().lower()
    finally:
        os.chdir(cwd)
        del os.environ["AIENG_STACK_DRIFT_STRICT"]
