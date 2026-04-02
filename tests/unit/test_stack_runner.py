"""Tests for dynamic Python path detection in stack_runner.

RED phase: these tests target functions that do not exist yet:
- detect_python_source_root(project_root) -> str
- detect_python_test_dir(project_root) -> str | None

The functions will parse pyproject.toml for source/test directories and
fall back to filesystem probing when config is absent.

All tests use tmp_path for isolated project structures.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_engineering.policy.checks.stack_runner import (
    detect_python_source_root,
    detect_python_test_dir,
)
from ai_engineering.policy.gates import GateResult
from ai_engineering.state.models import GateHook

# -- detect_python_source_root ------------------------------------------------


class TestDetectPythonSourceRoot:
    """Tests for detect_python_source_root fallback chain.

    Priority:
    1. pyproject.toml [tool.hatch.build.targets.wheel] packages
    2. pyproject.toml [tool.setuptools] packages
    3. Probe: src/ directory exists
    4. Fallback: "."
    """

    def test_from_hatch_config(self, tmp_path: Path) -> None:
        """Hatch build config packages takes highest priority."""
        # Arrange
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.hatch.build.targets.wheel]\npackages = ["src/myapp"]\n',
            encoding="utf-8",
        )

        # Act
        result = detect_python_source_root(tmp_path)

        # Assert
        assert result == "src/myapp"

    def test_from_setuptools(self, tmp_path: Path) -> None:
        """Setuptools packages config is used when hatch config is absent."""
        # Arrange
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.setuptools]\npackages = ["myapp"]\n',
            encoding="utf-8",
        )

        # Act
        result = detect_python_source_root(tmp_path)

        # Assert
        assert result == "myapp"

    def test_fallback_src_directory(self, tmp_path: Path) -> None:
        """Falls back to 'src' when pyproject.toml has no relevant config but src/ exists."""
        # Arrange -- no pyproject.toml, but src/ directory present
        (tmp_path / "src").mkdir()

        # Act
        result = detect_python_source_root(tmp_path)

        # Assert
        assert result == "src"

    def test_fallback_dot(self, tmp_path: Path) -> None:
        """Falls back to '.' when nothing else matches."""
        # Arrange -- empty project directory, no pyproject.toml, no src/

        # Act
        result = detect_python_source_root(tmp_path)

        # Assert
        assert result == "."

    def test_hatch_takes_priority_over_setuptools(self, tmp_path: Path) -> None:
        """When both hatch and setuptools are configured, hatch wins."""
        # Arrange
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/hatch_pkg"]\n\n'
            "[tool.setuptools]\n"
            'packages = ["setuptools_pkg"]\n',
            encoding="utf-8",
        )

        # Act
        result = detect_python_source_root(tmp_path)

        # Assert
        assert result == "src/hatch_pkg"

    def test_hatch_takes_priority_over_src_probe(self, tmp_path: Path) -> None:
        """Config is preferred even when src/ directory also exists."""
        # Arrange
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.hatch.build.targets.wheel]\npackages = ["lib/core"]\n',
            encoding="utf-8",
        )
        (tmp_path / "src").mkdir()

        # Act
        result = detect_python_source_root(tmp_path)

        # Assert
        assert result == "lib/core"

    def test_empty_hatch_packages_falls_through(self, tmp_path: Path) -> None:
        """Empty hatch packages list falls through to next strategy."""
        # Arrange
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[tool.hatch.build.targets.wheel]\npackages = []\n\n"
            '[tool.setuptools]\npackages = ["fallback_pkg"]\n',
            encoding="utf-8",
        )

        # Act
        result = detect_python_source_root(tmp_path)

        # Assert
        assert result == "fallback_pkg"


# -- detect_python_test_dir ---------------------------------------------------


class TestDetectPythonTestDir:
    """Tests for detect_python_test_dir fallback chain.

    Priority:
    1. pyproject.toml [tool.pytest.ini_options] testpaths
    2. Probe: tests/ directory exists
    3. Probe: test/ directory exists
    4. None (no test directory found)
    """

    def test_from_pytest_config(self, tmp_path: Path) -> None:
        """pytest ini_options testpaths takes highest priority."""
        # Arrange
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
            encoding="utf-8",
        )

        # Act
        result = detect_python_test_dir(tmp_path)

        # Assert -- no unit/ subdirectory, returns resolved path as-is
        assert result == "tests"

    def test_from_pytest_config_prefers_unit_subdir(self, tmp_path: Path) -> None:
        """When resolved dir has a unit/ subdirectory, return the narrower path."""
        # Arrange
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
            encoding="utf-8",
        )
        (tmp_path / "tests" / "unit").mkdir(parents=True)

        # Act
        result = detect_python_test_dir(tmp_path)

        # Assert
        assert result == "tests/unit"

    def test_probe_tests_directory(self, tmp_path: Path) -> None:
        """Falls back to 'tests' when the directory exists but no config."""
        # Arrange -- no pyproject.toml, but tests/ present
        (tmp_path / "tests").mkdir()

        # Act
        result = detect_python_test_dir(tmp_path)

        # Assert
        assert result == "tests"

    def test_probe_test_directory(self, tmp_path: Path) -> None:
        """Falls back to 'test' when tests/ is absent but test/ exists."""
        # Arrange -- no pyproject.toml, no tests/, but test/ present
        (tmp_path / "test").mkdir()

        # Act
        result = detect_python_test_dir(tmp_path)

        # Assert
        assert result == "test"

    def test_none_when_nothing_exists(self, tmp_path: Path) -> None:
        """Returns None when no test directory can be found."""
        # Arrange -- empty project directory

        # Act
        result = detect_python_test_dir(tmp_path)

        # Assert
        assert result is None

    def test_config_takes_priority_over_probe(self, tmp_path: Path) -> None:
        """testpaths from pyproject.toml wins over directory probing."""
        # Arrange
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.pytest.ini_options]\ntestpaths = ["integration_tests"]\n',
            encoding="utf-8",
        )
        (tmp_path / "tests").mkdir()  # exists but should be ignored

        # Act
        result = detect_python_test_dir(tmp_path)

        # Assert
        assert result == "integration_tests"

    def test_tests_takes_priority_over_test(self, tmp_path: Path) -> None:
        """When both tests/ and test/ exist, tests/ wins."""
        # Arrange
        (tmp_path / "tests").mkdir()
        (tmp_path / "test").mkdir()

        # Act
        result = detect_python_test_dir(tmp_path)

        # Assert
        assert result == "tests"


# -- Pre-push check skip behavior --------------------------------------------


class TestPrePushCheckSkipsWhenNoTestDir:
    """Verify that the stack-tests check skips gracefully when no test dir exists."""

    def test_skips_with_message_when_no_test_dir(self, tmp_path: Path) -> None:
        """When detect_python_test_dir returns None, the stack-tests check
        should pass with a skip message instead of failing."""
        # Arrange
        result = GateResult(hook=GateHook.PRE_PUSH)

        # Act -- patch detect_python_test_dir to return None
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.detect_python_test_dir",
                return_value=None,
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.detect_python_source_root",
                return_value="src",
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value="/usr/bin/uv",
            ),
            patch("ai_engineering.policy.checks.stack_runner.subprocess.run"),
        ):
            from ai_engineering.policy.checks.stack_runner import (
                PRE_PUSH_CHECKS,
                run_checks_for_stacks,
            )

            run_checks_for_stacks(tmp_path, result, PRE_PUSH_CHECKS, ["python"])

        # Assert -- stack-tests should be marked as passed with skip indication
        stack_test_checks = [c for c in result.checks if c.name == "stack-tests"]
        assert len(stack_test_checks) == 1, "Expected exactly one stack-tests check result"
        assert stack_test_checks[0].passed is True
        assert "skip" in stack_test_checks[0].output.lower()
