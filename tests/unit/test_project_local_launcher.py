"""RED-phase tests for spec-101 T-1.13 -- D-101-15 project_local launcher.

These tests assert the contract for
``ai_engineering.installer.launchers.resolve_project_local`` (created in
T-1.14 GREEN). The module does not exist yet -- import failure is the
expected RED signal.

Contract under test (per spec D-101-15):

    resolve_project_local(tool_spec: ToolSpec, cwd: Path) -> list[str]

Returns the launcher argv for the tool's stack:

| Stack                  | Launcher pattern                                   |
| ---------------------- | -------------------------------------------------- |
| typescript / javascript| ``["npx", "<tool>", ...]``                         |
| php                    | ``["./vendor/bin/<tool>", ...]``                   |
| java (Maven detected)  | ``["./mvnw", "<tool>", ...]``                      |
| java (Gradle detected) | ``["./gradlew", "<tool>", ...]``                   |
| kotlin                 | ``["./gradlew", "<tool>", ...]``                   |
| cpp                    | ``["cmake", "--build", ...]`` or ``["ctest", ...]``|

Stack detection: ``ToolSpec`` carries ``scope=ToolScope.PROJECT_LOCAL``.
The stack itself is supplied alongside the tool (the loader path in
T-2.24 routes via the StackSpec). For unit-testing the launcher in
isolation we accept a ``stack`` parameter on the resolver call.

Missing-dep behaviour:
    - When the project lacks the launcher's prerequisite (e.g.
      ``node_modules/.bin/<tool>`` for typescript when the tool is not
      installed) the resolver returns a sentinel argv whose first element
      is the marker token ``"__missing_dep__"`` and whose remaining
      elements form the actionable user-facing message naming the
      install command (``npm install``, ``composer install``,
      ``./mvnw install``).

These tests MUST fail with::

    ModuleNotFoundError: No module named 'ai_engineering.installer.launchers'

until T-1.14 lands ``installer/launchers.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# T-1.14 has not landed: this import is the RED signal.
from ai_engineering.installer.launchers import (
    MISSING_DEP_SENTINEL,
    resolve_project_local,
)
from ai_engineering.state.models import ToolScope, ToolSpec

# ---------------------------------------------------------------------------
# Helpers -- minimal project-tree scaffolding under tmp_path
# ---------------------------------------------------------------------------


def _make_tool_spec(name: str) -> ToolSpec:
    """Return a frozen ``ToolSpec`` with ``scope=project_local``."""
    return ToolSpec(name=name, scope=ToolScope.PROJECT_LOCAL)


def _seed_node_dep(cwd: Path, tool: str) -> Path:
    """Create ``node_modules/.bin/<tool>`` to simulate ``npm install``."""
    bin_dir = cwd / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    tool_path = bin_dir / tool
    tool_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    tool_path.chmod(0o755)
    # package.json must also exist for the project to be a "real" node project.
    (cwd / "package.json").write_text('{"name": "fixture"}', encoding="utf-8")
    return tool_path


def _seed_php_dep(cwd: Path, tool: str) -> Path:
    """Create ``vendor/bin/<tool>`` to simulate ``composer install``."""
    bin_dir = cwd / "vendor" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    tool_path = bin_dir / tool
    tool_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    tool_path.chmod(0o755)
    (cwd / "composer.json").write_text('{"name": "fixture/x"}', encoding="utf-8")
    return tool_path


def _seed_maven_wrapper(cwd: Path) -> None:
    """Create ``pom.xml`` + ``./mvnw`` wrapper to mark a Maven project."""
    (cwd / "pom.xml").write_text("<project/>", encoding="utf-8")
    mvnw = cwd / "mvnw"
    mvnw.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    mvnw.chmod(0o755)


def _seed_gradle_wrapper(cwd: Path) -> None:
    """Create ``build.gradle`` + ``./gradlew`` wrapper to mark a Gradle project."""
    (cwd / "build.gradle").write_text("// fixture", encoding="utf-8")
    gradlew = cwd / "gradlew"
    gradlew.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    gradlew.chmod(0o755)


def _seed_cmake_project(cwd: Path) -> None:
    """Create a minimal ``CMakeLists.txt`` to mark a C++ project."""
    (cwd / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.20)\nproject(fixture)\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# typescript / javascript -- npx launcher
# ---------------------------------------------------------------------------


class TestTypescriptJavascriptLauncher:
    """typescript and javascript route through ``npx <tool>`` (D-101-15)."""

    @pytest.mark.parametrize("stack", ["typescript", "javascript"])
    def test_npx_launcher_when_dep_present(self, stack: str, tmp_path: Path) -> None:
        """When ``node_modules/.bin/<tool>`` exists, returns ``["npx", tool]``."""
        _seed_node_dep(tmp_path, "eslint")
        spec = _make_tool_spec("eslint")

        argv = resolve_project_local(spec, cwd=tmp_path, stack=stack)

        assert argv[0] == "npx"
        assert argv[1] == "eslint"

    def test_npx_with_tsc(self, tmp_path: Path) -> None:
        """A second tool name produces the same launcher shape."""
        _seed_node_dep(tmp_path, "tsc")
        spec = _make_tool_spec("tsc")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="typescript")

        assert argv == ["npx", "tsc"]

    def test_missing_dep_returns_sentinel_with_npm_install_message(self, tmp_path: Path) -> None:
        """No ``node_modules/.bin/<tool>`` -> sentinel + 'npm install' message."""
        # Only package.json -- no node_modules at all.
        (tmp_path / "package.json").write_text('{"name": "fixture"}', encoding="utf-8")
        spec = _make_tool_spec("eslint")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="typescript")

        assert argv[0] == MISSING_DEP_SENTINEL
        message = " ".join(argv[1:])
        assert "npm install" in message
        assert "eslint" in message


# ---------------------------------------------------------------------------
# php -- vendor/bin launcher
# ---------------------------------------------------------------------------


class TestPhpLauncher:
    """php routes through ``./vendor/bin/<tool>`` (composer-installed)."""

    def test_vendor_bin_launcher_when_dep_present(self, tmp_path: Path) -> None:
        """``vendor/bin/<tool>`` exists -> returns ``["./vendor/bin/<tool>"]``."""
        _seed_php_dep(tmp_path, "phpstan")
        spec = _make_tool_spec("phpstan")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="php")

        assert argv[0] == "./vendor/bin/phpstan"

    def test_missing_dep_returns_sentinel_with_composer_install_message(
        self, tmp_path: Path
    ) -> None:
        """No ``vendor/bin/<tool>`` -> sentinel + 'composer install' message."""
        (tmp_path / "composer.json").write_text('{"name": "fixture/x"}', encoding="utf-8")
        spec = _make_tool_spec("phpstan")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="php")

        assert argv[0] == MISSING_DEP_SENTINEL
        message = " ".join(argv[1:])
        assert "composer install" in message
        assert "phpstan" in message


# ---------------------------------------------------------------------------
# java -- maven (./mvnw) or gradle (./gradlew) detection
# ---------------------------------------------------------------------------


class TestJavaLauncher:
    """java routes through the project's wrapper (mvnw or gradlew)."""

    def test_maven_wrapper_used_when_pom_xml_present(self, tmp_path: Path) -> None:
        """``pom.xml`` + ``./mvnw`` -> ``["./mvnw", <tool>]``."""
        _seed_maven_wrapper(tmp_path)
        spec = _make_tool_spec("checkstyle")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="java")

        assert argv[0] == "./mvnw"
        assert argv[1] == "checkstyle"

    def test_gradle_wrapper_used_when_build_gradle_present(self, tmp_path: Path) -> None:
        """``build.gradle`` + ``./gradlew`` -> ``["./gradlew", <tool>]``."""
        _seed_gradle_wrapper(tmp_path)
        spec = _make_tool_spec("checkstyle")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="java")

        assert argv[0] == "./gradlew"
        assert argv[1] == "checkstyle"

    def test_missing_wrapper_returns_sentinel_with_install_message(self, tmp_path: Path) -> None:
        """Neither ``pom.xml`` nor ``build.gradle`` -> sentinel + actionable msg."""
        spec = _make_tool_spec("checkstyle")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="java")

        assert argv[0] == MISSING_DEP_SENTINEL
        message = " ".join(argv[1:])
        # Either ``./mvnw install`` or ``./gradlew assemble`` is acceptable;
        # the message MUST name at least one of the two project bootstrap
        # commands so the user knows how to recover.
        assert ("./mvnw" in message) or ("./gradlew" in message)


# ---------------------------------------------------------------------------
# kotlin -- gradle wrapper
# ---------------------------------------------------------------------------


class TestKotlinLauncher:
    """kotlin always routes through ``./gradlew <task>``."""

    def test_gradlew_used_when_present(self, tmp_path: Path) -> None:
        """``build.gradle`` + ``./gradlew`` -> ``["./gradlew", <tool>]``."""
        _seed_gradle_wrapper(tmp_path)
        spec = _make_tool_spec("ktlint")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="kotlin")

        assert argv[0] == "./gradlew"
        assert argv[1] == "ktlint"

    def test_missing_gradlew_returns_sentinel(self, tmp_path: Path) -> None:
        """No ``./gradlew`` -> sentinel + actionable message naming gradlew."""
        spec = _make_tool_spec("ktlint")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="kotlin")

        assert argv[0] == MISSING_DEP_SENTINEL
        message = " ".join(argv[1:])
        assert "./gradlew" in message


# ---------------------------------------------------------------------------
# cpp -- cmake / ctest launcher
# ---------------------------------------------------------------------------


class TestCppLauncher:
    """cpp routes through ``cmake --build`` or ``ctest`` based on tool name."""

    def test_cmake_build_for_build_tool(self, tmp_path: Path) -> None:
        """A build tool routes to ``["cmake", "--build", ...]``."""
        _seed_cmake_project(tmp_path)
        spec = _make_tool_spec("cmake-build")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="cpp")

        assert argv[0] == "cmake"
        assert argv[1] == "--build"

    def test_ctest_for_test_tool(self, tmp_path: Path) -> None:
        """A test tool routes to ``["ctest", ...]``."""
        _seed_cmake_project(tmp_path)
        spec = _make_tool_spec("ctest")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="cpp")

        assert argv[0] == "ctest"

    def test_missing_cmakelists_returns_sentinel(self, tmp_path: Path) -> None:
        """No ``CMakeLists.txt`` -> sentinel + actionable message naming cmake."""
        spec = _make_tool_spec("ctest")

        argv = resolve_project_local(spec, cwd=tmp_path, stack="cpp")

        assert argv[0] == MISSING_DEP_SENTINEL
        message = " ".join(argv[1:])
        assert "cmake" in message.lower()


# ---------------------------------------------------------------------------
# Parametric matrix -- all 5 stack patterns covered (D-101-15, 5 cases)
# ---------------------------------------------------------------------------


def _seed_for_stack(stack: str, tool: str, cwd: Path) -> None:
    """Seed the minimal fixture for the requested stack."""
    if stack in {"typescript", "javascript"}:
        _seed_node_dep(cwd, tool)
    elif stack == "php":
        _seed_php_dep(cwd, tool)
    elif stack == "java":
        _seed_maven_wrapper(cwd)
    elif stack == "kotlin":
        _seed_gradle_wrapper(cwd)
    elif stack == "cpp":
        _seed_cmake_project(cwd)
    else:  # pragma: no cover -- defensive
        raise ValueError(f"unknown stack fixture: {stack}")


# (stack, tool, expected_first_argv_token)
_LAUNCHER_MATRIX: tuple[tuple[str, str, str], ...] = (
    ("typescript", "eslint", "npx"),
    ("php", "phpstan", "./vendor/bin/phpstan"),
    ("java", "checkstyle", "./mvnw"),
    ("kotlin", "ktlint", "./gradlew"),
    ("cpp", "ctest", "ctest"),
)


class TestParametricLauncherMatrix:
    """All 5 D-101-15 launcher patterns produce the expected argv shape."""

    @pytest.mark.parametrize(("stack", "tool", "expected_head"), _LAUNCHER_MATRIX)
    def test_each_stack_pattern(
        self, stack: str, tool: str, expected_head: str, tmp_path: Path
    ) -> None:
        """Every stack returns a non-sentinel argv whose head matches."""
        _seed_for_stack(stack, tool, tmp_path)
        spec = _make_tool_spec(tool)

        argv = resolve_project_local(spec, cwd=tmp_path, stack=stack)

        assert argv, "launcher must return a non-empty argv"
        assert argv[0] != MISSING_DEP_SENTINEL, (
            f"stack={stack} tool={tool} should resolve when fixture is seeded; got sentinel: {argv}"
        )
        assert argv[0] == expected_head, (
            f"stack={stack} tool={tool} expected head '{expected_head}', got '{argv[0]}'"
        )

    def test_matrix_covers_all_five_patterns(self) -> None:
        """The parametric matrix MUST cover the 5 D-101-15 stack patterns."""
        covered_stacks = {row[0] for row in _LAUNCHER_MATRIX}
        # typescript covers the typescript/javascript shared pattern;
        # the remaining 4 are distinct patterns. Total: 5 stacks, 5 patterns.
        assert covered_stacks == {"typescript", "php", "java", "kotlin", "cpp"}
        assert len(_LAUNCHER_MATRIX) >= 5
