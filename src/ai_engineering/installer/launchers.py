"""Project-local tool launcher resolution (spec-101 D-101-15).

When a tool is registered with ``ToolScope.PROJECT_LOCAL`` (e.g., typescript's
``eslint``, php's ``phpstan``, java's ``checkstyle``), the framework never
installs the tool itself -- the language's own package manager owns that. At
runtime the framework still needs to *invoke* the tool, so this module produces
the launcher argv that delegates to the project's package-manager bin shim.

Public API:

    resolve_project_local(tool_spec: ToolSpec, *, cwd: Path, stack: str) -> list[str]

Returns the launcher argv. When the project lacks the launcher's prerequisite
(e.g., ``node_modules/.bin/<tool>`` for a typescript tool) the returned argv's
first element is the marker token :data:`MISSING_DEP_SENTINEL` and subsequent
elements form the actionable user-facing message naming the install command
(``npm install``, ``composer install``, ``./mvnw install``, etc.).

Launcher patterns (per D-101-15):

| Stack                  | Launcher pattern                                   |
| ---------------------- | -------------------------------------------------- |
| typescript / javascript| ``["npx", "<tool>"]``                              |
| php                    | ``["./vendor/bin/<tool>"]``                        |
| java (Maven detected)  | ``["./mvnw", "<tool>"]``                           |
| java (Gradle detected) | ``["./gradlew", "<tool>"]``                        |
| kotlin                 | ``["./gradlew", "<tool>"]``                        |
| cpp                    | ``["cmake", "--build", ...]`` or ``["ctest", ...]``|
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.state.models import ToolSpec

# Marker token returned as ``argv[0]`` when the launcher's prerequisite is
# missing. Callers detect this token to surface the rest of argv as a
# user-facing recovery message rather than executing it.
MISSING_DEP_SENTINEL = "__missing_dep__"

# Stacks routed through ``npx <tool>`` (D-101-15 row 1).
_NODE_STACKS = frozenset({"typescript", "javascript"})

# C++ tool names treated as test runners rather than build drivers.
# Anything else under stack=cpp is routed through ``cmake --build``.
_CPP_TEST_TOOLS = frozenset({"ctest"})


# ---------------------------------------------------------------------------
# Detection helpers -- pure filesystem checks under cwd
# ---------------------------------------------------------------------------


def _detect_node(cwd: Path, tool: str) -> Path | None:
    """Return ``node_modules/.bin/<tool>`` if it exists, else ``None``."""
    candidate = cwd / "node_modules" / ".bin" / tool
    return candidate if candidate.exists() else None


def _detect_php_vendor(cwd: Path, tool: str) -> Path | None:
    """Return ``vendor/bin/<tool>`` if it exists, else ``None``."""
    candidate = cwd / "vendor" / "bin" / tool
    return candidate if candidate.exists() else None


def _detect_maven(cwd: Path) -> bool:
    """Return ``True`` when ``pom.xml`` is present at ``cwd``."""
    return (cwd / "pom.xml").exists()


def _detect_gradle(cwd: Path) -> bool:
    """Return ``True`` when a Gradle build script is present at ``cwd``."""
    return (cwd / "build.gradle").exists() or (cwd / "build.gradle.kts").exists()


def _detect_cmake(cwd: Path) -> bool:
    """Return ``True`` when ``CMakeLists.txt`` is present at ``cwd``."""
    return (cwd / "CMakeLists.txt").exists()


# ---------------------------------------------------------------------------
# Sentinel constructor
# ---------------------------------------------------------------------------


def _missing_dep(message: str) -> list[str]:
    """Return a sentinel argv whose tail spells ``message``."""
    return [MISSING_DEP_SENTINEL, *message.split()]


# ---------------------------------------------------------------------------
# Per-stack resolvers
# ---------------------------------------------------------------------------


def _resolve_node(tool: str, cwd: Path) -> list[str]:
    """typescript / javascript -> ``npx <tool>`` when installed, else sentinel."""
    if _detect_node(cwd, tool) is not None:
        return ["npx", tool]
    return _missing_dep(
        f"run 'npm install' to install {tool} into node_modules/.bin/",
    )


def _resolve_php(tool: str, cwd: Path) -> list[str]:
    """php -> ``./vendor/bin/<tool>`` when installed, else sentinel."""
    if _detect_php_vendor(cwd, tool) is not None:
        return [f"./vendor/bin/{tool}"]
    return _missing_dep(
        f"run 'composer install' to install {tool} into vendor/bin/",
    )


def _resolve_java(tool: str, cwd: Path) -> list[str]:
    """java -> ``./mvnw <tool>`` (Maven) or ``./gradlew <tool>`` (Gradle).

    Maven takes precedence when both are present (D-101-15 left-to-right
    detection order). Missing both wrappers returns a sentinel naming the
    bootstrap commands so the user can recover.
    """
    if _detect_maven(cwd):
        return ["./mvnw", tool]
    if _detect_gradle(cwd):
        return ["./gradlew", tool]
    return _missing_dep(
        "no Maven or Gradle project detected; run './mvnw install' "
        "or './gradlew assemble' to bootstrap the build wrapper",
    )


def _resolve_kotlin(tool: str, cwd: Path) -> list[str]:
    """kotlin -> ``./gradlew <tool>`` when a Gradle project is present."""
    if _detect_gradle(cwd):
        return ["./gradlew", tool]
    return _missing_dep(
        "no Gradle project detected; add build.gradle and run './gradlew assemble' "
        f"to bootstrap before invoking {tool}",
    )


def _resolve_cpp(tool: str, cwd: Path) -> list[str]:
    """cpp -> ``cmake --build`` (build tools) or ``ctest`` (test runners)."""
    if not _detect_cmake(cwd):
        return _missing_dep(
            f"no CMakeLists.txt detected; configure cmake before invoking {tool}",
        )
    if tool in _CPP_TEST_TOOLS:
        return ["ctest"]
    return ["cmake", "--build"]


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------


def resolve_project_local(
    tool_spec: ToolSpec,
    *,
    cwd: Path,
    stack: str,
) -> list[str]:
    """Resolve the launcher argv for a project-local tool.

    Args:
        tool_spec: Frozen ``ToolSpec`` with ``scope=ToolScope.PROJECT_LOCAL``.
            Only ``tool_spec.name`` is consumed by the dispatch routing.
        cwd: Project root used for filesystem detection (``node_modules/``,
            ``vendor/``, ``pom.xml``, ``build.gradle``, ``CMakeLists.txt``).
        stack: Stack key from the registry (``typescript``, ``javascript``,
            ``php``, ``java``, ``kotlin``, ``cpp``). Routes to the matching
            launcher pattern from D-101-15.

    Returns:
        Launcher argv (``list[str]``). When the prerequisite is missing the
        first element equals :data:`MISSING_DEP_SENTINEL` and the rest of argv
        forms a user-facing recovery message.

    Raises:
        ValueError: When ``stack`` is not one of the D-101-15 routed stacks.
    """
    tool = tool_spec.name

    if stack in _NODE_STACKS:
        return _resolve_node(tool, cwd)
    if stack == "php":
        return _resolve_php(tool, cwd)
    if stack == "java":
        return _resolve_java(tool, cwd)
    if stack == "kotlin":
        return _resolve_kotlin(tool, cwd)
    if stack == "cpp":
        return _resolve_cpp(tool, cwd)

    raise ValueError(
        f"resolve_project_local: stack '{stack}' is not routed by D-101-15; "
        "expected one of: typescript, javascript, php, java, kotlin, cpp",
    )
