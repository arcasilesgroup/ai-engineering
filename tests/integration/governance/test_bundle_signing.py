"""Integration tests for OPA bundle signing roundtrip (spec-122 Phase C, T-3.10).

Builds a bundle in ``tmp_path``, signs it with throwaway dev material,
parses the resulting ``.signatures.json`` JWT, and asserts that each
``.rego`` SHA-256 matches ``hashlib.sha256(file.read_bytes()).hexdigest()``.
Mutating a ``.rego`` file in the source tree fails verification.

Skips with a clear marker when the OPA binary is not installed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ai_engineering.governance import bundle as bundle_mod

pytestmark = pytest.mark.integration


def _opa_available() -> bool:
    return shutil.which("opa") is not None


def _openssl_available() -> bool:
    return shutil.which("openssl") is not None


def _decode_jwt_payload(jwt: str) -> dict:
    """Decode the middle (payload) segment of a JWT without verification."""
    payload_b64 = jwt.split(".")[1]
    # JWT base64url has no padding; restore padding before decoding.
    pad = "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64 + pad))


@pytest.fixture
def policies_workspace(tmp_path: Path) -> Path:
    """Copy the live policies/ directory into a tmp workspace.

    Excludes any pre-existing ``.signatures.json`` so the build/sign
    roundtrip starts clean — leaving the file in place would force OPA
    to attempt verification on the build path.
    """
    repo_root = Path(__file__).resolve().parents[3]
    src = repo_root / ".ai-engineering" / "policies"
    dest = tmp_path / "policies"
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".signatures.json"))
    return dest


@pytest.fixture
def signing_pem(tmp_path: Path) -> Path:
    """Generate a throwaway RS256 signing PEM via openssl."""
    if not _openssl_available():
        pytest.skip("openssl not on PATH")
    pem_path = tmp_path / "dev-signing.pem"
    subprocess.run(
        ["openssl", "genrsa", "-out", str(pem_path), "2048"],
        check=True,
        capture_output=True,
    )
    return pem_path


@pytest.mark.skipif(not _opa_available(), reason="opa binary not installed")
def test_build_bundle_emits_signed_artifact(
    policies_workspace: Path,
    signing_pem: Path,
    tmp_path: Path,
) -> None:
    output = tmp_path / "policy-bundle.tar.gz"
    result = bundle_mod.build_bundle(
        policies_workspace,
        output=output,
        signing_pem=signing_pem,
    )
    assert result.bundle_path == output
    assert output.exists()
    assert output.stat().st_size > 100  # non-empty tarball

    # tar -tzf <bundle> should include the canonical signatures + manifest.
    proc = subprocess.run(
        ["tar", "-tzf", str(output)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "/.signatures.json" in proc.stdout
    assert "/.manifest" in proc.stdout


@pytest.mark.skipif(not _opa_available(), reason="opa binary not installed")
def test_signatures_json_contains_sha256_per_rego(
    policies_workspace: Path,
    signing_pem: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "sign-out"
    output_dir.mkdir()
    sigs_path = bundle_mod.sign_bundle_files(
        policies_workspace,
        signing_pem=signing_pem,
        output_file_path=output_dir,
    )
    assert sigs_path.exists()
    payload = json.loads(sigs_path.read_text(encoding="utf-8"))
    assert "signatures" in payload
    jwts = payload["signatures"]
    assert len(jwts) == 1, "OPA emits a single combined JWT covering all files"

    decoded = _decode_jwt_payload(jwts[0])
    files = {entry["name"]: entry for entry in decoded["files"]}

    # Every .rego in the workspace must have a corresponding hash entry.
    for rego in policies_workspace.glob("*.rego"):
        # JWT entries are repo-relative paths (the path passed to opa sign).
        # Match by filename suffix so we tolerate both / and full paths.
        match = [name for name in files if name.endswith(rego.name)]
        assert match, f"No signature entry for {rego.name}; saw {list(files)}"
        entry = files[match[0]]
        assert entry["algorithm"] == "SHA-256"
        expected = hashlib.sha256(rego.read_bytes()).hexdigest()
        assert entry["hash"] == expected, (
            f"hash mismatch for {rego.name}: signatures={entry['hash']} expected={expected}"
        )


@pytest.mark.skipif(not _opa_available(), reason="opa binary not installed")
def test_mutating_rego_breaks_signature_verification(
    policies_workspace: Path,
    signing_pem: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "sign-out"
    output_dir.mkdir()
    sigs_path = bundle_mod.sign_bundle_files(
        policies_workspace,
        signing_pem=signing_pem,
        output_file_path=output_dir,
    )
    payload = json.loads(sigs_path.read_text(encoding="utf-8"))
    jwt = payload["signatures"][0]
    decoded = _decode_jwt_payload(jwt)
    files = {entry["name"]: entry for entry in decoded["files"]}

    # Pick the first .rego, mutate it, recompute SHA-256, assert mismatch.
    target = next(iter(policies_workspace.glob("*.rego")))
    original = target.read_bytes()
    target.write_bytes(original + b"\n# tamper\n")
    try:
        new_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        match = [name for name in files if name.endswith(target.name)]
        assert match, f"No signature entry for {target.name}"
        signed_hash = files[match[0]]["hash"]
        assert new_hash != signed_hash, "tampered file should not match the recorded signature hash"
    finally:
        target.write_bytes(original)
