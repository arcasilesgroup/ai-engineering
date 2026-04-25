"""RED-phase tests for ``installer.tool_registry`` (spec-101, T-1.1).

Verifies the contract described in spec D-101-06 + D-101-04 + D-101-13:

* ``TOOL_REGISTRY`` is a ``dict[str, dict]`` keyed by tool name.
* Each entry exposes per-OS mechanism keys (``darwin``, ``linux``, ``win32``)
  whose values are lists of typed mechanism objects (12 mechanism types per
  D-101-02 install-mechanism table).
* Each entry exposes a ``verify`` block of shape ``{"cmd": list[str],
  "regex": str}`` for offline-safe post-install verification (D-101-04).
* Per-tool ``verify.cmd`` is the canonical offline-safe invocation (e.g.
  ``gitleaks detect --no-git --source /dev/null --no-banner`` for gitleaks
  per D-101-04; ``semgrep --version`` for semgrep — never ``--config auto``).
* swift entries (swiftlint, swift-format) carry stack-level skip metadata
  pointing to D-101-13 (``platform_unsupported_stack: [linux, windows]``).
* A parametric loop covers >= 12 named tools spanning 14 stacks and asserts
  structure validity for each.

These tests MUST fail until T-1.2 (``installer/tool_registry.py``) lands.
They are written against the contract — no production code is created here.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Iterable

# ---------------------------------------------------------------------------
# Canonical expectations sourced from spec D-101-01 + D-101-02 + D-101-06.
# ---------------------------------------------------------------------------

# Per-OS mechanism keys spec.md D-101-06 example uses.
_OS_KEYS: tuple[str, ...] = ("darwin", "linux", "win32")

# 12 mechanism class names per task description (D-101-02 install-mechanism
# table). Each class lives in ``installer.tool_registry`` (or a sibling
# module re-exported through it).
_MECHANISM_CLASS_NAMES: tuple[str, ...] = (
    "BrewMechanism",
    "GitHubReleaseBinaryMechanism",
    "WingetMechanism",
    "ScoopMechanism",
    "UvToolMechanism",
    "UvPipVenvMechanism",
    "NpmDevMechanism",
    "DotnetToolMechanism",
    "CargoInstallMechanism",
    "GoInstallMechanism",
    "ComposerGlobalMechanism",
    "SdkmanMechanism",
)
assert len(_MECHANISM_CLASS_NAMES) == 12, (
    "spec-101 task T-1.1 mandates 12 mechanism types; "
    f"_MECHANISM_CLASS_NAMES has {len(_MECHANISM_CLASS_NAMES)}"
)

# Baseline tools required across every stack (D-101-01 baseline block).
_BASELINE_TOOLS: tuple[str, ...] = ("gitleaks", "semgrep", "jq")

# Tools that must be present in the registry. Covers the baseline + python
# + a representative spread across the 14 declared stacks. Total >= 12 so
# the parametric coverage assertion (T-1.1 requirement: "at least 12 named
# tools") holds even if some entries are temporarily withheld for upstream
# release-channel reasons.
#
# Full list mirrors required_tools in .ai-engineering/manifest.yml — covering
# baseline + all 14 stacks except the four project_local-only typescript/js
# tools (prettier/eslint/tsc/vitest) which are NOT installed via the registry
# per D-101-15 (they are launched via ``npx`` from ``installer/launchers.py``).
_REQUIRED_TOOL_NAMES: tuple[str, ...] = (
    # baseline (D-101-01)
    "gitleaks",
    "semgrep",
    "jq",
    # python (D-101-12 -- via uv tool install)
    "ruff",
    "ty",
    "pip-audit",
    "pytest",
    # java
    "checkstyle",
    "google-java-format",
    # csharp
    "dotnet-format",
    # go
    "staticcheck",
    "govulncheck",
    # php
    "phpstan",
    "php-cs-fixer",
    "composer",
    # rust
    "cargo-audit",
    # kotlin
    "ktlint",
    # swift (D-101-13: stack-level skip for linux/windows)
    "swiftlint",
    "swift-format",
    # dart
    "dart-stack-marker",
    # sql
    "sqlfluff",
    # bash
    "shellcheck",
    "shfmt",
    # cpp
    "clang-tidy",
    "clang-format",
    "cppcheck",
)
assert len(_REQUIRED_TOOL_NAMES) >= 12, (
    "spec-101 T-1.1 mandates parametric coverage of >= 12 tools; "
    f"_REQUIRED_TOOL_NAMES has {len(_REQUIRED_TOOL_NAMES)}"
)

# Tools that fall under stack-level platform_unsupported_stack per D-101-13
# (swiftlint, swift-format). These entries must carry stack metadata
# pointing to D-101-13.
_SWIFT_STACK_TOOLS: tuple[str, ...] = ("swiftlint", "swift-format")

# Specific verify.cmd shapes called out by spec D-101-04 + task description.
# Tools NOT listed here are validated by the generic regex-shape check below.
_EXPECTED_VERIFY_CMDS: dict[str, list[str]] = {
    # D-101-04: end-to-end offline-safe functional probe, not just --version.
    "gitleaks": ["gitleaks", "detect", "--no-git", "--source", "/dev/null", "--no-banner"],
    # D-101-04: semgrep phones home on broader invocations; --version only.
    "semgrep": ["semgrep", "--version"],
    # Task description: jq verify regex must match `jq-\d+`.
    # (No specific cmd mandated; tested separately via regex shape.)
}

# Specific verify.regex shapes. semver-shaped (vX.Y.Z) is the default; jq's
# output is `jq-1.7.1` so the regex must accommodate the `jq-\d+` shape.
_SEMVER_RE_SAMPLES: tuple[str, ...] = (
    "v1.2.3",
    "1.2.3",
    "v0.18.0",
    "0.4.0",
    "v2.10.5-beta",
)


# ---------------------------------------------------------------------------
# Module import contract — must currently FAIL with ModuleNotFoundError.
# ---------------------------------------------------------------------------


def _import_registry_module() -> object:
    """Import the registry module; pytest collects the ImportError below."""
    import importlib

    return importlib.import_module("ai_engineering.installer.tool_registry")


def _get_registry() -> dict[str, dict[str, object]]:
    """Return ``TOOL_REGISTRY`` from the installer module under test."""
    module = _import_registry_module()
    registry = getattr(module, "TOOL_REGISTRY", None)
    assert registry is not None, "ai_engineering.installer.tool_registry must export TOOL_REGISTRY"
    assert isinstance(registry, dict), "TOOL_REGISTRY must be a dict[str, dict] keyed by tool name"
    return registry


def _get_mechanism_classes() -> dict[str, type]:
    """Return the 12 mechanism classes exported by the registry module."""
    module = _import_registry_module()
    out: dict[str, type] = {}
    missing: list[str] = []
    for name in _MECHANISM_CLASS_NAMES:
        cls = getattr(module, name, None)
        if cls is None:
            missing.append(name)
            continue
        out[name] = cls
    assert not missing, (
        f"ai_engineering.installer.tool_registry must export all 12 "
        f"mechanism types; missing: {missing}"
    )
    return out


# ---------------------------------------------------------------------------
# Module + dict shape
# ---------------------------------------------------------------------------


class TestRegistryModuleShape:
    """Contract: module exports TOOL_REGISTRY and the 12 mechanism types."""

    def test_module_imports_cleanly(self) -> None:
        # Until T-1.2 lands, this MUST raise ModuleNotFoundError.
        _import_registry_module()

    def test_tool_registry_is_dict(self) -> None:
        registry = _get_registry()
        assert isinstance(registry, dict)
        assert len(registry) >= 12, f"TOOL_REGISTRY must cover >= 12 tools; has {len(registry)}"

    def test_all_12_mechanism_classes_exported(self) -> None:
        classes = _get_mechanism_classes()
        assert set(classes) == set(_MECHANISM_CLASS_NAMES)


# ---------------------------------------------------------------------------
# Per-tool entry presence + per-OS shape
# ---------------------------------------------------------------------------


class TestRequiredToolPresence:
    """Contract: every required tool name is keyed in TOOL_REGISTRY."""

    def test_all_baseline_tools_present(self) -> None:
        registry = _get_registry()
        for name in _BASELINE_TOOLS:
            assert name in registry, f"baseline tool '{name}' missing from TOOL_REGISTRY (D-101-01)"

    def test_key_python_tools_present(self) -> None:
        registry = _get_registry()
        for name in ("ruff", "ty", "pip-audit", "pytest"):
            assert name in registry, f"python tool '{name}' missing from TOOL_REGISTRY (D-101-12)"

    def test_at_least_one_tool_per_stack_present(self) -> None:
        """Coverage probe: every stack has at least one entry registered.

        Mirrors required_tools in manifest.yml. Excludes typescript /
        javascript because their tools are project_local (D-101-15).
        """
        registry = _get_registry()
        per_stack_probes: dict[str, str] = {
            "python": "ruff",
            "java": "checkstyle",
            "csharp": "dotnet-format",
            "go": "staticcheck",
            "php": "phpstan",
            "rust": "cargo-audit",
            "kotlin": "ktlint",
            "swift": "swiftlint",
            "dart": "dart-stack-marker",
            "sql": "sqlfluff",
            "bash": "shellcheck",
            "cpp": "clang-tidy",
        }
        missing: list[tuple[str, str]] = []
        for stack, probe in per_stack_probes.items():
            if probe not in registry:
                missing.append((stack, probe))
        assert not missing, f"TOOL_REGISTRY missing per-stack probe tools: {missing}"


class TestPerOsMechanismShape:
    """Contract: each entry has per-OS mechanism keys with list values."""

    def test_each_entry_has_per_os_mechanism_keys(self) -> None:
        registry = _get_registry()
        offenders: list[str] = []
        for tool_name, entry in registry.items():
            assert isinstance(entry, dict), (
                f"TOOL_REGISTRY['{tool_name}'] must be a dict; got {type(entry).__name__}"
            )
            for os_key in _OS_KEYS:
                if os_key not in entry:
                    offenders.append(f"{tool_name}.{os_key}")
        assert not offenders, (
            f"every entry must declare all per-OS keys ({_OS_KEYS}); missing: {offenders}"
        )

    def test_each_per_os_value_is_list_of_typed_mechanisms(self) -> None:
        registry = _get_registry()
        classes = _get_mechanism_classes()
        allowed_types = tuple(classes.values())
        offenders: list[str] = []
        for tool_name, entry in registry.items():
            for os_key in _OS_KEYS:
                mechanisms = entry.get(os_key)
                # Tools may legitimately have an empty list per OS (e.g. when
                # platform_unsupported applies); the value must still BE a
                # list, never None / missing / scalar.
                if not isinstance(mechanisms, list):
                    offenders.append(
                        f"{tool_name}.{os_key} must be list, got {type(mechanisms).__name__}"
                    )
                    continue
                for idx, mech in enumerate(mechanisms):
                    if not isinstance(mech, allowed_types):
                        offenders.append(
                            f"{tool_name}.{os_key}[{idx}] is not a mechanism "
                            f"(got {type(mech).__name__})"
                        )
        assert not offenders, (
            "mechanism entries must be instances of one of the 12 typed "
            f"mechanism classes; offenders: {offenders}"
        )


# ---------------------------------------------------------------------------
# Verify-block shape (D-101-04 + D-101-06)
# ---------------------------------------------------------------------------


def _get_verify(entry: dict[str, object]) -> dict[str, object]:
    verify = entry.get("verify")
    assert isinstance(verify, dict), (
        f"every entry must declare 'verify' as dict; got {type(verify).__name__}"
    )
    return verify


class TestVerifyBlockShape:
    """Contract: each entry has verify.cmd (list[str]) + verify.regex (str)."""

    def test_verify_block_present_for_every_tool(self) -> None:
        registry = _get_registry()
        offenders: list[str] = []
        for tool_name, entry in registry.items():
            if not isinstance(entry.get("verify"), dict):
                offenders.append(tool_name)
        assert not offenders, f"TOOL_REGISTRY entries missing 'verify' dict: {offenders}"

    def test_verify_cmd_is_list_of_str(self) -> None:
        registry = _get_registry()
        offenders: list[str] = []
        for tool_name, entry in registry.items():
            verify = _get_verify(entry)
            cmd = verify.get("cmd")
            if not isinstance(cmd, list) or not cmd:
                offenders.append(f"{tool_name}: cmd is not a non-empty list")
                continue
            for idx, part in enumerate(cmd):
                if not isinstance(part, str):
                    offenders.append(
                        f"{tool_name}: cmd[{idx}] must be str, got {type(part).__name__}"
                    )
        assert not offenders, f"verify.cmd shape violations: {offenders}"

    def test_verify_regex_is_compilable_str(self) -> None:
        registry = _get_registry()
        offenders: list[str] = []
        for tool_name, entry in registry.items():
            verify = _get_verify(entry)
            regex = verify.get("regex")
            if not isinstance(regex, str) or not regex:
                offenders.append(f"{tool_name}: regex must be non-empty str")
                continue
            try:
                re.compile(regex)
            except re.error as exc:
                offenders.append(f"{tool_name}: regex does not compile ({exc})")
        assert not offenders, f"verify.regex shape violations: {offenders}"


# ---------------------------------------------------------------------------
# Specific verify cmds called out by spec D-101-04
# ---------------------------------------------------------------------------


class TestVerifyCmdSpecCompliance:
    """Contract: D-101-04 mandates specific offline-safe verify invocations."""

    def test_gitleaks_verify_cmd_exact_match(self) -> None:
        # D-101-04: "gitleaks detect --no-git --source /dev/null --no-banner"
        # is the canonical offline-safe functional probe.
        registry = _get_registry()
        verify = _get_verify(registry["gitleaks"])
        assert verify["cmd"] == [
            "gitleaks",
            "detect",
            "--no-git",
            "--source",
            "/dev/null",
            "--no-banner",
        ], f"D-101-04 mandates the exact gitleaks offline-safe probe; got {verify['cmd']!r}"

    def test_semgrep_verify_cmd_is_version_only(self) -> None:
        # D-101-04: semgrep phones home on broader invocations; --version only.
        registry = _get_registry()
        verify = _get_verify(registry["semgrep"])
        assert verify["cmd"] == ["semgrep", "--version"], (
            f"D-101-04 mandates 'semgrep --version' only; got {verify['cmd']!r}"
        )
        # Defensive: ensure no network-touching args slipped in.
        forbidden = {"--config", "auto", "--refresh", "--update"}
        leaked = forbidden & set(verify["cmd"])
        assert not leaked, f"D-101-04 forbids network-touching semgrep args; leaked: {leaked}"

    def test_jq_verify_regex_matches_jq_dash_digits(self) -> None:
        # Task description: regex format `r"jq-\d+"` for jq.
        registry = _get_registry()
        verify = _get_verify(registry["jq"])
        regex = verify["regex"]
        assert isinstance(regex, str)
        # Must match real jq --version outputs.
        for sample in ("jq-1.7.1", "jq-1.6", "jq-2.0"):
            assert re.search(regex, sample), (
                f"jq regex '{regex}' fails to match real output sample '{sample}'"
            )

    def test_pip_audit_verify_cmd_is_version_only(self) -> None:
        # D-101-04: pip-audit phones home on broader invocations.
        registry = _get_registry()
        verify = _get_verify(registry["pip-audit"])
        assert verify["cmd"] == ["pip-audit", "--version"], (
            f"D-101-04 mandates 'pip-audit --version' only; got {verify['cmd']!r}"
        )


# ---------------------------------------------------------------------------
# Parametric per-tool structure (>= 12 tools per T-1.1 requirement)
# ---------------------------------------------------------------------------


class TestParametricToolStructure:
    """Each registered tool has correct per-OS + verify shape."""

    @pytest.mark.parametrize("tool_name", _REQUIRED_TOOL_NAMES)
    def test_tool_entry_shape(self, tool_name: str) -> None:
        registry = _get_registry()
        assert tool_name in registry, f"required tool '{tool_name}' missing from TOOL_REGISTRY"
        entry = registry[tool_name]
        assert isinstance(entry, dict)

        # Per-OS mechanism keys exist.
        for os_key in _OS_KEYS:
            assert os_key in entry, f"{tool_name} missing per-OS key '{os_key}'"
            assert isinstance(entry[os_key], list), f"{tool_name}.{os_key} must be list"

        # Verify block is well-formed.
        verify = entry.get("verify")
        assert isinstance(verify, dict), f"{tool_name} missing 'verify' dict"
        cmd = verify.get("cmd")
        assert isinstance(cmd, list) and cmd, f"{tool_name} verify.cmd not list"
        assert all(isinstance(p, str) for p in cmd), f"{tool_name} verify.cmd parts must be str"
        regex = verify.get("regex")
        assert isinstance(regex, str) and regex, f"{tool_name} verify.regex must be non-empty str"
        # regex is compilable
        re.compile(regex)


# ---------------------------------------------------------------------------
# Regex semver matching for tools whose --version outputs semver-shaped data
# ---------------------------------------------------------------------------


class TestRegexSemverShape:
    """Most tools output a semver string; verify regex must match the shape."""

    @pytest.mark.parametrize(
        "tool_name",
        # Subset whose --version output is canonical semver shaped (vX.Y.Z
        # or X.Y.Z). Excludes jq (custom format) and tools whose verify cmd
        # is a functional probe rather than --version (gitleaks).
        ("ruff", "ty", "pip-audit", "pytest", "semgrep", "ktlint", "shellcheck"),
    )
    def test_regex_matches_real_world_semver_samples(self, tool_name: str) -> None:
        registry = _get_registry()
        if tool_name not in registry:
            pytest.fail(f"required tool '{tool_name}' missing from TOOL_REGISTRY")
        verify = _get_verify(registry[tool_name])
        regex = verify["regex"]
        compiled = re.compile(regex)
        # At least ONE of the canonical samples must match — otherwise the
        # regex is not capturing real --version output.
        matches = [s for s in _SEMVER_RE_SAMPLES if compiled.search(s)]
        assert matches, (
            f"{tool_name} regex '{regex}' fails to match any of the canonical "
            f"semver samples: {_SEMVER_RE_SAMPLES}"
        )


# ---------------------------------------------------------------------------
# Swift entries carry stack-level skip metadata (D-101-13)
# ---------------------------------------------------------------------------


class TestSwiftStackSkipMetadata:
    """D-101-13: swift tools carry stack-level skip metadata."""

    @pytest.mark.parametrize("tool_name", _SWIFT_STACK_TOOLS)
    def test_swift_tool_marks_stack_skip(self, tool_name: str) -> None:
        registry = _get_registry()
        if tool_name not in registry:
            pytest.fail(f"swift tool '{tool_name}' missing from TOOL_REGISTRY")
        entry = registry[tool_name]

        # The exact key name is left to T-1.2 implementation (likely
        # `platform_unsupported_stack` mirroring the manifest schema or
        # `stack_skip` shorthand). Probe both common shapes; one must hold
        # AND must declare both linux and windows.
        candidates: list[Iterable[str] | None] = [
            entry.get("platform_unsupported_stack"),
            entry.get("stack_skip"),
            entry.get("skipped_on"),
        ]
        unsupported = next(
            (c for c in candidates if c is not None),
            None,
        )
        assert unsupported is not None, (
            f"D-101-13: swift tool '{tool_name}' must carry stack-level skip "
            "metadata (e.g. platform_unsupported_stack=['linux','windows'])"
        )
        unsupported_set = set(unsupported)
        assert {"linux", "windows"}.issubset(unsupported_set), (
            f"D-101-13: swift tool '{tool_name}' skip metadata must include "
            f"'linux' AND 'windows'; got {unsupported_set!r}"
        )

    @pytest.mark.parametrize("tool_name", _SWIFT_STACK_TOOLS)
    def test_swift_tool_carries_unsupported_reason(self, tool_name: str) -> None:
        # D-101-03 + D-101-13: any platform_unsupported_stack declaration MUST
        # carry a sibling `unsupported_reason` (lint enforces it; the registry
        # entry should expose it for use in error messages).
        registry = _get_registry()
        entry = registry[tool_name]
        reason = entry.get("unsupported_reason")
        assert isinstance(reason, str) and reason, (
            f"D-101-13: swift tool '{tool_name}' must declare "
            "'unsupported_reason' alongside its stack-skip metadata"
        )
