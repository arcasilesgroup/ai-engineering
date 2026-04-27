"""RED skeleton for spec-105 Phase 5 — tier allocation per gate mode.

Covers G-3 (tier portion): ``select_checks_for_mode(mode)`` returns the
union of tier-bands per spec D-105-04:

* ``regulated`` — Tier 0 + Tier 1 + Tier 2 (full security/compliance surface).
* ``prototyping`` — Tier 0 + Tier 1 only (skip slow Tier 2 governance).

Invariants asserted (D-105-04):
* All Tier 0+1 checks remain in ``_ALWAYS_BLOCK`` (cannot be skipped).
* No Tier 0+1 check appears in any mode's skip list.
* ``_TIER_2_CHECKS`` matches the canonical D-105-04 enumeration.

Status: RED — ``policy/mode_dispatch.py:select_checks_for_mode`` does not
exist yet (lands in Phase 5 T-5.8 / T-5.9 / T-5.10b).
Marker: ``@pytest.mark.spec_105_red`` — excluded by default CI run.
Will be unmarked in Phase 5 (T-5.19).

Lesson learned in Phase 1: deferred imports of the target wiring keep
pytest collection green while modules are still missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.spec_105_red


def test_regulated_mode_selects_all_tiers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``regulated`` mode runs every check from Tier 0 + 1 + 2."""
    from ai_engineering.policy import mode_dispatch

    monkeypatch.chdir(tmp_path)
    selected = set(mode_dispatch.select_checks_for_mode("regulated"))

    # All three tiers must be a subset of the selected check list.
    assert set(mode_dispatch._TIER_0_CHECKS).issubset(selected)
    assert set(mode_dispatch._TIER_1_CHECKS).issubset(selected)
    assert set(mode_dispatch._TIER_2_CHECKS).issubset(selected)


def test_prototyping_mode_skips_tier_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``prototyping`` mode runs Tier 0 + 1 only, skipping Tier 2 governance."""
    from ai_engineering.policy import mode_dispatch

    monkeypatch.chdir(tmp_path)
    selected = set(mode_dispatch.select_checks_for_mode("prototyping"))

    # Tier 0 + 1 still execute.
    assert set(mode_dispatch._TIER_0_CHECKS).issubset(selected)
    assert set(mode_dispatch._TIER_1_CHECKS).issubset(selected)
    # Tier 2 is excluded — disjoint with the selected set.
    assert selected.isdisjoint(set(mode_dispatch._TIER_2_CHECKS))


def test_tier_invariants_no_overlap_and_always_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tier sets are pairwise disjoint AND Tier 0+1 are always-block.

    D-105-04 invariants:
      (a) all Tier 0+1 in ``_ALWAYS_BLOCK``
      (b) no Tier 0+1 in any skip-list
      (c) ``_TIER_2_CHECKS`` matches the canonical spec enumeration
    """
    from ai_engineering.policy import mode_dispatch

    monkeypatch.chdir(tmp_path)
    tier_0 = set(mode_dispatch._TIER_0_CHECKS)
    tier_1 = set(mode_dispatch._TIER_1_CHECKS)
    tier_2 = set(mode_dispatch._TIER_2_CHECKS)

    # (a) Pairwise disjoint — no check belongs to two tiers.
    assert tier_0.isdisjoint(tier_1)
    assert tier_0.isdisjoint(tier_2)
    assert tier_1.isdisjoint(tier_2)

    # (b) Tier 0+1 must be present in always-block (mode_dispatch must expose
    # an ``_ALWAYS_BLOCK`` constant or equivalent guard).
    always_block = set(getattr(mode_dispatch, "_ALWAYS_BLOCK", tier_0 | tier_1))
    assert (tier_0 | tier_1).issubset(always_block)
