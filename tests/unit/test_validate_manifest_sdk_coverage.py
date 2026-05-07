"""Tests for spec-101 T-4.9 SDK-coverage lint extension.

The lint surface lives in
:mod:`ai_engineering.validator.categories.required_tools` alongside the
existing R-15 / D-101-03 / D-101-13 governance. T-4.9 adds:

- forward direction: every declared SDK-required stack MUST appear in
  ``prereqs.sdk_per_stack`` with a non-empty ``install_link``;
- inverse direction: an ``sdk_per_stack`` entry for a stack NOT in the
  SDK-required set is itself a violation (misleading manifest shape).

The SDK-required set is `{java, kotlin, swift, dart, csharp, go, rust, php,
cpp}` (D-101-14 / NG-11). Other stacks (python, typescript, javascript,
sql, bash) MUST NOT carry an entry.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent


def _write_manifest(root: Path, body: str) -> Path:
    ai_dir = root / ".ai-engineering"
    ai_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = ai_dir / "manifest.yml"
    manifest_path.write_text(dedent(body).lstrip("\n"), encoding="utf-8")
    return manifest_path


def _run_lint(root: Path):
    from ai_engineering.validator._shared import IntegrityStatus
    from ai_engineering.validator.categories.required_tools import (
        _check_required_tools,
    )
    from ai_engineering.validator.service import IntegrityReport

    report = IntegrityReport()
    _check_required_tools(root, report)
    fails = [c for c in report.checks if c.status == IntegrityStatus.FAIL]
    return report, fails


# Shared body builder. Test fixtures interpolate stacks + required_tools
# block + prereqs section to exercise specific lint paths.
#
# Both ``required_tools`` and ``prereqs`` are passed as ``textwrap.dedent``-able
# blocks. We :func:`textwrap.dedent` them eagerly, normalise the leading
# newline, and concatenate at column 0 so the final YAML is a single
# uniformly-indented document. The required_tools governance lint already
# carries an indent normaliser for ``required_tools:`` (see
# ``_normalise_required_tools_indent``); for everything else the test author
# is responsible for the column-0 invariant.
def _manifest_body(
    *,
    stacks: str,
    required_tools: str,
    prereqs: str = "",
) -> str:
    head = (
        'schema_version: "2.0"\n'
        'framework_version: "0.4.0"\n'
        "name: t49-fixture\n"
        'version: "0.0.1"\n'
        "\n"
        "providers:\n"
        "  vcs: github\n"
        "  ides: [terminal]\n"
        f"  stacks: {stacks}\n"
        "\n"
        "ai_providers:\n"
        "  enabled: [claude-code]\n"
        "  primary: claude-code\n"
    )
    parts = [head]
    if prereqs:
        parts.append(dedent(prereqs).strip("\n") + "\n")
    parts.append(dedent(required_tools).strip("\n") + "\n")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Forward direction: declared SDK-required stack MUST have prereqs entry
# ---------------------------------------------------------------------------


class TestSdkRequiredStackMustHavePrereq:
    """T-4.9 forward direction."""

    def test_declared_java_without_prereq_fails(self, tmp_path: Path) -> None:
        """`stacks: [java]` but no `prereqs.sdk_per_stack.java` is a hard fail."""
        body = _manifest_body(
            stacks="[java]",
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              java:
                - {name: checkstyle}
            """,
            # prereqs deliberately omitted.
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert any("sdk-coverage-missing-prereq" in c.name for c in fails), (
            "Declared java stack without prereqs.sdk_per_stack.java must fail T-4.9; "
            f"got: {[(c.name, c.message) for c in fails]}"
        )

    def test_declared_rust_with_empty_link_fails(self, tmp_path: Path) -> None:
        """`prereqs.sdk_per_stack.rust.install_link: ''` is a hard fail."""
        body = _manifest_body(
            stacks="[rust]",
            prereqs="""
            prereqs:
              uv:
                version_range: ">=0.4.0,<1.0"
              sdk_per_stack:
                rust: {name: Rust toolchain, install_link: ""}
            """,
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              rust:
                - {name: cargo-audit}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert any("sdk-coverage-empty-link" in c.name for c in fails), (
            f"Empty install_link must fail T-4.9; got: {[(c.name, c.message) for c in fails]}"
        )

    def test_declared_python_without_prereq_passes(self, tmp_path: Path) -> None:
        """`stacks: [python]` is NOT in the SDK-required set — no prereqs needed."""
        body = _manifest_body(
            stacks="[python]",
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              python:
                - {name: ruff}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert not any("sdk-coverage" in c.name for c in fails), (
            "Python stack does not require an SDK prereq entry; "
            f"got: {[(c.name, c.message) for c in fails]}"
        )

    def test_declared_go_with_link_passes(self, tmp_path: Path) -> None:
        """Happy path: declared go stack with valid prereq link."""
        body = _manifest_body(
            stacks="[go]",
            prereqs="""
            prereqs:
              uv:
                version_range: ">=0.4.0,<1.0"
              sdk_per_stack:
                go: {name: Go toolchain, install_link: "https://go.dev/dl/"}
            """,
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              go:
                - {name: staticcheck}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert not any("sdk-coverage" in c.name for c in fails), (
            f"Happy path must pass T-4.9; got: {[(c.name, c.message) for c in fails]}"
        )


# ---------------------------------------------------------------------------
# Inverse direction: spurious entry for non-SDK-required stack
# ---------------------------------------------------------------------------


class TestSpuriousSdkEntry:
    """T-4.9 inverse direction — entries for stacks outside the SDK-required set fail."""

    def test_spurious_python_entry_fails(self, tmp_path: Path) -> None:
        """`prereqs.sdk_per_stack.python` is forbidden — python is auto-installed."""
        body = _manifest_body(
            stacks="[python]",
            prereqs="""
            prereqs:
              uv:
                version_range: ">=0.4.0,<1.0"
              sdk_per_stack:
                python: {name: Python, install_link: "https://www.python.org/"}
            """,
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              python:
                - {name: ruff}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert any("sdk-coverage-spurious-entry" in c.name for c in fails), (
            f"Spurious python entry must fail T-4.9; got: {[(c.name, c.message) for c in fails]}"
        )

    def test_spurious_typescript_entry_fails(self, tmp_path: Path) -> None:
        body = _manifest_body(
            stacks="[typescript]",
            prereqs="""
            prereqs:
              uv:
                version_range: ">=0.4.0,<1.0"
              sdk_per_stack:
                typescript: {name: Node, install_link: "https://nodejs.org/"}
            """,
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              typescript:
                - {name: prettier, scope: project_local}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert any("sdk-coverage-spurious-entry" in c.name for c in fails), (
            "Spurious typescript entry must fail T-4.9; "
            f"got: {[(c.name, c.message) for c in fails]}"
        )


# ---------------------------------------------------------------------------
# Multi-stack coverage matrix
# ---------------------------------------------------------------------------


class TestMultiStackCoverage:
    """End-to-end shape of a full canonical manifest."""

    def test_canonical_14_stack_manifest_passes(self, tmp_path: Path) -> None:
        """When the manifest declares the canonical 14 stacks plus the matching
        prereqs.sdk_per_stack entries, the lint must produce zero T-4.9 fails."""
        # Project declares only python here (mirrors the canonical
        # `.ai-engineering/manifest.yml` providers.stacks). Required_tools
        # block carries every stack so the R-15 drift check does not trip,
        # and prereqs covers all 9 SDK-required stacks.
        body = _manifest_body(
            stacks="[python]",
            prereqs="""
            prereqs:
              uv:
                version_range: ">=0.4.0,<1.0"
              sdk_per_stack:
                java: {name: JDK, min_version: "21", install_link: "https://adoptium.net/"}
                kotlin: {name: JDK, min_version: "21", install_link: "https://adoptium.net/"}
                swift: {name: Swift toolchain, install_link: "https://www.swift.org/install/"}
                dart: {name: Dart SDK, install_link: "https://dart.dev/get-dart"}
                csharp: {name: ".NET SDK", min_version: "9", install_link: "https://dotnet.microsoft.com/download"}
                go: {name: Go toolchain, install_link: "https://go.dev/dl/"}
                rust: {name: Rust toolchain, install_link: "https://rustup.rs/"}
                php: {name: PHP, min_version: "8.2", install_link: "https://www.php.net/downloads"}
                cpp: {name: clang/LLVM, install_link: "https://llvm.org/builds/"}
            """,
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              python:
                - {name: ruff}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        assert not any("sdk-coverage" in c.name for c in fails), (
            f"Canonical-shape manifest must pass T-4.9; got: {[(c.name, c.message) for c in fails]}"
        )

    def test_two_sdk_stacks_one_missing_fails(self, tmp_path: Path) -> None:
        """Both java and rust declared; only java has an entry — fail names rust."""
        body = _manifest_body(
            stacks="[java, rust]",
            prereqs="""
            prereqs:
              uv:
                version_range: ">=0.4.0,<1.0"
              sdk_per_stack:
                java: {name: JDK, min_version: "21", install_link: "https://adoptium.net/"}
            """,
            required_tools="""
            required_tools:
              baseline:
                - {name: gitleaks}
              java:
                - {name: checkstyle}
              rust:
                - {name: cargo-audit}
            """,
        )
        _write_manifest(tmp_path, body)
        _, fails = _run_lint(tmp_path)
        joined_messages = " ".join(c.message for c in fails)
        assert any("sdk-coverage-missing-prereq" in c.name for c in fails), (
            "Missing prereq for declared rust must fail T-4.9; "
            f"got: {[(c.name, c.message) for c in fails]}"
        )
        assert "rust" in joined_messages, (
            f"Failure message must name 'rust'; got: {joined_messages}"
        )
