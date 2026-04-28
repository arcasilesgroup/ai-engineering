"""SHA256 pin-enforcement tests for spec-101 R-21 / D-101-04.

Wave 23 quality fix #1: GitHubReleaseBinaryMechanism MUST never accept a
download without an explicit SHA256 pin. The previous implementation
short-circuited :func:`_verify_sha256` when ``expected_sha256`` was empty,
silently accepting whatever curl wrote to disk -- a critical contract
breach surfaced by reviewer-security. These tests assert:

1. Empty / missing pin raises :class:`Sha256MismatchError` with
   ``expected="<missing>"`` -- never silent.
2. The error surfaces both ``expected`` and ``received`` substrings so
   operators can diff manually (matches the existing mismatch contract).
3. The :data:`_PIN_REQUIRED` flag defaults to True at module load.
4. Setting :data:`_PIN_REQUIRED` to False (test scaffolding only) restores
   the no-op behaviour for fixtures while pins are populated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer import mechanisms as mech_mod
from ai_engineering.installer.mechanisms import (
    Sha256MismatchError,
    _verify_sha256,
)


def test_pin_required_defaults_to_true() -> None:
    """Production default MUST be pin-required (spec.md L353/L378)."""
    assert mech_mod._PIN_REQUIRED is True


def test_empty_pin_raises_when_pin_required(tmp_path: Path) -> None:
    """Empty ``expected_hash`` raises ``Sha256MismatchError`` -- never silent."""
    artifact = tmp_path / "fake-binary"
    artifact.write_bytes(b"binary contents that should be pinned")

    with pytest.raises(Sha256MismatchError) as excinfo:
        _verify_sha256(artifact, "")

    msg = str(excinfo.value)
    assert "<missing>" in msg, "error MUST mention <missing> as the expected pin"
    assert excinfo.value.expected == "<missing>"
    # The received digest is the actual file contents -- non-empty proves we
    # hashed the file rather than short-circuiting.
    assert excinfo.value.received
    assert len(excinfo.value.received) == 64  # SHA256 hex digest length


def test_none_pin_raises_when_pin_required(tmp_path: Path) -> None:
    """``None`` is treated like the empty string -- both are absent pins."""
    artifact = tmp_path / "fake-binary"
    artifact.write_bytes(b"contents")

    # The helper is typed ``str`` so ``None`` is technically out-of-contract,
    # but the call sites pass ``self.expected_sha256 or ""`` which collapses
    # both to "". Exercise the same path.
    with pytest.raises(Sha256MismatchError):
        _verify_sha256(artifact, "")


def test_empty_pin_no_op_when_pin_not_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test scaffolding: ``_PIN_REQUIRED=False`` restores the legacy no-op."""
    artifact = tmp_path / "fake-binary"
    artifact.write_bytes(b"contents")

    monkeypatch.setattr(mech_mod, "_PIN_REQUIRED", False)
    # Should NOT raise; the helper returns silently in this scaffolding mode.
    _verify_sha256(artifact, "")


def test_correct_pin_passes(tmp_path: Path) -> None:
    """A matching SHA256 pin passes through cleanly."""
    import hashlib

    artifact = tmp_path / "fake-binary"
    payload = b"contents to pin"
    artifact.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()

    # Should not raise.
    _verify_sha256(artifact, expected)


def test_wrong_pin_raises_with_both_digests(tmp_path: Path) -> None:
    """Mismatched pin still raises with both digests in the error surface."""
    artifact = tmp_path / "fake-binary"
    artifact.write_bytes(b"actual contents")
    bogus_pin = "0" * 64

    with pytest.raises(Sha256MismatchError) as excinfo:
        _verify_sha256(artifact, bogus_pin)

    msg = str(excinfo.value)
    assert bogus_pin in msg
    assert excinfo.value.received in msg
    assert excinfo.value.received != bogus_pin


def test_github_release_binary_install_raises_without_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: install() with no expected_sha256 raises Sha256MismatchError.

    Mocks ``_safe_run`` to simulate a successful curl download and creates a
    placeholder file at the target path so :func:`_verify_sha256` has something
    to hash. With ``sha256_pinned=True`` and ``expected_sha256=None``, the
    enforcement path raises.
    """
    from types import SimpleNamespace

    from ai_engineering.installer.mechanisms import GitHubReleaseBinaryMechanism

    # Pre-create the target so _verify_sha256 has a file to hash.
    target_dir = Path.home() / ".local" / "bin"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "test-fake-binary-spec101-wave23"
    target.write_bytes(b"placeholder")

    def fake_safe_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "ai_engineering.installer.mechanisms._safe_run",
        fake_safe_run,
    )

    try:
        with pytest.raises(Sha256MismatchError) as excinfo:
            GitHubReleaseBinaryMechanism(
                repo="example/example",
                binary="test-fake-binary-spec101-wave23",
                sha256_pinned=True,
            ).install()
        assert excinfo.value.expected == "<missing>"
    finally:
        if target.exists():
            target.unlink()
