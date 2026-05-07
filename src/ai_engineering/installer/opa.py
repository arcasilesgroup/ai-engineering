"""OPA bundle build + sign helpers for per-install keypair provisioning.

spec-124 D-124-08: each `ai-eng install` produces signed OPA bundle
artifacts (`.ai-engineering/policies/.signatures.json` + `.manifest`)
using a per-install RS256 keypair. The secret half lives at
``~/.config/ai-engineering/opa-signing-key.pem`` (mode 0600); the
public half ships under ``<project>/keys/opa-bundle-signing-dev.pub.pem``
(gitignored via ``*.pem``).

Each install has its own root of trust — no shared dev key in the source
repo. Rotation is supported via ``ai-eng install --rotate-opa-keys`` (a
follow-up subcommand; not in this module's scope).

Failure mode: missing ``opa`` or ``openssl`` binary degrades to
``signed=False`` with an actionable message. Install continues; ``ai-eng
doctor`` surfaces the gap as a WARN.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


_SECRET_KEY_REL = Path(".config") / "ai-engineering" / "opa-signing-key.pem"
_PUBLIC_KEY_REL = Path("keys") / "opa-bundle-signing-dev.pub.pem"


def secret_key_path(home_dir: Path | None = None) -> Path:
    """Return the canonical secret-key path under the user's home dir."""

    base = home_dir if home_dir is not None else Path.home()
    return base / _SECRET_KEY_REL


def public_key_path(project_root: Path) -> Path:
    """Return the per-project public-key path (gitignored install output)."""

    return project_root / _PUBLIC_KEY_REL


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Thin subprocess wrapper that captures output as text.

    Mirrors the helper at ``installer/engram.py:_run`` so tests can patch
    a single call site.
    """

    logger.debug("opa install: invoking %s", cmd)
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _which(name: str) -> str | None:
    return shutil.which(name)


def generate_keypair(secret_path: Path, public_path: Path) -> tuple[bool, str]:
    """Generate a 2048-bit RS256 keypair using openssl.

    Writes the secret half to ``secret_path`` (mode 0600) and the public
    counterpart to ``public_path``. Returns ``(success, message)``.
    """

    if _which("openssl") is None:
        return False, "openssl binary not on PATH; install openssl to enable bundle signing"

    secret_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)

    gen = _run(["openssl", "genrsa", "-out", str(secret_path), "2048"])
    if gen.returncode != 0:
        return False, f"openssl genrsa failed: {gen.stderr.strip() or 'unknown error'}"
    try:
        os.chmod(secret_path, 0o600)
    except OSError as exc:
        return False, f"chmod 0600 on {secret_path} failed: {exc}"

    pub = _run(
        [
            "openssl",
            "rsa",
            "-in",
            str(secret_path),
            "-pubout",
            "-out",
            str(public_path),
        ]
    )
    if pub.returncode != 0:
        return False, f"openssl rsa pubout failed: {pub.stderr.strip() or 'unknown error'}"

    return True, f"keypair generated at {secret_path} (0600) + {public_path}"


def build_bundle(policies_dir: Path, output: Path) -> tuple[bool, str]:
    """Build a tarball bundle from ``policies_dir`` via ``opa build``."""

    if _which("opa") is None:
        return False, "opa binary not on PATH; run `brew install opa` to enable"
    if not policies_dir.is_dir():
        return False, f"policies directory missing at {policies_dir}"

    output.parent.mkdir(parents=True, exist_ok=True)
    result = _run(["opa", "build", "-o", str(output), str(policies_dir)])
    if result.returncode != 0:
        return False, f"opa build failed: {result.stderr.strip() or 'unknown error'}"
    return True, f"bundle built at {output}"


def sign_bundle(policies_dir: Path, secret_key: Path) -> tuple[bool, str]:
    """Sign the policies under ``policies_dir`` using ``secret_key``.

    ``opa sign`` writes ``.signatures.json`` to the current working
    directory by default. We invoke it from ``policies_dir`` so the
    signature lands next to the .rego files (matching the spec-122-c
    layout consumed by ``opa eval --bundle``).
    """

    if _which("opa") is None:
        return False, "opa binary not on PATH"
    if not secret_key.is_file():
        return False, f"signing key missing at {secret_key}"

    # Run opa sign with cwd=policies_dir so .signatures.json lands there.
    result = subprocess.run(
        [
            "opa",
            "sign",
            "--signing-alg",
            "RS256",
            "--signing-key",
            str(secret_key),
            "--bundle",
            ".",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(policies_dir),
    )
    if result.returncode != 0:
        return False, f"opa sign failed: {result.stderr.strip() or 'unknown error'}"
    return True, f"bundle signed; .signatures.json written under {policies_dir}"


def ensure_bundle_signed(project_root: Path) -> dict[str, object]:
    """Orchestrator: generate keypair if absent, build, sign.

    Returns a dict with keys: ``signed`` (bool), ``secret_key_present``
    (bool), ``signatures_present`` (bool), ``message`` (str). Fail-open:
    any subprocess failure surfaces in ``message`` and the caller (the
    governance install phase) treats the result as advisory.
    """

    secret = secret_key_path()
    public = public_key_path(project_root)
    policies_dir = project_root / ".ai-engineering" / "policies"
    bundle_out = project_root / ".ai-engineering" / "state" / "runtime" / "bundle.tar.gz"

    result: dict[str, object] = {
        "signed": False,
        "secret_key_present": secret.is_file(),
        "signatures_present": False,
        "message": "",
    }

    if not secret.is_file():
        ok, message = generate_keypair(secret, public)
        if not ok:
            result["message"] = message
            return result
        result["secret_key_present"] = True

    ok, message = build_bundle(policies_dir, bundle_out)
    if not ok:
        result["message"] = message
        return result

    ok, message = sign_bundle(policies_dir, secret)
    if not ok:
        result["message"] = message
        return result

    signatures = policies_dir / ".signatures.json"
    result["signatures_present"] = signatures.is_file()
    result["signed"] = bool(result["signatures_present"])
    result["message"] = "OPA bundle built and signed locally"
    return result
