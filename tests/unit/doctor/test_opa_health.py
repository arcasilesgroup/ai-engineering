"""Unit tests for ``ai-eng doctor`` OPA health runtime probe (spec-123 T-4.4).

Each probe is exercised in isolation with monkeypatched binary paths and
subprocess output so the test suite stays hermetic regardless of whether
``opa`` is installed on the executing host.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.runtime import opa_health


def _ctx(target: Path) -> DoctorContext:
    return DoctorContext(target=target)


def _seed_bundle(target: Path) -> Path:
    bundle = target / ".ai-engineering" / "policies"
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / ".manifest").write_text("{}\n", encoding="utf-8")
    (bundle / ".signatures.json").write_text(
        json.dumps({"signatures": [{"keyid": "default", "alg": "HS256"}]}),
        encoding="utf-8",
    )
    return bundle


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


# ---------------------------------------------------------------------------
# opa-binary probe
# ---------------------------------------------------------------------------


def test_binary_missing_warns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(opa_health.shutil, "which", lambda _: None)
    results = opa_health.check(_ctx(tmp_path))
    assert len(results) == 1
    assert results[0].name == "opa-binary"
    assert results[0].status == CheckStatus.WARN


# ---------------------------------------------------------------------------
# opa-version probe
# ---------------------------------------------------------------------------


def test_version_below_minimum_warns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(opa_health.shutil, "which", lambda _: "/usr/bin/opa")
    monkeypatch.setattr(
        opa_health.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="Version: 0.50.0\nBuild: stub\n"),
    )
    _seed_bundle(tmp_path)
    results = opa_health.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["opa-version"].status == CheckStatus.WARN
    assert "0.50.0" in by_name["opa-version"].message
    # Bundle load probe runs with the same stub stdout — it'll WARN because
    # the JSON shape isn't a valid bundle response, but that's not the
    # assertion under test; we only care that opa-version surfaced WARN.
    assert "opa-bundle-load" in by_name


def test_version_meets_minimum_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(opa_health.shutil, "which", lambda _: "/usr/bin/opa")
    _seed_bundle(tmp_path)
    bundle_payload = json.dumps(
        {
            "result": [
                {
                    "expressions": [
                        {
                            "value": {
                                "branch_protection": {},
                                "commit_conventional": {},
                                "risk_acceptance_ttl": {},
                            }
                        }
                    ]
                }
            ]
        }
    )

    def _fake_run(args, *_, **__):
        if "version" in args:
            return _completed(0, stdout="Version: 1.16.1\n")
        if "eval" in args:
            return _completed(0, stdout=bundle_payload)
        return _completed(1)

    monkeypatch.setattr(opa_health.subprocess, "run", _fake_run)
    results = opa_health.check(_ctx(tmp_path))
    by_name = {r.name: r.status for r in results}
    assert by_name["opa-binary"] == CheckStatus.OK
    assert by_name["opa-version"] == CheckStatus.OK
    assert by_name["opa-bundle-load"] == CheckStatus.OK
    assert by_name["opa-bundle-signature"] == CheckStatus.OK


# ---------------------------------------------------------------------------
# opa-bundle-load probe
# ---------------------------------------------------------------------------


def test_bundle_load_missing_directory_warns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(opa_health.shutil, "which", lambda _: "/usr/bin/opa")
    monkeypatch.setattr(
        opa_health.subprocess,
        "run",
        lambda *_, **__: _completed(0, stdout="Version: 1.0.0\n"),
    )
    # No bundle seeded -> bundle-load should warn.
    results = opa_health.check(_ctx(tmp_path))
    by_name = {r.name: r.status for r in results}
    assert by_name["opa-bundle-load"] == CheckStatus.WARN


def test_bundle_load_returns_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(opa_health.shutil, "which", lambda _: "/usr/bin/opa")
    _seed_bundle(tmp_path)

    def _fake_run(args, *_, **__):
        if "version" in args:
            return _completed(0, stdout="Version: 1.0.0\n")
        if "eval" in args:
            return _completed(1, stderr="parse error: unexpected token\n")
        return _completed(1)

    monkeypatch.setattr(opa_health.subprocess, "run", _fake_run)
    results = opa_health.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["opa-bundle-load"].status == CheckStatus.WARN
    assert "parse error" in by_name["opa-bundle-load"].message


# ---------------------------------------------------------------------------
# opa-bundle-signature probe
# ---------------------------------------------------------------------------


def test_bundle_signature_missing_files_warns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(opa_health.shutil, "which", lambda _: "/usr/bin/opa")

    def _fake_run(args, *_, **__):
        if "version" in args:
            return _completed(0, stdout="Version: 1.0.0\n")
        return _completed(0, stdout="{}")

    monkeypatch.setattr(opa_health.subprocess, "run", _fake_run)
    # Create only the directory, no signature/manifest files.
    (tmp_path / ".ai-engineering" / "policies").mkdir(parents=True)
    results = opa_health.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["opa-bundle-signature"].status == CheckStatus.WARN
    assert ".signatures.json" in by_name["opa-bundle-signature"].message


def test_bundle_signature_empty_signatures_warns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(opa_health.shutil, "which", lambda _: "/usr/bin/opa")
    bundle = tmp_path / ".ai-engineering" / "policies"
    bundle.mkdir(parents=True)
    (bundle / ".manifest").write_text("{}\n", encoding="utf-8")
    (bundle / ".signatures.json").write_text(json.dumps({"signatures": []}), encoding="utf-8")

    def _fake_run(args, *_, **__):
        if "version" in args:
            return _completed(0, stdout="Version: 1.0.0\n")
        return _completed(0, stdout="{}")

    monkeypatch.setattr(opa_health.subprocess, "run", _fake_run)
    results = opa_health.check(_ctx(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["opa-bundle-signature"].status == CheckStatus.WARN
