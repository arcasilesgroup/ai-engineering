"""Integration golden tests for OPA policies (spec-122 Phase C, T-3.14).

Invokes ``opa eval --bundle .ai-engineering/policies/`` against the live
policies for each fixture in the table. Skips with a clear marker when
the OPA binary is not installed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[3]
_POLICIES_DIR = _REPO_ROOT / ".ai-engineering" / "policies"


def _opa_available() -> bool:
    return shutil.which("opa") is not None


def _opa_eval(query: str, input_data: dict[str, Any]) -> dict[str, Any]:
    """Run ``opa eval`` against the live policies bundle and return the JSON."""
    proc = subprocess.run(
        [
            "opa",
            "eval",
            "--bundle",
            str(_POLICIES_DIR),
            "--stdin-input",
            "--format",
            "json",
            query,
        ],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10.0,
        check=False,
    )
    assert proc.returncode == 0, f"opa eval failed: {proc.stderr}"
    return json.loads(proc.stdout)


def _deny_messages(payload: dict[str, Any]) -> list[str]:
    """Extract the deny messages list from an opa eval JSON payload."""
    results = payload.get("result") or []
    if not results:
        return []
    expressions = results[0].get("expressions") or []
    if not expressions:
        return []
    value = expressions[0].get("value")
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


# ---------------------------------------------------------------------------
# branch_protection
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _opa_available(), reason="opa binary not installed")
@pytest.mark.parametrize(
    ("input_data", "expected_deny_count"),
    [
        ({"branch": "feat/spec-122", "action": "push"}, 0),
        ({"branch": "main", "action": "push"}, 1),
        ({"branch": "master", "action": "push"}, 1),
        ({"branch": "release/v1", "action": "push"}, 0),
        ({"branch": "main", "action": "fetch"}, 0),
    ],
)
def test_branch_protection_golden(input_data: dict[str, Any], expected_deny_count: int) -> None:
    payload = _opa_eval("data.branch_protection.deny", input_data)
    deny = _deny_messages(payload)
    assert len(deny) == expected_deny_count, f"input={input_data} deny={deny}"


# ---------------------------------------------------------------------------
# commit_conventional
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _opa_available(), reason="opa binary not installed")
@pytest.mark.parametrize(
    ("subject", "expected_deny_count"),
    [
        ("feat: add OPA wiring", 0),
        ("feat(spec-122): add OPA wiring", 0),
        ("fix(deps): bump rego", 0),
        ("feat(api)!: breaking change", 0),
        ("fixed the thing", 1),
        ("wibble: not a real type", 1),
        ("", 1),
        ("feat:", 1),
    ],
)
def test_commit_conventional_golden(subject: str, expected_deny_count: int) -> None:
    payload = _opa_eval("data.commit_conventional.deny", {"subject": subject})
    deny = _deny_messages(payload)
    assert len(deny) == expected_deny_count, f"subject={subject!r} deny={deny}"


# ---------------------------------------------------------------------------
# risk_acceptance_ttl
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _opa_available(), reason="opa binary not installed")
@pytest.mark.parametrize(
    ("input_data", "expected_deny_count"),
    [
        # Future TTL -- allowed.
        (
            {"now": "2026-05-05T00:00:00Z", "ttl_expires_at": "2026-06-01T00:00:00Z"},
            0,
        ),
        # Past TTL -- denied.
        (
            {"now": "2026-05-05T00:00:00Z", "ttl_expires_at": "2026-04-01T00:00:00Z"},
            1,
        ),
        # Equal -- denied (>=).
        (
            {"now": "2026-05-05T00:00:00Z", "ttl_expires_at": "2026-05-05T00:00:00Z"},
            1,
        ),
        # Cross-timezone allow case.
        (
            {"now": "2026-05-05T12:00:00Z", "ttl_expires_at": "2026-05-05T08:00:00-05:00"},
            0,
        ),
    ],
)
def test_risk_acceptance_ttl_golden(input_data: dict[str, Any], expected_deny_count: int) -> None:
    payload = _opa_eval("data.risk_acceptance_ttl.deny", input_data)
    deny = _deny_messages(payload)
    assert len(deny) == expected_deny_count, f"input={input_data} deny={deny}"
