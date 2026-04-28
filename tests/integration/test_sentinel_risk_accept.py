"""GREEN tests for spec-107 G-9 (Phase 4) — Sentinel risk-accept escape.

Spec-107 D-107-07 routes user allowlist exceptions through the existing
spec-105 risk-acceptance machinery instead of introducing a new file
format. Canonical `finding_id` format:

    f"sentinel-{category}-{pattern_normalized}"

where ``pattern_normalized`` is lower-cased + ``/`` replaced with ``_``
for idempotent lookups.

Spec contract (G-9 + G-8 integration):
- IOC match without active DEC → ``deny``.
- IOC match WITH active DEC for the matching ``finding_id`` → ``warn``
  (allow execution + log audit event for compliance trace).
- DEC expiry / revocation reverts the verdict to ``deny`` on next match.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "prompt-injection-guard.py"
IOCS_PATH = REPO_ROOT / ".ai-engineering" / "references" / "iocs.json"


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("_pi_guard_test_module_ra", HOOK_PATH)
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
    (root / ".ai-engineering" / "references").mkdir(parents=True)
    target = root / ".ai-engineering" / "references" / "iocs.json"
    target.write_text(IOCS_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return root


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_store(project_root: Path, decisions: list[dict]) -> Path:
    payload = {"schemaVersion": "1.1", "decisions": decisions}
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


def _active_decision_for(finding_id: str, dec_id: str) -> dict:
    """Build a canonical active risk-acceptance entry for a sentinel finding-id."""
    return {
        "id": dec_id,
        "context": f"sentinel-ioc:{finding_id}",
        "decision": f"Risk-accepted: allow IOC pattern '{finding_id}'",
        "decidedAt": _iso(datetime.now(tz=UTC)),
        "spec": "spec-107",
        "expiresAt": _iso(datetime.now(tz=UTC) + timedelta(days=90)),
        "riskCategory": "risk-acceptance",
        "severity": "low",
        "acceptedBy": "test-suite",
        "followUpAction": "Re-evaluate in 90 days",
        "status": "active",
        "renewalCount": 0,
        "findingId": finding_id,
    }


def _expired_decision_for(finding_id: str, dec_id: str) -> dict:
    long_ago = datetime.now(tz=UTC) - timedelta(days=30)
    return {
        "id": dec_id,
        "context": f"sentinel-ioc:{finding_id}",
        "decision": f"Risk-accepted (expired): IOC '{finding_id}'",
        "decidedAt": _iso(long_ago - timedelta(days=60)),
        "spec": "spec-107",
        "expiresAt": _iso(long_ago),
        "riskCategory": "risk-acceptance",
        "severity": "low",
        "acceptedBy": "test-suite",
        "followUpAction": "Renew or remediate",
        "status": "active",
        "renewalCount": 0,
        "findingId": finding_id,
    }


# ---------------------------------------------------------------------------
# Surface contract: hook integrates spec-105 risk-acceptance primitive
# ---------------------------------------------------------------------------


def test_hook_imports_risk_acceptance_lookup() -> None:
    """G-9: hook reuses spec-105 ``find_active_risk_acceptance`` primitive."""
    assert HOOK_PATH.is_file(), f"hook missing: {HOOK_PATH}"
    text = HOOK_PATH.read_text(encoding="utf-8")
    assert "find_active_risk_acceptance" in text, (
        "prompt-injection-guard.py missing `find_active_risk_acceptance` "
        "lookup — Phase 4 T-4.7 must reuse spec-105 D-105-07 primitive so "
        "the audit trail is consistent across surfaces"
    )


def test_hook_normalises_pattern_for_finding_id(hook_module) -> None:
    """G-9: hook normalises pattern (lower-case + slashes -> underscores)."""
    # Direct call to the canonical id helper.
    assert hook_module.canonical_finding_id("sensitive_paths", "~/.ssh/ID_RSA") == (
        "sentinel-sensitive_paths-~_.ssh_id_rsa"
    )
    # Module-level normalizer must exist for callers to reuse.
    assert hook_module._normalize_pattern("FOO/BAR") == "foo_bar"


# ---------------------------------------------------------------------------
# 3-valued decision protocol: allow / deny / warn (per match acceptance)
# ---------------------------------------------------------------------------


def test_no_match_returns_allow(hook_module, project_root: Path) -> None:
    """G-9 baseline: clean payload with no IOC overlap returns allow."""
    result = hook_module.evaluate_against_iocs(project_root, "echo hello world")
    assert result["verdict"] == "allow"


def test_ioc_match_no_dec_returns_deny(hook_module, project_root: Path) -> None:
    """G-9: IOC match without DEC returns deny verdict + remediation hint."""
    # No decision-store written.
    result = hook_module.evaluate_against_iocs(project_root, "cat ~/.ssh/id_rsa")
    assert result["verdict"] == "deny"
    assert "ai-eng risk accept" in result["reason"], (
        "deny reason must include the remediation banner with the canonical "
        "`ai-eng risk accept --finding-id sentinel-...` invocation"
    )


def test_ioc_match_with_active_dec_returns_warn(hook_module, project_root: Path) -> None:
    """G-9: IOC match WITH active DECs for ALL matching finding-ids returns warn.

    The IOC catalog deliberately overlaps narrower patterns inside broader
    parents (e.g. ``~/.ssh/`` is a prefix of ``~/.ssh/id_rsa``). For the
    verdict to convert from ``deny`` to ``warn`` the evaluator must see an
    active DEC for EVERY match in the payload — partial acceptance keeps
    the deny stance (the unaccepted match is sufficient to deny).
    """
    # The payload below hits both `~/.ssh/` and `~/.ssh/id_rsa`. Both
    # finding-ids must have active DECs.
    finding_broad = hook_module.canonical_finding_id("sensitive_paths", "~/.ssh/")
    finding_narrow = hook_module.canonical_finding_id("sensitive_paths", "~/.ssh/id_rsa")
    _write_store(
        project_root,
        [
            _active_decision_for(finding_broad, "DEC-SENT-BROAD"),
            _active_decision_for(finding_narrow, "DEC-SENT-NARROW"),
        ],
    )
    result = hook_module.evaluate_against_iocs(project_root, "cat ~/.ssh/id_rsa")
    assert result["verdict"] == "warn", (
        f"active DECs for both {finding_broad} and {finding_narrow} should "
        f"convert deny -> warn; got {result}"
    )
    accepted_matches = [m for m in result["matches"] if m["accepted"]]
    assert len(accepted_matches) >= 2, (
        f"expected >=2 accepted matches for overlapping patterns; got {accepted_matches}"
    )
    dec_ids = {m.get("dec_id") for m in accepted_matches}
    assert "DEC-SENT-NARROW" in dec_ids, (
        "warn match metadata must include the dec_id of the narrow matching acceptance"
    )
    assert "DEC-SENT-BROAD" in dec_ids, (
        "warn match metadata must include the dec_id of the broad matching acceptance"
    )


def test_expired_dec_reverts_to_deny(hook_module, project_root: Path) -> None:
    """G-9: an expired DEC must NOT permit execution; verdict is deny again."""
    finding_id = hook_module.canonical_finding_id("sensitive_paths", "~/.ssh/id_rsa")
    _write_store(project_root, [_expired_decision_for(finding_id, "DEC-SENT-EXP")])
    result = hook_module.evaluate_against_iocs(project_root, "cat ~/.ssh/id_rsa")
    assert result["verdict"] == "deny", (
        "expired DEC silently allowed IOC match — TTL bypass detected"
    )


def test_revoked_dec_reverts_to_deny(hook_module, project_root: Path) -> None:
    """G-9: a revoked DEC must NOT permit execution; verdict is deny."""
    finding_id = hook_module.canonical_finding_id("sensitive_paths", "~/.ssh/id_rsa")
    decision = _active_decision_for(finding_id, "DEC-SENT-REV")
    decision["status"] = "revoked"
    _write_store(project_root, [decision])
    result = hook_module.evaluate_against_iocs(project_root, "cat ~/.ssh/id_rsa")
    assert result["verdict"] == "deny"


def test_dec_for_unrelated_finding_does_not_apply(hook_module, project_root: Path) -> None:
    """G-9: DEC for finding-id A must not allow IOC match for finding-id B."""
    finding_other = hook_module.canonical_finding_id("sensitive_paths", "~/.aws/credentials")
    _write_store(project_root, [_active_decision_for(finding_other, "DEC-OTHER")])
    # Hit a different sensitive path that has no DEC.
    result = hook_module.evaluate_against_iocs(project_root, "cat ~/.ssh/id_rsa")
    assert result["verdict"] == "deny", (
        "DEC-scoping leak: unrelated finding-id permitted access to a different IOC pattern"
    )


# ---------------------------------------------------------------------------
# CLI integration sanity (spec-105 lifecycle reused, no new surface)
# ---------------------------------------------------------------------------


def test_risk_accept_finding_id_listable_via_cli_filter() -> None:
    """G-9 prerequisite: the spec-105 risk CLI module is present.

    spec-107 reuses the spec-105 lifecycle for sentinel-* finding-ids; no
    new CLI surface is needed.
    """
    candidates = list((REPO_ROOT / "src" / "ai_engineering").rglob("risk*.py"))
    assert candidates, (
        "spec-105 risk CLI module missing — preconditions for sentinel "
        "risk-accept escape (G-9) are not met"
    )
