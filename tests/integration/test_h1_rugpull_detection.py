"""GREEN tests for spec-107 G-11 — H1 tool-spec hash rug-pull detection.

Spec-107 D-107-09 detects silent mutation of installed tool specs via
per-tool SHA256 hashing of the canonical spec JSON. The hash is
persisted in ``InstallState.tool_spec_hashes`` and re-validated on
every install / sync cycle.

Decision protocol:
- First install: empty baseline -> populate hashes silently (no banner).
- Subsequent install: hash mismatch -> emit CLI banner + lookup active
  risk-acceptance for ``finding_id = "tool-spec-mismatch-<stack>-<tool>"``.
- DEC active -> permit + update baseline + emit telemetry.
- DEC absent -> banner remains; user must run
  ``ai-eng risk accept --finding-id tool-spec-mismatch-<stack>-<tool> ...``.

Phase 5 acceptance contract for T-5.7 / T-5.8 / T-5.9 / T-5.10 / T-5.11 / T-5.13.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_engineering.installer.service import (
    _check_tool_spec_hashes,
    _format_tool_spec_mismatch_banner,
    _has_active_finding_dec,
)
from ai_engineering.state.manifest import compute_tool_spec_hash
from ai_engineering.state.models import (
    Decision,
    DecisionStatus,
    DecisionStore,
    InstallState,
    RiskCategory,
    RiskSeverity,
    ToolScope,
    ToolSpec,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Source-presence assertions (spec-107 G-11 wiring contract)
# ---------------------------------------------------------------------------


def test_compute_tool_spec_hash_helper_exists() -> None:
    """G-11: `compute_tool_spec_hash` helper exists in state.manifest module."""
    manifest_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "manifest.py"
    assert manifest_path.is_file(), f"state.manifest missing: {manifest_path}"
    text = manifest_path.read_text(encoding="utf-8")
    assert "def compute_tool_spec_hash(" in text, (
        "state.manifest missing `compute_tool_spec_hash()` — Phase 5 T-5.7 "
        "must add SHA256 of canonical-JSON tool spec"
    )


def test_install_state_carries_tool_spec_hashes_field() -> None:
    """G-11: InstallState model has `tool_spec_hashes: dict[str, str]` field."""
    models_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "models.py"
    assert models_path.is_file(), f"state.models missing: {models_path}"
    text = models_path.read_text(encoding="utf-8")
    assert "tool_spec_hashes" in text, (
        "InstallState model missing `tool_spec_hashes: dict[str, str]` — "
        "Phase 5 T-5.8 must add the field for H1 baseline storage"
    )


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


def test_cli_banner_template_documents_remediation() -> None:
    """G-11: installer banner includes remediation hint with ai-eng risk accept."""
    service_path = REPO_ROOT / "src" / "ai_engineering" / "installer" / "service.py"
    if not service_path.is_file():
        pytest.skip("installer.service missing — covered by sibling test")
    text = service_path.read_text(encoding="utf-8")
    assert (
        "Tool Spec Mismatch" in text or "tool-spec-mismatch" in text or "ai-eng risk accept" in text
    ), (
        "installer.service missing CLI banner template for H1 mismatch — "
        "Phase 5 T-5.10 must add the user-facing remediation hint"
    )


def test_first_run_populates_baseline_silently() -> None:
    """G-11: first-run with empty baseline must populate without alerting."""
    service_path = REPO_ROOT / "src" / "ai_engineering" / "installer" / "service.py"
    if not service_path.is_file():
        pytest.skip("installer.service missing — covered by sibling test")
    text = service_path.read_text(encoding="utf-8")
    assert "first" in text.lower() or "empty" in text.lower() or "tool_spec_hashes" in text, (
        "installer.service missing first-run baseline-population branch — "
        "Phase 5 T-5.11 must populate hashes silently when baseline is empty"
    )


# ---------------------------------------------------------------------------
# Behavioral: helper invariants
# ---------------------------------------------------------------------------


def test_compute_tool_spec_hash_is_canonical_and_stable() -> None:
    """compute_tool_spec_hash returns the same hex digest for equivalent specs."""
    spec_a = ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL)
    spec_b = ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL)
    assert compute_tool_spec_hash(spec_a) == compute_tool_spec_hash(spec_b)
    # Stable across pydantic dump vs raw dict invocation.
    raw = spec_a.model_dump(mode="json")
    assert compute_tool_spec_hash(raw) == compute_tool_spec_hash(spec_a)


def test_compute_tool_spec_hash_differs_on_semantic_change() -> None:
    """compute_tool_spec_hash differs when scope or name changes."""
    spec_a = ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL)
    spec_b = ToolSpec(name="ruff", scope=ToolScope.PROJECT_LOCAL)
    spec_c = ToolSpec(name="ty", scope=ToolScope.USER_GLOBAL_UV_TOOL)
    assert compute_tool_spec_hash(spec_a) != compute_tool_spec_hash(spec_b)
    assert compute_tool_spec_hash(spec_a) != compute_tool_spec_hash(spec_c)


# ---------------------------------------------------------------------------
# Behavioral: _check_tool_spec_hashes fixture-project flows
# ---------------------------------------------------------------------------


def _write_minimal_manifest(target: Path, *, ruff_scope: str = "user_global_uv_tool") -> None:
    """Write a minimal manifest.yml with required_tools.baseline + python."""
    manifest_path = target / ".ai-engineering" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        f"""\
providers:
  stacks: [python]
  ides: [terminal]
  vcs: github
required_tools:
  baseline:
    name: baseline
    tools:
      - name: uv
        scope: user_global
  python:
    name: python
    tools:
      - name: ruff
        scope: {ruff_scope}
""",
        encoding="utf-8",
    )


def _decision_store_with_h1_acceptance(stack_tool: str) -> DecisionStore:
    """Construct a DecisionStore carrying an active H1 risk-acceptance."""
    finding_id = f"tool-spec-mismatch-{stack_tool.replace(':', '-')}"
    decision = Decision(
        id=f"DEC-H1-{stack_tool.upper().replace(':', '-')}",
        context=f"finding:{finding_id}",
        decision="Accepted; manifest update is intentional.",
        decided_at=datetime.now(tz=UTC),
        spec="spec-107",
        risk_category=RiskCategory.RISK_ACCEPTANCE,
        severity=RiskSeverity.HIGH,
        accepted_by="test-suite",
        follow_up_action="Re-anchor baseline at next scheduled review.",
        status=DecisionStatus.ACTIVE,
        finding_id=finding_id,
        expires_at=datetime.now(tz=UTC) + timedelta(days=30),
    )
    return DecisionStore(decisions=[decision])


def test_first_run_populates_baseline_silently_on_real_state(tmp_path: Path) -> None:
    """First install with empty tool_spec_hashes populates without banner."""
    target = tmp_path / "project"
    target.mkdir()
    _write_minimal_manifest(target)

    state = InstallState()
    assert state.tool_spec_hashes == {}
    manual_steps: list[str] = []

    _check_tool_spec_hashes(target, state, manual_steps=manual_steps)

    # Baseline populated for baseline:uv + python:ruff
    assert "baseline:uv" in state.tool_spec_hashes
    assert "python:ruff" in state.tool_spec_hashes
    # No banner on first run
    assert manual_steps == []


def test_no_mismatch_is_silent_on_subsequent_run(tmp_path: Path) -> None:
    """Subsequent install with matching hashes is a no-op."""
    target = tmp_path / "project"
    target.mkdir()
    _write_minimal_manifest(target)

    # Run 1: anchor baseline.
    state = InstallState()
    _check_tool_spec_hashes(target, state, manual_steps=[])
    baseline_snapshot = dict(state.tool_spec_hashes)

    # Run 2: no manifest change.
    manual_steps: list[str] = []
    _check_tool_spec_hashes(target, state, manual_steps=manual_steps)

    assert state.tool_spec_hashes == baseline_snapshot
    assert manual_steps == []


def test_mismatch_without_dec_appends_remediation_banner(tmp_path: Path) -> None:
    """Hash mismatch without active DEC must surface a CLI banner."""
    target = tmp_path / "project"
    target.mkdir()
    _write_minimal_manifest(target, ruff_scope="user_global_uv_tool")

    # Run 1: anchor baseline.
    state = InstallState()
    _check_tool_spec_hashes(target, state, manual_steps=[])

    # Mutate manifest -> different ruff scope.
    _write_minimal_manifest(target, ruff_scope="project_local")

    # Empty decision-store on disk (no DEC).
    store_path = target / ".ai-engineering" / "state" / "decision-store.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(
        json.dumps({"schemaVersion": "1.1", "decisions": []}, indent=2),
        encoding="utf-8",
    )

    manual_steps: list[str] = []
    _check_tool_spec_hashes(target, state, manual_steps=manual_steps)

    # Banner must be appended for python:ruff mismatch.
    assert any("python:ruff" in step for step in manual_steps), manual_steps
    assert any("Tool Spec Mismatch" in step for step in manual_steps), manual_steps
    assert any("ai-eng risk accept" in step for step in manual_steps), manual_steps
    # Baseline NOT updated when DEC absent.
    canonical = compute_tool_spec_hash(ToolSpec(name="ruff", scope=ToolScope.PROJECT_LOCAL))
    assert state.tool_spec_hashes["python:ruff"] != canonical


def test_mismatch_with_active_dec_permits_and_updates_baseline(tmp_path: Path) -> None:
    """Active DEC permits mismatch + updates baseline + suppresses banner."""
    target = tmp_path / "project"
    target.mkdir()
    _write_minimal_manifest(target, ruff_scope="user_global_uv_tool")

    # Run 1: anchor baseline.
    state = InstallState()
    _check_tool_spec_hashes(target, state, manual_steps=[])

    # Mutate manifest.
    _write_minimal_manifest(target, ruff_scope="project_local")

    # Persist DEC active for python:ruff mismatch.
    store = _decision_store_with_h1_acceptance("python:ruff")
    store_path = target / ".ai-engineering" / "state" / "decision-store.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(
        store.model_dump_json(by_alias=True, indent=2),
        encoding="utf-8",
    )

    manual_steps: list[str] = []
    _check_tool_spec_hashes(target, state, manual_steps=manual_steps)

    # No banner — DEC permitted the change.
    assert not any("python:ruff" in step for step in manual_steps), manual_steps
    # Baseline updated to the new hash.
    expected = compute_tool_spec_hash(ToolSpec(name="ruff", scope=ToolScope.PROJECT_LOCAL))
    assert state.tool_spec_hashes["python:ruff"] == expected


def test_new_tool_added_post_baseline_is_additive(tmp_path: Path) -> None:
    """Tools added after baseline are additive — no alert, just record."""
    target = tmp_path / "project"
    target.mkdir()
    # Run 1: only python stack.
    _write_minimal_manifest(target)
    state = InstallState()
    _check_tool_spec_hashes(target, state, manual_steps=[])
    initial_keys = set(state.tool_spec_hashes)

    # Run 2: add a new tool to baseline.
    manifest_path = target / ".ai-engineering" / "manifest.yml"
    manifest_path.write_text(
        """\
providers:
  stacks: [python]
  ides: [terminal]
  vcs: github
required_tools:
  baseline:
    name: baseline
    tools:
      - name: uv
        scope: user_global
      - name: gitleaks
        scope: user_global
  python:
    name: python
    tools:
      - name: ruff
        scope: user_global_uv_tool
""",
        encoding="utf-8",
    )

    manual_steps: list[str] = []
    _check_tool_spec_hashes(target, state, manual_steps=manual_steps)

    assert "baseline:gitleaks" in state.tool_spec_hashes
    # Existing baselines preserved + no banner for additive change.
    assert initial_keys.issubset(set(state.tool_spec_hashes))
    assert manual_steps == []


def test_has_active_finding_dec_filters_by_status_and_expiry() -> None:
    """_has_active_finding_dec only matches ACTIVE non-expired risk-acceptances."""
    finding_id = "tool-spec-mismatch-python-ruff"
    now = datetime.now(tz=UTC)

    # Expired DEC -> not active.
    expired = Decision(
        id="DEC-EXPIRED",
        context=f"finding:{finding_id}",
        decision="x",
        decided_at=now - timedelta(days=120),
        spec="spec-107",
        risk_category=RiskCategory.RISK_ACCEPTANCE,
        severity=RiskSeverity.HIGH,
        status=DecisionStatus.ACTIVE,
        finding_id=finding_id,
        expires_at=now - timedelta(days=10),
    )
    store_expired = DecisionStore(decisions=[expired])
    assert _has_active_finding_dec(store_expired, finding_id) is False

    # Revoked DEC -> not active.
    revoked = Decision(
        id="DEC-REVOKED",
        context=f"finding:{finding_id}",
        decision="x",
        decided_at=now,
        spec="spec-107",
        risk_category=RiskCategory.RISK_ACCEPTANCE,
        severity=RiskSeverity.HIGH,
        status=DecisionStatus.REVOKED,
        finding_id=finding_id,
    )
    store_revoked = DecisionStore(decisions=[revoked])
    assert _has_active_finding_dec(store_revoked, finding_id) is False

    # Active risk-acceptance with no expiry -> active.
    active = Decision(
        id="DEC-ACTIVE",
        context=f"finding:{finding_id}",
        decision="x",
        decided_at=now,
        spec="spec-107",
        risk_category=RiskCategory.RISK_ACCEPTANCE,
        severity=RiskSeverity.HIGH,
        status=DecisionStatus.ACTIVE,
        finding_id=finding_id,
    )
    store_active = DecisionStore(decisions=[active])
    assert _has_active_finding_dec(store_active, finding_id) is True

    # Wrong category (architecture-decision) -> not a risk acceptance.
    arch = Decision(
        id="DEC-ARCH",
        context=f"finding:{finding_id}",
        decision="x",
        decided_at=now,
        spec="spec-107",
        risk_category=RiskCategory.ARCHITECTURE_DECISION,
        status=DecisionStatus.ACTIVE,
        finding_id=finding_id,
    )
    store_arch = DecisionStore(decisions=[arch])
    assert _has_active_finding_dec(store_arch, finding_id) is False


def test_format_tool_spec_mismatch_banner_renders_canonical_template() -> None:
    """Banner template includes finding-id, hashes (truncated), and risk-accept CLI."""
    banner = _format_tool_spec_mismatch_banner(
        stack_tool="python:ruff",
        baseline_hash="a" * 64,
        current_hash="b" * 64,
        finding_id="tool-spec-mismatch-python-ruff",
    )
    assert "python:ruff" in banner
    assert "Tool Spec Mismatch" in banner
    assert "aaaaaaaaaaaa" in banner  # baseline truncated to 12
    assert "bbbbbbbbbbbb" in banner  # current truncated to 12
    assert "tool-spec-mismatch-python-ruff" in banner
    assert "ai-eng risk accept" in banner
    assert "spec-107" in banner
