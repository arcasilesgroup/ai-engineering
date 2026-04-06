"""Helpers for running pip-audit in Windows environments with enterprise TLS."""

from __future__ import annotations

import contextlib
import os
import ssl
import subprocess
import sys
import tempfile
from pathlib import Path


def pip_audit_command(*args: str) -> list[str]:
    """Return the canonical command used to run pip-audit for this repo."""
    return ["uv", "run", "python", "-m", "ai_engineering.verify.tls_pip_audit", *args]


def main(argv: list[str] | None = None) -> int:
    """Run pip-audit with Windows trust-store compatibility when needed."""
    args = list(sys.argv[1:] if argv is None else argv)
    env = os.environ.copy()
    bundle_path: str | None = None

    if sys.platform == "win32":
        bundle_path = _configure_windows_ca_bundle(env)

    try:
        completed = subprocess.run([sys.executable, "-m", "pip_audit", *args], env=env)
    finally:
        if bundle_path:
            with contextlib.suppress(OSError):
                Path(bundle_path).unlink()

    return completed.returncode


def _configure_windows_ca_bundle(env: dict[str, str]) -> str | None:
    """Set CA bundle env vars from the Windows trust store when none are configured."""
    if env.get("REQUESTS_CA_BUNDLE") or env.get("SSL_CERT_FILE"):
        return None

    bundle_path = _write_windows_ca_bundle()
    if bundle_path is None:
        return None

    env["REQUESTS_CA_BUNDLE"] = bundle_path
    env["SSL_CERT_FILE"] = bundle_path
    return bundle_path


def _write_windows_ca_bundle() -> str | None:
    """Export trusted Windows certificates to a temporary PEM bundle."""
    enum_certificates = getattr(ssl, "enum_certificates", None)
    if enum_certificates is None:
        return None

    pem_blocks: list[str] = []
    seen_blocks: set[str] = set()
    for store_name in ("ROOT", "CA"):
        try:
            certificates = enum_certificates(store_name)
        except OSError:
            continue

        for cert_bytes, encoding, _trust in certificates:
            if encoding != "x509_asn":
                continue
            pem_block = ssl.DER_cert_to_PEM_cert(cert_bytes)
            if pem_block in seen_blocks:
                continue
            seen_blocks.add(pem_block)
            pem_blocks.append(pem_block)

    if not pem_blocks:
        return None

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="ascii",
        prefix="ai-eng-ca-",
        suffix=".pem",
        delete=False,
    ) as handle:
        handle.write("".join(pem_blocks))
        return handle.name


if __name__ == "__main__":
    raise SystemExit(main())
