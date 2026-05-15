"""``/ai-build --no-hitl`` unattended-mode contract — spec-134 sub-003 T-3.1.

Asserts the published surface (SKILL.md + ``handlers/no-hitl.md``) declares
the no-HITL contract from D-134-03:

* (a) ``--no-hitl`` is documented in ``ai-build/SKILL.md`` (argument-hint,
  Process step, and Handler Dispatch Table row).
* (b) The handler declares the single-concern gate (heading-count + absent
  autopilot manifest signals).
* (c) The handler references ``EXIT_STACK_DRIFT`` / exit ``78`` and the
  structured ``Reason / Detected / Recovery / Then retry`` envelope.
* (d) The handler names all three audit emitters:
  ``emit_build_event(mode="no_hitl_entry")``,
  ``emit_build_event(mode="no_hitl_blocker")``,
  ``emit_build_event(mode="no_hitl_complete")``.
* (e) The handler prohibits auto-retry explicitly and the Procedure section
  is free of ``retry`` action verbs.

All five cases run as document-assertions (read SKILL.md / handler body,
substring + regex match) — the surface is the contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]

_SKILL_MD = _REPO_ROOT / ".claude" / "skills" / "ai-build" / "SKILL.md"
_HANDLER_MD = _REPO_ROOT / ".claude" / "skills" / "ai-build" / "handlers" / "no-hitl.md"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing file: {path}"
    return path.read_text(encoding="utf-8")


@pytest.mark.unit
def test_no_hitl_flag_documented_in_skill() -> None:
    """SKILL.md surfaces ``--no-hitl`` and routes to ``handlers/no-hitl.md``."""
    body = _read(_SKILL_MD)
    assert "--no-hitl" in body, "ai-build SKILL.md must document --no-hitl flag"
    assert "handlers/no-hitl.md" in body, "ai-build SKILL.md must route to handlers/no-hitl.md"
    # Handler Dispatch Table row presence (markdown table cell).
    assert re.search(r"\|\s*No-HITL\s*\|", body), (
        "ai-build SKILL.md Handler Dispatch Table must include a No-HITL row"
    )


@pytest.mark.unit
def test_no_hitl_handler_declares_single_concern_gate() -> None:
    """Handler names the heading-count + autopilot-manifest absence gate."""
    body = _read(_HANDLER_MD)
    # Heading-count signal: must reference counting ``## Task Group`` or
    # ``### Phase`` headings and refusing when >1.
    assert "## Task Group" in body, (
        "no-hitl handler must reference `## Task Group` heading count signal"
    )
    assert "### Phase" in body, "no-hitl handler must reference `### Phase` heading count signal"
    # Autopilot manifest absence signal.
    assert ".ai-engineering/runtime/autopilot/manifest.md" in body, (
        "no-hitl handler must reference autopilot manifest path as a refusal signal"
    )
    assert "multi-concern" in body.lower(), (
        "no-hitl handler must explicitly mention multi-concern refusal"
    )


@pytest.mark.unit
def test_no_hitl_handler_declares_exit_78_on_blocker() -> None:
    """Handler references EXIT_STACK_DRIFT/78 and the structured envelope."""
    body = _read(_HANDLER_MD)
    assert "EXIT_STACK_DRIFT" in body, "no-hitl handler must reference EXIT_STACK_DRIFT constant"
    assert "78" in body, "no-hitl handler must reference exit code 78"
    # Structured envelope fields per D-133-23/24 + D-134-03 overload.
    for field in ("Reason:", "Detected:", "Recovery:", "Then retry:"):
        assert field in body, f"no-hitl handler must declare structured envelope field {field!r}"


@pytest.mark.unit
def test_no_hitl_handler_emits_three_audit_events() -> None:
    """Handler names all three emit_build_event mode invocations."""
    body = _read(_HANDLER_MD)
    expected_modes = (
        'emit_build_event(mode="no_hitl_entry")',
        'emit_build_event(mode="no_hitl_blocker")',
        'emit_build_event(mode="no_hitl_complete")',
    )
    for invocation in expected_modes:
        assert invocation in body, f"no-hitl handler must name audit emitter call {invocation!r}"


@pytest.mark.unit
def test_no_hitl_handler_prohibits_auto_retry() -> None:
    """Handler declares ``no auto-retry`` and Procedure section is retry-free."""
    body = _read(_HANDLER_MD)
    assert "no auto-retry" in body.lower(), "no-hitl handler must explicitly prohibit auto-retry"
    # Procedure section must not contain retry action verbs (case-insensitive).
    # Locate the ``## Procedure`` section and stop at the next ``## `` header.
    procedure_match = re.search(
        r"(?s)^## Procedure\s*\n(?P<body>.*?)(?=^## )",
        body,
        flags=re.MULTILINE,
    )
    assert procedure_match is not None, (
        "no-hitl handler must contain a top-level `## Procedure` section"
    )
    procedure_body = procedure_match.group("body")
    # Forbidden action verbs in Procedure (these would imply an auto-retry
    # loop). Allow ``retry`` only in the structured envelope's ``Then retry:``
    # header which lives in a sibling section (Exit Envelope) — not Procedure.
    forbidden = re.search(r"\bretry\b|\bretrie[ds]\b|\bretrying\b", procedure_body, re.IGNORECASE)
    assert forbidden is None, (
        "no-hitl handler Procedure section must not contain retry action verbs; "
        f"matched {forbidden.group(0)!r} at offset {forbidden.start()}"
    )
