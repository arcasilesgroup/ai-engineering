"""RED tests for spec-101 T-0.11: ``python_env.mode`` schema.

Drives the design of T-0.12 -- the ``PythonEnvMode`` enum and its
manifest loader hook in ``ai_engineering.state.manifest``.

Coverage:

* ``PythonEnvMode`` exposes ``UV_TOOL``, ``VENV``, ``SHARED_PARENT`` members
  with the canonical wire values (``uv-tool``, ``venv``, ``shared-parent``).
* The loader returns ``PythonEnvMode.UV_TOOL`` for each canonical wire value.
* Manifest with no ``python_env`` block -> default ``UV_TOOL`` (per D-101-12).
* Manifest with ``python_env`` block but no ``mode`` key -> default ``UV_TOOL``.
* Manifest with ``python_env.mode: legacy-venv`` (invalid) raises
  ``pydantic.ValidationError``.

These tests intentionally fail (RED phase) -- ``state/manifest.py`` and
``PythonEnvMode`` are introduced by T-0.12.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_engineering.state.manifest import PythonEnvMode, load_python_env_mode

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Create a temp directory with an ``.ai-engineering/`` directory."""
    (tmp_path / ".ai-engineering").mkdir()
    return tmp_path


def _write_manifest(root: Path, body: str) -> None:
    """Write *body* into ``<root>/.ai-engineering/manifest.yml``."""
    (root / ".ai-engineering" / "manifest.yml").write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Enum members + wire values
# ---------------------------------------------------------------------------


class TestPythonEnvModeEnum:
    """``PythonEnvMode`` exposes the three canonical members."""

    def test_uv_tool_member_exists(self) -> None:
        assert PythonEnvMode.UV_TOOL.value == "uv-tool"

    def test_venv_member_exists(self) -> None:
        assert PythonEnvMode.VENV.value == "venv"

    def test_shared_parent_member_exists(self) -> None:
        assert PythonEnvMode.SHARED_PARENT.value == "shared-parent"

    def test_only_three_members(self) -> None:
        assert {m.value for m in PythonEnvMode} == {
            "uv-tool",
            "venv",
            "shared-parent",
        }


# ---------------------------------------------------------------------------
# Valid wire values parse correctly
# ---------------------------------------------------------------------------


class TestValidModes:
    """``load_python_env_mode`` round-trips each canonical wire value."""

    def test_uv_tool_parses(self, tmp_project: Path) -> None:
        _write_manifest(tmp_project, "python_env:\n  mode: uv-tool\n")
        assert load_python_env_mode(tmp_project) is PythonEnvMode.UV_TOOL

    def test_venv_parses(self, tmp_project: Path) -> None:
        _write_manifest(tmp_project, "python_env:\n  mode: venv\n")
        assert load_python_env_mode(tmp_project) is PythonEnvMode.VENV

    def test_shared_parent_parses(self, tmp_project: Path) -> None:
        _write_manifest(tmp_project, "python_env:\n  mode: shared-parent\n")
        assert load_python_env_mode(tmp_project) is PythonEnvMode.SHARED_PARENT


# ---------------------------------------------------------------------------
# Default behaviour (D-101-12: default = uv-tool)
# ---------------------------------------------------------------------------


class TestDefaultUvTool:
    """Missing block or missing key both default to ``uv-tool``."""

    def test_missing_python_env_block_defaults_to_uv_tool(self, tmp_project: Path) -> None:
        # Manifest exists but has no python_env block at all.
        _write_manifest(tmp_project, "name: example\nproviders:\n  vcs: github\n")

        assert load_python_env_mode(tmp_project) is PythonEnvMode.UV_TOOL

    def test_python_env_block_without_mode_key_defaults_to_uv_tool(self, tmp_project: Path) -> None:
        # Block present, ``mode`` key absent.
        _write_manifest(tmp_project, "python_env: {}\n")

        assert load_python_env_mode(tmp_project) is PythonEnvMode.UV_TOOL

    def test_missing_manifest_file_defaults_to_uv_tool(self, tmp_path: Path) -> None:
        # No ``.ai-engineering/`` at all -- still safe defaults.
        assert load_python_env_mode(tmp_path) is PythonEnvMode.UV_TOOL


# ---------------------------------------------------------------------------
# Invalid wire values fail loudly
# ---------------------------------------------------------------------------


class TestInvalidMode:
    """Unknown ``python_env.mode`` values raise ``pydantic.ValidationError``."""

    def test_legacy_venv_value_raises(self, tmp_project: Path) -> None:
        _write_manifest(tmp_project, "python_env:\n  mode: legacy-venv\n")

        with pytest.raises(ValidationError):
            load_python_env_mode(tmp_project)

    @pytest.mark.parametrize(
        "bad_value",
        [
            "system",
            "uv_tool",  # underscore form -- canonical wire uses hyphen
            "venv-shared",
            "VENV",  # case sensitivity guard
            "",
        ],
    )
    def test_other_invalid_values_raise(self, tmp_project: Path, bad_value: str) -> None:
        _write_manifest(tmp_project, f"python_env:\n  mode: {bad_value!r}\n")

        with pytest.raises(ValidationError):
            load_python_env_mode(tmp_project)
