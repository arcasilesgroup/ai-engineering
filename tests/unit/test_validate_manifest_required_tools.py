"""Tests for required_tools governance lint (spec-101 T-0.7 RED).

Covers governance rules per D-101-03 and D-101-13:

- Tool-level ``platform_unsupported`` cap: at most 2 of the 3 supported OSes.
  Listing all three at tool-level is an abuse vector and MUST fail the lint.
- Stack-level ``platform_unsupported_stack`` is permitted for any subset of
  the 3 OSes -- including all three -- because legitimate cases exist
  (e.g. swift tooling has no Linux/Windows binaries).
- ``unsupported_reason`` is mandatory whenever ``platform_unsupported`` (any
  level) is declared. Missing reason fails the lint.
- The OS enum at either level is closed: ``{darwin, linux, windows}``. Any
  other value (e.g. ``bsd``) fails the lint.
- R-15: every stack declared in ``providers.stacks`` MUST have a matching
  ``required_tools.<stack>`` entry. Drift between manifest and stack runner
  is the lint's primary purpose.
- A manifest without any ``required_tools`` block fails the lint.

The lint is the GREEN-phase work for T-0.8 -- this RED file will not pass
until that landing. Tests target the function surface (``_check_required_tools``
under ``ai_engineering.validator.categories.required_tools``) AND the public
``validate_content_integrity`` aggregator.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

# Import lazily inside helpers/tests so collection still succeeds even if the
# module does not yet exist. Tests will surface ImportError as RED failures.


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _write_manifest(root: Path, body: str) -> Path:
    """Write a minimal manifest.yml under ``<root>/.ai-engineering/`` and return its path."""
    ai_dir = root / ".ai-engineering"
    ai_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = ai_dir / "manifest.yml"
    manifest_path.write_text(dedent(body).lstrip("\n"), encoding="utf-8")
    return manifest_path


def _valid_manifest_body(stacks: str = "[python]", required_tools: str | None = None) -> str:
    """Return a syntactically-valid manifest body with the given stacks and required_tools.

    The body auto-includes a complete ``prereqs.sdk_per_stack`` block covering
    all 9 SDK-required stacks so unrelated tests do not trip the T-4.9
    coverage lint. Tests that target the SDK-coverage lint directly live in
    ``test_validate_manifest_sdk_coverage.py`` and build their own bodies.
    """
    if required_tools is None:
        required_tools = """
        required_tools:
          baseline:
            - {name: gitleaks}
          python:
            - {name: ruff}
        """
    return f"""
    schema_version: "2.0"
    framework_version: "0.4.0"
    name: spec-101-fixture
    version: "0.0.1"

    providers:
      vcs: github
      ides: [terminal]
      stacks: {stacks}

    ai_providers:
      enabled: [claude_code]
      primary: claude_code

    prereqs:
      uv:
        version_range: ">=0.4.0,<1.0"
      sdk_per_stack:
        java: {{name: JDK, min_version: "21", install_link: "https://adoptium.net/"}}
        kotlin: {{name: JDK, min_version: "21", install_link: "https://adoptium.net/"}}
        swift: {{name: Swift toolchain, install_link: "https://www.swift.org/install/"}}
        dart: {{name: Dart SDK, install_link: "https://dart.dev/get-dart"}}
        csharp: {{name: ".NET SDK", min_version: "9", install_link: "https://dotnet.microsoft.com/download"}}
        go: {{name: Go toolchain, install_link: "https://go.dev/dl/"}}
        rust: {{name: Rust toolchain, install_link: "https://rustup.rs/"}}
        php: {{name: PHP, min_version: "8.2", install_link: "https://www.php.net/downloads"}}
        cpp: {{name: clang/LLVM, install_link: "https://llvm.org/builds/"}}

    {dedent(required_tools).strip()}
    """


def _run_lint(root: Path):
    """Invoke the required_tools lint and return (report, fail_results).

    ``fail_results`` is the list of FAIL-status entries belonging to the
    required_tools category (or whichever category the lint registers under).
    """
    from ai_engineering.validator._shared import IntegrityStatus
    from ai_engineering.validator.categories.required_tools import (
        _check_required_tools,
    )
    from ai_engineering.validator.service import IntegrityReport

    report = IntegrityReport()
    _check_required_tools(root, report)
    fail_results = [c for c in report.checks if c.status == IntegrityStatus.FAIL]
    return report, fail_results


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestValidManifest:
    """A manifest that satisfies every governance rule produces zero FAILs."""

    def test_valid_manifest_passes_lint(self, tmp_path: Path) -> None:
        body = _valid_manifest_body(
            stacks="[python]",
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
                - name: semgrep
                  platform_unsupported: [windows]
                  unsupported_reason: "no Windows release"
              python:
                - {name: ruff}
                - {name: ty}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails == [], f"Expected no FAILs, got: {[f.message for f in fails]}"


# ---------------------------------------------------------------------------
# Tool-level platform_unsupported governance (D-101-03)
# ---------------------------------------------------------------------------


class TestToolLevelPlatformUnsupported:
    """Tool-level cap: at most 2 of 3 OSes per D-101-03."""

    def test_all_three_oses_at_tool_level_fails(self, tmp_path: Path) -> None:
        """Listing darwin+linux+windows at tool-level is the abuse case -- must fail."""
        body = _valid_manifest_body(
            stacks="[python]",
            required_tools="""
            required_tools:
              baseline:
                - name: bogus
                  platform_unsupported: [darwin, linux, windows]
                  unsupported_reason: "abuse vector test"
              python:
                - {name: ruff}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails, "Tool listing all 3 OSes must fail tool-level governance"
        joined = " ".join(f.message for f in fails).lower()
        assert (
            "bogus" in joined
            or "all three" in joined
            or "all 3" in joined
            or "tool-level" in joined
        ), f"Failure message should identify the tool-level cap; got: {joined}"

    def test_tool_level_missing_unsupported_reason_fails(self, tmp_path: Path) -> None:
        """``platform_unsupported`` without ``unsupported_reason`` must fail (D-101-03)."""
        body = _valid_manifest_body(
            stacks="[python]",
            required_tools="""
            required_tools:
              baseline:
                - name: semgrep
                  platform_unsupported: [windows]
                  # unsupported_reason intentionally omitted
              python:
                - {name: ruff}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails, "Missing unsupported_reason at tool-level must fail"
        joined = " ".join(f.message for f in fails).lower()
        assert "unsupported_reason" in joined or "reason" in joined, (
            f"Failure message must mention unsupported_reason; got: {joined}"
        )

    def test_tool_level_two_of_three_oses_passes_with_reason(self, tmp_path: Path) -> None:
        """2-of-3 OSes at tool-level WITH reason is the legitimate case (must pass)."""
        body = _valid_manifest_body(
            stacks="[python]",
            required_tools="""
            required_tools:
              baseline:
                - name: legacy-mac-only
                  platform_unsupported: [linux, windows]
                  unsupported_reason: "only ships an Apple-signed binary"
              python:
                - {name: ruff}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails == [], f"2-of-3 OSes with reason must pass; got: {[f.message for f in fails]}"


# ---------------------------------------------------------------------------
# Stack-level platform_unsupported_stack carve-out (D-101-13)
# ---------------------------------------------------------------------------


class TestStackLevelPlatformUnsupportedStack:
    """Stack-level allows up to all 3 OSes per D-101-13 carve-out."""

    def test_stack_level_two_of_three_passes_with_reason(self, tmp_path: Path) -> None:
        """Stack-level 2-of-3 with reason: legitimate case (e.g. swift)."""
        body = _valid_manifest_body(
            stacks="[swift]",
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              swift:
                platform_unsupported_stack: [linux, windows]
                unsupported_reason: "swiftlint and swift-format have no Linux/Windows binaries"
                tools:
                  - {name: swiftlint}
                  - {name: swift-format}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails == [], (
            f"Stack-level 2-of-3 with reason must pass; got: {[f.message for f in fails]}"
        )

    def test_stack_level_all_three_oses_passes_with_reason(self, tmp_path: Path) -> None:
        """D-101-13 carve-out: stack-level may legitimately list all 3 OSes."""
        body = _valid_manifest_body(
            stacks="[swift]",
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              swift:
                platform_unsupported_stack: [darwin, linux, windows]
                unsupported_reason: "stack disabled pending toolchain modernisation"
                tools:
                  - {name: swiftlint}
                  - {name: swift-format}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails == [], (
            "Stack-level all-3 OSes with reason is the D-101-13 carve-out and must pass; "
            f"got: {[f.message for f in fails]}"
        )

    def test_stack_level_missing_reason_fails(self, tmp_path: Path) -> None:
        """Stack-level ``platform_unsupported_stack`` without reason must fail (D-101-03)."""
        body = _valid_manifest_body(
            stacks="[swift]",
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              swift:
                platform_unsupported_stack: [linux, windows]
                # unsupported_reason intentionally omitted
                tools:
                  - {name: swiftlint}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails, "Stack-level platform_unsupported_stack without reason must fail"
        joined = " ".join(f.message for f in fails).lower()
        assert "unsupported_reason" in joined or "reason" in joined, (
            f"Failure must mention unsupported_reason; got: {joined}"
        )


# ---------------------------------------------------------------------------
# OS enum validation (D-101-03)
# ---------------------------------------------------------------------------


class TestOsEnumValidation:
    """Only ``{darwin, linux, windows}`` are valid OS values at any level."""

    def test_invalid_os_value_at_tool_level_fails(self, tmp_path: Path) -> None:
        """``bsd`` (or any other) is not in the closed enum -- must fail."""
        body = _valid_manifest_body(
            stacks="[python]",
            required_tools="""
            required_tools:
              baseline:
                - name: weirdo
                  platform_unsupported: [bsd]
                  unsupported_reason: "obscure OS"
              python:
                - {name: ruff}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails, "Invalid OS value (bsd) must fail tool-level enum validation"
        joined = " ".join(f.message for f in fails).lower()
        assert "bsd" in joined or "os" in joined or "enum" in joined or "darwin" in joined, (
            f"Failure should reference invalid OS; got: {joined}"
        )

    def test_invalid_os_value_at_stack_level_fails(self, tmp_path: Path) -> None:
        """Stack-level ``platform_unsupported_stack`` shares the same OS enum."""
        body = _valid_manifest_body(
            stacks="[swift]",
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              swift:
                platform_unsupported_stack: [bsd]
                unsupported_reason: "swiftlint and swift-format have no BSD binaries"
                tools:
                  - {name: swiftlint}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails, "Invalid OS value at stack-level must fail enum validation"
        joined = " ".join(f.message for f in fails).lower()
        assert "bsd" in joined or "os" in joined or "enum" in joined or "darwin" in joined, (
            f"Failure should reference invalid OS; got: {joined}"
        )


# ---------------------------------------------------------------------------
# R-15: stack drift (manifest <-> stack_runner)
# ---------------------------------------------------------------------------


class TestStackDriftR15:
    """R-15: every declared stack MUST appear in ``required_tools``."""

    def test_declared_stack_without_required_tools_entry_fails(self, tmp_path: Path) -> None:
        """``providers.stacks: [java]`` but no ``required_tools.java`` -- must fail (R-15)."""
        body = _valid_manifest_body(
            stacks="[java]",
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              python:
                - {name: ruff}
              # NOTE: java intentionally absent — this is the R-15 drift case.
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails, "Declared stack with no required_tools entry must fail (R-15)"
        joined = " ".join(f.message for f in fails).lower()
        assert "java" in joined, f"Failure must name the missing stack 'java'; got: {joined}"

    def test_multiple_declared_stacks_partial_coverage_fails(self, tmp_path: Path) -> None:
        """Two declared stacks, only one covered: lint fails for the missing one."""
        body = _valid_manifest_body(
            stacks="[python, kotlin]",
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              python:
                - {name: ruff}
              # kotlin missing
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails, "Partial stack coverage must fail R-15"
        joined = " ".join(f.message for f in fails).lower()
        assert "kotlin" in joined, f"Failure must name 'kotlin'; got: {joined}"


# ---------------------------------------------------------------------------
# Block presence
# ---------------------------------------------------------------------------


class TestRequiredToolsBlockPresence:
    """A manifest without any ``required_tools`` block must fail the lint."""

    def test_manifest_without_required_tools_block_fails(self, tmp_path: Path) -> None:
        body = """
        schema_version: "2.0"
        framework_version: "0.4.0"
        name: spec-101-fixture
        version: "0.0.1"

        providers:
          vcs: github
          ides: [terminal]
          stacks: [python]

        ai_providers:
          enabled: [claude_code]
          primary: claude_code
        # NOTE: required_tools block intentionally absent.
        """
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert fails, "Manifest without required_tools block must fail the lint"
        joined = " ".join(f.message for f in fails).lower()
        assert "required_tools" in joined or "missing" in joined, (
            f"Failure must reference the absent block; got: {joined}"
        )


# ---------------------------------------------------------------------------
# Aggregator integration (validate_content_integrity)
# ---------------------------------------------------------------------------


class TestAggregatorIntegration:
    """Verify the lint is wired into the public validator service.

    Marked xfail until T-0.8 registers the new check with
    ``validate_content_integrity``. The integration test still serves to
    document the contract: aggregator must FAIL when the lint detects a
    governance violation.
    """

    @pytest.mark.xfail(
        reason="T-0.8 must register required_tools lint with validate_content_integrity",
        strict=False,
    )
    def test_aggregator_surfaces_required_tools_violation(self, tmp_path: Path) -> None:
        from ai_engineering.validator.service import validate_content_integrity

        body = _valid_manifest_body(
            stacks="[java]",
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              python:
                - {name: ruff}
              # java missing — R-15 drift
            """,
        )
        _write_manifest(tmp_path, body)
        # The lint should be picked up automatically; if not registered yet,
        # ``passed`` may still be True -- the xfail above documents that.
        report = validate_content_integrity(tmp_path)
        assert not report.passed, (
            "Aggregator must report failure when required_tools governance is violated"
        )
