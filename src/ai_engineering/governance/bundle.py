"""Bundle build + sign helper (spec-122 Phase C, T-3.9).

Wraps ``opa build`` (produce ``bundle.tar.gz``) and ``opa sign`` so
callers (CI, doctor phase, release tooling) can build and verify a
signed policy bundle without re-deriving the argv conventions.

The dev-mode signing PEM lives at
``~/.config/ai-engineering/opa-bundle-signing-dev.pem`` (mode 0600);
the matching public PEM is committed at
``keys/opa-bundle-signing-dev.pub.pem``. The committed file is the
public verification artefact only; the local file is regenerated on
demand using ``openssl genrsa``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LOCAL_PEM: Path = Path.home() / ".config" / "ai-engineering" / "opa-bundle-signing-dev.pem"
DEFAULT_PUBLIC_PEM_REL: Path = Path("keys") / "opa-bundle-signing-dev.pub.pem"
DEFAULT_BUNDLE_NAME: str = "bundle.tar.gz"
DEFAULT_SIGNING_ALG: str = "RS256"

__all__ = [
    "DEFAULT_BUNDLE_NAME",
    "DEFAULT_LOCAL_PEM",
    "DEFAULT_PUBLIC_PEM_REL",
    "DEFAULT_SIGNING_ALG",
    "BundleError",
    "BundleResult",
    "build_bundle",
    "ensure_dev_pem",
    "sign_bundle_files",
]


class BundleError(RuntimeError):
    """Raised when the bundle build / sign pipeline fails."""


@dataclass(frozen=True)
class BundleResult:
    """Output of :func:`build_bundle`."""

    bundle_path: Path
    signatures_path: Path | None


def _opa_binary() -> str:
    binary = shutil.which("opa")
    if binary is None:
        raise BundleError("opa binary not on PATH; run 'ai-eng install'")
    return binary


def ensure_dev_pem(target_path: Path = DEFAULT_LOCAL_PEM) -> Path:
    """Generate dev RS256 signing material on demand (idempotent).

    Shells out to ``openssl genrsa`` (a hard dependency on every
    supported developer platform: ships with macOS, ubuntu, and the
    Windows MSYS / Git-Bash layer). The PEM is written with mode 0600;
    the public counterpart is written next to it with suffix ``.pub.pem``.
    """
    if target_path.exists():
        return target_path

    target_path.parent.mkdir(parents=True, exist_ok=True)

    openssl = shutil.which("openssl")
    if openssl is None:
        raise BundleError(
            "openssl binary required for dev material generation; "
            "install via your package manager or supply pre-generated material",
        )

    try:
        proc = subprocess.run(
            [openssl, "genrsa", "-out", str(target_path), "2048"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30.0,
        )
    except subprocess.TimeoutExpired as exc:
        raise BundleError("openssl genrsa timed out") from exc

    if proc.returncode != 0:
        raise BundleError(
            f"openssl genrsa failed (exit {proc.returncode}): {proc.stderr.strip()}",
        )

    os.chmod(target_path, 0o600)

    pub_target = target_path.with_suffix(".pub.pem")
    try:
        proc = subprocess.run(
            [openssl, "rsa", "-in", str(target_path), "-pubout", "-out", str(pub_target)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30.0,
        )
    except subprocess.TimeoutExpired as exc:
        raise BundleError("openssl rsa -pubout timed out") from exc

    if proc.returncode != 0:
        raise BundleError(
            f"openssl rsa -pubout failed (exit {proc.returncode}): {proc.stderr.strip()}",
        )

    return target_path


def build_bundle(
    policies_dir: Path,
    *,
    output: Path | None = None,
    signing_pem: Path | None = None,
    signing_alg: str = DEFAULT_SIGNING_ALG,
    ignore_patterns: tuple[str, ...] = ("*_test.rego",),
) -> BundleResult:
    """Run ``opa build`` against ``policies_dir`` and return the artefact path.

    When ``signing_pem`` is supplied, ``opa build`` is called with the
    signing flags so the resulting tarball contains a ``.signatures.json``
    entry. When omitted, the bundle is built unsigned (useful for CI dry
    runs).

    By default ``*_test.rego`` files are excluded — they belong to the
    coverage suite (T-3.2) but the .manifest roots only enumerate
    production packages, so an unfiltered build would fail with a
    "manifest roots ... do not permit" error.
    """
    binary = _opa_binary()
    out = output or (policies_dir.parent / DEFAULT_BUNDLE_NAME)

    cmd = [
        binary,
        "build",
        "--bundle",
        str(policies_dir),
        "-o",
        str(out),
    ]
    for pattern in ignore_patterns:
        cmd.extend(["--ignore", pattern])
    if signing_pem is not None:
        if not signing_pem.exists():
            raise BundleError(f"signing material not found: {signing_pem}")
        cmd.extend(["--signing-key", str(signing_pem), "--signing-alg", signing_alg])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30.0,
        )
    except subprocess.TimeoutExpired as exc:
        raise BundleError("opa build timed out") from exc

    if proc.returncode != 0:
        details = (proc.stderr or proc.stdout or "").strip() or "no stderr/stdout"
        raise BundleError(
            f"opa build failed (exit {proc.returncode}): {details}; cmd={cmd!r}",
        )

    return BundleResult(bundle_path=out, signatures_path=None)


def sign_bundle_files(
    policies_dir: Path,
    *,
    signing_pem: Path,
    signing_alg: str = DEFAULT_SIGNING_ALG,
    output_file_path: Path | None = None,
) -> Path:
    """Run ``opa sign`` over a bundle directory and return the signatures path.

    Writes ``.signatures.json`` next to the bundle directory by default.
    Returns the path to that file.
    """
    binary = _opa_binary()
    if not signing_pem.exists():
        raise BundleError(f"signing material not found: {signing_pem}")

    output_dir = output_file_path or policies_dir.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        binary,
        "sign",
        "--bundle",
        "--signing-key",
        str(signing_pem),
        "--signing-alg",
        signing_alg,
        "--output-file-path",
        str(output_dir),
        str(policies_dir),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30.0,
        )
    except subprocess.TimeoutExpired as exc:
        raise BundleError("opa sign timed out") from exc

    if proc.returncode != 0:
        raise BundleError(
            f"opa sign failed (exit {proc.returncode}): {proc.stderr.strip()}",
        )

    return output_dir / ".signatures.json"
