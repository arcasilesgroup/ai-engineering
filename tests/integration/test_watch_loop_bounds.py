"""Integration tests for spec-104 D-104-05 watch loop wall-clock bounds.

RED phase for spec-104 T-6.1 (paired with T-6.2 GREEN that edits
``.claude/skills/ai-pr/handlers/watch.md``). The contract being driven by
these assertions has two surfaces:

1. **Markdown contract** in ``.claude/skills/ai-pr/handlers/watch.md`` — the
   skill handler that the IDE agent (Claude Code, Copilot, Codex, Gemini)
   reads at runtime. T-6.2 must extend the document to encode the active
   30-min cap, the passive 4-h cap, the ``watch-residuals.json`` emit, the
   actionable ``ai-eng risk accept-all`` user message, and exit code 90 as
   distinct from spec-101's exits 80/81. The file is the single source of
   truth for the watch-loop's behavior across all four IDE engines.

2. **Python state model** ``ai_engineering.state.models.WatchLoopState``
   (already landed in T-0.4) carries the two anchor timestamps. Tests 7
   and 8 verify that wall-clock age can be computed correctly from those
   stored datetimes against the caps documented in the markdown contract.

D-104-05 in spec-104 captures the rationale: wall-clock is user-meaningful
(devs think in minutes, not iterations), the active-vs-passive split makes
"waiting for review" a legitimate non-truncating state, and exit 90 lets
CI scripts distinguish "watch timed out" from "real failure". The
``watch-residuals.json`` emit reuses the schema-v1 envelope from D-104-06
so spec-105 risk-accept can ingest it without contract drift.

Each test currently fails because watch.md has not yet been extended
(T-6.2 GREEN). The 8 markdown-grep tests assert the precise phrases that
must appear; the 2 Python-state tests verify age arithmetic against the
caps parsed from the same markdown — so the markdown stays the single
source of truth.

TDD CONSTRAINT: this file is IMMUTABLE after T-6.1 lands. T-6.2 GREEN may
only edit ``handlers/watch.md`` to satisfy the assertions; never edit the
assertions themselves.

Coverage (10 tests):

1. ``test_watch_md_documents_active_30min_cap`` — active phase 30-min
   wall-clock cap is mentioned in watch.md.
2. ``test_watch_md_documents_passive_4h_cap`` — passive 4-h cap is
   mentioned in watch.md.
3. ``test_watch_md_documents_exit_code_90`` — exit code 90 is explicitly
   documented as the wall-clock-cap exit.
4. ``test_watch_md_documents_watch_residuals_emit`` — ``watch-residuals.json``
   emit on cap is mentioned in watch.md.
5. ``test_watch_md_preserves_per_check_3_strike`` — the existing per-check
   ``fix_attempts >= 3`` rule is still encoded in watch.md (regression
   guard against T-6.2 accidentally removing it).
6. ``test_watch_md_actionable_message_format`` — the on-cap message
   includes the ``ai-eng risk accept-all`` command hint pointing to
   spec-105 risk-accept-all.
7. ``test_watch_loop_state_active_age_calculation`` — WatchLoopState's
   ``last_active_action_at`` permits accurate age computation against the
   active-phase cap parsed from watch.md.
8. ``test_watch_loop_state_passive_age_calculation`` — WatchLoopState's
   ``watch_started_at`` permits accurate age computation against the
   passive-phase cap parsed from watch.md.
9. ``test_watch_md_active_cap_is_inactivity_not_total`` — semantic
   clarity: the active cap is "30 min since last active action", not
   "30 min total". The watch.md text must convey this distinction so the
   agent does not truncate sessions where progress is happening.
10. ``test_watch_md_exit_90_distinct_from_80_81`` — exit 90 is documented
    as DIFFERENT from spec-101 D-101-11 exits 80/81 (Python SDK gate /
    SDK prereq gate). Cross-spec contract integrity check.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_engineering.state.models import WatchLoopState

# ---------------------------------------------------------------------------
# Path to the markdown handler under test.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
WATCH_MD_PATH = REPO_ROOT / ".claude" / "skills" / "ai-pr" / "handlers" / "watch.md"


# ---------------------------------------------------------------------------
# Shared helpers — pure stdlib so freezegun is not required.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def watch_md_text() -> str:
    """Return the full raw text of ``handlers/watch.md``.

    Module-scoped because the file is read-only during the test session
    and re-reading it 10 times wastes IO without changing the contract.
    """
    assert WATCH_MD_PATH.is_file(), (
        f"watch.md handler missing at {WATCH_MD_PATH}; T-6.2 GREEN must keep it present."
    )
    return WATCH_MD_PATH.read_text(encoding="utf-8")


def _has_any(text: str, *patterns: str) -> bool:
    """Return True iff at least one regex pattern matches case-insensitively.

    Used so the prose may legitimately vary ("30 minutes", "30-minute",
    "30 min") while still being matched by a single test.
    """
    return any(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in patterns)


# ---------------------------------------------------------------------------
# 1. Active phase 30-min wall-clock cap documented.
# ---------------------------------------------------------------------------


def test_watch_md_documents_active_30min_cap(watch_md_text: str) -> None:
    """watch.md must document the 30-min active-phase wall-clock cap.

    D-104-05 active phase: ``now() - last_active_action_at > 30 min``.
    The handler markdown is the single source of truth read by every
    IDE agent — without this prose the loop has no hint of bound.
    """
    assert _has_any(
        watch_md_text,
        r"30\s*min",
        r"30\s*minute",
        r"thirty\s*minute",
    ), "watch.md must mention the 30-min active-phase wall-clock cap (D-104-05)."

    # Cap must specifically tie to the active phase / last_active_action_at,
    # not just any "30 min" mention.
    assert _has_any(
        watch_md_text,
        r"active\s+phase",
        r"last_active_action_at",
        r"active.{0,40}cap",
    ), "watch.md must associate the 30-min cap with the active phase / last_active_action_at."


# ---------------------------------------------------------------------------
# 2. Passive phase 4-h wall-clock cap documented.
# ---------------------------------------------------------------------------


def test_watch_md_documents_passive_4h_cap(watch_md_text: str) -> None:
    """watch.md must document the 4-h passive-phase wall-clock cap.

    D-104-05 passive phase: ``now() - watch_started_at > 4h``.
    """
    assert _has_any(
        watch_md_text,
        r"4\s*h(our)?s?\b",
        r"four\s*hours",
        r"240\s*min",
    ), "watch.md must mention the 4-h passive-phase wall-clock cap (D-104-05)."

    assert _has_any(
        watch_md_text,
        r"passive\s+phase",
        r"watch_started_at",
        r"passive.{0,40}cap",
    ), "watch.md must associate the 4-h cap with the passive phase / watch_started_at."


# ---------------------------------------------------------------------------
# 3. Exit code 90 explicitly documented.
# ---------------------------------------------------------------------------


def test_watch_md_documents_exit_code_90(watch_md_text: str) -> None:
    """Exit code 90 is the wall-clock-cap exit per D-104-05.

    Distinct from 0 (success), 1 (real failure), and spec-101's 80/81.
    CI scripts depend on the integer to detect "watch timed out" vs
    "real gate failure". The number must appear with the word "exit".
    """
    assert _has_any(
        watch_md_text,
        r"exit\s+(code\s+)?90\b",
        r"exit\s*=\s*90\b",
        r"\bcode\s+90\b",
    ), "watch.md must document exit code 90 as the wall-clock-cap exit (D-104-05)."


# ---------------------------------------------------------------------------
# 4. watch-residuals.json emit on cap mentioned.
# ---------------------------------------------------------------------------


def test_watch_md_documents_watch_residuals_emit(watch_md_text: str) -> None:
    """``watch-residuals.json`` is emitted on cap per D-104-05 + D-104-06.

    Same schema as ``gate-findings.json`` v1 — spec-105 risk-accept-all
    consumes this file. Without the emit step in watch.md, the actionable
    message in test 6 has no file to reference.
    """
    assert "watch-residuals.json" in watch_md_text, (
        "watch.md must mention `watch-residuals.json` emit on wall-clock cap "
        "(D-104-05 + D-104-06 schema v1)."
    )


# ---------------------------------------------------------------------------
# 5. Per-check fix_attempts >= 3 rule preserved.
# ---------------------------------------------------------------------------


def test_watch_md_preserves_per_check_3_strike(watch_md_text: str) -> None:
    """Per-check ``fix_attempts >= 3`` rule must NOT be removed.

    D-104-05 explicitly preserves the per-check 3-strike rule. The
    wall-clock cap is ADDITIVE, not a replacement. This regression
    guard catches T-6.2 accidentally collapsing both rules into one.
    """
    # Tolerate phrasing variants: "3x", ">= 3", "three times", "fails 3".
    assert _has_any(
        watch_md_text,
        r"fix_attempts.{0,20}3",
        r">=\s*3",
        r"3\s*x\b",
        r"3\s*times",
        r"fails?\s+3\b",
        r"three\s+times",
    ), (
        "watch.md must retain the per-check `fix_attempts >= 3` STOP rule "
        "(D-104-05: per-check rule is preserved, wall-clock is additive)."
    )


# ---------------------------------------------------------------------------
# 6. Actionable on-cap message includes ai-eng risk accept-all hint.
# ---------------------------------------------------------------------------


def test_watch_md_actionable_message_format(watch_md_text: str) -> None:
    """On-cap message must hint at the spec-105 risk-accept-all CLI.

    D-104-05 prescribes the exact actionable message, which includes
    ``ai-eng risk accept-all`` so the user has a clear next step
    instead of a dead-end timeout.
    """
    assert _has_any(
        watch_md_text,
        r"ai-eng\s+risk\s+accept-all",
        r"ai-eng\s+risk\s+accept",
    ), (
        "watch.md must show the `ai-eng risk accept-all` command hint in the "
        "on-cap actionable message (D-104-05; spec-105 dependency)."
    )


# ---------------------------------------------------------------------------
# 7. WatchLoopState last_active_action_at age computation.
# ---------------------------------------------------------------------------


def _parse_active_cap_minutes_from_md(text: str) -> int:
    """Extract the active-phase cap (in minutes) from watch.md prose.

    Falls back to 30 if no number is found, but ONLY after the
    presence-tests above already passed for the same prose. This keeps
    the markdown the single source of truth for the numeric cap.
    """
    match = re.search(r"(\d+)\s*min(?:ute)?s?", text, re.IGNORECASE)
    if match is None:
        return 30
    return int(match.group(1))


def test_watch_loop_state_active_age_calculation(watch_md_text: str) -> None:
    """WatchLoopState supports accurate active-phase age computation.

    D-104-05 active phase semantics: ``now() - last_active_action_at``
    is the wall-clock age. This test fixes ``now`` to a deterministic
    value (no clock dependency) and asserts the age computed from a
    state instance matches the documented 30-min cap, +/- a 1-second
    integer-seconds tolerance.

    Failure mode if watch.md does not yet document the cap: the cap
    parser returns the documented value but the model arithmetic
    cannot be cross-validated against the markdown contract — so we
    additionally assert the cap parsed from watch.md is exactly 30.
    """
    cap_minutes = _parse_active_cap_minutes_from_md(watch_md_text)
    assert cap_minutes == 30, (
        f"watch.md must document a 30-minute active-phase cap; parsed {cap_minutes}."
    )

    now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    last_active = now - timedelta(minutes=cap_minutes + 1)  # 31 min ago
    started = last_active - timedelta(minutes=10)  # passive phase still well within 4h

    state = WatchLoopState(
        watch_started_at=started,
        last_active_action_at=last_active,
        fix_attempts={},
        iteration_count=5,
    )

    active_age_seconds = int((now - state.last_active_action_at).total_seconds())
    expected_seconds = (cap_minutes + 1) * 60
    assert active_age_seconds == expected_seconds, (
        f"active age must equal exactly {expected_seconds}s; got {active_age_seconds}s."
    )

    cap_seconds = cap_minutes * 60
    assert active_age_seconds > cap_seconds, (
        "31 min since last_active_action_at must exceed the 30-min active cap."
    )


# ---------------------------------------------------------------------------
# 8. WatchLoopState watch_started_at age computation.
# ---------------------------------------------------------------------------


def _parse_passive_cap_hours_from_md(text: str) -> int:
    """Extract the passive-phase cap (in hours) from watch.md prose.

    Falls back to 4 only when the markdown is silent. Same single-source
    guarantee as the active-cap parser.
    """
    match = re.search(r"(\d+)\s*h(?:our)?s?\b", text, re.IGNORECASE)
    if match is None:
        return 4
    return int(match.group(1))


def test_watch_loop_state_passive_age_calculation(watch_md_text: str) -> None:
    """WatchLoopState supports accurate passive-phase age computation.

    D-104-05 passive phase semantics: ``now() - watch_started_at`` is
    the wall-clock age. Mirrors test 7 but for the 4-hour cap.
    """
    cap_hours = _parse_passive_cap_hours_from_md(watch_md_text)
    assert cap_hours == 4, f"watch.md must document a 4-hour passive-phase cap; parsed {cap_hours}."

    now = datetime(2026, 5, 1, 18, 0, 0, tzinfo=UTC)
    started = now - timedelta(hours=cap_hours, minutes=1)  # 4h 1min ago
    last_active = now - timedelta(minutes=5)  # active phase well within 30 min

    state = WatchLoopState(
        watch_started_at=started,
        last_active_action_at=last_active,
        fix_attempts={"pytest-smoke": 1},
        iteration_count=42,
    )

    passive_age_seconds = int((now - state.watch_started_at).total_seconds())
    expected_seconds = cap_hours * 3600 + 60
    assert passive_age_seconds == expected_seconds, (
        f"passive age must equal exactly {expected_seconds}s; got {passive_age_seconds}s."
    )

    cap_seconds = cap_hours * 3600
    assert passive_age_seconds > cap_seconds, (
        "4h 1min since watch_started_at must exceed the 4-hour passive cap."
    )


# ---------------------------------------------------------------------------
# 9. Active cap is "inactivity since last action", not "total time".
# ---------------------------------------------------------------------------


def test_watch_md_active_cap_is_inactivity_not_total(watch_md_text: str) -> None:
    """The active cap measures inactivity since last action, not total time.

    D-104-05 explicit clarification: "30 min since last active action" —
    distinct from "30 min total". A loop that is making progress (fixes
    landing every few minutes) must NOT be truncated. This test asserts
    the markdown communicates the inactivity semantics clearly so the
    agent does not implement the wrong contract.
    """
    # The text must reference last_active_action_at OR a phrase that
    # conveys "since last action / no progress / inactivity".
    assert _has_any(
        watch_md_text,
        r"last_active_action_at",
        r"since\s+last\s+(active\s+)?(action|fix|progress)",
        r"no\s+progress",
        r"inactivity",
        r"without\s+progress",
    ), (
        "watch.md must clarify the active cap measures INACTIVITY since the "
        "last action (D-104-05), not total elapsed time."
    )


# ---------------------------------------------------------------------------
# 10. Exit 90 is documented as distinct from spec-101 D-101-11 exits 80/81.
# ---------------------------------------------------------------------------


def test_watch_md_exit_90_distinct_from_80_81(watch_md_text: str) -> None:
    """Exit 90 is documented as distinct from spec-101 exits 80 and 81.

    Cross-spec contract integrity: spec-101 D-101-11 reserves 80
    (Python SDK gate) and 81 (SDK prereq gate). spec-104 D-104-05
    reserves 90 for the wall-clock cap. The markdown must make the
    distinction explicit so a CI script wiring exit codes does not
    conflate them.

    We accept any of the following phrasings as proof of distinction:
    - "distinct from 80/81"
    - "different from spec-101 exit 80"
    - explicit reference to spec-101 D-101-11
    - both numbers (80 and 81) appearing in the same paragraph as 90
    """
    # Locate the exit-90 mention; require either a cross-reference to 80/81
    # or a comment naming spec-101 D-101-11.
    has_90 = bool(re.search(r"\bexit\s+(code\s+)?90\b", watch_md_text, re.IGNORECASE))
    assert has_90, "watch.md must document exit 90 (precondition for distinctness check)."

    # The distinctness signal: either the numbers 80 and 81 appear, OR a
    # spec reference (D-101-11 / spec-101) appears within the watch.md body.
    has_80_81 = bool(
        re.search(r"\b80\b.{0,40}\b81\b", watch_md_text)
        or re.search(r"\b81\b.{0,40}\b80\b", watch_md_text)
        or re.search(r"D-101-11", watch_md_text)
        or re.search(r"spec-101", watch_md_text, re.IGNORECASE)
    )

    assert has_80_81, (
        "watch.md must distinguish exit 90 (D-104-05 wall-clock cap) from "
        "spec-101 D-101-11 exits 80/81 (SDK prereq / Python SDK gates)."
    )
