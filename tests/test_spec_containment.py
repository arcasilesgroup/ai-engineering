"""Tests for spec 031 / B-031-3: spec self-containment.

A spec carries the whole job on its own — no "as discussed", no "the remaining work" — and
an evaluator can resolve a section by number without duplicating it (Loop-Engineering's
numberless-interface rule). A spec that leans on the conversation cannot be the only
interface to a builder who reads just that file.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import spec  # noqa: E402

CLEAN = """# Title

## Context and problem

Something is wrong and this is why.

## Decision

We chose the first option.

## Examples somebody can check

Given a clean spec,
When it is read,
Then it passes.
"""

LEAKED = """# Title

## Context and problem

As we discussed, the API is slow.

## Decision

The remaining work is to wire it.

## Examples somebody can check

Given a leaked spec,
When it is read,
Then it is refused.
"""

LEAKS = (
    "as we discussed",
    "as discussed",
    "the remaining work",
    "per our conversation",
    "like we said",
)


def test_a_clean_spec_passes_self_contained():
    assert spec.self_contained(CLEAN) == []


def test_a_spec_that_says_as_discussed_is_refused():
    problems = spec.self_contained(LEAKED)
    assert any("as we discussed" in p or "as discussed" in p for p in problems)


def test_section_resolves_by_position_without_copying():
    assert "# Context and problem" in spec.section(CLEAN, 1)
    assert "# Decision" in spec.section(CLEAN, 2)
    assert "# Examples somebody can check" in spec.section(CLEAN, 3)


def test_section_out_of_range_is_empty():
    assert spec.section(CLEAN, 99) == ""
