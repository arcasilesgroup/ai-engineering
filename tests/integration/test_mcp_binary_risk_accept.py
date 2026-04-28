"""GREEN tests for spec-107 G-1 — MCP binary risk-accept escape hatch.

Companion to ``test_mcp_binary_allowlist.py``: validates that an active
risk-acceptance entry in ``decision-store.json`` keyed on
``mcp-binary-<binary>`` permits an otherwise-rejected binary, while
expired or missing acceptances revert to the default deny path.

Test surface:
- Active DEC for ``mcp-binary-mvn`` → ``_binary_allowed("mvn")`` is True
  AND emits a ``binary-allowed-via-dec`` telemetry event with ``dec_id``.
- Expired DEC for ``mcp-binary-mvn`` → ``_binary_allowed("mvn")`` is
  False AND emits a ``binary-rejected`` event (no expired-DEC bypass).
- Missing decision-store → ``_binary_allowed("mvn")`` is False (fail-
  closed); the hook never crashes the host on missing state.

Also exercises ``_find_active_mcp_binary_acceptance`` directly for fast
unit coverage of the lookup primitive.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "mcp-health.py"


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("_mcp_health_test_module_ra", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hook_module():
    return _load_hook_module()


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".ai-engineering" / "state").mkdir(parents=True)
    return root


def _write_store(project_root: Path, decisions: list[dict]) -> Path:
    """Persist a decision-store.json fixture and return its path."""
    payload = {
        "schemaVersion": "1.1",
        "decisions": decisions,
    }
    store_path = project_root / ".ai-engineering" / "state" / "decision-store.json"
    store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return store_path


def _events_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


def _read_events(project_root: Path) -> list[dict]:
    path = _events_path(project_root)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _active_decision_for(binary: str, dec_id: str = "DEC-MCP-MVN-001") -> dict:
    """Build a canonical active risk-acceptance entry for ``mcp-binary-<binary>``."""
    return {
        "id": dec_id,
        "context": f"mcp-binary:{binary}",
        "decision": f"Risk-accepted: allow MCP server binary '{binary}'",
        "decidedAt": _iso(datetime.now(tz=UTC)),
        "spec": "spec-107",
        "expiresAt": _iso(datetime.now(tz=UTC) + timedelta(days=90)),
        "riskCategory": "risk-acceptance",
        "severity": "low",
        "acceptedBy": "test-suite",
        "followUpAction": "Re-evaluate in 90 days",
        "status": "active",
        "renewalCount": 0,
        "findingId": f"mcp-binary-{binary}",
    }


def _expired_decision_for(binary: str, dec_id: str = "DEC-MCP-MVN-EXP") -> dict:
    """Build an EXPIRED risk-acceptance entry."""
    long_ago = datetime.now(tz=UTC) - timedelta(days=30)
    return {
        "id": dec_id,
        "context": f"mcp-binary:{binary}",
        "decision": f"Risk-accepted (expired): allow MCP server binary '{binary}'",
        "decidedAt": _iso(long_ago - timedelta(days=60)),
        "spec": "spec-107",
        "expiresAt": _iso(long_ago),
        "riskCategory": "risk-acceptance",
        "severity": "low",
        "acceptedBy": "test-suite",
        "followUpAction": "Renew or remediate",
        "status": "active",
        "renewalCount": 0,
        "findingId": f"mcp-binary-{binary}",
    }


def test_active_dec_permits_otherwise_rejected_binary(hook_module, project_root: Path) -> None:
    """G-1: active DEC for mcp-binary-mvn permits execution + emits telemetry."""
    _write_store(project_root, [_active_decision_for("mvn")])
    permitted = hook_module._binary_allowed(
        "mvn",
        project_root=project_root,
        server_name="atlassian",
        cmd_kind="probe",
    )
    assert permitted is True, (
        "active risk-acceptance for mcp-binary-mvn was not honored — escape "
        "hatch broken (D-107-01 step 2)"
    )
    events = _read_events(project_root)
    matched = [
        e
        for e in events
        if e.get("kind") == "control_outcome"
        and e.get("detail", {}).get("control") == "binary-allowed-via-dec"
    ]
    assert len(matched) == 1, (
        f"expected 1 binary-allowed-via-dec event, got {len(matched)}: {matched!r}"
    )
    detail = matched[0]["detail"]
    assert detail.get("category") == "mcp-sentinel"
    assert detail.get("binary") == "mvn"
    assert detail.get("server") == "atlassian"
    assert detail.get("dec_id") == "DEC-MCP-MVN-001"
    assert detail.get("cmd_kind") == "probe"


def test_expired_dec_rejects_binary_and_emits_rejection(hook_module, project_root: Path) -> None:
    """G-1: an expired DEC must NOT permit execution; deny path engaged."""
    _write_store(project_root, [_expired_decision_for("mvn")])
    permitted = hook_module._binary_allowed(
        "mvn",
        project_root=project_root,
        server_name="atlassian",
        cmd_kind="probe",
    )
    assert permitted is False, (
        "expired risk-acceptance silently allowed binary — TTL bypass detected"
    )
    events = _read_events(project_root)
    rejected = [
        e
        for e in events
        if e.get("kind") == "control_outcome"
        and e.get("detail", {}).get("control") == "binary-rejected"
    ]
    assert len(rejected) == 1, (
        f"expected 1 binary-rejected event for expired DEC, got {len(rejected)}: {rejected!r}"
    )
    accepted = [e for e in events if e.get("detail", {}).get("control") == "binary-allowed-via-dec"]
    assert accepted == [], (
        f"expired DEC must NEVER emit a binary-allowed-via-dec event; got {accepted!r}"
    )


def test_missing_decision_store_rejects_unallowed_binary(hook_module, project_root: Path) -> None:
    """G-1: hook is fail-closed when decision-store.json is absent."""
    # No store written.
    permitted = hook_module._binary_allowed(
        "mvn",
        project_root=project_root,
        server_name="atlassian",
        cmd_kind="probe",
    )
    assert permitted is False, (
        "missing decision-store should fail-closed; allowing binary risks RCE"
    )


def test_lookup_primitive_returns_none_for_unrelated_finding_id(
    hook_module, project_root: Path
) -> None:
    """``_find_active_mcp_binary_acceptance`` must scope strictly by finding_id."""
    decisions = [
        _active_decision_for("php"),
        _active_decision_for("mvn"),
    ]
    _write_store(project_root, decisions)
    # Unrelated binary — no DEC.
    assert hook_module._find_active_mcp_binary_acceptance(project_root, "java") is None
    # Exact match.
    decision = hook_module._find_active_mcp_binary_acceptance(project_root, "mvn")
    assert decision is not None
    assert decision.get("findingId") == "mcp-binary-mvn"


def test_lookup_primitive_skips_non_acceptance_decisions(hook_module, project_root: Path) -> None:
    """Only ``risk_category == risk-acceptance`` entries should match."""
    decision = _active_decision_for("mvn")
    decision["riskCategory"] = "architecture"  # ineligible
    _write_store(project_root, [decision])
    assert hook_module._find_active_mcp_binary_acceptance(project_root, "mvn") is None


def test_lookup_primitive_skips_revoked_decisions(hook_module, project_root: Path) -> None:
    """Only ``status == active`` entries should match."""
    decision = _active_decision_for("mvn")
    decision["status"] = "revoked"
    _write_store(project_root, [decision])
    assert hook_module._find_active_mcp_binary_acceptance(project_root, "mvn") is None
