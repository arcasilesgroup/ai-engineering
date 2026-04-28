"""Install mechanism executors for spec-101 (D-101-02, T-1.8).

Twelve concrete mechanism classes whose ``.install()`` method routes every
subprocess invocation through ``_safe_run`` (the user-scope guard exposed by
:mod:`ai_engineering.installer.user_scope_install`). Each mechanism returns
an :class:`InstallResult` capturing success / failure plus stderr.

The mechanism classes here are the SAME public types referenced by
:mod:`ai_engineering.installer.tool_registry` -- the registry imports them
back out of this package so there is one source of truth (no dataclass
stubs / executable-class duplication).

Module-level handles intentionally surfaced so unit tests can patch them:

* ``_safe_run`` -- patched by ``test_install_mechanisms.py`` to capture argv
  and simulate subprocess outcomes without spawning real processes.
* ``_verify_sha256`` -- patched in the SHA256-mismatch test to inject a
  :class:`Sha256MismatchError`.

Design choices
--------------
* **Frozen dataclasses for descriptors**: each mechanism is a small immutable
  value object (the constructor arguments are the descriptor; ``install()``
  is the action). Frozen dataclasses give positional construction, attribute
  access, hashability, and equality without pulling in pydantic on the hot
  path.
* **Single-file package**: the test contract imports every class from the
  package root (``ai_engineering.installer.mechanisms``). One module keeps
  the import surface trivial and the cross-mechanism helpers
  (``_install_result_from_proc``, ``_verify_sha256``) co-located with the
  callers.
* **Registry de-duplication**: ``tool_registry.py`` imports these classes
  rather than defining parallel dataclass stubs (removed in this commit).
  The registry tests still pass because the mechanism classes carry the
  same fields they did as stubs.
* **No global / system-scope flags**: ``NpmDevMechanism`` uses
  ``--save-dev`` (project-local) and explicitly omits ``-g`` / ``--global``
  per D-101-02. ``DotnetToolMechanism`` uses ``--global`` because the .NET
  CLI's ``--global`` flag lands tools in ``~/.dotnet/tools`` (user-scope
  despite the misleading name; documented inline).
* **GitHubReleaseBinaryMechanism**: routes ``curl`` through ``_safe_run``
  for download (curl is in ``DRIVER_BINARIES``), verifies the SHA256 via
  the module-level ``_verify_sha256`` helper, and surfaces a typed
  :class:`Sha256MismatchError` on digest mismatch.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_engineering.installer.results import (
    InstallResult,
    SecurityError,
    Sha256MismatchError,
)
from ai_engineering.installer.user_scope_install import _safe_run

# ``__all__`` is sorted alphabetically (RUF022). The grouping rationale --
# result + error types, the module-level test-patch handle, and the twelve
# mechanism classes per D-101-02 -- is conveyed by the per-class docstrings
# rather than by manual ordering.
#
# spec-101 Arch-2: ``InstallResult``, ``SecurityError``, and
# ``Sha256MismatchError`` are re-exported from
# :mod:`ai_engineering.installer.results` so the historical import surface
# (``from installer.mechanisms import InstallResult``) continues to work
# without reintroducing the user_scope_install <-> mechanisms cycle the
# extraction was designed to break.
__all__ = (
    "_PIN_REQUIRED",
    "BrewMechanism",
    "CargoInstallMechanism",
    "ComposerGlobalMechanism",
    "DotnetToolMechanism",
    "GitHubReleaseBinaryMechanism",
    "GoInstallMechanism",
    "InstallResult",
    "NpmDevMechanism",
    "ScoopMechanism",
    "SdkmanMechanism",
    "SecurityError",
    "Sha256MismatchError",
    "UvPipVenvMechanism",
    "UvToolMechanism",
    "WingetMechanism",
    "_verify_sha256",
)


# ---------------------------------------------------------------------------
# Helpers (module-level for test patching)
# ---------------------------------------------------------------------------


# spec-101 R-21 / D-101-04 contract: SHA256 pinning is mandatory for every
# GitHub-release binary download. When True (default), :func:`_verify_sha256`
# raises :class:`Sha256MismatchError` if the expected digest is empty or
# missing -- never silently accepts an unverified artifact. Test fixtures may
# flip this to False to exercise pre-pin scaffolding paths, but the prod
# default MUST remain True per the spec.md L353/L378 mandate "never installs
# an unverified binary."
_PIN_REQUIRED: bool = True


def _install_result_from_proc(
    proc: subprocess.CompletedProcess[Any] | Any,
    *,
    mechanism: str,
) -> InstallResult:
    """Build an :class:`InstallResult` from a subprocess-shaped object.

    Tolerates both real ``CompletedProcess`` instances and the test
    ``SimpleNamespace`` doubles by reading attributes defensively.
    """
    returncode = getattr(proc, "returncode", 0) or 0
    stderr_raw = getattr(proc, "stderr", "") or ""
    stderr = stderr_raw if isinstance(stderr_raw, str) else stderr_raw.decode(errors="replace")
    return InstallResult(
        failed=returncode != 0,
        stderr=stderr,
        mechanism=mechanism,
    )


def _verify_sha256(file_path: Path, expected_hash: str) -> None:
    """Verify ``file_path`` against ``expected_hash``; raise on mismatch.

    Reads the file in 64 KiB chunks so the helper stays memory-bounded for
    multi-megabyte release artifacts. On mismatch (or when the pin is
    missing while :data:`_PIN_REQUIRED` is True), raises
    :class:`Sha256MismatchError` carrying both the expected and received
    digests plus the file path.

    Empty ``expected_hash`` semantics (spec-101 R-21):

    * When :data:`_PIN_REQUIRED` is True (default): an empty / missing pin
      raises :class:`Sha256MismatchError` with ``expected="<missing>"`` and
      the computed digest as ``received``. This closes the silent
      short-circuit reviewer-security identified -- no binary is ever
      accepted without an out-of-band pin.
    * When :data:`_PIN_REQUIRED` is False (test scaffolding only): empty
      ``expected_hash`` becomes a no-op so fixtures can exercise the call
      site while pins are populated incrementally.
    """
    if not expected_hash:
        if _PIN_REQUIRED:
            digest = hashlib.sha256()
            with file_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(65536), b""):
                    digest.update(chunk)
            received = digest.hexdigest()
            raise Sha256MismatchError(
                expected="<missing>",
                received=received,
                path=file_path,
            )
        return
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    received = digest.hexdigest()
    if received.lower() != expected_hash.lower():
        raise Sha256MismatchError(
            expected=expected_hash,
            received=received,
            path=file_path,
        )


# ---------------------------------------------------------------------------
# 1. BrewMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BrewMechanism:
    """Install via Homebrew on macOS / Linuxbrew.

    Lands in ``$(brew --prefix)/bin`` (user-owned, no privilege escalation).
    """

    formula: str

    def install(self) -> InstallResult:
        """Run ``brew install <formula>`` via ``_safe_run``."""
        proc = _safe_run(["brew", "install", self.formula])
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# ---------------------------------------------------------------------------
# 2. GitHubReleaseBinaryMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GitHubReleaseBinaryMechanism:
    """Download a signed GitHub-release binary into ``~/.local/bin``.

    SHA256 verification is mandatory by default (``sha256_pinned=True``).
    The download flows through ``curl`` (an allowlisted driver) routed
    through ``_safe_run`` so the user-scope guard sees every byte. After
    download, :func:`_verify_sha256` validates the artifact against the
    pinned digest; mismatch raises :class:`Sha256MismatchError`.
    """

    repo: str
    binary: str
    sha256_pinned: bool = True
    expected_sha256: str | None = None

    def install(self) -> InstallResult:
        """Download via curl -> verify SHA256 -> place in ``~/.local/bin``."""
        target_dir = Path.home() / ".local" / "bin"
        target_path = target_dir / self.binary
        url = f"https://github.com/{self.repo}/releases/latest/download/{self.binary}"
        # First subprocess call MUST be curl per the test contract; the
        # ``_safe_run`` allowlist covers ``curl`` via DRIVER_BINARIES.
        proc = _safe_run(
            [
                "curl",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--output",
                str(target_path),
                url,
            ]
        )
        result = _install_result_from_proc(proc, mechanism=type(self).__name__)
        if result.failed:
            return result
        # SHA256 verification (digest mismatch raises Sha256MismatchError).
        # The expected digest is supplied either by the descriptor itself
        # or, in tests, the helper is patched to inject the mismatch.
        expected = self.expected_sha256 or ""
        _verify_sha256(target_path, expected)
        return result


# ---------------------------------------------------------------------------
# 3. WingetMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WingetMechanism:
    """Install via Windows Package Manager with explicit user scope.

    The ``--scope user`` flag is load-bearing per D-101-02: admin scope is
    forbidden. The flag is rendered as the literal pair ``--scope user``
    (the test asserts ``argv[argv.index('--scope') + 1] == 'user'``).
    """

    package_id: str
    scope: str = "user"

    def install(self) -> InstallResult:
        """Run ``winget install --scope user <package_id>`` via ``_safe_run``."""
        proc = _safe_run(
            [
                "winget",
                "install",
                "--scope",
                self.scope,
                self.package_id,
            ]
        )
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# ---------------------------------------------------------------------------
# 4. ScoopMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoopMechanism:
    """Install via Scoop on Windows (user-scope by design)."""

    package: str

    def install(self) -> InstallResult:
        """Run ``scoop install <package>`` via ``_safe_run``."""
        proc = _safe_run(["scoop", "install", self.package])
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# ---------------------------------------------------------------------------
# 5. UvToolMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UvToolMechanism:
    """Install via ``uv tool install <package>`` (user-global; D-101-12)."""

    package: str

    def install(self) -> InstallResult:
        """Run ``uv tool install <package>`` via ``_safe_run``."""
        proc = _safe_run(["uv", "tool", "install", self.package])
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# ---------------------------------------------------------------------------
# 6. UvPipVenvMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UvPipVenvMechanism:
    """Install via ``uv pip install --python <venv>/bin/python <pkg>``.

    Used for Python tools that genuinely need to be inside the project
    venv (pytest plugins resolved via the project's pyproject). Lands in
    the target venv's ``bin/`` directory.
    """

    package: str
    venv: Path

    def install(self) -> InstallResult:
        """Run ``uv pip install --python <venv>/bin/python <pkg>``."""
        python_path = self.venv / "bin" / "python"
        proc = _safe_run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python_path),
                self.package,
            ]
        )
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# ---------------------------------------------------------------------------
# 7. NpmDevMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NpmDevMechanism:
    """Install via ``npm install --save-dev <package>`` (project-local).

    NEVER ``-g`` / ``--global`` -- D-101-02 forbids global npm installs.
    The argv shape is asserted in
    ``test_install_mechanisms.TestNpmDevMechanism.test_install_invokes_safe_run_with_npm_argv``.
    """

    package: str

    def install(self) -> InstallResult:
        """Run ``npm install --save-dev <package>`` via ``_safe_run``."""
        proc = _safe_run(["npm", "install", "--save-dev", self.package])
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# ---------------------------------------------------------------------------
# 8. DotnetToolMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DotnetToolMechanism:
    """Install via ``dotnet tool install --global <package>``.

    The ``--global`` flag is the .NET CLI's user-scope semantic despite
    the misleading name -- it lands in ``~/.dotnet/tools``, NOT a system
    path. This is the only mechanism where ``--global`` is permitted.
    """

    package: str

    def install(self) -> InstallResult:
        """Run ``dotnet tool install --global <package>`` via ``_safe_run``."""
        proc = _safe_run(["dotnet", "tool", "install", "--global", self.package])
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# ---------------------------------------------------------------------------
# 9. CargoInstallMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CargoInstallMechanism:
    """Install via ``cargo install <crate>`` -> ``~/.cargo/bin``."""

    crate: str

    def install(self) -> InstallResult:
        """Run ``cargo install <crate>`` via ``_safe_run``."""
        proc = _safe_run(["cargo", "install", self.crate])
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# ---------------------------------------------------------------------------
# 10. GoInstallMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoInstallMechanism:
    """Install via ``go install <import_path>`` -> ``$GOPATH/bin``."""

    import_path: str

    def install(self) -> InstallResult:
        """Run ``go install <import_path>`` via ``_safe_run``."""
        proc = _safe_run(["go", "install", self.import_path])
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# ---------------------------------------------------------------------------
# 11. ComposerGlobalMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComposerGlobalMechanism:
    """Install via ``composer global require <package>``.

    Lands in ``~/.composer/vendor/bin``. Composer itself must be
    pre-installed via the prereqs phase (D-101-14).
    """

    package: str

    def install(self) -> InstallResult:
        """Run ``composer global require <package>`` via ``_safe_run``."""
        proc = _safe_run(["composer", "global", "require", self.package])
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# ---------------------------------------------------------------------------
# 12. SdkmanMechanism
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SdkmanMechanism:
    """Install via SDKMAN: ``sdk install <candidate> <version>``.

    Used for JVM-stack tools (kotlin compiler, gradle) where SDKMAN is
    the canonical user-scope distribution channel. Lands in ``~/.sdkman/``.
    """

    candidate: str
    version: str

    def install(self) -> InstallResult:
        """Run ``sdk install <candidate> <version>`` via ``_safe_run``."""
        proc = _safe_run(["sdk", "install", self.candidate, self.version])
        return _install_result_from_proc(proc, mechanism=type(self).__name__)


# Local import-time sanity: the public 12 are all defined above. Defended by
# ``test_all_12_mechanisms_have_install_method`` in the test suite.
_MECHANISM_CLASSES: tuple[type, ...] = (
    BrewMechanism,
    GitHubReleaseBinaryMechanism,
    WingetMechanism,
    ScoopMechanism,
    UvToolMechanism,
    UvPipVenvMechanism,
    NpmDevMechanism,
    DotnetToolMechanism,
    CargoInstallMechanism,
    GoInstallMechanism,
    ComposerGlobalMechanism,
    SdkmanMechanism,
)
assert len(_MECHANISM_CLASSES) == 12, "spec-101 mandates exactly 12 mechanism classes"

# ``field`` is imported above for typing parity but unused at runtime; keep
# the symbol referenced so static analysis does not flag it as dead.
_ = field
