"""RED skeleton for spec-105 Phase 2 — `apply_risk_acceptances` core logic.

Covers spec-105 G-2 contract: partition findings into (blocking, accepted)
based on active DEC matches via canonical context format `f"finding:{rule_id}"`.
Includes expiry handling, telemetry per accepted finding, edge cases.

Status: RED (target module `policy/checks/_accept_lookup.py` does not exist).
Marker: `@pytest.mark.spec_105_red` — excluded by default CI run.
Will be unmarked in Phase 2 (T-2.9) once module is implemented.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.spec_105_red

# Imports are deferred inside each test so collection succeeds even though the
# target module does not exist yet. Tests fail at execution time (when the
# marker is explicitly enabled), not at collection time. This keeps
# `pytest -m 'not spec_105_red'` clean for CI default runs.


def test_apply_partitions_findings_into_blocking_and_accepted() -> None:
    """`apply_risk_acceptances` returns (blocking, accepted) tuples respecting active DEC."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances

    blocking, accepted = apply_risk_acceptances([], None, now=datetime.now(tz=UTC))
    assert blocking == []
    assert accepted == []


def test_apply_skips_expired_decisions() -> None:
    """Findings matching an expired DEC remain blocking (not accepted)."""
    # Phase 2 T-2.8 will implement expiry partition logic.
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances  # noqa: F401

    raise NotImplementedError("Phase 2 T-2.8 will implement expiry partition")


def test_apply_emits_control_outcome_telemetry_per_accepted() -> None:
    """Each accepted finding emits exactly one telemetry event."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances  # noqa: F401

    raise NotImplementedError("Phase 2 T-2.8 will implement telemetry emission")


def test_finding_is_accepted_canonical_context_format() -> None:
    """`finding_is_accepted` looks up via `f\"finding:{rule_id}\"` + context_hash."""
    from ai_engineering.policy.checks._accept_lookup import finding_is_accepted

    result = finding_is_accepted(None, None, now=datetime.now(tz=UTC))
    assert result is None
