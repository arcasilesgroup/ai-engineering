"""RED-phase tests for ``state.manifest.load_required_tools`` (spec-101, T-0.5).

Verifies the contract described in spec D-101-01 + D-101-13:

* ``load_required_tools(stacks)`` returns the union of baseline and
  ``tools_for_stack`` for each declared stack.
* Empty ``stacks`` returns the baseline only.
* Each of the 14 declared stacks individually returns at least its own tool
  list plus the baseline.
* An unknown stack raises :class:`state.manifest.UnknownStackError`.
* When the current OS is in a stack's ``platform_unsupported_stack`` list,
  that stack contributes no tools and a skip-marker captures the reason.

These tests MUST fail until T-0.4 (``ToolSpec``/``StackSpec``) and T-0.6
(``state/manifest.py``) land. They are written against the contract --
no production code is created here.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:  # pragma: no cover - import-time-only typing
    from collections.abc import Iterable

# ---------------------------------------------------------------------------
# Fixture wiring
# ---------------------------------------------------------------------------

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "test_manifests"
    / "spec101_required_tools.yml"
)

# Canonical baseline + per-stack tool name expectations from spec D-101-01.
BASELINE_TOOLS: tuple[str, ...] = ("gitleaks", "semgrep", "jq")

STACK_TOOLS: dict[str, tuple[str, ...]] = {
    "python": ("ruff", "ty", "pip-audit", "pytest"),
    "typescript": ("prettier", "eslint", "tsc", "vitest"),
    "javascript": ("prettier", "eslint", "vitest"),
    "java": ("checkstyle", "google-java-format"),
    "csharp": ("dotnet-format",),
    "go": ("staticcheck", "govulncheck"),
    "php": ("phpstan", "php-cs-fixer", "composer"),
    "rust": ("cargo-audit",),
    "kotlin": ("ktlint",),
    "swift": ("swiftlint", "swift-format"),
    "dart": ("dart-stack-marker",),
    "sql": ("sqlfluff",),
    "bash": ("shellcheck", "shfmt"),
    "cpp": ("clang-tidy", "clang-format", "cppcheck"),
}

# Sanity guard against silent test omission as the framework adds stacks.
assert len(STACK_TOOLS) == 14, f"spec-101 declares 14 stacks; STACK_TOOLS has {len(STACK_TOOLS)}"


@pytest.fixture()
def fixture_manifest_root(tmp_path: Path) -> Path:
    """Stage the canonical spec-101 manifest fixture into a temp project root.

    Returns the project root containing ``.ai-engineering/manifest.yml``.
    """
    ai_dir = tmp_path / ".ai-engineering"
    ai_dir.mkdir()
    target = ai_dir / "manifest.yml"
    shutil.copyfile(FIXTURE_PATH, target)
    return tmp_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _names(specs: Iterable[object]) -> list[str]:
    """Project a list of ``ToolSpec`` instances onto their ``.name`` field."""
    return [spec.name for spec in specs]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Baseline + single-stack contract
# ---------------------------------------------------------------------------


class TestBaselineAndSingleStack:
    """Contract: baseline always present; declared stacks add tools."""

    def test_python_stack_returns_baseline_union_python_tools(
        self, fixture_manifest_root: Path
    ) -> None:
        from ai_engineering.state.manifest import load_required_tools

        result = load_required_tools(["python"], root=fixture_manifest_root)
        names = _names(result)

        for tool in BASELINE_TOOLS:
            assert tool in names, f"baseline tool '{tool}' missing from result"
        for tool in STACK_TOOLS["python"]:
            assert tool in names, f"python tool '{tool}' missing from result"

    def test_empty_stacks_returns_baseline_only(self, fixture_manifest_root: Path) -> None:
        from ai_engineering.state.manifest import load_required_tools

        result = load_required_tools([], root=fixture_manifest_root)
        names = _names(result)

        # All baseline tools present.
        for tool in BASELINE_TOOLS:
            assert tool in names, f"baseline tool '{tool}' missing"
        # No stack-specific tools leak through.
        all_stack_tools = {t for tools in STACK_TOOLS.values() for t in tools}
        leaked = set(names) & all_stack_tools
        assert leaked == set(), f"non-baseline tools leaked into empty result: {leaked}"
        assert len(names) == len(BASELINE_TOOLS), (
            f"expected exactly {len(BASELINE_TOOLS)} baseline tools, got {len(names)}: {names}"
        )

    def test_python_and_typescript_returns_baseline_plus_both(
        self, fixture_manifest_root: Path
    ) -> None:
        from ai_engineering.state.manifest import load_required_tools

        result = load_required_tools(["python", "typescript"], root=fixture_manifest_root)
        names = _names(result)

        for tool in BASELINE_TOOLS:
            assert tool in names
        for tool in STACK_TOOLS["python"]:
            assert tool in names
        for tool in STACK_TOOLS["typescript"]:
            assert tool in names


# ---------------------------------------------------------------------------
# Unknown stack contract
# ---------------------------------------------------------------------------


class TestUnknownStack:
    """Contract: unknown stacks raise UnknownStackError, not silent skip."""

    def test_unknown_stack_raises_unknown_stack_error(self, fixture_manifest_root: Path) -> None:
        from ai_engineering.state.manifest import UnknownStackError, load_required_tools

        with pytest.raises(UnknownStackError) as exc_info:
            load_required_tools(["nonexistent"], root=fixture_manifest_root)

        # The error message should name the offending stack so users can fix it.
        assert "nonexistent" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Parametric per-stack coverage (asserts every stack returns its tools)
# ---------------------------------------------------------------------------


_test_cases: list[tuple[str, tuple[str, ...]]] = sorted(STACK_TOOLS.items())
assert len(_test_cases) == 14, (
    f"per-stack coverage parametric must enumerate all 14 stacks; got {len(_test_cases)}"
)


class TestPerStackParametric:
    """Each declared stack name resolves to baseline plus that stack's tools."""

    @pytest.mark.parametrize(("stack", "expected_tools"), _test_cases)
    def test_each_stack_contributes_its_tools(
        self,
        fixture_manifest_root: Path,
        stack: str,
        expected_tools: tuple[str, ...],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Force darwin so swift (which has platform_unsupported_stack: [linux, windows])
        # contributes its tools in the per-stack baseline assertion. Other stacks
        # are not OS-gated, so the patch is a no-op for them.
        monkeypatch.setattr("platform.system", lambda: "Darwin")

        from ai_engineering.state.manifest import load_required_tools

        result = load_required_tools([stack], root=fixture_manifest_root)
        names = _names(result)

        # Baseline always present.
        for tool in BASELINE_TOOLS:
            assert tool in names, f"baseline tool '{tool}' missing for stack '{stack}'"

        # Stack tools all present.
        for tool in expected_tools:
            assert tool in names, f"stack '{stack}' tool '{tool}' missing"


# ---------------------------------------------------------------------------
# Stack-level platform skip (D-101-13)
# ---------------------------------------------------------------------------


class TestStackPlatformSkip:
    """D-101-13: ``platform_unsupported_stack`` covering current OS skips stack tools."""

    def test_swift_on_linux_yields_no_swift_tools_with_skip_marker(
        self,
        fixture_manifest_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # spec D-101-13: swift declares platform_unsupported_stack: [linux, windows].
        # On linux, the loader must drop swift's tools and surface a skip-reason.
        monkeypatch.setattr("platform.system", lambda: "Linux")

        from ai_engineering.state.manifest import load_required_tools

        result = load_required_tools(["swift"], root=fixture_manifest_root)
        names = _names(result)

        # Swift tools MUST NOT appear when the stack is platform-skipped.
        for tool in STACK_TOOLS["swift"]:
            assert tool not in names, (
                f"swift tool '{tool}' unexpectedly present on linux; "
                "platform_unsupported_stack must filter it out"
            )

        # Baseline still present (skip is per-stack, not global).
        for tool in BASELINE_TOOLS:
            assert tool in names, f"baseline tool '{tool}' should remain on linux"

        # The loader must surface a skip-reason marker the installer can
        # record as state=skipped_platform_unsupported_stack. The exact
        # surface is up to T-0.6 implementation, but the result must EITHER
        # carry a sibling skip record OR expose ``skipped_stacks`` data.
        # We probe both common shapes; one must hold.
        skip_payload = getattr(result, "skipped_stacks", None)
        if skip_payload is None and hasattr(result, "__iter__"):
            # Allow attribute on the returned container OR a tuple shape
            # (tools, skipped) -- spec leaves the surface unspecified.
            skip_payload = getattr(result, "skips", None)
        assert skip_payload is not None, (
            "load_required_tools must expose a skip-reason marker for "
            "platform_unsupported_stack-filtered stacks (e.g. .skipped_stacks "
            "or .skips). None of the expected attributes were found on the result."
        )

        # The skip payload must mention swift and the reason from the manifest.
        skip_str = str(skip_payload)
        assert "swift" in skip_str, "skip marker must name the swift stack"
        assert (
            "swiftlint" in skip_str.lower()
            or "linux" in skip_str.lower()
            or "binar" in skip_str.lower()
        ), "skip marker must include the unsupported_reason from the manifest"

    def test_swift_on_darwin_normal_path(
        self,
        fixture_manifest_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # On macOS swift is supported; tools should be present.
        monkeypatch.setattr("platform.system", lambda: "Darwin")

        from ai_engineering.state.manifest import load_required_tools

        result = load_required_tools(["swift"], root=fixture_manifest_root)
        names = _names(result)

        for tool in STACK_TOOLS["swift"]:
            assert tool in names, (
                f"swift tool '{tool}' should be present on darwin where the stack is supported"
            )
