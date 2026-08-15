"""Five ways a scanner lane is INCOMPLETE, and one way it passes.

Specification 014: a missing engine, missing rules, a crash, a timeout or zero inputs each
produce INCOMPLETE with its own fixture. The point of the list is that every one of them is
a way for a lane to report nothing and be read as having found nothing — which is the
failure this whole wave is named after.

Each fixture drives a real subprocess. A lane runner tested against a stubbed runner proves
the branches; it does not prove that a missing binary raises what the code catches.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def engine(tmp_path: Path, body: str) -> tuple[str, ...]:
    """A one-file stand-in for a scanner, executed for real."""
    script = tmp_path / "engine.py"
    script.write_text(body, encoding="utf-8")
    return (sys.executable, str(script))


def test_a_lane_that_ran_and_found_nothing_is_the_only_way_to_pass(tmp_path):
    from ai_engineering import scan

    lane = scan.Lane("clean", engine(tmp_path, "raise SystemExit(0)"))
    fact = scan.run(lane, tmp_path, ["src/thing.py"])

    assert fact.status == "PASS"
    assert fact.id == "lane-clean"


def test_a_lane_that_found_something_fails_and_does_not_go_quiet(tmp_path):
    from ai_engineering import scan

    lane = scan.Lane("noisy", engine(tmp_path, "raise SystemExit(1)"))
    fact = scan.run(lane, tmp_path, ["src/thing.py"])

    assert fact.status == "FAIL"
    assert "found" in fact.detail


def test_a_missing_engine_is_incomplete_and_never_clean(tmp_path):
    """The commonest one, and the most dangerous: a lane whose binary is not installed exits
    nothing at all, and a runner that shrugged would report a clean scan of a scanner that
    never ran."""
    from ai_engineering import scan

    lane = scan.Lane("absent", (str(tmp_path / "no-such-engine"),))
    fact = scan.run(lane, tmp_path, ["src/thing.py"])

    assert fact.status == "INCOMPLETE"
    assert "LANE_ENGINE_MISSING" in fact.detail


def test_missing_rules_are_incomplete_even_when_the_engine_is_there(tmp_path):
    """An engine with no rules runs perfectly and looks for nothing. Exit zero, no findings,
    and a green that means the opposite of what it says."""
    from ai_engineering import scan

    lane = scan.Lane(
        "unruled", engine(tmp_path, "raise SystemExit(0)"), rules=tmp_path / "gone.yml"
    )
    fact = scan.run(lane, tmp_path, ["src/thing.py"])

    assert fact.status == "INCOMPLETE"
    assert "LANE_RULES_MISSING" in fact.detail


def test_a_crash_is_incomplete_and_not_a_finding(tmp_path):
    """An exit code with no defined meaning is not a verdict. Reading it as "found nothing"
    is the fail-open direction and reading it as "found something" cries wolf."""
    from ai_engineering import scan

    lane = scan.Lane("broken", engine(tmp_path, "raise SystemExit(97)"))
    fact = scan.run(lane, tmp_path, ["src/thing.py"])

    assert fact.status == "INCOMPLETE"
    assert "LANE_CRASHED" in fact.detail and "97" in fact.detail


def test_a_timeout_is_incomplete_and_the_lane_says_how_long_it_waited(tmp_path):
    from ai_engineering import scan

    lane = scan.Lane("slow", engine(tmp_path, "import time; time.sleep(30)"), timeout=1)
    fact = scan.run(lane, tmp_path, ["src/thing.py"])

    assert fact.status == "INCOMPLETE"
    assert "LANE_TIMEOUT" in fact.detail and "1" in fact.detail


def test_zero_inputs_is_incomplete_rather_than_a_clean_sweep(tmp_path):
    """A scan of nothing finds nothing. The repository with no Python files and the
    repository whose Python files were never handed to the scanner print the same result,
    and only one of them is safe."""
    from ai_engineering import scan

    lane = scan.Lane("empty", engine(tmp_path, "raise SystemExit(0)"))
    fact = scan.run(lane, tmp_path, [])

    assert fact.status == "INCOMPLETE"
    assert "LANE_NO_INPUTS" in fact.detail


def test_the_lane_never_returns_a_status_outside_the_vocabulary(tmp_path):
    """Every path, in one place: whatever happens, the answer is one of three words and the
    detail names the reason with a stable code."""
    from ai_engineering import scan

    bodies = ["raise SystemExit(0)", "raise SystemExit(1)", "raise SystemExit(97)"]
    facts = [
        scan.run(scan.Lane("x", engine(tmp_path, body)), tmp_path, ["a.py"]) for body in bodies
    ]
    facts.append(scan.run(scan.Lane("y", (str(tmp_path / "gone"),)), tmp_path, ["a.py"]))

    assert {fact.status for fact in facts} == {"PASS", "FAIL", "INCOMPLETE"}
    assert all(fact.detail for fact in facts), "a lane answered without saying why"


@pytest.mark.parametrize("code", list(range(2, 6)))
def test_every_undefined_exit_code_is_incomplete(tmp_path, code):
    """Not just the one the fixture happened to pick. Any exit code with no meaning in this
    lane's contract is unreadable, and unreadable is INCOMPLETE."""
    from ai_engineering import scan

    lane = scan.Lane("varied", engine(tmp_path, f"raise SystemExit({code})"))
    assert scan.run(lane, tmp_path, ["a.py"]).status == "INCOMPLETE"


def test_the_privacy_scanner_and_the_lane_runner_agree_on_the_vocabulary():
    """Two implementations of the same rule, bound so they cannot drift. `gitleaks_v1`
    predates this module and keeps its own path; what must not differ is what each of them
    calls a scanner that is absent, one that found something, and one that did not."""
    from ai_engineering import acceptance_privacy, scan

    unavailable = acceptance_privacy._unavailable("not installed")
    assert unavailable.outcome == "INCOMPLETE"
    assert scan.MISSING_ENGINE.startswith("LANE_")
    assert acceptance_privacy.CLEAN.outcome == "PASS"
