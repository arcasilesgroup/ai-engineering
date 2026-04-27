"""RED skeleton for spec-105 Phase 5 - prototyping mode wall-clock speedup.

Covers G-3: ``manifest.yml.gates.mode: prototyping`` reduces wall-clock of
``ai-eng gate run`` >=40% over regulated baseline. Comparison protocol:
5-run median wall-clock per mode, sigma <=15% of mean for validity,
assertion ``prototyping_p50_ms <= 0.6 * regulated_p50_ms``.

Status: RED (mode_dispatch.py + gates.mode field land in Phase 5).
Marker: ``pytest.mark.spec_105_red`` -- excluded by default CI run;
will be unmarked in Phase 5 (T-5.19).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.spec_105_red, pytest.mark.perf]


def test_prototyping_mode_p50_at_most_60_percent_of_regulated() -> None:
    """G-3 perf assertion -- prototyping p50 <= 0.6 * regulated p50 wall-clock."""
    from ai_engineering.policy import mode_dispatch

    assert mode_dispatch is not None  # placeholder usage
    pytest.fail("Phase 5 RED -- perf harness lands in T-5.18")
