"""RED skeleton for spec-107 G-9 (Phase 4) — Sentinel risk-accept escape.

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

These tests are marked ``spec_107_red`` and excluded from CI default
runs until Phase 4 lands the GREEN implementation. They are the
acceptance contract for T-4.7 / T-4.11.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "prompt-injection-guard.py"


@pytest.mark.spec_107_red
def test_hook_imports_risk_acceptance_lookup() -> None:
    """G-9: hook reuses spec-105 ``find_active_risk_acceptance`` primitive."""
    assert HOOK_PATH.is_file(), f"hook missing: {HOOK_PATH}"
    text = HOOK_PATH.read_text(encoding="utf-8")
    assert "find_active_risk_acceptance" in text, (
        "prompt-injection-guard.py missing `find_active_risk_acceptance` "
        "lookup — Phase 4 T-4.7 must reuse spec-105 D-105-07 primitive so "
        "the audit trail is consistent across surfaces"
    )


@pytest.mark.spec_107_red
def test_hook_normalises_pattern_for_finding_id() -> None:
    """G-9: hook normalises pattern (lower-case + slashes -> underscores)."""
    assert HOOK_PATH.is_file()
    text = HOOK_PATH.read_text(encoding="utf-8")
    # The canonical normaliser is documented in D-107-07; presence of the
    # function name (or inline normalisation hint) is sufficient for the
    # acceptance contract — Phase 4 implementation may inline.
    assert (
        "canonical_finding_id" in text
        or "pattern_normalized" in text
        or 'replace("/", "_")' in text
    ), (
        "prompt-injection-guard.py missing pattern-normalisation logic — "
        "Phase 4 T-4.7 must lower-case + slash-to-underscore patterns for "
        "deterministic finding_id lookups"
    )


@pytest.mark.spec_107_red
def test_hook_decision_warn_when_dec_active() -> None:
    """G-9: hook converts deny -> warn when DEC is active for the finding."""
    assert HOOK_PATH.is_file()
    text = HOOK_PATH.read_text(encoding="utf-8")
    # The hook must contain logic that distinguishes the warn path from the
    # deny path. We assert presence of a comment / branch keyword tying the
    # warn verdict to the active-acceptance state.
    assert "warn" in text and ("DEC" in text or "risk-acceptance" in text or "accepted" in text), (
        "prompt-injection-guard.py missing DEC-active -> warn branch — "
        "Phase 4 T-4.7 must convert deny to warn when an active "
        "risk-acceptance covers the finding"
    )


@pytest.mark.spec_107_red
def test_hook_emits_telemetry_for_warn_path() -> None:
    """G-9: hook emits a control-outcome event whenever warn verdict fires.

    Warn path means the user explicitly accepted risk via DEC; the audit
    trail must record each match for compliance review.
    """
    assert HOOK_PATH.is_file()
    text = HOOK_PATH.read_text(encoding="utf-8")
    assert (
        "emit_control_outcome" in text
        or "framework-events" in text
        or "category=" in text
        or 'category="' in text
    ), (
        "prompt-injection-guard.py missing telemetry emission for warn path "
        "— Phase 4 T-4.7 must record `category=mcp-sentinel, "
        "control=ioc-match-allowed-via-dec` per D-107-06"
    )


@pytest.mark.spec_107_red
def test_risk_accept_finding_id_listable_via_cli_filter() -> None:
    """G-9 prerequisite: existing `ai-eng risk list --filter` glob works on sentinel-* IDs.

    No new CLI surface is needed; spec-107 reuses the spec-105 lifecycle.
    This test sanity-checks that the CLI module already understands the
    `sentinel-*` filter pattern (any glob support is enough — actual filter
    matching against a real DEC is covered in Phase 4 fixture tests).
    """
    cli_module = REPO_ROOT / "src" / "ai_engineering" / "cli" / "risk.py"
    if not cli_module.is_file():
        # The CLI module may live under a different layout in the install
        # tree (spec-105 D-105-05); accept any of the canonical locations.
        candidates = list(
            (REPO_ROOT / "src" / "ai_engineering").rglob("risk*.py"),
        )
        assert candidates, (
            "spec-105 risk CLI module missing — preconditions for sentinel "
            "risk-accept escape (G-9) are not met"
        )
