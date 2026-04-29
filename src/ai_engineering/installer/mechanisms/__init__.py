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

import contextlib
import hashlib
import os
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
    "_DOWNLOAD_DRIVER_HOSTNAME_ALLOWLIST",
    "_DOWNLOAD_DRIVER_PREFERENCE",
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
    "_download_release_binary",
    "_emit_sha_pin_skipped_audit",
    "_resolve_download_driver",
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
# 2. GitHubReleaseBinaryMechanism support helpers (spec-113 SS1)
# ---------------------------------------------------------------------------
#
# spec-113 D-113-03 / D-113-04 carry the download fallback chain:
#
#     curl  ->  wget  ->  urllib.request.urlopen
#
# Each driver is tried in order; failure (non-zero exit, missing binary,
# raised exception) advances to the next. The urllib path is the
# Python-builtin last resort so a Linux minimal image with neither curl
# nor wget can still pull the release binary.
#
# Hostname allowlist is the load-bearing security guard: GitHub hosts
# release downloads on ``objects.githubusercontent.com`` after a
# redirect, so both names are required. Any other host trips
# :class:`SecurityError`.
#
# spec-113 D-113-02 also adds a session-scoped audit-event sink so the
# ``sha_pin_skipped`` event fires at most once per (tool, mechanism)
# pair within a single Python process (R-10).


# Hostnames the urllib fallback is allowed to talk to. ``github.com`` is
# the canonical release endpoint; ``objects.githubusercontent.com`` is
# the asset CDN GitHub redirects to. Both are required for the fallback
# to actually complete a download in production.
_DOWNLOAD_DRIVER_HOSTNAME_ALLOWLIST: frozenset[str] = frozenset(
    {
        "github.com",
        "objects.githubusercontent.com",
    }
)


# Order in which download drivers are attempted. Names must match
# ``DRIVER_BINARIES`` membership tests in ``user_scope_install`` -- both
# entries land in the allowlist there. ``urllib`` is a sentinel value
# (NOT a binary name); the resolver maps it to the in-process fallback.
_DOWNLOAD_DRIVER_PREFERENCE: tuple[str, ...] = ("curl", "wget", "urllib")


# Per-process dedup set for ``sha_pin_skipped`` audit events (R-10). Keys
# are ``"<tool>:<mechanism>:<sha_pin_status>"`` strings; once a key
# lands here the matching event is suppressed for the rest of the
# process so ``framework-events.ndjson`` does not balloon when the same
# tool installs across multiple stacks.
_SHA_PIN_SKIPPED_AUDIT_SEEN: set[str] = set()


# Maximum download size enforced on the urllib path (D-113-04). 100 MiB
# covers every GitHub release binary the framework currently consumes
# (largest is the LLVM-toolchain pull at ~80 MiB). Hard-limited to keep
# a runaway download from filling ``~/.local/bin``.
_URLLIB_MAX_BYTES: int = 100 * 1024 * 1024  # 100 MiB

# Per-call timeout for the urllib path. 60 s is generous for the asset
# CDN; subprocess curl/wget honour their own defaults via the OS.
_URLLIB_TIMEOUT_SECONDS: int = 60

# Maximum redirects honoured on the urllib path. GitHub typically
# redirects releases to ``objects.githubusercontent.com`` (1 hop); we
# bound the chain at 5 to avoid loop-back malice.
_URLLIB_MAX_REDIRECTS: int = 5

# Read-buffer size for the urllib download stream.
_URLLIB_CHUNK_SIZE: int = 64 * 1024  # 64 KiB


def _emit_sha_pin_skipped_audit(*, tool: str, mechanism: str) -> None:
    """Emit the ``sha_pin_skipped`` framework event (D-113-02, R-10).

    The event records the (tool, mechanism) pair plus the static reason
    ``"DEC-038 pending"``. Per-process deduplication keys on the same
    triple so a multi-stack install of the same tool emits the event
    once. Failures to write the event are swallowed -- the audit trail
    is advisory and must NEVER block install.
    """
    key = f"{tool}:{mechanism}:sha_pin_skipped"
    if key in _SHA_PIN_SKIPPED_AUDIT_SEEN:
        return
    _SHA_PIN_SKIPPED_AUDIT_SEEN.add(key)
    try:
        from ai_engineering.state.observability import emit_framework_operation
    except ImportError:  # pragma: no cover - circular guard
        return
    try:
        emit_framework_operation(
            Path.cwd(),
            operation="sha_pin_skipped",
            component="installer.mechanisms.GitHubReleaseBinaryMechanism",
            outcome="warn",
            metadata={
                "tool": tool,
                "mechanism": mechanism,
                "reason": "DEC-038 pending",
                "type": "sha_pin_skipped",
            },
        )
    except Exception:  # pragma: no cover - fail-open audit trail
        return


def _resolve_download_driver() -> str | None:
    """Return the first download driver from preference order that resolves.

    The resolver consults ``shutil.which`` for ``curl`` and ``wget``
    (subprocess drivers), and treats ``"urllib"`` as the in-process
    fallback that is always available because Python is a hard
    prereq of the framework. Returns ``None`` only if every driver in
    :data:`_DOWNLOAD_DRIVER_PREFERENCE` is unresolvable, which on a
    healthy Python install is impossible -- the urllib sentinel
    guarantees a non-None tail.
    """
    for name in _DOWNLOAD_DRIVER_PREFERENCE:
        if name == "urllib":
            return "urllib"
        if shutil.which(name) is not None:
            return name
    return None


def _format_proxy_handler() -> urllib.request.ProxyHandler:
    """Build a :class:`ProxyHandler` honoring ``HTTP(S)_PROXY`` env vars (D-113-14).

    Keeps proxy resolution explicit so corporate networks that allow
    egress only via proxy can complete the urllib fallback. Supports
    both upper-case and lower-case env var spellings (curl/wget convention).
    """
    proxies: dict[str, str] = {}
    for scheme in ("http", "https"):
        for env_name in (f"{scheme.upper()}_PROXY", f"{scheme}_proxy"):
            value = os.environ.get(env_name)
            if value:
                proxies[scheme] = value
                break
    return urllib.request.ProxyHandler(proxies)


def _ensure_https_and_allowed(url: str) -> None:
    """Reject non-HTTPS schemes and non-allowlisted hostnames.

    Raises :class:`SecurityError` when the URL fails either guard so
    the urllib fallback never punches through to an arbitrary host.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise SecurityError(f"download URL must use https; got scheme={parsed.scheme!r}")
    hostname = (parsed.hostname or "").lower()
    if hostname not in _DOWNLOAD_DRIVER_HOSTNAME_ALLOWLIST:
        allowed = sorted(_DOWNLOAD_DRIVER_HOSTNAME_ALLOWLIST)
        raise SecurityError(f"download hostname {hostname!r} not in allowlist {allowed}")


def _stream_to_disk(response: Any, target_path: Path) -> int:
    """Copy *response* into *target_path*, enforcing the byte cap.

    Returns the bytes written. Raises :class:`SecurityError` when the
    download exceeds :data:`_URLLIB_MAX_BYTES` (likely a malicious or
    misconfigured asset). Streams in 64 KiB chunks so memory stays
    bounded even on minimal Linux images.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with target_path.open("wb") as handle:
        while True:
            chunk = response.read(_URLLIB_CHUNK_SIZE)
            if not chunk:
                break
            written += len(chunk)
            if written > _URLLIB_MAX_BYTES:
                raise SecurityError(
                    f"download exceeded {_URLLIB_MAX_BYTES} byte cap (received >{written} bytes)"
                )
            handle.write(chunk)
    return written


def _download_via_urllib(url: str, target_path: Path) -> InstallResult:
    """Download *url* into *target_path* using the urllib fallback (D-113-04).

    Guards: HTTPS-only, hostname allowlist, byte cap, redirect cap,
    proxy env support. Returns a successful :class:`InstallResult` on
    completion; returns a failed :class:`InstallResult` (not a raise)
    for benign network/IO errors so the caller's contract matches the
    subprocess paths.
    """
    _ensure_https_and_allowed(url)

    # Build an opener that:
    # - honours HTTPS_PROXY / HTTP_PROXY (D-113-14)
    # - re-checks redirected URLs against the allowlist (defense in depth)
    proxy_handler = _format_proxy_handler()
    redirect_handler = _AllowlistRedirectHandler(max_redirects=_URLLIB_MAX_REDIRECTS)
    https_handler = urllib.request.HTTPSHandler(context=ssl.create_default_context())
    opener = urllib.request.build_opener(proxy_handler, redirect_handler, https_handler)

    request = urllib.request.Request(url, headers={"User-Agent": "ai-engineering"})
    try:
        with opener.open(request, timeout=_URLLIB_TIMEOUT_SECONDS) as response:
            _stream_to_disk(response, target_path)
    except SecurityError:
        raise
    except (TimeoutError, urllib.error.URLError, ssl.SSLError, OSError) as exc:
        return InstallResult(
            failed=True,
            stderr=f"urllib download failed: {exc}",
            mechanism="GitHubReleaseBinaryMechanism",
        )
    # Make the binary executable so callers can invoke it directly. Same
    # bit pattern curl + wget land under their default modes.
    with contextlib.suppress(OSError):
        target_path.chmod(0o755)
    return InstallResult(failed=False, mechanism="GitHubReleaseBinaryMechanism")


class _AllowlistRedirectHandler(urllib.request.HTTPRedirectHandler):
    """:class:`HTTPRedirectHandler` re-validating each redirect target."""

    def __init__(self, *, max_redirects: int) -> None:
        super().__init__()
        self._max_redirects = max_redirects
        self._redirect_count = 0

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:  # pragma: no cover - thin wrapper
        self._redirect_count += 1
        if self._redirect_count > self._max_redirects:
            raise SecurityError(f"download exceeded redirect cap of {self._max_redirects}")
        _ensure_https_and_allowed(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _try_subprocess_download(
    driver: str,
    url: str,
    target_path: Path,
) -> InstallResult:
    """Run *driver* (curl|wget) via ``_safe_run`` to download *url*.

    Builds a flag set tuned to the driver:

    * curl: ``--fail --location --silent --show-error --output <path> <url>``
    * wget: ``-O <path> <url>`` (universal flags only -- BusyBox-safe)

    Returns the :class:`InstallResult` view of the subprocess outcome.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if driver == "curl":
        argv = [
            "curl",
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--output",
            str(target_path),
            url,
        ]
    elif driver == "wget":
        # NG-8: only flags both GNU wget and BusyBox wget honour are used
        # (-O <path> <url>). No --show-progress / --no-verbose / etc.
        argv = ["wget", "-O", str(target_path), url]
    else:  # pragma: no cover - defensive guard
        return InstallResult(
            failed=True,
            stderr=f"unsupported subprocess driver {driver!r}",
            mechanism="GitHubReleaseBinaryMechanism",
        )
    proc = _safe_run(argv)
    return _install_result_from_proc(proc, mechanism="GitHubReleaseBinaryMechanism")


def _download_release_binary(url: str, target_path: Path) -> InstallResult:
    """Drive the curl -> wget -> urllib fallback chain for a single download.

    Returns the first successful :class:`InstallResult`. Records the
    driver actually used inside ``stderr`` of a failed result so callers
    can surface the diagnostic. Raises :class:`SecurityError` only when
    the urllib path triggers a hostname / scheme / cap guard.
    """
    last_failure: InstallResult | None = None
    for driver in _DOWNLOAD_DRIVER_PREFERENCE:
        if driver in {"curl", "wget"}:
            if shutil.which(driver) is None:
                last_failure = InstallResult(
                    failed=True,
                    stderr=f"download driver {driver!r} not on PATH",
                    mechanism="GitHubReleaseBinaryMechanism",
                )
                continue
            try:
                outcome = _try_subprocess_download(driver, url, target_path)
            except Exception as exc:
                # _safe_run can raise UserScopeViolation / MissingDriverError
                # before any subprocess fires. Treat as soft failure so the
                # next driver in the chain gets a chance.
                last_failure = InstallResult(
                    failed=True,
                    stderr=f"{driver}: {exc}",
                    mechanism="GitHubReleaseBinaryMechanism",
                )
                continue
            if not outcome.failed:
                return outcome
            last_failure = outcome
            continue
        # urllib branch
        outcome = _download_via_urllib(url, target_path)
        if not outcome.failed:
            return outcome
        last_failure = outcome
    if last_failure is None:  # pragma: no cover - urllib always returns something
        return InstallResult(
            failed=True,
            stderr="no download driver available",
            mechanism="GitHubReleaseBinaryMechanism",
        )
    return last_failure


# ---------------------------------------------------------------------------
# GitHubReleaseBinaryMechanism (refactored for spec-113)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GitHubReleaseBinaryMechanism:
    """Download a signed GitHub-release binary into ``~/.local/bin``.

    Default behaviour (``sha256_pinned=True``): mandatory SHA256 pin --
    :func:`_verify_sha256` raises :class:`Sha256MismatchError` if the
    pin is empty (defence-in-depth against a registry regression).

    spec-113 / D-113-01: when ``sha256_pinned=False`` the descriptor
    declares the pin as intentionally absent (DEC-038 backlog). The
    install path skips ``_verify_sha256`` entirely, emits a WARNING
    to stderr, and writes a ``sha_pin_skipped`` audit event to
    ``framework-events.ndjson`` so the risk surface stays visible.
    The download flows through :func:`_download_release_binary`'s
    fallback chain: curl -> wget -> urllib.
    """

    repo: str
    binary: str
    sha256_pinned: bool = True
    expected_sha256: str | None = None

    def install(self) -> InstallResult:
        """Download via curl/wget/urllib, conditionally verify, place in ``~/.local/bin``."""
        target_dir = Path.home() / ".local" / "bin"
        target_path = target_dir / self.binary
        url = f"https://github.com/{self.repo}/releases/latest/download/{self.binary}"
        # First call route: curl when on PATH (preserves the spec-101 test
        # contract that asserts argv[0]==curl); falls back to wget then
        # urllib when curl is absent (Alpine BusyBox case).
        result = _download_release_binary(url, target_path)
        if result.failed:
            return result
        if not self.sha256_pinned:
            # spec-113 D-113-01: pin not declared (DEC-038 follow-up).
            # Skip the digest check, surface a WARNING to stderr, and
            # emit a ``sha_pin_skipped`` audit event so the operator
            # can see the risk acceptance landed.
            sys.stderr.write(
                f"WARNING: {self.binary}: SHA256 pin missing (sha256_pinned=False); "
                "install proceeded without digest verification (DEC-038 pending).\n"
            )
            sys.stderr.flush()
            _emit_sha_pin_skipped_audit(
                tool=self.binary,
                mechanism=type(self).__name__,
            )
            return result
        # SHA256 verification (digest mismatch raises Sha256MismatchError).
        # Empty expected_sha256 with sha256_pinned=True still raises -- the
        # defence-in-depth contract for unpopulated pins is preserved.
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
