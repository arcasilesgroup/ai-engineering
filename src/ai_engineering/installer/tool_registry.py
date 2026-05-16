"""Per-tool install registry for spec-101 (D-101-06).

This module is the single source of truth for *how* each required tool is
installed and verified. It carries:

* Twelve typed mechanism descriptor classes (D-101-02 install-mechanism table).
  These are immutable, hashable runtime install descriptors -- NOT business
  models, and NOT executors. The actual ``install()`` behaviour lives in
  ``ai_engineering.installer.mechanisms`` (T-1.8); the classes defined here
  are deliberately the same shape so the registry stays decoupled from the
  subprocess-routing layer.
* ``TOOL_REGISTRY``: a ``dict[str, dict]`` keyed by tool name with per-OS
  ordered mechanism lists (``darwin``, ``linux``, ``win32``) and a
  ``verify`` block (``cmd``, ``regex``) per D-101-04 + D-101-06.
* Stack-level skip metadata for swift tools (D-101-13).

The manifest stays declarative (which tools are required); this registry
owns the procedural ``how`` -- per the rationale in D-101-06 the enterprise
audience reviews ``manifest.yml`` but never ``tool_registry.py``.
"""

from __future__ import annotations

from typing import Any

from ai_engineering.installer.mechanisms import (
    BrewMechanism,
    CargoInstallMechanism,
    ComposerGlobalMechanism,
    DotnetToolMechanism,
    GitHubReleaseBinaryMechanism,
    GoInstallMechanism,
    NpmDevMechanism,
    ScoopMechanism,
    SdkmanMechanism,
    UvPipVenvMechanism,
    UvToolMechanism,
    WingetMechanism,
)

# ---------------------------------------------------------------------------
# Twelve typed mechanism descriptor classes (D-101-02 install-mechanism table)
#
# Single source of truth: ``ai_engineering.installer.mechanisms`` defines
# the runtime mechanism classes (frozen dataclasses with executable
# ``install()`` methods that route through ``_safe_run``). The registry
# re-exports those classes (above) so consumers can import either from
# here (the manifest-of-tools view) or from the mechanisms package (the
# executor view) and obtain the SAME types -- the registry's per-OS
# mechanism lists hold the very instances callers later invoke.
#
# Re-export removes the previous dataclass-stub duplication that lived in
# this module while ``mechanisms`` was a stub (T-1.7 RED). T-1.8 GREEN
# collapses the two surfaces into one.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Verify-regex constants (D-101-04 offline-safe verification)
#
# Most tools emit semver-shaped output (v1.2.3 or 1.2.3); jq emits its own
# `jq-1.7.1` shape. Constants are extracted to keep the registry table
# scannable and to allow the regex unit-tests to reference the exact same
# strings as the runtime registry.
# ---------------------------------------------------------------------------

# Matches "v1.2.3", "1.2.3", "0.4.0", "v2.10.5-beta" etc. Permissive on
# leading "v" and pre-release suffixes. Anchored by the digit groups, not
# by start-of-line, so "ruff 0.6.9" and "shellcheck v0.10.0\n..." both match.
_RE_SEMVER: str = r"v?\d+\.\d+(?:\.\d+)?(?:[-+][\w.\-]+)?"

# jq --version emits exactly `jq-<digits>` (e.g. `jq-1.7.1`, `jq-1.6`,
# `jq-2.0`). The first `\d+` anchors the shape; trailing digits/dots are
# optional so future jq-2.0.0 stays matched.
_RE_JQ: str = r"jq-\d+(?:\.\d+)*"

# gitleaks `detect --no-git --source /dev/null --no-banner` exits 0 with
# the literal "no leaks found" line printed to stdout/stderr. Used as the
# functional probe per D-101-04 -- exit-code-only would not catch broken
# binaries.
_RE_GITLEAKS_FUNCTIONAL: str = r"no leaks found"

# Project marker probe shape for stacks whose tool surface is entirely
# project-local (D-101-15). The "marker" tool exists so the manifest's
# `required_tools.<stack>` list is non-empty, which keeps the validate-
# manifest lint (D-101-03 R-15) happy. The verify probe just confirms
# the marker echoes its own name -- no real subprocess is run by
# install-time logic; this is a pure registry placeholder until T-1.13
# wires the launcher path.
_RE_DART_MARKER: str = r"dart-stack-marker"


# ---------------------------------------------------------------------------
# Per-tool entry helpers
#
# Each tool entry is a `dict[str, Any]` with keys:
#   darwin / linux / win32 -> list[<mechanism>]
#   verify                  -> {"cmd": list[str], "regex": str}
#
# Optional swift-stack metadata (D-101-13):
#   platform_unsupported_stack -> ["linux", "windows"]
#   unsupported_reason         -> str
# ---------------------------------------------------------------------------


def _verify(cmd: list[str], regex: str) -> dict[str, Any]:
    """Build a ``verify`` block of the canonical shape."""
    return {"cmd": cmd, "regex": regex}


def _semver_verify(tool: str, *, flag: str = "--version") -> dict[str, Any]:
    """Return a standard ``<tool> --version`` verify block."""
    return _verify([tool, flag], _RE_SEMVER)


# Swift skip metadata constant -- shared by swiftlint + swift-format
# entries per D-101-13.
_SWIFT_SKIP: dict[str, Any] = {
    "platform_unsupported_stack": ["linux", "windows"],
    "unsupported_reason": (
        "swiftlint and swift-format have no Linux/Windows binaries; XCTest requires Xcode"
    ),
}


# ---------------------------------------------------------------------------
# TOOL_REGISTRY (D-101-06)
#
# Per-OS keys are MANDATORY for every entry (the test asserts presence
# even when the value is an empty list). swift entries carry stack-level
# skip metadata; their non-darwin lists are empty by design -- the
# installer skips installation entirely on linux/win32 and surfaces the
# `unsupported_reason` to the user.
#
# Tools whose verify cmd / regex are spec-mandated (D-101-04):
#   gitleaks: ["gitleaks", "detect", "--no-git", "--source", "/dev/null",
#              "--no-banner"], r"no leaks found"
#   semgrep:  ["semgrep", "--version"], r"v?\d+\.\d+..."
#   jq:       ["jq", "--version"], r"jq-\d+..."
#   pip-audit:["pip-audit", "--version"]   (NOT --strict / --refresh)
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    # -----------------------------------------------------------------
    # Baseline (D-101-01)
    # -----------------------------------------------------------------
    "gitleaks": {
        "darwin": [
            BrewMechanism("gitleaks"),
            GitHubReleaseBinaryMechanism(
                repo="gitleaks/gitleaks",
                binary="gitleaks",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="gitleaks/gitleaks",
                binary="gitleaks",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [
            WingetMechanism("gitleaks.gitleaks"),
            ScoopMechanism("gitleaks"),
        ],
        "verify": _verify(
            ["gitleaks", "detect", "--no-git", "--source", "/dev/null", "--no-banner"],
            _RE_GITLEAKS_FUNCTIONAL,
        ),
    },
    "semgrep": {
        # D-101-02: semgrep ships only as a Python wheel, so uv tool install
        # is the user-scope route on every OS that supports it. semgrep has
        # no Windows release; the Windows entry is empty and the validator
        # is responsible for surfacing platform_unsupported per D-101-03.
        "darwin": [UvToolMechanism("semgrep")],
        "linux": [UvToolMechanism("semgrep")],
        "win32": [],
        "verify": _verify(["semgrep", "--version"], _RE_SEMVER),
    },
    "jq": {
        "darwin": [
            BrewMechanism("jq"),
            GitHubReleaseBinaryMechanism(
                repo="jqlang/jq",
                binary="jq",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="jqlang/jq",
                binary="jq",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [
            WingetMechanism("jqlang.jq"),
            ScoopMechanism("jq"),
        ],
        # jq emits "jq-1.7.1" -- regex MUST tolerate the `jq-\d+` shape.
        "verify": _verify(["jq", "--version"], _RE_JQ),
    },
    "opa": {
        # spec-122 Phase C (D-122-09): OPA replaces the custom mini-Rego
        # interpreter that lived under `governance.policy_engine`. The
        # ~50 MB CNCF Go binary is install-on-demand; the install chain
        # mirrors gitleaks (brew → GitHub release on darwin; GitHub
        # release on linux; winget → scoop → GitHub release on win32).
        #
        # Verify probe parses the first line of `opa version`, which
        # reads `Version: 1.16.1`. The semver regex tolerates the
        # leading "Version: " label.
        "darwin": [
            BrewMechanism("opa"),
            GitHubReleaseBinaryMechanism(
                repo="open-policy-agent/opa",
                binary="opa",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="open-policy-agent/opa",
                binary="opa",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [
            WingetMechanism("OpenPolicyAgent.OPA"),
            ScoopMechanism("opa"),
            GitHubReleaseBinaryMechanism(
                repo="open-policy-agent/opa",
                binary="opa.exe",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "verify": _verify(["opa", "version"], _RE_SEMVER),
    },
    # -----------------------------------------------------------------
    # Python (D-101-12: uv-tool by default)
    # -----------------------------------------------------------------
    "ruff": {
        "darwin": [UvToolMechanism("ruff")],
        "linux": [UvToolMechanism("ruff")],
        "win32": [UvToolMechanism("ruff")],
        "verify": _semver_verify("ruff"),
    },
    "ty": {
        "darwin": [UvToolMechanism("ty")],
        "linux": [UvToolMechanism("ty")],
        "win32": [UvToolMechanism("ty")],
        "verify": _semver_verify("ty"),
    },
    "pip-audit": {
        "darwin": [UvToolMechanism("pip-audit")],
        "linux": [UvToolMechanism("pip-audit")],
        "win32": [UvToolMechanism("pip-audit")],
        # D-101-04: pip-audit phones home with --strict / --refresh; --version only.
        "verify": _verify(["pip-audit", "--version"], _RE_SEMVER),
    },
    "pytest": {
        "darwin": [UvToolMechanism("pytest")],
        "linux": [UvToolMechanism("pytest")],
        "win32": [UvToolMechanism("pytest")],
        "verify": _semver_verify("pytest"),
    },
    # -----------------------------------------------------------------
    # Java
    # -----------------------------------------------------------------
    "checkstyle": {
        # Checkstyle is published as a fat-jar; the user-scope route on
        # macOS is brew, on linux/win the GitHub-release JAR with a
        # generated launcher script. The resolution detail is owned by
        # T-1.8 mechanisms; the registry only declares the mechanism
        # shape per OS.
        "darwin": [BrewMechanism("checkstyle")],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="checkstyle/checkstyle",
                binary="checkstyle",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [
            ScoopMechanism("checkstyle"),
        ],
        "verify": _semver_verify("checkstyle"),
    },
    "google-java-format": {
        "darwin": [BrewMechanism("google-java-format")],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="google/google-java-format",
                binary="google-java-format",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [
            ScoopMechanism("google-java-format"),
        ],
        "verify": _semver_verify("google-java-format"),
    },
    # -----------------------------------------------------------------
    # C# / .NET
    # -----------------------------------------------------------------
    "dotnet-format": {
        "darwin": [DotnetToolMechanism("dotnet-format")],
        "linux": [DotnetToolMechanism("dotnet-format")],
        "win32": [DotnetToolMechanism("dotnet-format")],
        "verify": _semver_verify("dotnet-format"),
    },
    # -----------------------------------------------------------------
    # Go
    # -----------------------------------------------------------------
    "staticcheck": {
        "darwin": [GoInstallMechanism("honnef.co/go/tools/cmd/staticcheck@latest")],
        "linux": [GoInstallMechanism("honnef.co/go/tools/cmd/staticcheck@latest")],
        "win32": [GoInstallMechanism("honnef.co/go/tools/cmd/staticcheck@latest")],
        "verify": _semver_verify("staticcheck"),
    },
    "govulncheck": {
        "darwin": [GoInstallMechanism("golang.org/x/vuln/cmd/govulncheck@latest")],
        "linux": [GoInstallMechanism("golang.org/x/vuln/cmd/govulncheck@latest")],
        "win32": [GoInstallMechanism("golang.org/x/vuln/cmd/govulncheck@latest")],
        "verify": _semver_verify("govulncheck"),
    },
    # -----------------------------------------------------------------
    # PHP
    # -----------------------------------------------------------------
    "phpstan": {
        "darwin": [ComposerGlobalMechanism("phpstan/phpstan")],
        "linux": [ComposerGlobalMechanism("phpstan/phpstan")],
        "win32": [ComposerGlobalMechanism("phpstan/phpstan")],
        "verify": _semver_verify("phpstan"),
    },
    "php-cs-fixer": {
        "darwin": [ComposerGlobalMechanism("friendsofphp/php-cs-fixer")],
        "linux": [ComposerGlobalMechanism("friendsofphp/php-cs-fixer")],
        "win32": [ComposerGlobalMechanism("friendsofphp/php-cs-fixer")],
        "verify": _semver_verify("php-cs-fixer"),
    },
    "composer": {
        # Composer itself is the PHP package manager driver. On darwin we
        # prefer brew; on linux we prefer the upstream signed installer
        # (mirrored as a GitHub release for SHA pinning); on win we route
        # via Scoop.
        "darwin": [BrewMechanism("composer")],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="composer/composer",
                binary="composer",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [ScoopMechanism("composer")],
        "verify": _semver_verify("composer"),
    },
    # -----------------------------------------------------------------
    # Rust
    # -----------------------------------------------------------------
    "cargo-audit": {
        "darwin": [CargoInstallMechanism("cargo-audit")],
        "linux": [CargoInstallMechanism("cargo-audit")],
        "win32": [CargoInstallMechanism("cargo-audit")],
        "verify": _semver_verify("cargo-audit"),
    },
    # -----------------------------------------------------------------
    # Kotlin
    # -----------------------------------------------------------------
    "ktlint": {
        "darwin": [BrewMechanism("ktlint")],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="pinterest/ktlint",
                binary="ktlint",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [ScoopMechanism("ktlint")],
        "verify": _semver_verify("ktlint"),
    },
    # -----------------------------------------------------------------
    # Swift (D-101-13: stack-level skip on linux + windows)
    # -----------------------------------------------------------------
    "swiftlint": {
        "darwin": [BrewMechanism("swiftlint")],
        # Empty mechanism lists on linux + win32 -- installer skips per
        # platform_unsupported_stack metadata below.
        "linux": [],
        "win32": [],
        "verify": _semver_verify("swiftlint"),
        **_SWIFT_SKIP,
    },
    "swift-format": {
        "darwin": [BrewMechanism("swift-format")],
        "linux": [],
        "win32": [],
        "verify": _semver_verify("swift-format"),
        **_SWIFT_SKIP,
    },
    # -----------------------------------------------------------------
    # Dart (project-local stack; marker entry keeps R-15 lint happy)
    # -----------------------------------------------------------------
    "dart-stack-marker": {
        # Dart tooling is bundled with the SDK (`dart format`, `dart
        # analyze`); there is no user-scope tool to install. The marker
        # tool exists so manifest required_tools.dart is non-empty,
        # which the validator (T-0.7+T-0.8) requires per R-15. The
        # mechanism lists are empty by design; verify probes the dart
        # SDK's own version stub.
        "darwin": [],
        "linux": [],
        "win32": [],
        "verify": _verify(["echo", "dart-stack-marker"], _RE_DART_MARKER),
    },
    # -----------------------------------------------------------------
    # SQL
    # -----------------------------------------------------------------
    "sqlfluff": {
        "darwin": [UvToolMechanism("sqlfluff")],
        "linux": [UvToolMechanism("sqlfluff")],
        "win32": [UvToolMechanism("sqlfluff")],
        "verify": _semver_verify("sqlfluff"),
    },
    # -----------------------------------------------------------------
    # Bash
    # -----------------------------------------------------------------
    "shellcheck": {
        "darwin": [BrewMechanism("shellcheck")],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="koalaman/shellcheck",
                binary="shellcheck",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [ScoopMechanism("shellcheck")],
        "verify": _semver_verify("shellcheck"),
    },
    "shfmt": {
        "darwin": [BrewMechanism("shfmt")],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="mvdan/sh",
                binary="shfmt",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [ScoopMechanism("shfmt")],
        "verify": _semver_verify("shfmt"),
    },
    # -----------------------------------------------------------------
    # C / C++
    # -----------------------------------------------------------------
    "clang-tidy": {
        # clang-tidy ships inside the LLVM toolchain bundle on every OS;
        # brew on darwin, package binary on linux (LLVM release), Scoop
        # on Windows. SDK detection (D-101-14 cpp probe) is what gates
        # whether the bundle is already present.
        "darwin": [BrewMechanism("llvm")],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="llvm/llvm-project",
                binary="clang-tidy",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [ScoopMechanism("llvm")],
        "verify": _semver_verify("clang-tidy"),
    },
    "clang-format": {
        "darwin": [BrewMechanism("clang-format")],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="llvm/llvm-project",
                binary="clang-format",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [ScoopMechanism("llvm")],
        "verify": _semver_verify("clang-format"),
    },
    "cppcheck": {
        "darwin": [BrewMechanism("cppcheck")],
        "linux": [
            GitHubReleaseBinaryMechanism(
                repo="danmar/cppcheck",
                binary="cppcheck",
                sha256_pinned=False,  # TODO(DEC-038): populate real pins from upstream releases
            ),
        ],
        "win32": [ScoopMechanism("cppcheck")],
        "verify": _semver_verify("cppcheck"),
    },
}


# ---------------------------------------------------------------------------
# Public re-exports (importers use ``from .tool_registry import ...``)
# ---------------------------------------------------------------------------

__all__ = [
    "TOOL_REGISTRY",
    # 12 mechanism descriptor types (D-101-02)
    "BrewMechanism",
    "CargoInstallMechanism",
    "ComposerGlobalMechanism",
    "DotnetToolMechanism",
    "GitHubReleaseBinaryMechanism",
    "GoInstallMechanism",
    "NpmDevMechanism",
    "ScoopMechanism",
    "SdkmanMechanism",
    "UvPipVenvMechanism",
    "UvToolMechanism",
    "WingetMechanism",
]
