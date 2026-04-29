"""RED-phase tests for spec-101 T-1.3: DRIVER_BINARIES resolution.

Covers spec D-101-02 (driver allowlist) + Hardening 4 (cached path resolution).

These tests target `ai_engineering.installer.user_scope_install`, which does
NOT exist yet. Every test MUST fail with `ModuleNotFoundError` until the
GREEN-phase implementation lands.

Contract under test:

* `DRIVER_BINARIES` is an immutable container (frozenset or tuple) of allowlisted
  driver names enumerated in D-101-02 (git, uv, python, node, npm/pnpm/bun,
  dotnet, brew, winget, scoop, curl) plus the SDK probes from D-101-14
  (java, kotlinc, swift, dart, go, rustc/cargo, php, composer, clang/llvm).
* `resolve_driver(name) -> Path` returns an absolute Path when the driver is
  present on PATH; raises `MissingDriverError` with an actionable message when
  absent (per Hardening 4: error message names the driver and provides an
  install hint).
* Resolution is idempotent and cached at module-load time per Hardening 4
  (TOCTOU-resistance): two calls return the same Path object.
* Calling `resolve_driver` with a name outside the allowlist raises (KeyError
  or `LookupError`-derived) -- only allowlisted drivers resolve.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# All assertions live inside the test bodies so collection succeeds and pytest
# emits one ModuleNotFoundError per test (RED proof) rather than a single
# collection error masking the test count.

_MODULE = "ai_engineering.installer.user_scope_install"


def _import_module() -> Any:
    """Import the not-yet-existent module under test.

    Wrapped so each test produces its own ModuleNotFoundError in RED, and so
    GREEN-phase swaps the wrapper for a real import without touching test
    bodies.
    """
    import importlib

    return importlib.import_module(_MODULE)


# ---------------------------------------------------------------------------
# Driver names enumerated by spec D-101-02 + D-101-14 SDK probes.
#
# Kept as a module-level tuple so the parametric tests below can iterate it.
# ---------------------------------------------------------------------------

EXPECTED_DRIVERS: tuple[str, ...] = (
    # D-101-02 install-time helpers
    "git",
    "uv",
    "python",
    "node",
    "npm",
    "pnpm",
    "bun",
    "dotnet",
    "brew",
    "winget",
    "scoop",
    "curl",
    # spec-113 G-2: wget joined the download driver allowlist
    "wget",
    # D-101-14 SDK probes
    "java",
    "kotlinc",
    "swift",
    "dart",
    "go",
    "rustc",
    "cargo",
    "php",
    "composer",
    "clang",
    "llvm-config",
)


# ---------------------------------------------------------------------------
# Container shape + size invariants
# ---------------------------------------------------------------------------


class TestDriverBinariesContainer:
    """`DRIVER_BINARIES` must be an immutable, sized, allowlist container."""

    def test_module_exposes_driver_binaries_constant(self) -> None:
        """The module under test publishes `DRIVER_BINARIES` at top level."""
        module = _import_module()
        assert hasattr(module, "DRIVER_BINARIES"), (
            "user_scope_install module must export DRIVER_BINARIES per D-101-02"
        )

    def test_driver_binaries_is_immutable_container(self) -> None:
        """`DRIVER_BINARIES` is a frozenset or tuple — never list/dict/set.

        D-101-02 Hardening 4 requires the driver set to be pinned/frozen at
        module import time so `$PATH` mutation between checks cannot smuggle
        new drivers in.
        """
        module = _import_module()
        assert isinstance(module.DRIVER_BINARIES, frozenset | tuple), (
            "DRIVER_BINARIES must be frozenset or tuple (immutable) — "
            f"got {type(module.DRIVER_BINARIES).__name__}"
        )

    def test_driver_binaries_size_at_least_seventeen(self) -> None:
        """Spec calls for >= 17 drivers (D-101-02 + D-101-14 union)."""
        module = _import_module()
        assert len(module.DRIVER_BINARIES) >= 17, (
            f"DRIVER_BINARIES must contain at least 17 entries; got {len(module.DRIVER_BINARIES)}"
        )

    def test_driver_binaries_covers_d101_02_helpers(self) -> None:
        """All install-time helpers from D-101-02 are present."""
        module = _import_module()
        d101_02 = {
            "git",
            "uv",
            "python",
            "node",
            "npm",
            "pnpm",
            "bun",
            "dotnet",
            "brew",
            "winget",
            "scoop",
            "curl",
        }
        missing = d101_02 - set(module.DRIVER_BINARIES)
        assert not missing, f"DRIVER_BINARIES missing D-101-02 helpers: {sorted(missing)}"

    def test_driver_binaries_covers_d101_14_sdk_probes(self) -> None:
        """All SDK probes from D-101-14 are present."""
        module = _import_module()
        d101_14 = {
            "java",
            "kotlinc",
            "swift",
            "dart",
            "go",
            "rustc",
            "cargo",
            "php",
            "composer",
            "clang",
        }
        missing = d101_14 - set(module.DRIVER_BINARIES)
        assert not missing, f"DRIVER_BINARIES missing D-101-14 SDK probes: {sorted(missing)}"

    def test_driver_binaries_contains_no_duplicates(self) -> None:
        """No duplicate driver names — frozenset enforces, tuple needs check."""
        module = _import_module()
        names = list(module.DRIVER_BINARIES)
        assert len(names) == len(set(names)), (
            f"DRIVER_BINARIES contains duplicates: {sorted(names)}"
        )

    def test_driver_binaries_attempt_mutation_raises(self) -> None:
        """Attempting to mutate DRIVER_BINARIES must raise."""
        module = _import_module()
        binaries = module.DRIVER_BINARIES
        # frozenset has no .add / .discard; tuple has no item assignment.
        with pytest.raises((AttributeError, TypeError)):
            if isinstance(binaries, frozenset):
                binaries.add("hostile-driver")  # type: ignore[attr-defined]
            else:
                binaries[0] = "hostile-driver"  # type: ignore[index]


# ---------------------------------------------------------------------------
# `MissingDriverError` exception shape
# ---------------------------------------------------------------------------


class TestMissingDriverError:
    """Module exposes a dedicated exception with an actionable message."""

    def test_missing_driver_error_is_exception_subclass(self) -> None:
        """`MissingDriverError` derives from Exception."""
        module = _import_module()
        assert hasattr(module, "MissingDriverError"), (
            "user_scope_install must expose MissingDriverError"
        )
        assert issubclass(module.MissingDriverError, Exception)


# ---------------------------------------------------------------------------
# `resolve_driver` happy path — driver present on PATH
# ---------------------------------------------------------------------------


class TestResolveDriverPresent:
    """When `shutil.which` resolves a driver, `resolve_driver` returns its Path."""

    @pytest.mark.parametrize("driver", EXPECTED_DRIVERS)
    def test_resolve_driver_returns_absolute_path_when_present(
        self, driver: str, tmp_path: Path
    ) -> None:
        """For every allowlisted driver, present-on-PATH yields an absolute Path."""
        module = _import_module()
        fake_path = tmp_path / "bin" / driver
        fake_path.parent.mkdir(parents=True, exist_ok=True)
        fake_path.write_text("", encoding="utf-8")

        # Patch shutil.which inside the module under test so cached lookups
        # also see the override (Hardening 4 caches at module import — tests
        # exercise re-resolution paths via a clear_cache hook if exposed).
        with patch(f"{_MODULE}.shutil.which", return_value=str(fake_path)):
            resolved = module.resolve_driver(driver)

        assert isinstance(resolved, Path), (
            f"resolve_driver({driver!r}) must return Path — got {type(resolved).__name__}"
        )
        assert resolved.is_absolute(), f"resolve_driver({driver!r}) must return an absolute Path"


# ---------------------------------------------------------------------------
# `resolve_driver` missing-driver path — actionable error
# ---------------------------------------------------------------------------


class TestResolveDriverMissing:
    """When `shutil.which` returns None, `resolve_driver` raises with a hint."""

    @pytest.mark.parametrize("driver", EXPECTED_DRIVERS)
    def test_resolve_driver_raises_missing_driver_error_when_absent(self, driver: str) -> None:
        """Absent driver triggers MissingDriverError naming the driver + install hint."""
        module = _import_module()
        with (
            patch(f"{_MODULE}.shutil.which", return_value=None),
            pytest.raises(module.MissingDriverError) as exc_info,
        ):
            module.resolve_driver(driver)

        message = str(exc_info.value)
        assert driver in message, f"MissingDriverError must name the driver — got: {message!r}"
        # Actionable hint: the message should reference how to install
        # ("install", "PATH", or a known package manager keyword).
        hint_keywords = (
            "install",
            "PATH",
            "brew",
            "winget",
            "scoop",
            "uv",
            "apt",
            "https://",
        )
        assert any(kw.lower() in message.lower() for kw in hint_keywords), (
            f"MissingDriverError must include an actionable install hint — got: {message!r}"
        )


# ---------------------------------------------------------------------------
# Idempotence — cached resolution per Hardening 4
# ---------------------------------------------------------------------------


class TestResolveDriverIdempotent:
    """Repeated calls return the same Path object (module-load-time cache)."""

    def test_resolve_driver_returns_same_path_object_on_repeat_calls(self, tmp_path: Path) -> None:
        """Two calls to resolve_driver('git') return the IDENTICAL Path object.

        Hardening 4 mandates module-load-time caching to eliminate the TOCTOU
        race between `shutil.which` and exec. Identity (`is`) check is the
        strongest assertion the contract supports.
        """
        module = _import_module()
        fake_path = tmp_path / "bin" / "git"
        fake_path.parent.mkdir(parents=True, exist_ok=True)
        fake_path.write_text("", encoding="utf-8")

        with patch(f"{_MODULE}.shutil.which", return_value=str(fake_path)):
            first = module.resolve_driver("git")
            second = module.resolve_driver("git")

        assert first is second, (
            "resolve_driver must be idempotent — repeated calls must return "
            "the SAME Path object (module-load-time cache, Hardening 4)"
        )

    def test_resolve_driver_cache_survives_path_mutation(self, tmp_path: Path) -> None:
        """Once resolved, a driver Path is immune to subsequent shutil.which mutation.

        This guards Hardening 4's TOCTOU defense: an attacker who flips PATH
        after module import must not be able to swing resolution to a hostile
        binary.
        """
        module = _import_module()
        legit = tmp_path / "legit-bin" / "git"
        legit.parent.mkdir(parents=True, exist_ok=True)
        legit.write_text("", encoding="utf-8")

        hostile = tmp_path / "hostile-bin" / "git"
        hostile.parent.mkdir(parents=True, exist_ok=True)
        hostile.write_text("", encoding="utf-8")

        with patch(f"{_MODULE}.shutil.which", return_value=str(legit)):
            initial = module.resolve_driver("git")

        # Now flip the lookup to a hostile path. Cached resolution must NOT
        # honour the new value.
        with patch(f"{_MODULE}.shutil.which", return_value=str(hostile)):
            second = module.resolve_driver("git")

        assert second == initial, (
            "Cached driver resolution must ignore subsequent shutil.which "
            "results — Hardening 4 TOCTOU defense"
        )


# ---------------------------------------------------------------------------
# Allowlist enforcement — non-allowlisted names are rejected
# ---------------------------------------------------------------------------


class TestResolveDriverAllowlistEnforcement:
    """Only allowlisted driver names resolve; everything else raises."""

    @pytest.mark.parametrize(
        "name",
        [
            "not-in-allowlist",
            "rm",
            "sudo",
            "bash",
            "sh",
            "ssh",
            "",
            "../../etc/passwd",
        ],
    )
    def test_resolve_driver_rejects_non_allowlisted_name(self, name: str) -> None:
        """Calling resolve_driver with a non-allowlisted name raises.

        Per D-101-02 the driver allowlist is the load-bearing control — any
        name outside DRIVER_BINARIES must be rejected at lookup time, before
        `shutil.which` is even consulted.
        """
        module = _import_module()
        with pytest.raises((KeyError, LookupError, ValueError)):
            module.resolve_driver(name)

    def test_resolve_driver_does_not_consult_path_for_disallowed_name(self) -> None:
        """Allowlist check happens BEFORE `shutil.which` is invoked.

        If a hostile name reaches `shutil.which`, we have a TOCTOU window. The
        allowlist must short-circuit lookup entirely.
        """
        module = _import_module()
        with (
            patch(f"{_MODULE}.shutil.which") as mock_which,
            pytest.raises((KeyError, LookupError, ValueError)),
        ):
            module.resolve_driver("not-a-real-driver")
        mock_which.assert_not_called()
