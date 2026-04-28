"""RED skeleton for spec-107 G-11 (Phase 5) — H1 tool-spec hash rug-pull detection.

Spec-107 D-107-09 detects silent mutation of installed MCP tool specs
via per-tool SHA256 hashing of the canonical spec JSON. The hash is
persisted in ``InstallState.tool_spec_hashes`` and re-validated on
every install / sync cycle.

Decision protocol:
- First install: empty baseline -> populate hashes silently (no banner).
- Subsequent install: hash mismatch -> emit CLI banner + lookup active
  risk-acceptance for ``finding_id = "tool-spec-mismatch-<server>"``.
- DEC active -> permit + update baseline + emit telemetry.
- DEC absent -> banner remains; user must run
  ``ai-eng risk accept --finding-id tool-spec-mismatch-<server> ...``.

These tests are marked ``spec_107_red`` and excluded from CI default
runs until Phase 5 lands the GREEN implementation. They are the
acceptance contract for T-5.7 / T-5.8 / T-5.9 / T-5.10 / T-5.11 / T-5.13.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.spec_107_red
def test_compute_tool_spec_hash_helper_exists() -> None:
    """G-11: `compute_tool_spec_hash` helper exists in state.manifest module."""
    manifest_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "manifest.py"
    assert manifest_path.is_file(), f"state.manifest missing: {manifest_path}"
    text = manifest_path.read_text(encoding="utf-8")
    assert "def compute_tool_spec_hash(" in text, (
        "state.manifest missing `compute_tool_spec_hash()` — Phase 5 T-5.7 "
        "must add SHA256 of canonical-JSON tool spec"
    )


@pytest.mark.spec_107_red
def test_install_state_carries_tool_spec_hashes_field() -> None:
    """G-11: InstallState model has `tool_spec_hashes: dict[str, str]` field."""
    models_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "models.py"
    assert models_path.is_file(), f"state.models missing: {models_path}"
    text = models_path.read_text(encoding="utf-8")
    assert "tool_spec_hashes" in text, (
        "InstallState model missing `tool_spec_hashes: dict[str, str]` — "
        "Phase 5 T-5.8 must add the field for H1 baseline storage"
    )


@pytest.mark.spec_107_red
def test_installer_service_wires_h1_detection() -> None:
    """G-11: installer.service compares current vs baseline hashes."""
    service_path = REPO_ROOT / "src" / "ai_engineering" / "installer" / "service.py"
    assert service_path.is_file(), f"installer.service missing: {service_path}"
    text = service_path.read_text(encoding="utf-8")
    assert "tool_spec_hashes" in text or "compute_tool_spec_hash" in text, (
        "installer.service missing H1 detection wiring — Phase 5 T-5.9 must "
        "compute current hash per tool, compare vs baseline, emit banner on "
        "mismatch"
    )


@pytest.mark.spec_107_red
def test_cli_banner_template_documents_remediation() -> None:
    """G-11: installer banner includes remediation hint with ai-eng risk accept."""
    service_path = REPO_ROOT / "src" / "ai_engineering" / "installer" / "service.py"
    if not service_path.is_file():
        pytest.skip("installer.service missing — covered by sibling test")
    text = service_path.read_text(encoding="utf-8")
    # Look for the canonical remediation banner words.
    assert (
        "Tool Spec Mismatch" in text or "tool-spec-mismatch" in text or "ai-eng risk accept" in text
    ), (
        "installer.service missing CLI banner template for H1 mismatch — "
        "Phase 5 T-5.10 must add the user-facing remediation hint"
    )


@pytest.mark.spec_107_red
def test_first_run_populates_baseline_silently() -> None:
    """G-11: first-run with empty baseline must populate without alerting."""
    service_path = REPO_ROOT / "src" / "ai_engineering" / "installer" / "service.py"
    if not service_path.is_file():
        pytest.skip("installer.service missing — covered by sibling test")
    text = service_path.read_text(encoding="utf-8")
    # Heuristic: code mentions either an "empty"/"first-run" branch OR
    # initializes hashes when missing.
    assert "first" in text.lower() or "empty" in text.lower() or "tool_spec_hashes" in text, (
        "installer.service missing first-run baseline-population branch — "
        "Phase 5 T-5.11 must populate hashes silently when baseline is empty"
    )
