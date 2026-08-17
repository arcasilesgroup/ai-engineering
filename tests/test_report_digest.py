"""`EP-306`: denials counted per guard, inside a window, and both halves are load bearing.

The window was already there — `report digest --weeks N` bounds every count to the last
`7 × N` days. What was not there was the per-guard total. `by_reason` keys on the pair of
guard and reason, which is the right key for "what keeps getting stopped" and the wrong one
for "which control is doing the work": a guard that denied five calls for five different
reasons appears as five rows of one, and reads as five quiet controls rather than one busy
one. That is the opposite of what happened, in the report a person reads to decide whether
a control is still firing.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from ai_engineering import report


def event(name: str, reason: str, *, days_ago: int = 0, cls: str = "blocked") -> dict:
    when = (date.today() - timedelta(days=days_ago)).isoformat()
    return {"ts": f"{when}T12:00:00Z", "cls": cls, "name": name, "data": {"reason": reason}}


def test_one_busy_guard_is_not_reported_as_five_quiet_ones():
    """The defect, stated as the two counters disagreeing on the same events.

    Five denials by one guard for five reasons: `by_reason` has five rows of one and
    `by_guard` has one row of five. Both are true and only the second answers whether the
    control fired.
    """

    events = [event("injection_guard", f"reason {n}") for n in range(5)]

    assert sorted(report.by_reason(events, "blocked").values()) == [1, 1, 1, 1, 1]
    assert report.by_guard(events, "blocked") == {"injection_guard": 5}


def test_the_count_is_per_guard_and_not_per_call_or_per_reason():
    """Three guards, uneven, with one repeat — enough that a counter which summed wrongly,
    counted distinct reasons, or dropped duplicates would produce a different answer to
    each of the three."""

    events = [
        event("injection_guard", "a prompt injection"),
        event("injection_guard", "a prompt injection"),
        event("injection_guard", "a credential path"),
        event("no_verify_guard", "--no-verify"),
        event("loop_guard", "the same command four times"),
    ]

    assert report.by_guard(events, "blocked") == {
        "injection_guard": 3,
        "no_verify_guard": 1,
        "loop_guard": 1,
    }


def test_a_class_that_is_not_a_denial_is_not_counted_as_one():
    """`bypassed` is its own line in the report and its own question — a guard somebody
    walked past is not a guard that stopped something. Summing them here would make the
    denial count read higher than the number of calls actually denied."""

    events = [
        event("no_verify_guard", "--no-verify"),
        event("no_verify_guard", "--no-verify", cls="bypassed"),
        event("ai-eng check", "", cls="command"),
        event("chain", "", cls="error"),
    ]

    assert report.by_guard(events, "blocked") == {"no_verify_guard": 1}
    assert report.by_guard(events, "bypassed") == {"no_verify_guard": 1}


@pytest.mark.parametrize("weeks, expected", [(1, 2), (2, 3), (4, 4)])
def test_the_window_is_what_the_flag_says_and_nothing_older_is_counted(weeks, expected):
    """The other half of the requirement, and the half that would rot silently: a report
    that quietly counted everything would look identical on a young repository and would
    slowly stop meaning "this week" on an old one."""

    events = [
        event("injection_guard", "today"),
        event("injection_guard", "six days ago", days_ago=6),
        event("injection_guard", "ten days ago", days_ago=10),
        event("injection_guard", "twenty days ago", days_ago=20),
        event("injection_guard", "a year ago", days_ago=365),
    ]

    counted = report.by_guard(report.within(events, 7 * weeks), "blocked")

    assert counted["injection_guard"] == expected


def test_the_digest_prints_the_per_guard_line_and_carries_it_as_a_fact(monkeypatch, capsys):
    """It reaches the report a person actually reads, and the machine-readable envelope too.

    A counter nothing prints is the `EP-184` shape again — correct arithmetic nobody meets.
    """

    from ai_engineering import doctor

    monkeypatch.setattr(
        doctor,
        "events",
        lambda root: [
            event("injection_guard", "a credential path"),
            event("injection_guard", "a pipe to a shell"),
            event("no_verify_guard", "--no-verify", days_ago=3),
            event("loop_guard", "long ago", days_ago=400),
        ],
    )
    monkeypatch.setattr(report.paths, "repo_root", lambda: None)

    report.main(["digest"])
    printed = capsys.readouterr().out

    assert "Per guard, in the 7 days since" in printed
    assert "injection_guard 2" in printed
    assert "no_verify_guard 1" in printed
    assert "loop_guard" not in printed.split("Per guard")[1].split("\n")[0], (
        "an event outside the window was counted"
    )
