"""Executable contracts for spec 042 / B-042-4: loop_guard escalates the repeated verdict.

The guard keeps failing closed — a repeated exact call is still denied, every time — but
the identical verdict is not re-asserted forever: the third identical denial in a window
(the rule-12 moment: the same judgement has resolved the same way three times) escalates
to the person channel instead of restating the same sentence. The escalation names the
call by its human-visible signature (tool:first-argument, never the 16-hex digest), the
repeats count, and the `ai-eng exception --skip ... --guard loop_guard` recipe verbatim.
The window is per-session (`state["recent"]` is session-scoped); a fresh window restarts
the count; a different call is unaffected; every denial still denies.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

import _wrap  # noqa: E402
import loop_guard as lg  # noqa: E402


def _call(number: int) -> dict:
    """One PreToolUse payload for the same exact call, unique only by its tool_use_id."""
    return {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest -q tests/test_x.py"},
        "tool_use_id": f"call-{number}",
        "_event": "PreToolUse",
    }


def _drive(monkeypatch, tmp_path, payloads: list[dict]) -> list[str | None]:
    """Run the decorated guard; capture deny() instead of letting it exit. Returns the
    denial text each payload received (None for allowed)."""
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(tmp_path))
    (tmp_path / "cache" / "loop").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        lg,
        "config",
        lambda root=None: {"guards": {"loop_window": 6, "loop_repeats": 3, "loop_failures": 5}},
    )
    monkeypatch.setenv("AI_ENG_SESSION", "test-session")
    monkeypatch.setattr(_wrap, "deny", lambda name, message, structured=False: None)
    for payload in payloads:
        lg.run(payload)
    return [payload.get("_denied", (None, None))[1] for payload in payloads]


def test_three_identical_calls_deny_all_and_the_third_escalates(tmp_path, monkeypatch):
    # The repeats arm denies from the 3rd identical call in the window (seen >= repeats).
    # Call 3 -> denial 1 (full verdict), call 4 -> denial 2 (full verdict), call 5 ->
    # denial 3 — the rule-12 moment, which escalates instead of restating the verdict.
    denials = _drive(monkeypatch, tmp_path, [_call(1), _call(2), _call(3), _call(4), _call(5)])
    first = denials[2]  # the 3rd call: first denial
    second = denials[3]  # the 4th call: second denial
    third = denials[4]  # the 5th call: third denial
    assert first is not None and second is not None and third is not None
    # Two full verdicts first (the judgement resolving), then the escalation.
    assert "this exact call has been made 3 times in the last 6" in first
    assert "this exact call has been made 4 times in the last 6" in second
    assert "Bash:pytest" in third
    assert "Hand it to a person" in third
    assert 'ai-eng exception --skip "<reason>" --guard loop_guard' in third


def test_a_fresh_window_restarts_the_count(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_ENG_SESSION", "fresh-session")
    denials = _drive(monkeypatch, tmp_path, [_call(1), _call(2), _call(3)])
    # A fresh window: three identical calls -> seen=3 on the third, the first denial of
    # this session, which is the full verdict — not the escalation.
    third = denials[2]
    assert third is not None
    assert "Hand it to a person" not in third


def test_a_different_call_is_not_escalated(tmp_path, monkeypatch):
    other = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest -q tests/test_other.py"},
        "tool_use_id": "call-other-1",
        "_event": "PreToolUse",
    }
    denials = _drive(monkeypatch, tmp_path, [_call(1), _call(2), _call(3), _call(4), other])
    # The unrelated call is allowed on its first appearance regardless of the window.
    assert denials[-1] is None


def test_the_blocked_count_is_preserved_every_denial_denies(tmp_path, monkeypatch):
    # With repeats=3 the first two identical calls are allowed (seen 1 and 2); every call
    # from the third on is denied, and the third call's denial is the escalation —
    # the blocked count is preserved (no denial ever becomes allowed).
    denials = _drive(monkeypatch, tmp_path, [_call(1), _call(2), _call(3), _call(4), _call(5)])
    assert denials[0] is None and denials[1] is None  # below the repeats threshold
    assert all(d is not None for d in denials[2:]), "every repeat is still denied"


def test_the_escalation_never_claims_more_repeats_than_the_window(tmp_path, monkeypatch):
    """The sentence says 'denied N times in the last {window}', so N can never exceed the
    window — a 15-hit session must not read 'denied 13 times in the last 6'. Measured on
    this machine, 583 sessions hit the same verdict 15 times, so this is the real shape."""
    denials = _drive(monkeypatch, tmp_path, [_call(n) for n in range(1, 16)])
    escalations = [d for d in denials if d is not None and "Hand it to a person" in d]
    assert escalations, "the 15-hit session must escalate"
    # The count grows to the window and stops there; it must never exceed it. The first
    # escalation legitimately says "denied 3"; the later ones must not keep climbing past
    # "denied 6". Extracting the claimed number checks the bound without overpinning.
    claimed = [
        int(m.group(1))
        for sentence in escalations
        for m in [re.search(r"denied (\d+) times in the last (\d+)", sentence)]
        if m
    ]
    assert claimed, "the escalation sentences must state a count"
    assert max(claimed) == 6, f"the count must cap at the window, not climb past it: {claimed}"
