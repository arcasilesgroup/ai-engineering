"""Tests for the Windows certificate-aware pip-audit wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering.verify import tls_pip_audit


def test_pip_audit_command_uses_wrapper_module() -> None:
    command = tls_pip_audit.pip_audit_command("--format", "json")

    assert command[:5] == [
        "uv",
        "run",
        "python",
        "-m",
        "ai_engineering.verify.tls_pip_audit",
    ]
    assert command[-2:] == ["--format", "json"]


def test_main_sets_bundle_env_on_windows_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bundle_path = tmp_path / "enterprise-ca.pem"
    bundle_path.write_text("pem", encoding="ascii")
    captured: dict[str, object] = {}

    monkeypatch.setattr(tls_pip_audit.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(
        tls_pip_audit,
        "_write_windows_ca_bundle",
        lambda: str(bundle_path),
        raising=False,
    )

    def _run(cmd: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(tls_pip_audit.subprocess, "run", _run, raising=False)

    exit_code = tls_pip_audit.main(["--format", "json"])

    assert exit_code == 0
    assert captured["cmd"] == [
        tls_pip_audit.sys.executable,
        "-m",
        "pip_audit",
        "--format",
        "json",
    ]
    env = captured["env"]
    assert env["REQUESTS_CA_BUNDLE"] == str(bundle_path)
    assert env["SSL_CERT_FILE"] == str(bundle_path)
    assert bundle_path.exists() is False


def test_main_preserves_existing_bundle_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tls_pip_audit.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(
        tls_pip_audit.os,
        "environ",
        {"REQUESTS_CA_BUNDLE": "C:/corp/root.pem"},
        raising=False,
    )

    def _fail_write() -> str:
        raise AssertionError("bundle generation should not run")

    monkeypatch.setattr(tls_pip_audit, "_write_windows_ca_bundle", _fail_write, raising=False)
    monkeypatch.setattr(
        tls_pip_audit.subprocess,
        "run",
        lambda cmd, *, env: subprocess.CompletedProcess(cmd, 0),
        raising=False,
    )

    assert tls_pip_audit.main([]) == 0


def test_write_windows_ca_bundle_collects_unique_pem_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    certificates = {
        "ROOT": [(b"root-cert", "x509_asn", True)],
        "CA": [
            (b"root-cert", "x509_asn", True),
            (b"ca-cert", "x509_asn", True),
        ],
    }

    monkeypatch.setattr(
        tls_pip_audit.ssl,
        "enum_certificates",
        lambda store: certificates[store],
        raising=False,
    )
    monkeypatch.setattr(
        tls_pip_audit.ssl,
        "DER_cert_to_PEM_cert",
        lambda cert: f"pem:{cert.decode('ascii')}\n",
        raising=False,
    )

    bundle_path = tls_pip_audit._write_windows_ca_bundle()

    assert bundle_path is not None
    content = Path(bundle_path).read_text(encoding="ascii")
    assert content == "pem:root-cert\npem:ca-cert\n"
    Path(bundle_path).unlink()
