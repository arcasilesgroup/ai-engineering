"""spec-105 D-105-04 -- tier allocation invariants for ``policy/mode_dispatch.py``.

These invariants are the load-bearing safety net for the prototyping
mode: if any Tier 0+1 check were to slip into a skip-list, the whole
"prototyping never leaks" guarantee collapses.

Asserted invariants (per D-105-04):

* (a) All Tier 0 + Tier 1 checks live in ``_ALWAYS_BLOCK``.
* (b) No Tier 0 + Tier 1 check appears in any skip-list (regulated and
  prototyping check sets are supersets of always-block).
* (c) ``_TIER_2_CHECKS`` matches the canonical D-105-04 enumeration
  exactly -- additions/removals require an explicit spec amendment.
* (d) Tier sets are pairwise disjoint -- no check can belong to two
  tiers.

This test file is GREEN-on-day-one (no ``spec_105_red`` marker) so the
invariants run on every CI cycle.
"""

from __future__ import annotations

from ai_engineering.policy import mode_dispatch

# Canonical D-105-04 Tier 2 check names; must remain in lock-step with
# the spec table. Any change here requires updating spec.md too.
_CANONICAL_TIER_2: tuple[str, ...] = (
    "ai-eng-validate",
    "ai-eng-spec-verify",
    "docs-gate",
    "risk-expiry-warning",
)


def test_tier_0_and_tier_1_present_in_always_block() -> None:
    """Invariant (a): every Tier 0 + Tier 1 check appears in ``_ALWAYS_BLOCK``."""
    tier_0 = set(mode_dispatch._TIER_0_CHECKS)
    tier_1 = set(mode_dispatch._TIER_1_CHECKS)
    always_block = set(mode_dispatch._ALWAYS_BLOCK)
    assert tier_0.issubset(always_block), (
        f"Tier 0 checks not all in ALWAYS_BLOCK: missing {tier_0 - always_block}"
    )
    assert tier_1.issubset(always_block), (
        f"Tier 1 checks not all in ALWAYS_BLOCK: missing {tier_1 - always_block}"
    )


def test_no_tier_0_or_1_in_prototyping_skip_list() -> None:
    """Invariant (b): no Tier 0 or Tier 1 check is excluded by prototyping mode."""
    prototyping_selected = set(mode_dispatch.select_checks_for_mode("prototyping"))
    tier_0 = set(mode_dispatch._TIER_0_CHECKS)
    tier_1 = set(mode_dispatch._TIER_1_CHECKS)
    assert tier_0.issubset(prototyping_selected), (
        f"Prototyping mode dropped Tier 0 checks: {tier_0 - prototyping_selected}"
    )
    assert tier_1.issubset(prototyping_selected), (
        f"Prototyping mode dropped Tier 1 checks: {tier_1 - prototyping_selected}"
    )


def test_tier_2_matches_canonical_d_105_04_enumeration() -> None:
    """Invariant (c): ``_TIER_2_CHECKS`` matches the spec D-105-04 list."""
    assert tuple(mode_dispatch._TIER_2_CHECKS) == _CANONICAL_TIER_2, (
        "Tier 2 enumeration drifted from spec D-105-04. "
        f"Expected {_CANONICAL_TIER_2}, got {mode_dispatch._TIER_2_CHECKS}."
    )


def test_tier_sets_are_pairwise_disjoint() -> None:
    """Invariant (d): no check belongs to two tiers."""
    tier_0 = set(mode_dispatch._TIER_0_CHECKS)
    tier_1 = set(mode_dispatch._TIER_1_CHECKS)
    tier_2 = set(mode_dispatch._TIER_2_CHECKS)
    assert tier_0.isdisjoint(tier_1), f"Tier 0/1 overlap: {tier_0 & tier_1}"
    assert tier_0.isdisjoint(tier_2), f"Tier 0/2 overlap: {tier_0 & tier_2}"
    assert tier_1.isdisjoint(tier_2), f"Tier 1/2 overlap: {tier_1 & tier_2}"


def test_regulated_mode_includes_all_three_tiers() -> None:
    """Sanity: ``select_checks_for_mode("regulated")`` covers all three tiers."""
    selected = set(mode_dispatch.select_checks_for_mode("regulated"))
    expected = (
        set(mode_dispatch._TIER_0_CHECKS)
        | set(mode_dispatch._TIER_1_CHECKS)
        | set(mode_dispatch._TIER_2_CHECKS)
    )
    assert selected == expected, (
        f"Regulated mode mismatch. Missing: {expected - selected}, extra: {selected - expected}"
    )


def test_prototyping_mode_excludes_only_tier_2() -> None:
    """Sanity: prototyping = regulated minus Tier 2 exactly."""
    regulated = set(mode_dispatch.select_checks_for_mode("regulated"))
    prototyping = set(mode_dispatch.select_checks_for_mode("prototyping"))
    excluded = regulated - prototyping
    assert excluded == set(mode_dispatch._TIER_2_CHECKS), (
        f"Prototyping mode excluded unexpected checks. "
        f"Expected exactly Tier 2 ({set(mode_dispatch._TIER_2_CHECKS)}), got {excluded}."
    )
