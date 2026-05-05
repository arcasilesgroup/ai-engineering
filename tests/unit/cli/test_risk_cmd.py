"""Unit tests for ``ai-eng risk accept`` OPA gating (spec-123 D-123-18 / T-4.1).

Spec-122 Phase C wired ``_gate_risk_acceptance_via_opa`` into ``risk_cmd``;
spec-123 closes the loop by exercising the gate with both happy-path and
deny-path inputs. The tests stub ``opa_runner.available`` and
``opa_gate.evaluate_deny`` so they run regardless of whether the OPA
binary is installed in the executing environment.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import typer

from ai_engineering.cli_commands import risk_cmd
from ai_engineering.policy.checks.opa_gate import OpaDecision


def _call_gate(
    *,
    expires_at: datetime | None,
    monkeypatch: pytest.MonkeyPatch,
    opa_available: bool = True,
    decision: OpaDecision | None = None,
) -> list[dict[str, Any]]:
    """Invoke ``_gate_risk_acceptance_via_opa`` with controlled stubs.

    Returns the captured argument dicts so individual tests can assert on
    the policy/component/source wiring contract.
    """
    captured: list[dict[str, Any]] = []

    def _fake_available() -> bool:
        return opa_available

    def _fake_evaluate(**kwargs: Any) -> OpaDecision:
        captured.append(kwargs)
        if decision is None:
            return OpaDecision(passed=True, output="policy allow", deny_messages=[])
        return decision

    from ai_engineering.governance import opa_runner
    from ai_engineering.policy.checks import opa_gate

    monkeypatch.setattr(opa_runner, "available", _fake_available)
    monkeypatch.setattr(opa_gate, "evaluate_deny", _fake_evaluate)

    risk_cmd._gate_risk_acceptance_via_opa(
        project_root=Path.cwd(),
        now=datetime.now(tz=UTC),
        expires_at=expires_at,
        severity="high",
        justification="ttl gate test",
    )
    return captured


def test_gate_skipped_when_no_explicit_expires_at(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--expires-at`` omitted → OPA is not invoked (severity defaults are safe)."""
    captured = _call_gate(expires_at=None, monkeypatch=monkeypatch)
    assert captured == []


def test_gate_skipped_when_opa_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """OPA binary missing → fail-open during rollout (no exit)."""
    future = datetime.now(tz=UTC) + timedelta(days=30)
    captured = _call_gate(expires_at=future, monkeypatch=monkeypatch, opa_available=False)
    assert captured == []


def test_gate_allows_future_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Future TTL → policy allow; helper returns silently with the right wiring."""
    future = datetime.now(tz=UTC) + timedelta(days=30)
    captured = _call_gate(expires_at=future, monkeypatch=monkeypatch)
    assert len(captured) == 1
    payload = captured[0]
    assert payload["policy"] == "risk_acceptance_ttl"
    assert payload["component"] == "risk-cmd"
    assert payload["source"] == "risk-accept"
    assert payload["input_data"]["severity"] == "high"
    assert payload["input_data"]["justification"] == "ttl gate test"
    # ttl_expires_at and now must be ISO-8601 strings, not datetime objects.
    assert isinstance(payload["input_data"]["ttl_expires_at"], str)
    assert isinstance(payload["input_data"]["now"], str)


def test_gate_rejects_past_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Past TTL → policy deny → ``typer.Exit(2)`` with the deny message."""
    past = datetime.now(tz=UTC) - timedelta(days=1)
    deny = OpaDecision(
        passed=False,
        output="risk acceptance TTL expired",
        deny_messages=["risk acceptance TTL expired"],
    )
    with pytest.raises(typer.Exit) as exc:
        _call_gate(expires_at=past, monkeypatch=monkeypatch, decision=deny)
    assert exc.value.exit_code == 2


def test_gate_rejects_with_default_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty deny_messages still triggers exit with a fallback message."""
    future = datetime.now(tz=UTC) + timedelta(days=30)
    deny = OpaDecision(passed=False, output="", deny_messages=[])
    with pytest.raises(typer.Exit) as exc:
        _call_gate(expires_at=future, monkeypatch=monkeypatch, decision=deny)
    assert exc.value.exit_code == 2
