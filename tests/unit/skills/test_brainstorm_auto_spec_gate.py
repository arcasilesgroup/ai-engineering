"""``/ai-brainstorm`` auto-spec gate — spec-134 sub-004 T-4.1 (RED).

Asserts the published surface + Python helper for the auto-spec gate
declared in D-134-04:

* (a) Hard triggers (one per vector) short-circuit any diff to the full
  interrogation route, regardless of threshold counts:
  ``public_api``, ``state_or_schema``, ``new_dependency``,
  ``security_surface``.
* (b) A trivial diff (≤ thresholds, no hard triggers) routes to the
  condensed-spec path.
* (c) ``gates.mode = regulated`` substitutes ``regulated_overrides``
  over the prototyping ``thresholds`` map — a diff that passes in
  prototyping may flip to ``full`` under regulated.
* (d) ``AutoSpecGateConfig(enabled=False)`` is the mandatory opt-out
  knob: every call returns ``route='full'``.
* (e) ``SKILL.md`` invokes the gate (``0b. Auto-spec gate`` or
  ``auto-spec-gate``) BEFORE the first reference to
  ``handlers/interrogate.md`` and AFTER ``--consolidate-spec``. The
  ordering guards the structural workflow change.

Cases (a)-(d) exercise the pure helper
:func:`ai_engineering.brainstorm.auto_spec_gate.classify_diff`; case
(e) reads the canonical SKILL.md and asserts marker ordering.

§10.5 TDD — these tests MUST fail before any production code lands.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.brainstorm.auto_spec_gate import (
    AutoSpecGateConfig,
    GateDecision,
    classify_diff,
)
from ai_engineering.config.manifest import (
    AutoSpecGateHardTriggers,
    AutoSpecGateThresholds,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRAINSTORM_SKILL_MD = _REPO_ROOT / ".claude" / "skills" / "ai-brainstorm" / "SKILL.md"


def _default_config() -> AutoSpecGateConfig:
    """Build a fresh gate config matching framework defaults."""
    return AutoSpecGateConfig(
        enabled=True,
        thresholds=AutoSpecGateThresholds(files=3, loc=50, cross_module=1),
        hard_triggers=AutoSpecGateHardTriggers(
            public_api=True,
            state_or_schema=True,
            new_dependency=True,
            security_surface=True,
        ),
        regulated_overrides=AutoSpecGateThresholds(files=1, loc=20, cross_module=1),
    )


# ---------------------------------------------------------------------------
# (a) Hard-trigger short-circuit — one parametric case per vector.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_hard_trigger_public_api_routes_to_full() -> None:
    """Changes touching public-API surfaces flip to full interrogation."""
    decision = classify_diff(
        files=["src/ai_engineering/__init__.py"],
        diff_text=" 1 file changed, 1 insertion(+)\n",
        config=_default_config(),
        regulated=False,
    )
    assert isinstance(decision, GateDecision)
    assert decision.route == "full"
    assert "public_api" in decision.triggers


@pytest.mark.unit
def test_hard_trigger_state_or_schema_routes_to_full() -> None:
    """Changes under state/schema paths flip to full interrogation."""
    decision = classify_diff(
        files=[".ai-engineering/schemas/manifest.schema.json"],
        diff_text=" 1 file changed, 2 insertions(+)\n",
        config=_default_config(),
        regulated=False,
    )
    assert decision.route == "full"
    assert "state_or_schema" in decision.triggers


@pytest.mark.unit
def test_hard_trigger_new_dependency_routes_to_full() -> None:
    """Added dependency lines in pyproject/package.json flip to full."""
    diff_text = (
        "diff --git a/pyproject.toml b/pyproject.toml\n"
        "+++ b/pyproject.toml\n"
        "@@ -10,6 +10,7 @@\n"
        " [project]\n"
        " dependencies = [\n"
        '+    "httpx>=0.27",\n'
        " ]\n"
        " 1 file changed, 1 insertion(+)\n"
    )
    decision = classify_diff(
        files=["pyproject.toml"],
        diff_text=diff_text,
        config=_default_config(),
        regulated=False,
    )
    assert decision.route == "full"
    assert "new_dependency" in decision.triggers


@pytest.mark.unit
def test_hard_trigger_security_surface_routes_to_full() -> None:
    """Changes under security surfaces flip to full interrogation."""
    decision = classify_diff(
        files=[".ai-engineering/scripts/hooks/pre_commit.py"],
        diff_text=" 1 file changed, 3 insertions(+)\n",
        config=_default_config(),
        regulated=False,
    )
    assert decision.route == "full"
    assert "security_surface" in decision.triggers


# ---------------------------------------------------------------------------
# (b) Condensed-spec path — trivial diff with no hard triggers.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_trivial_diff_routes_to_condensed() -> None:
    """A single-file, low-LoC diff with no hard triggers is condensed."""
    decision = classify_diff(
        files=["docs/getting-started.md"],
        diff_text=" 1 file changed, 5 insertions(+), 0 deletions(-)\n",
        config=_default_config(),
        regulated=False,
    )
    assert decision.route == "condensed"
    assert decision.triggers == []


# ---------------------------------------------------------------------------
# (c) Regulated mode tightens thresholds.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_regulated_mode_tightens_thresholds() -> None:
    """Same diff that passes prototyping flips to full under regulated."""
    cfg = _default_config()
    # Two files, no hard triggers — passes prototyping (files threshold = 3)
    # but fails regulated (files threshold = 1).
    files = ["docs/getting-started.md", "README.md"]
    diff_text = " 2 files changed, 4 insertions(+), 0 deletions(-)\n"

    prototyping_decision = classify_diff(
        files=files,
        diff_text=diff_text,
        config=cfg,
        regulated=False,
    )
    assert prototyping_decision.route == "condensed"

    regulated_decision = classify_diff(
        files=files,
        diff_text=diff_text,
        config=cfg,
        regulated=True,
    )
    assert regulated_decision.route == "full"


# ---------------------------------------------------------------------------
# (d) Opt-out knob.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_opt_out_knob_short_circuits_to_full() -> None:
    """``enabled=False`` is the mandatory opt-out path."""
    cfg = AutoSpecGateConfig(
        enabled=False,
        thresholds=AutoSpecGateThresholds(),
        hard_triggers=AutoSpecGateHardTriggers(),
        regulated_overrides=AutoSpecGateThresholds(files=1, loc=20, cross_module=1),
    )
    decision = classify_diff(
        files=["docs/getting-started.md"],
        diff_text=" 1 file changed, 1 insertion(+)\n",
        config=cfg,
        regulated=False,
    )
    assert decision.route == "full"


# ---------------------------------------------------------------------------
# (e) SKILL.md ordering: gate fires BEFORE interrogation.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_skill_md_invokes_gate_before_interrogation() -> None:
    """SKILL.md must invoke the auto-spec gate before interrogate.md."""
    body = _BRAINSTORM_SKILL_MD.read_text(encoding="utf-8")

    # Gate marker presence — accept either the step heading or the handler
    # path so the test pins meaning, not exact wording.
    gate_markers = ("0b. Auto-spec gate", "auto-spec-gate")
    gate_offsets = [body.find(m) for m in gate_markers if body.find(m) != -1]
    assert gate_offsets, (
        "ai-brainstorm SKILL.md must reference the auto-spec gate "
        "(either `0b. Auto-spec gate` or `auto-spec-gate`)"
    )
    gate_offset = min(gate_offsets)

    # Interrogation marker (downstream — must come after the gate).
    interrogate_offset = body.find("handlers/interrogate.md")
    assert interrogate_offset != -1, (
        "ai-brainstorm SKILL.md must still reference `handlers/interrogate.md`"
    )
    assert gate_offset < interrogate_offset, (
        "auto-spec gate must be invoked BEFORE interrogate.md "
        f"(gate at {gate_offset}, interrogate at {interrogate_offset})"
    )

    # Consolidate-spec fast-path stays at the very front (Step 0a).
    consolidate_offset = body.find("--consolidate-spec")
    assert consolidate_offset != -1, (
        "ai-brainstorm SKILL.md must still reference --consolidate-spec"
    )
    assert consolidate_offset < gate_offset, (
        "auto-spec gate must run AFTER the --consolidate-spec fast-path "
        f"(consolidate at {consolidate_offset}, gate at {gate_offset})"
    )
