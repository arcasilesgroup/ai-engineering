"""RED-phase tests for spec-101 T-1.5: `_safe_run` runtime subprocess guard.

Covers spec D-101-02 (install-target prefix allowlist + driver allowlist) +
the runtime subprocess guard described in spec.md lines 154-160.

These tests target `ai_engineering.installer.user_scope_install`, which does
NOT exist yet. Every test MUST fail with `ModuleNotFoundError` until the
T-1.6 GREEN-phase implementation lands.

Contract under test:

* `_safe_run(argv, **kwargs)` resolves `argv[0]` (via `shutil.which` /
  cached `RESOLVED_DRIVERS`) and asserts the resolved absolute path starts
  with one of two allowlists:
  - **Install-target prefixes** (D-101-02 (a)): `~/`, `~/.local/`,
    `~/.cargo/`, `~/.dotnet/tools/`, `~/.composer/vendor/bin/`,
    `~/go/bin/`, `~/.local/share/uv/tools/`, `$(brew --prefix)/`,
    the active virtualenv's `bin/`.
  - **Driver allowlist** (D-101-02 (b)): the resolved path of one of
    the names in `DRIVER_BINARIES` (git, uv, python, node, npm/pnpm/bun,
    dotnet, brew, winget, scoop, curl, plus D-101-14 SDK probes).
* When `argv[0]` resolves OUTSIDE both allowlists, `_safe_run` raises
  `UserScopeViolation` BEFORE the subprocess is spawned. The exception
  message names both the rejected absolute path AND the policy reason.
* The runtime guard catches obfuscated forbidden invocations that grep
  cannot — string concatenation (`"s" + "udo"`), `getattr(os, "sys" + "tem")`,
  reversed slicing — because the check operates on the resolved `argv[0]`,
  not on source-code text.
* `_safe_run([])` raises `ValueError` (degenerate input).
* `_safe_run([<unknown-binary>])` raises `MissingDriverError` or
  `UserScopeViolation` (whichever the implementation wires).

Quality bar:

* All assertions live INSIDE test bodies so collection succeeds and pytest
  emits one ModuleNotFoundError per test (RED proof).
* Tests exercise contract shape, not implementation detail. The GREEN
  phase is free to choose any internal data structure as long as the
  observable behaviour matches.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

_MODULE = "ai_engineering.installer.user_scope_install"


def _import_module() -> Any:
    """Import the not-yet-existent module under test.

    Wrapped so each test produces its own ModuleNotFoundError in RED. T-1.6
    GREEN swaps the wrapper for a real import without touching test bodies.
    """
    return importlib.import_module(_MODULE)


# ---------------------------------------------------------------------------
# Fixture data — install-target prefixes + driver paths.
#
# `~` resolves through `Path.home()` so tests are user-agnostic.
# Tests fabricate absolute paths under each prefix to feed into a patched
# `shutil.which`, then assert `_safe_run` accepts the call.
# ---------------------------------------------------------------------------

INSTALL_TARGET_PREFIXES: tuple[str, ...] = (
    ".local/bin",
    ".cargo/bin",
    ".dotnet/tools",
    ".composer/vendor/bin",
    "go/bin",
    ".local/share/uv/tools",
)

# A small representative set of drivers from D-101-02 + D-101-14. The full
# allowlist is exercised by `test_driver_binaries.py` (T-1.3); here we only
# need to confirm that resolution via `DRIVER_BINARIES` is honoured.
DRIVER_SAMPLE: tuple[str, ...] = (
    "git",
    "uv",
    "python",
    "node",
    "npm",
    "dotnet",
    "brew",
    "curl",
    "java",
    "go",
    "rustc",
    "cargo",
)


# ---------------------------------------------------------------------------
# Module surface — `_safe_run` and `UserScopeViolation` must exist.
# ---------------------------------------------------------------------------


class TestModuleSurface:
    """The module must expose the public guard names."""

    def test_module_exposes_safe_run(self) -> None:
        """`_safe_run` is callable at module top level."""
        module = _import_module()
        assert hasattr(module, "_safe_run"), (
            "user_scope_install must export _safe_run per spec.md L154"
        )
        assert callable(module._safe_run)

    def test_module_exposes_user_scope_violation(self) -> None:
        """`UserScopeViolation` exception type is exported."""
        module = _import_module()
        assert hasattr(module, "UserScopeViolation"), (
            "user_scope_install must export UserScopeViolation per spec.md L154"
        )
        assert issubclass(module.UserScopeViolation, Exception)


# ---------------------------------------------------------------------------
# Allowlist (a) — install-target prefixes.
#
# When `argv[0]` resolves under `~/`, `~/.local/`, `~/.cargo/`, etc., the
# call must succeed (no exception). We patch `subprocess.run` so the real
# binary is never invoked.
# ---------------------------------------------------------------------------


class TestAllowlistInstallTargets:
    """`_safe_run` accepts argv[0] resolving under user-scope install prefixes."""

    @pytest.mark.parametrize("prefix", INSTALL_TARGET_PREFIXES)
    def test_argv_resolving_under_install_target_prefix_succeeds(self, prefix: str) -> None:
        """Each install-target prefix in D-101-02 (a) is honoured."""
        module = _import_module()
        fake_resolved = Path.home() / prefix / "ruff"

        with (
            patch(f"{_MODULE}.shutil.which", return_value=str(fake_resolved)),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
        ):
            mock_run.return_value = object()  # placeholder CompletedProcess
            module._safe_run(["ruff", "check"])

        # Subprocess was reached — i.e. the guard did NOT raise.
        assert mock_run.called, (
            f"`_safe_run` must reach subprocess.run for argv resolving under "
            f"{prefix!r} — got blocked by guard"
        )

    @pytest.mark.skipif(
        __import__("sys").platform == "win32",
        reason=(
            "POSIX-only path: ``Path('/opt/homebrew/bin/jq')`` is treated as a "
            "drive-relative path on Windows and resolves against CWD, breaking "
            "the prefix match. Brew is unavailable on Windows so the carve-out "
            "is academic."
        ),
    )
    def test_brew_prefix_bin_is_allowlisted(self) -> None:
        """`$(brew --prefix)/bin/...` resolves against the install-target allowlist.

        D-101-02 R-12 mitigation: brew prefix may be `/opt/homebrew` (Apple
        Silicon) or `/usr/local` (Intel) — both must be accepted when the
        resolved path comes from `brew --prefix`.
        """
        module = _import_module()
        # Use Apple Silicon canonical path; if implementation hard-codes
        # `/opt/homebrew` only it will still pass for that platform.
        fake_resolved = Path("/opt/homebrew/bin/jq")

        with (
            patch(f"{_MODULE}.shutil.which", return_value=str(fake_resolved)),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
        ):
            mock_run.return_value = object()
            module._safe_run(["jq", "."])

        assert mock_run.called, "`_safe_run` must accept argv[0] resolving under $(brew --prefix)/"

    def test_project_venv_bin_is_allowlisted(self) -> None:
        """A path under the active virtualenv's `bin/` is honoured.

        D-101-02 (a): "the active virtualenv's `bin/`" — match by detecting
        a `.venv/bin/` segment in the resolved path.
        """
        module = _import_module()
        fake_resolved = Path.cwd() / ".venv" / "bin" / "ruff"

        with (
            patch(f"{_MODULE}.shutil.which", return_value=str(fake_resolved)),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
        ):
            mock_run.return_value = object()
            module._safe_run(["ruff", "format", "--check"])

        assert mock_run.called, "`_safe_run` must accept argv[0] resolving under .venv/bin/"


# ---------------------------------------------------------------------------
# Allowlist (b) — driver binaries enumerated in DRIVER_BINARIES.
# ---------------------------------------------------------------------------


class TestAllowlistDrivers:
    """`_safe_run` accepts argv[0] resolving via the driver allowlist."""

    @pytest.mark.parametrize("driver", DRIVER_SAMPLE)
    def test_driver_binary_resolution_succeeds(self, driver: str, tmp_path: Path) -> None:
        """Every allowlisted driver name resolves via `DRIVER_BINARIES`.

        We fabricate a system-style absolute path (e.g. `/usr/bin/git`) which
        is OUTSIDE the install-target prefixes — yet the call must succeed
        because `git` is in `DRIVER_BINARIES`.
        """
        module = _import_module()
        # System path — would FAIL the install-target prefix check on its own.
        fake_resolved = tmp_path / "usr" / "bin" / driver
        fake_resolved.parent.mkdir(parents=True, exist_ok=True)
        fake_resolved.write_text("", encoding="utf-8")

        with (
            patch(f"{_MODULE}.shutil.which", return_value=str(fake_resolved)),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
        ):
            mock_run.return_value = object()
            module._safe_run([driver, "--version"])

        assert mock_run.called, (
            f"`_safe_run` must accept driver {driver!r} via DRIVER_BINARIES allowlist"
        )

    def test_module_uses_driver_binaries_constant(self) -> None:
        """The driver allowlist is sourced from `DRIVER_BINARIES` (T-1.3 contract).

        Confirms shared lineage with T-1.3 RED so the guard cannot silently
        diverge from the documented allowlist.
        """
        module = _import_module()
        assert hasattr(module, "DRIVER_BINARIES"), (
            "user_scope_install must expose DRIVER_BINARIES (shared with T-1.3)"
        )
        # Sample membership check — T-1.3 already exhaustively asserts size + content.
        assert "git" in module.DRIVER_BINARIES
        assert "uv" in module.DRIVER_BINARIES


# ---------------------------------------------------------------------------
# Reject — argv[0] resolves to a system path NOT in either allowlist.
# ---------------------------------------------------------------------------


class TestRejectOutsideAllowlist:
    """argv[0] resolving to `/usr/local/bin/sudo` raises `UserScopeViolation`."""

    def test_sudo_resolution_raises_user_scope_violation(self) -> None:
        """`sudo` is not in `DRIVER_BINARIES` and `/usr/local/bin/` is not an install target.

        Direct invocation of `sudo` is the canonical D-101-02 violation per
        G-4 (zero subprocess calls outside the user-scope allowlist).
        """
        module = _import_module()
        with (
            patch(f"{_MODULE}.shutil.which", return_value="/usr/local/bin/sudo"),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
            pytest.raises(module.UserScopeViolation),
        ):
            module._safe_run(["sudo", "rm", "-rf", "/"])

        # Subprocess MUST NOT have been spawned — guard happens before exec.
        mock_run.assert_not_called()

    @pytest.mark.parametrize(
        "resolved_path",
        [
            "/usr/local/bin/sudo",
            "/usr/bin/apt",
            "/usr/bin/yum",
            "/usr/bin/dnf",
            "/sbin/shutdown",
            "/Applications/Some.app/Contents/MacOS/binary",
        ],
    )
    def test_disallowed_system_paths_all_raise(self, resolved_path: str) -> None:
        """Every D-101-02 forbidden invocation surface is blocked at runtime.

        Even if a hostile caller smuggles in a system-path resolution, the
        guard rejects pre-exec.
        """
        module = _import_module()
        with (
            patch(f"{_MODULE}.shutil.which", return_value=resolved_path),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
            pytest.raises(module.UserScopeViolation),
        ):
            module._safe_run(["whatever", "--flag"])

        mock_run.assert_not_called()

    def test_blocked_call_does_not_invoke_subprocess(self) -> None:
        """Guard runs BEFORE `subprocess.run` — fail-closed semantics."""
        module = _import_module()
        with (
            patch(f"{_MODULE}.shutil.which", return_value="/usr/local/bin/sudo"),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
        ):
            with pytest.raises(module.UserScopeViolation):
                module._safe_run(["sudo", "ls"])
            mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# Obfuscation — runtime guard catches what grep cannot.
#
# Spec.md L154 closes with: "The runtime guard is effective against
# obfuscated forbidden substrings (string concatenation, reversed slicing,
# `getattr(os, "sys" + "tem")`) that grep cannot catch."
# ---------------------------------------------------------------------------


class TestObfuscationAttempts:
    """argv[0] reconstructed via concatenation / reversal still gets caught."""

    def test_string_concatenation_for_sudo_is_caught(self) -> None:
        """`["s" + "udo", "ls"]` resolves to `/usr/local/bin/sudo` and raises.

        The literal `"sudo"` substring is absent from the source code — only
        the runtime resolution of `argv[0]` reveals the violation.
        """
        module = _import_module()
        argv = ["s" + "udo", "ls"]
        assert argv[0] == "sudo", "Sanity: concatenation produced 'sudo'"

        with (
            patch(f"{_MODULE}.shutil.which", return_value="/usr/local/bin/sudo"),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
            pytest.raises(module.UserScopeViolation),
        ):
            module._safe_run(argv)

        mock_run.assert_not_called()

    def test_reversed_slice_for_apt_is_caught(self) -> None:
        """`"tpa"[::-1]` reconstructs `"apt"` — runtime resolution still rejects."""
        module = _import_module()
        argv = ["tpa"[::-1], "install", "rogue"]
        assert argv[0] == "apt", "Sanity: reversed slice produced 'apt'"

        with (
            patch(f"{_MODULE}.shutil.which", return_value="/usr/bin/apt"),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
            pytest.raises(module.UserScopeViolation),
        ):
            module._safe_run(argv)

        mock_run.assert_not_called()

    def test_getattr_obfuscation_argv_is_caught(self) -> None:
        """A `getattr`-style command name still resolves and gets rejected.

        Demonstrates the runtime check operates on whatever string ends up
        in `argv[0]`, regardless of how that string was assembled.
        """
        module = _import_module()
        # Equivalent to `getattr(builtins, "sys" + "tem")(...)` shape — here
        # we just confirm that any reconstruction reaching `argv[0]` is
        # subject to the same allowlist gate.
        argv_name = "sys" + "tem"
        argv = [argv_name, "rm -rf /"]
        assert argv[0] == "system"

        with (
            patch(f"{_MODULE}.shutil.which", return_value="/usr/bin/system"),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
            pytest.raises(module.UserScopeViolation),
        ):
            module._safe_run(argv)

        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# Exception message contract.
# ---------------------------------------------------------------------------


class TestUserScopeViolationMessage:
    """`UserScopeViolation` message names the rejected path AND the policy."""

    def test_message_contains_rejected_absolute_path(self) -> None:
        """The exception message includes the resolved absolute path."""
        module = _import_module()
        rejected = "/usr/local/bin/sudo"

        with (
            patch(f"{_MODULE}.shutil.which", return_value=rejected),
            patch(f"{_MODULE}.subprocess.run"),
            pytest.raises(module.UserScopeViolation) as exc_info,
        ):
            module._safe_run(["sudo", "ls"])

        message = str(exc_info.value)
        assert rejected in message, (
            f"UserScopeViolation message must name the rejected path "
            f"({rejected!r}); got: {message!r}"
        )

    def test_message_includes_policy_reason(self) -> None:
        """The exception message references the policy / allowlist concept.

        Surface keywords: "allowlist", "user-scope", "D-101-02", "user scope",
        or "outside" — any one suffices to direct the operator to the policy.
        """
        module = _import_module()
        with (
            patch(f"{_MODULE}.shutil.which", return_value="/usr/local/bin/sudo"),
            patch(f"{_MODULE}.subprocess.run"),
            pytest.raises(module.UserScopeViolation) as exc_info,
        ):
            module._safe_run(["sudo", "ls"])

        message = str(exc_info.value).lower()
        policy_keywords = (
            "allowlist",
            "user-scope",
            "user scope",
            "d-101-02",
            "outside",
            "policy",
        )
        assert any(kw in message for kw in policy_keywords), (
            f"UserScopeViolation message must reference the policy reason "
            f"(one of {policy_keywords!r}); got: {message!r}"
        )


# ---------------------------------------------------------------------------
# Degenerate inputs — empty argv, unknown binary.
# ---------------------------------------------------------------------------


class TestNullArgv:
    """Edge cases: empty argv, unknown binary."""

    def test_empty_argv_raises_value_error(self) -> None:
        """`_safe_run([])` is a programmer error — raise `ValueError`."""
        module = _import_module()
        with pytest.raises(ValueError):
            module._safe_run([])

    def test_unknown_binary_raises_missing_or_violation(self) -> None:
        """`_safe_run(["nonexistent-binary-xyz"])` raises a guard exception.

        Either `MissingDriverError` (the binary is in the driver allowlist
        but not on PATH) or `UserScopeViolation` (the binary is outside the
        allowlist entirely) is acceptable — the contract is "do not exec".
        """
        module = _import_module()
        with (
            patch(f"{_MODULE}.shutil.which", return_value=None),
            patch(f"{_MODULE}.subprocess.run") as mock_run,
            pytest.raises((module.MissingDriverError, module.UserScopeViolation)),
        ):
            module._safe_run(["nonexistent-binary-xyz", "--flag"])

        mock_run.assert_not_called()
