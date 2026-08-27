"""Five ways a scanner lane is INCOMPLETE, and one way it passes.

Specification 014: a missing engine, missing rules, a crash, a timeout or zero inputs each
produce INCOMPLETE with its own fixture. The point of the list is that every one of them is
a way for a lane to report nothing and be read as having found nothing — which is the
failure this whole wave is named after.

Each fixture drives a real subprocess. A lane runner tested against a stubbed runner proves
the branches; it does not prove that a missing binary raises what the code catches.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import repository

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
    assert "LANE_CRASHED" in fact.detail
    assert "97" in fact.detail


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


def test_one_flipped_byte_in_the_rules_stops_the_lane(tmp_path):
    """EP-051's tamper fixture, at the one artefact this repository pins today.

    A rule deleted from the middle of a file leaves an engine that runs, exits zero and no
    longer looks for the thing it was deleted for. That is indistinguishable from a clean
    scan unless the bytes themselves are pinned, so the lane refuses when they differ."""

    import hashlib

    from ai_engineering import scan

    rules = tmp_path / "rules.yml"
    rules.write_text("rules: []\n", encoding="utf-8")
    pinned = hashlib.sha256(rules.read_bytes()).hexdigest()
    lane = scan.Lane(
        "pinned", engine(tmp_path, "raise SystemExit(0)"), rules=rules, rules_digest=pinned
    )

    assert scan.run(lane, tmp_path, ["a.py"]).status == "PASS"

    body = bytearray(rules.read_bytes())
    body[0] ^= 0x01  # one byte, and the engine would still have run happily
    rules.write_bytes(bytes(body))

    tampered = scan.run(lane, tmp_path, ["a.py"])
    assert tampered.status == "INCOMPLETE"
    assert "LANE_RULES_TAMPERED" in tampered.detail


def test_the_baseline_pin_is_the_rules_file_this_repository_actually_ships():
    """The pin moves deliberately or the gate goes red. This is the same discipline as the
    line ceiling: the number lives in one place, and changing the thing it measures without
    changing it is what turns the build red.

    To move it: python -c "import hashlib,pathlib;
    print(hashlib.sha256(pathlib.Path('policy/semgrep.yml').read_bytes()).hexdigest())"
    """

    import hashlib

    from ai_engineering import scan

    semantic = next(lane for lane in scan.BASELINE if lane.id == "semantic")
    actual = hashlib.sha256((ROOT / "policy" / "semgrep.yml").read_bytes()).hexdigest()

    assert semantic.rules_digest == actual, (
        "policy/semgrep.yml changed and its pin did not. Move the pin in the same commit."
    )


def test_a_cross_check_nobody_installed_is_declined_and_not_failed(tmp_path, monkeypatch):
    """EP-046 and EP-282. The proposal names two products as optional cross-checks and the
    tree said nothing at all about them: a search found spec prose and no code, so a reader
    could not tell "we decided not to require these" from "nobody thought about it".

    The requirement asks for exactly that distinction. Absent is not applicable and passes —
    an organisation that never installed a tool is declining a second opinion, not failing a
    check. Configured and unable to answer is INCOMPLETE, and INCOMPLETE is not a pass,
    which is the same contract the three baseline lanes already run under.

    Neither is in `BASELINE`, and that is the decision: this repository's security answer is
    three lanes and it passes with neither of these installed. A cross-check that became a
    dependency would stop being a cross-check.
    """

    from ai_engineering import scan

    assert {lane.id for lane in scan.CROSS_CHECKS} == {"skillspector", "claude-security"}
    assert not {lane.id for lane in scan.CROSS_CHECKS} & {lane.id for lane in scan.BASELINE}

    for lane in scan.CROSS_CHECKS:
        fact = scan.cross_check(lane, tmp_path, ["."])
        assert fact.status == "SKIPPED", fact
        assert "not installed here" in (fact.detail or "")

    # Installed and unable to answer is the other half, and it is not a pass. The engine is
    # a script that exits with a code the lane contract reads as "could not run".
    engine = tmp_path / "bin"
    engine.mkdir()
    (engine / "skillspector").write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
    (engine / "skillspector").chmod(0o755)
    monkeypatch.setenv("PATH", f"{engine}:{os.environ['PATH']}")

    fact = scan.cross_check(scan.CROSS_CHECKS[0], tmp_path, ["."])
    assert fact.status == "INCOMPLETE", fact


def test_the_dependency_answer_names_the_stacks_it_was_about(tmp_path, capsys):
    """EP-263. One `trivy fs .` reads every repository and names no stack, so one whose
    manifests the engine does not support passes exactly like one it read and found nothing
    in. That is the difference this module exists to keep, and it was not kept here.

    A repository with no manifest at all is declining a dependency scan rather than passing
    one, and a container lane over a repository with no image is a lane scanning nothing.
    Both are said out loud instead of being absent from the output.
    """

    from ai_engineering import scan

    # Two manifests side by side, because one is the case where "names the stack" and
    # "names nothing" are indistinguishable. Asked here rather than only against ROOT:
    # mutmut runs the suite from its own `mutants/` tree, which holds the package and the
    # tests and none of the repository's root files, so a ROOT assertion answered a
    # different question there and turned the whole-tree lane red on a true statement.
    both = tmp_path / "both"
    both.mkdir()
    (both / "package.json").write_text("{}", encoding="utf-8")
    (both / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    assert scan.stacks(both) == ["package.json", "pyproject.toml"]
    assert scan.images(both) == []

    # And once against this repository, which is the only tree where the answer can be
    # checked against something a person can see.
    assert scan.stacks(repository()) == ["package.json", "pyproject.toml"]
    assert scan.images(repository()) == []

    # Shallow, and one level down. A manifest inside `node_modules` belongs to somebody
    # else's project, and walking the whole tree turns one answer into hundreds.
    # Its own subtree, because "one level down" means a sibling fixture in `tmp_path` is
    # inside the answer: built directly under `tmp_path`, `both/` above put two more
    # manifests into this list and the expectation stopped being about `service/` at all.
    work = tmp_path / "work"
    (work / "service").mkdir(parents=True)
    (work / "service" / "go.mod").write_text("module x\n", encoding="utf-8")
    (work / "node_modules" / "left-pad").mkdir(parents=True)
    (work / "node_modules" / "left-pad" / "package.json").write_text("{}", encoding="utf-8")
    (work / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    assert scan.stacks(work) == ["go.mod"]
    assert scan.images(work) == ["Dockerfile"]

    # And a repository with neither says so rather than printing nothing.
    bare = tmp_path / "bare"
    bare.mkdir()
    assert scan.stacks(bare) == []
    assert scan.images(bare) == []


# EP-043 and the standing overclaim beside it. `ai-security` defines a finding as seven
# fields and no eighth, and until now nothing in this repository produced one: `just
# security` printed "it found something" and the next move was always to run the engine
# again by hand. These fixtures drive real SARIF through the reader, including SARIF that
# is not SARIF, because a reader that only ever meets well-formed input is a reader nobody
# has watched fail.
SARIF = """{"version": "2.1.0", "runs": [{"results": [
  {"ruleId": "policy.shell-with-user-string",
   "message": {"text": "A shell string built from a variable."},
   "locations": [{"physicalLocation": {
     "artifactLocation": {"uri": "src/thing.py"}, "region": {"startLine": 12}}}]}
]}]}"""


def writer(tmp_path: Path, body: str) -> tuple[str, ...]:
    """An engine that writes the report it was asked for, then exits as a finding."""
    script = tmp_path / "reporter.py"
    script.write_text(
        "import sys\n"
        "where = sys.argv[sys.argv.index('--out') + 1]\n"
        f"open(where, 'w', encoding='utf-8').write({body!r})\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    return (sys.executable, str(script))


def test_a_finding_a_scanner_produced_is_seven_fields_and_incomplete(tmp_path):
    """The four fields a scanner cannot fill are the reason the record exists.

    The effect, the location and the command are observations. The boundary crossed, what an
    attacker controls, the refutation somebody tried and what would close it are judgements,
    and no engine has made any of them. The skill's own rule is that a blank field makes the
    finding INCOMPLETE, so every finding that arrives this way arrives INCOMPLETE and names
    which four are blank — a scanner hit presented as a completed finding is a preference
    with a severity attached."""
    from ai_engineering import scan

    lane = scan.Lane("semantic", writer(tmp_path, SARIF), sarif=("--out", "{}"))
    found = scan.report(lane, tmp_path, ["src/thing.py"])

    assert len(found) == 1
    finding = found[0]
    assert finding.state == "INCOMPLETE"
    assert finding.effect == "A shell string built from a variable."
    assert "src/thing.py:12" in finding.decided_by
    assert finding.blank() == ("boundary", "attacker_controls", "refutation", "closed_by")

    # Seven and no eighth, read off the record rather than counted here by hand.
    from dataclasses import fields

    assert len(fields(scan.Finding)) == 7


def test_a_lane_never_asked_for_sarif_reports_nothing_rather_than_nothing_found(tmp_path):
    """The same distinction the module is named for, one level down: an engine nobody asked
    for a report has not reported that there is nothing to report."""
    from ai_engineering import scan

    lane = scan.Lane("quiet", writer(tmp_path, SARIF))
    assert scan.report(lane, tmp_path, ["src/thing.py"]) == []
    assert scan.report(scan.BASELINE[0], tmp_path, []) == []


@pytest.mark.parametrize(
    "body", ("not json at all", "[]", '{"runs": "a string"}', '{"runs": [{"results": [1, 2]}]}')
)
def test_a_report_that_is_not_sarif_yields_no_findings_and_does_not_crash(tmp_path, body):
    from ai_engineering import scan

    lane = scan.Lane("broken", writer(tmp_path, body), sarif=("--out", "{}"))
    assert scan.report(lane, tmp_path, ["src/thing.py"]) == []


def test_an_engine_that_cannot_run_produces_no_findings_and_never_a_verdict(tmp_path):
    """`report` never decides anything. The gate's verdict is the exit code `run` read, and
    an engine that is missing here has already been INCOMPLETE there."""
    from ai_engineering import scan

    lane = scan.Lane("gone", ("this-engine-is-not-installed",), sarif=("--out", "{}"))
    assert scan.report(lane, tmp_path, ["src/thing.py"]) == []


def test_the_gate_prints_the_findings_of_a_lane_that_failed(tmp_path, capsys, monkeypatch):
    """What an operator sees. "It found something" is where this used to stop."""
    from ai_engineering import scan

    lane = scan.Lane("semantic", writer(tmp_path, SARIF), sarif=("--out", "{}"))
    monkeypatch.setattr(scan, "BASELINE", (lane,))
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    assert scan.baseline(tmp_path) == 1
    printed = capsys.readouterr().out
    assert "FAIL        semantic" in printed
    assert "INCOMPLETE  semantic      A shell string built from a variable." in printed
    assert "nobody has answered: boundary, attacker_controls, refutation, closed_by" in printed


def test_every_baseline_lane_knows_how_to_be_asked_for_its_findings():
    """A lane with no `sarif` flags is a lane whose findings nobody can read, and all three
    of this repository's own lanes support the format their vendors document."""
    from ai_engineering import scan

    for lane in scan.BASELINE:
        assert lane.sarif, f"{lane.id} cannot be asked what it found"
        assert "{}" in " ".join(lane.sarif), f"{lane.id} names no file to write"


# EP-042's other half: which engine covers a stack, and which file it read. A list of
# manifests cannot answer either. Measured on this repository while writing these: trivy
# read `uv.lock` and nothing else, so every package in `package-lock.json` — twenty-three of
# them — had been excluded from every scan this gate ever ran, and the lane exited zero.
def lister(tmp_path: Path, body: str) -> tuple[str, ...]:
    """An engine that answers the listing question and nothing else."""
    script = tmp_path / "lister.py"
    script.write_text(f"print({body!r})\n", encoding="utf-8")
    return (sys.executable, str(script))


def test_a_stack_the_engine_read_no_file_for_is_incomplete(tmp_path, capsys, monkeypatch):
    """The failure this closes, in its exact shape: a manifest is there, the engine read
    nothing for it, and the lane above says it found nothing. Both statements are true and
    together they read as a clean scan of a stack nobody scanned."""
    from ai_engineering import scan

    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    lane = scan.Lane("dependencies", lister(tmp_path, '{"Results": [{"Target": "uv.lock"}]}'))
    # The lane the gate runs and the engine `covered` asks are the same engine, which is the
    # point: the file it read is read off the run that decided the verdict.
    monkeypatch.setattr(scan, "BASELINE", (lane,))

    assert scan.unread(tmp_path, lane) == ["package.json"]
    assert scan.baseline(tmp_path) == 1

    printed = capsys.readouterr().out
    assert "INCOMPLETE  coverage      the engine read no file for package.json" in printed
    assert "a stack it did not read reports as a stack with nothing in it" in printed


def test_a_stack_whose_resolved_file_was_read_is_covered(tmp_path, monkeypatch):
    from ai_engineering import scan

    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    lane = scan.Lane(
        "dependencies", lister(tmp_path, '{"Results": [{"Target": "package-lock.json"}]}')
    )
    assert scan.unread(tmp_path, lane) == []


def test_an_engine_that_cannot_answer_leaves_every_stack_uncovered(tmp_path):
    """Fail closed. An engine that is missing, crashes or answers with something that is not
    its own format has not told us it read anything, and the honest reading of that is that
    it did not."""
    from ai_engineering import scan

    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    for body in ("not json", "[]", '{"Results": "a string"}'):
        lane = scan.Lane("dependencies", lister(tmp_path, body))
        assert scan.covered(tmp_path, lane) == set()
        assert scan.unread(tmp_path, lane) == ["pyproject.toml"]

    gone = scan.Lane("dependencies", ("this-engine-is-not-installed",))
    assert scan.covered(tmp_path, gone) == set()


def test_every_manifest_this_gate_looks_for_says_which_file_answers_for_it():
    """A manifest in one table and not the other would be a stack that is always
    INCOMPLETE, or one that is never checked. Neither is a decision anybody took."""
    from ai_engineering import scan

    assert set(scan.MANIFESTS) == set(scan.READS)
    for manifest, reads in scan.READS.items():
        assert reads, manifest


def test_the_dependency_lane_includes_the_packages_a_build_depends_on():
    """With this flag off, this repository's entire npm tree was excluded from every scan
    the gate ran and the lane exited zero — the same silence as a clean one. A build
    dependency compiles the plugin that ships inside the wheel, so "it is only a development
    dependency" is not a boundary this project has.

    The measurement is here rather than in a commit message, because a docstring that says
    "measured" over an assertion about a constant is the claim outrunning its proof, which
    an independent review said about the first version of this test. What is measured is the
    lock file: every package in it is a development one, so with the flag off there is
    nothing for the engine to report and its silence is indistinguishable from a clean tree.
    """
    import json

    from ai_engineering import scan

    lane = next(one for one in scan.BASELINE if one.id == "dependencies")
    assert "--include-dev-deps" in lane.extra

    lock = json.loads((repository() / "package-lock.json").read_text(encoding="utf-8"))
    packages = [row for name, row in lock["packages"].items() if name]
    assert packages, "the lock file names no packages, so this measured nothing"
    assert all(row.get("dev") for row in packages), (
        "a non-development package appeared in the lock file; the flag is still right, but "
        "the reason written here no longer describes what is in it"
    )


# What an independent review of the two commits above found, each one reproduced here first
# and then held. All three were the same shape: a control that reads stronger than it is.
@pytest.mark.parametrize(
    ("name", "body"),
    (
        ("message is a plain string", '{"runs": [{"results": [{"message": "a string"}]}]}'),
        (
            "region is a list",
            '{"runs": [{"results": [{"locations": [{"physicalLocation": {"region": []}}]}]}]}',
        ),
        (
            "artifactLocation is a string",
            '{"runs": [{"results": [{"locations":'
            ' [{"physicalLocation": {"artifactLocation": "x"}}]}]}]}',
        ),
        ("the text is a number", '{"runs": [{"results": [{"message": {"text": 7}}]}]}'),
        ("locations is an object", '{"runs": [{"results": [{"locations": {}}]}]}'),
        (
            "physicalLocation is a string",
            '{"runs": [{"results": [{"locations": [{"physicalLocation": "x"}]}]}]}',
        ),
    ),
)
def test_sarif_shaped_differently_yields_findings_or_none_and_never_a_traceback(
    tmp_path, name, body
):
    """The reader's own docstring promised this and did not keep it. Every earlier fixture
    stopped at the `runs`/`results` level, so the extraction loop had never met a malformed
    row — and `"message": "a string"` is a shape real converters emit. What came out of the
    security gate was an AttributeError rather than a verdict, and a gate that terminates
    with a traceback has not decided anything: this module's whole rule is that a lane which
    could not answer is INCOMPLETE."""
    from ai_engineering import scan

    lane = scan.Lane("odd", writer(tmp_path, body), sarif=("--out", "{}"))
    for finding in scan.report(lane, tmp_path, ["src/thing.py"]):
        assert finding.state == "INCOMPLETE", name
        assert isinstance(finding.effect, str)
        assert isinstance(finding.decided_by, str)


def test_a_manifest_one_directory_down_is_covered_by_the_file_the_engine_read(tmp_path):
    """`stacks` descends one level on purpose and returns bare file names; the engine
    returns the path it read them at. Comparing the two directly made every repository with
    a `web/` or `api/` package permanently INCOMPLETE over a file the engine had read, with
    no cure but hoisting the lock to the root — and a control somebody can only satisfy by
    rearranging their repository is a control they learn to skip."""
    from ai_engineering import scan

    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "package.json").write_text("{}", encoding="utf-8")
    lane = scan.Lane(
        "dependencies", lister(tmp_path, '{"Results": [{"Target": "api/package-lock.json"}]}')
    )

    assert scan.stacks(tmp_path) == ["package.json"]
    assert scan.unread(tmp_path, lane) == []

    # And a stack it genuinely read nothing for is still caught, wherever it sits.
    (tmp_path / "api" / "Cargo.toml").write_text("", encoding="utf-8")
    assert scan.unread(tmp_path, lane) == ["Cargo.toml"]


def test_the_coverage_question_is_asked_with_the_lane_s_own_arguments(tmp_path):
    """Built from `argv` alone, this asked a different question than the run that decided the
    verdict: the flags were a second copy, so removing `--include-dev-deps` from the lane
    would have left the coverage line still reporting the npm tree read — a green answer
    about a scan that skipped it, which is the defect that flag was added to close."""
    from ai_engineering import scan

    echo = tmp_path / "echo.py"
    echo.write_text(
        "import sys, json\nprint(json.dumps({'Results': [{'Target': ' '.join(sys.argv[1:])}]}))\n",
        encoding="utf-8",
    )
    lane = scan.Lane("dependencies", (sys.executable, str(echo)), extra=("--a-lane-flag",))

    assert any("--a-lane-flag" in target for target in scan.covered(tmp_path, lane))


def test_a_stack_the_engine_read_nothing_for_is_told_how_to_close_it(tmp_path, capsys, monkeypatch):
    """Two legitimate shapes land on INCOMPLETE here — a manifest whose lock file is not
    committed, and a stack whose lock file is opt-in and rarely used. Both are genuinely
    unscanned, so neither is a false positive. What would turn this into a control people
    skip is arriving with no way forward, so the line names the file that would answer it
    and the command that records the decision not to."""
    from ai_engineering import scan

    (tmp_path / "Cargo.toml").write_text("", encoding="utf-8")
    lane = scan.Lane("dependencies", lister(tmp_path, '{"Results": []}'))
    monkeypatch.setattr(scan, "BASELINE", (lane,))

    assert scan.baseline(tmp_path) == 1
    printed = capsys.readouterr().out
    assert "Cargo.lock" in printed
    assert "ai-eng accept" in printed


def test_the_gate_asks_the_cross_checks_and_does_not_only_declare_them(
    tmp_path, capsys, monkeypatch
):
    """`cross_check` existed and nothing in the product called it — an independent audit
    found it exercised by its own test alone.

    An organisation that installs one of the two engines the proposal names, expecting this
    framework to read it, would have got exactly the silence of one that installed nothing.
    That is the distinction this module is named after, so the baseline asks both: absent is
    SKIPPED and passes, present and unable to answer is INCOMPLETE and does not."""
    from ai_engineering import scan

    monkeypatch.setattr(scan, "BASELINE", ())
    monkeypatch.setattr(scan, "CROSS_CHECKS", (scan.Lane("second-opinion", ("no-such-engine",)),))
    assert scan.baseline(tmp_path) == 0
    assert "SKIPPED     second-opinion" in capsys.readouterr().out

    # And one that is installed and cannot answer fails the gate rather than declining it.
    monkeypatch.setattr(
        scan,
        "CROSS_CHECKS",
        (scan.Lane("second-opinion", engine(tmp_path, "raise SystemExit(97)")),),
    )
    assert scan.baseline(tmp_path) == 1
    printed = capsys.readouterr().out
    assert "INCOMPLETE  second-opinion" in printed
    assert "LANE_CRASHED" in printed


def only_the_report(monkeypatch):
    """Drive `baseline` with no engines, so what is asserted is what it says about the tree.

    The three lanes and the two cross-checks are real subprocesses judged elsewhere in this
    file. Emptying them here leaves the half nobody had held: the lines `just security` prints
    about boundaries, manifests and coverage, which are the only part of this output a person
    reads when every engine passes.
    """
    from ai_engineering import scan

    monkeypatch.setattr(scan, "BASELINE", ())
    monkeypatch.setattr(scan, "CROSS_CHECKS", ())
    return scan


def test_a_repository_with_no_threat_model_is_declining_and_not_failing(
    tmp_path, monkeypatch, capsys
):
    """Absent is declined. Demanding a threat model from every consumer would make this lane
    an opinion, and the exit code says so as loudly as the word does."""
    scan = only_the_report(monkeypatch)

    assert scan.baseline(tmp_path) == 0
    printed = capsys.readouterr().out
    assert "SKIPPED     boundaries    this repository declares no threat model" in printed
    assert "SKIPPED     manifests     no dependency manifest here" in printed
    assert "coverage" not in printed, "a tree with no manifest was told about coverage"


def test_a_threat_model_that_cannot_be_read_fails_and_says_which_of_the_two_it_is(
    tmp_path, monkeypatch, capsys
):
    """Present-and-unreadable is INCOMPLETE, which is the same rule this module applies to an
    engine. The two states have to be distinguishable in the line, or a consumer cannot tell
    "we never wrote one" from "ours is broken"."""
    scan = only_the_report(monkeypatch)
    (tmp_path / "policy").mkdir()
    (tmp_path / "policy" / "threat-model.toml").write_text("[[boundary]\n", encoding="utf-8")

    assert scan.baseline(tmp_path) == 1
    printed = capsys.readouterr().out
    assert "INCOMPLETE  boundaries    the threat model is there and could not be read" in printed
    assert "declares no threat model" not in printed


def test_the_boundaries_line_counts_the_whole_ones_separately(tmp_path, monkeypatch, capsys):
    """Two numbers, and the second is the one that matters: a boundary whose row carries a
    `reason` is a control this tree does not hold whole, and a count that folded them together
    would report a threat model as complete on the strength of its own admissions."""
    scan = only_the_report(monkeypatch)
    (tmp_path / "policy").mkdir()
    (tmp_path / "policy" / "threat-model.toml").write_text(
        '[[boundary]]\nid = "a"\n\n[[boundary]]\nid = "b"\nreason = "half built"\n'
        '\n[[boundary]]\nid = "c"\n',
        encoding="utf-8",
    )

    assert scan.baseline(tmp_path) == 0
    assert "OBSERVED    boundaries    3 declared, 2 with a control this tree holds whole" in (
        capsys.readouterr().out
    )


def test_the_manifests_line_names_them_and_coverage_names_what_was_not_read(
    tmp_path, monkeypatch, capsys
):
    """A manifest the engine read no file for is a stack that was not scanned, and the lane
    above reports it as nothing found. So it fails, and the line carries the cure — because a
    control that arrives with no way forward but rearranging the repository is a control people
    learn to skip."""
    scan = only_the_report(monkeypatch)
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    assert scan.baseline(tmp_path) == 1
    printed = capsys.readouterr().out
    assert "OBSERVED    manifests     package.json, pyproject.toml" in printed
    assert "INCOMPLETE  coverage      the engine read no file for" in printed
    assert "commit the file the engine reads for it" in printed
    assert "a stack it did not read reports as a stack with nothing in it" in printed


def test_every_refusal_says_the_whole_sentence_and_the_whole_cure(tmp_path):
    """Eight branches, and until now the fixtures asserted the code and never the words.

    `"LANE_NO_INPUTS" in fact.detail` passes with every human sentence in this module rewritten
    to anything at all — measured: fifty mutants of `run` survived, and most of them were the
    sentences a person actually reads when a security lane refuses. The code is for a machine;
    the sentence and the cure are the whole of what a consumer gets, and they are the part that
    decides whether the refusal is acted on or worked around.

    So each branch is pinned whole: the exact detail, the exact cure, and the status beside
    them. A rewrite is then a deliberate edit to this table rather than a silent one.
    """
    from ai_engineering import scan

    # One directory per engine. `engine()` always writes `engine.py`, so building several in
    # one `tmp_path` leaves every lane pointing at whichever script was written last — the
    # sleeping one became an immediate exit and the timeout branch reported PASS.
    def own(name: str, body: str) -> tuple[str, ...]:
        where = tmp_path / name
        where.mkdir()
        return engine(where, body)

    rules = tmp_path / "rules.yml"
    rules.write_text("rules: []\n", encoding="utf-8")

    cases = (
        (
            scan.Lane("empty", own("empty", "raise SystemExit(0)")),
            [],
            "INCOMPLETE",
            "LANE_NO_INPUTS: there was nothing to scan, so nothing was scanned",
            "point the lane at files that exist, or say why this stack has none",
        ),
        (
            scan.Lane(
                "unruled", own("unruled", "raise SystemExit(0)"), rules=tmp_path / "gone.yml"
            ),
            ["a.py"],
            "INCOMPLETE",
            "LANE_RULES_MISSING: the rules at gone.yml are not there",
            "restore the rules file; an engine with no rules looks for nothing",
        ),
        (
            scan.Lane(
                "pinned",
                engine(tmp_path, "raise SystemExit(0)"),
                rules=rules,
                rules_digest="deadbeef",
            ),
            ["a.py"],
            "INCOMPLETE",
            "LANE_RULES_TAMPERED: rules.yml is not the file this lane was pinned to",
            "review the change and move the pin deliberately, or restore the file",
        ),
        (
            scan.Lane("absent", (str(tmp_path / "no-such-engine"),)),
            ["a.py"],
            "INCOMPLETE",
            f"LANE_ENGINE_MISSING: {tmp_path / 'no-such-engine'} is not installed here",
            "install the pinned engine, or record this lane as not applicable",
        ),
        (
            scan.Lane("slow", own("slow", "import time; time.sleep(30)"), timeout=1),
            ["a.py"],
            "INCOMPLETE",
            "LANE_TIMEOUT: it did not finish within 1 seconds",
            "narrow the inputs or raise the bound deliberately",
        ),
        (
            scan.Lane("broken", own("broken", "raise SystemExit(97)")),
            ["a.py"],
            "INCOMPLETE",
            "LANE_CRASHED: it exited 97, which has no meaning in this lane",
            "read its output; an exit code with no defined meaning is not a verdict",
        ),
        (
            scan.Lane("noisy", own("noisy", "raise SystemExit(1)")),
            ["a.py", "b.py"],
            "FAIL",
            "it ran over 2 input(s) and found something",
            "read its output, fix what it found, and run it again",
        ),
        (
            scan.Lane("clean", own("clean", "raise SystemExit(0)")),
            ["a.py", "b.py", "c.py"],
            "PASS",
            "it ran over 3 input(s) and found nothing",
            None,
        ),
    )

    for lane, inputs, status, detail, cure in cases:
        fact = scan.run(lane, tmp_path, inputs)
        assert fact.status == status, f"{lane.id}: {fact.status}"
        assert fact.detail == detail, f"{lane.id}: {fact.detail!r}"
        assert fact.cure == cure, f"{lane.id}: {fact.cure!r}"
        assert fact.id == f"lane-{lane.id}"
        assert fact.summary == f"The {lane.id} lane"


def test_the_inputs_are_counted_and_not_described(tmp_path):
    """`len(inputs)` and not a word for it. The count is the one number in a lane's answer
    that a reader can check against what they asked for, and "some" or "several" in its place
    would make a lane that scanned one file indistinguishable from one that scanned a hundred.
    """
    from ai_engineering import scan

    lane = scan.Lane("counted", engine(tmp_path, "raise SystemExit(0)"))
    for how_many in (1, 2, 7):
        fact = scan.run(lane, tmp_path, [f"file{n}.py" for n in range(how_many)])
        assert fact.detail == f"it ran over {how_many} input(s) and found nothing"


def test_the_order_of_the_checks_is_the_order_the_docstring_claims(tmp_path):
    """Inputs before the engine, rules before the exit code. The docstring says why and
    nothing held it: a lane with no inputs and no engine has two reasons to refuse, and which
    one it names decides whether somebody installs a tool or fixes a path.
    """
    from ai_engineering import scan

    nowhere = scan.Lane("both", (str(tmp_path / "absent-engine"),), rules=tmp_path / "gone.yml")

    # No inputs wins over a missing engine and over missing rules.
    assert "LANE_NO_INPUTS" in scan.run(nowhere, tmp_path, []).detail

    # Missing rules win over a missing engine, because an engine with no rules exits zero
    # having looked for nothing — the worst of the two outcomes to mistake for a pass.
    assert "LANE_RULES_MISSING" in scan.run(nowhere, tmp_path, ["a.py"]).detail


def test_the_sarif_reader_keeps_every_shape_it_can_read_and_drops_the_rest(tmp_path):
    """Fifteen mutants of `_results` survived, which means the shapes were named and never
    counted. The reader's promise is exact: a row it cannot read yields nothing rather than an
    answer, and `report` turns nothing into INCOMPLETE — so what has to be pinned is which rows
    survive the filter and how many, not merely that a malformed one does not crash.
    """
    from ai_engineering import scan

    where = tmp_path / "r.sarif"

    # Two readable rows among five, and the three dropped ones are each a shape a real
    # converter emits: a message that is a string, locations that are not a list, and a row
    # that is not an object at all.
    where.write_text(
        '{"runs": [{"results": ['
        '{"message": {"text": "one"}},'
        '{"message": "a string"},'
        '{"locations": "not a list"},'
        '"not an object",'
        '{"message": {"text": "two"}, "locations": [{"physicalLocation": {}}]}'
        "]}]}",
        encoding="utf-8",
    )
    kept = scan._results(where)
    assert len(kept) == 2, kept
    assert [row["message"]["text"] for row in kept] == ["one", "two"]

    # Two runs are two sources of results and both are read; a run that is not an object is
    # skipped without taking the other one with it.
    where.write_text(
        '{"runs": [{"results": [{"message": {"text": "a"}}]}, 7,'
        ' {"results": [{"message": {"text": "b"}}]}]}',
        encoding="utf-8",
    )
    assert [row["message"]["text"] for row in scan._results(where)] == ["a", "b"]

    # And every way of not being a report at all is the empty answer, never an exception.
    for body in ("[]", "7", '"a string"', "null", "{not json", ""):
        where.write_text(body, encoding="utf-8")
        assert scan._results(where) == [], body
    assert scan._results(tmp_path / "absent.sarif") == []


def test_the_coverage_answer_comes_from_the_engine_and_never_from_a_guess(tmp_path):
    """`covered` asks the engine which files it read. Seventeen mutants survived, and the two
    that matter are the ones this function was rewritten to prevent: asking a different
    question than the run that decided the verdict, and treating "nobody asked" as "everything
    was read".
    """
    from ai_engineering import scan

    # The lane's own extra arguments reach the coverage run. Built from `argv` alone, this
    # asked a narrower question than the verdict did — so an engine invoked without
    # `--include-dev-deps` would still have reported the development tree read.
    seen = tmp_path / "argv.json"
    spy = engine(
        tmp_path,
        "import json, sys, pathlib\n"
        f"pathlib.Path({str(seen)!r}).write_text(json.dumps(sys.argv[1:]))\n"
        'print(json.dumps({"Results": [{"Target": "pyproject.toml"}]}))\n',
    )
    lane = scan.Lane("dep", spy, extra=("--include-dev-deps",))

    assert scan.covered(tmp_path, lane) == {"pyproject.toml"}
    import json as _json

    assert "--include-dev-deps" in _json.loads(seen.read_text("utf-8"))

    # Nobody asked is not everything read. With no lane and no baseline this used to raise on
    # an empty tuple, which is a crash where the rule is that an engine unable to answer
    # leaves every stack unread.
    monkey = scan.BASELINE
    try:
        scan.BASELINE = ()
        assert scan.covered(tmp_path) == set()
    finally:
        scan.BASELINE = monkey

    # Every shape that is not an answer is the empty set, and a row with no target is not one.
    (tmp_path / "quiet").mkdir()
    for body in ("[]", "7", "{not json", "", '{"Results": null}', '{"Results": [{"Target": ""}]}'):
        quiet = scan.Lane("quiet", engine(tmp_path / "quiet", f"print({body!r})"))
        assert scan.covered(tmp_path, quiet) == set(), body

    # And an engine that is not installed answers nothing rather than raising.
    assert scan.covered(tmp_path, scan.Lane("gone", (str(tmp_path / "no-engine"),))) == set()


def sarif_engine(where: Path, body: str) -> tuple[str, ...]:
    """An engine that writes a SARIF file where it is told and exits saying it found something.

    `report` formats the lane's `sarif` flags with a temporary path and reads the file back, so
    an engine that ignores the flag proves nothing about the reader. This one honours it.
    """
    where.mkdir(parents=True, exist_ok=True)
    return engine(
        where,
        "import sys, pathlib\n"
        "target = sys.argv[sys.argv.index('--out') + 1]\n"
        f"pathlib.Path(target).write_text({body!r})\n"
        "raise SystemExit(1)\n",
    )


def test_a_finding_carries_the_engine_the_file_and_the_line_it_came_from(tmp_path):
    """Thirty-six mutants of `report` survived, which is every field of a finding except the
    count of them. What a person acts on is `decided_by` — which engine said so, in which file,
    at which line — and the effect in the engine's own words. Those are pinned exactly.

    The four judgement fields stay unanswered on purpose: a scanner cannot say what boundary a
    hit crosses or what would refute it, and a finding that arrived looking complete would be
    the green nobody earned with the sign reversed.
    """
    from ai_engineering import scan

    lane = scan.Lane(
        "semantic",
        sarif_engine(
            tmp_path / "found",
            '{"runs": [{"results": [{"message": {"text": "  a  ragged   message  "},'
            ' "locations": [{"physicalLocation": {"artifactLocation": {"uri": "src/thing.py"},'
            ' "region": {"startLine": 12}}}]}]}]}',
        ),
        sarif=("--out", "{0}"),
    )

    found = scan.report(lane, tmp_path, ["."])
    assert len(found) == 1
    only = found[0]
    assert only.effect == "a ragged message", "whitespace was not collapsed"
    assert only.state == "INCOMPLETE"
    assert only.decided_by.endswith(" — src/thing.py:12")
    assert only.boundary == scan.UNANSWERED
    assert only.attacker_controls == scan.UNANSWERED
    assert only.refutation == scan.UNANSWERED
    assert only.closed_by == scan.UNANSWERED
    assert only.blank() == ("boundary", "attacker_controls", "refutation", "closed_by")


def test_a_finding_with_nothing_to_locate_says_so_rather_than_inventing_a_place(tmp_path):
    """Every field has a stated fallback and none of them is a guess. A row with no location
    is `an unnamed file:?`, and a row with no message falls back to its rule id — because a
    finding whose text is empty reads as a finding about nothing.
    """
    from ai_engineering import scan

    lane = scan.Lane(
        "bare",
        sarif_engine(
            tmp_path / "bare",
            '{"runs": [{"results": ['
            '{"ruleId": "RULE-7"},'
            '{"message": {"text": "located"}, "locations": [{"physicalLocation":'
            ' {"artifactLocation": "not an object", "region": "not an object"}}]}'
            "]}]}",
        ),
        sarif=("--out", "{0}"),
    )

    first, second = scan.report(lane, tmp_path, ["."])
    assert first.effect == "RULE-7", "a row with no message did not fall back to its rule"
    assert first.decided_by.endswith(" — an unnamed file:?")
    assert second.effect == "located"
    assert second.decided_by.endswith(" — an unnamed file:?")


def test_a_lane_that_cannot_report_returns_nothing_and_never_a_partial_list(tmp_path):
    """Three ways there is nothing to report, and each is the empty list rather than an
    exception or a half-answer: a lane that declares no SARIF flags, a call with no inputs, and
    an engine that is not installed. The gate's verdict comes from the exit code and nothing
    here may change it, so failing loudly here would be this function overruling the lane."""
    from ai_engineering import scan

    quiet = scan.Lane("quiet", engine(tmp_path, "raise SystemExit(1)"))
    assert scan.report(quiet, tmp_path, ["."]) == [], "a lane with no sarif flags reported"

    declared = scan.Lane(
        "declared", engine(tmp_path, "raise SystemExit(1)"), sarif=("--out", "{0}")
    )
    assert scan.report(declared, tmp_path, []) == [], "a call with no inputs reported"

    absent = scan.Lane("absent", (str(tmp_path / "no-engine"),), sarif=("--out", "{0}"))
    assert scan.report(absent, tmp_path, ["."]) == [], "a missing engine raised instead"


def test_the_security_lane_prints_every_finding_a_failing_engine_gave_it(
    tmp_path, monkeypatch, capsys
):
    """`baseline`'s own loop, with a lane that really fails and really reports.

    Forty-two mutants survived here because the fixtures either emptied the lanes or ran the
    real engines, and neither exercises the branch that matters: a FAIL is followed by every
    finding, each on three lines — what it is, who decided it, and which four questions nobody
    has answered. That third line is the one that keeps a scanner hit from reading as a
    completed finding.
    """
    from ai_engineering import scan

    lane = scan.Lane(
        "semantic",
        sarif_engine(
            tmp_path / "noisy",
            '{"runs": [{"results": [{"message": {"text": "a real hit"},'
            ' "locations": [{"physicalLocation": {"artifactLocation": {"uri": "a.py"},'
            ' "region": {"startLine": 3}}}]}]}]}',
        ),
        sarif=("--out", "{0}"),
        findings_exit=1,
    )
    monkeypatch.setattr(scan, "BASELINE", (lane,))
    monkeypatch.setattr(scan, "CROSS_CHECKS", ())

    assert scan.baseline(tmp_path) == 1
    printed = capsys.readouterr().out
    assert "FAIL        semantic      it ran over 1 input(s) and found something" in printed
    assert "INCOMPLETE  semantic      a real hit" in printed
    assert "decided by" in printed
    assert "a.py:3" in printed
    assert "nobody has answered: boundary, attacker_controls, refutation, closed_by" in printed


def test_a_cross_check_that_cannot_answer_fails_the_gate_and_an_absent_one_does_not(
    tmp_path, monkeypatch, capsys
):
    """The two halves of the second opinion, in `baseline`'s own loop. Absent is SKIPPED and
    passes, because an organisation that never installed a tool is declining a check rather
    than failing one. Present and unable to answer is INCOMPLETE and does not pass, which is
    the same rule this module applies to its own engines."""
    from ai_engineering import scan

    monkeypatch.setattr(scan, "BASELINE", ())
    monkeypatch.setattr(
        scan, "CROSS_CHECKS", (scan.Lane("absent-tool", (str(tmp_path / "nope"),)),)
    )
    assert scan.baseline(tmp_path) == 0
    assert "SKIPPED     absent-tool" in capsys.readouterr().out

    monkeypatch.setattr(
        scan, "CROSS_CHECKS", (scan.Lane("broken-tool", engine(tmp_path, "raise SystemExit(97)")),)
    )
    assert scan.baseline(tmp_path) == 1
    assert "INCOMPLETE  broken-tool" in capsys.readouterr().out


def test_the_whole_security_report_is_this_exact_block_of_lines(tmp_path, monkeypatch, capsys):
    """Every line `just security` prints, for one fully described tree, compared whole.

    Fragments were not enough. Asserting `"OBSERVED    boundaries" in printed` leaves the rest
    of the sentence, the column widths and the order free, and thirty-eight mutants of this
    function lived in exactly that freedom — a padding changed, a word swapped, two lines
    transposed. What a person reads is the block, so the block is what is pinned.

    It is also the most honest form of this assertion: if somebody improves the wording they
    have to say so here, in a diff, beside the words they changed.
    """
    from ai_engineering import scan

    (tmp_path / "policy").mkdir()
    (tmp_path / "policy" / "threat-model.toml").write_text(
        '[[boundary]]\nid = "whole"\n\n[[boundary]]\nid = "half"\nreason = "not built"\n',
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    failing = scan.Lane(
        "semantic",
        sarif_engine(
            tmp_path / "sem",
            '{"runs": [{"results": [{"message": {"text": "a real hit"},'
            ' "locations": [{"physicalLocation": {"artifactLocation": {"uri": "a.py"},'
            ' "region": {"startLine": 3}}}]}]}]}',
        ),
        sarif=("--out", "{0}"),
        findings_exit=1,
    )
    (tmp_path / "sec").mkdir()
    clean = scan.Lane("secrets", engine(tmp_path / "sec", "raise SystemExit(0)"))
    monkeypatch.setattr(scan, "BASELINE", (clean, failing))
    monkeypatch.setattr(
        scan, "CROSS_CHECKS", (scan.Lane("second-opinion", (str(tmp_path / "nope"),)),)
    )

    assert scan.baseline(tmp_path) == 1

    decided = " ".join(failing.argv)
    assert capsys.readouterr().out.splitlines() == [
        "  PASS        secrets       it ran over 1 input(s) and found nothing",
        "  FAIL        semantic      it ran over 1 input(s) and found something",
        "  INCOMPLETE  semantic      a real hit",
        f"                            decided by {decided} — a.py:3",
        "                            nobody has answered: boundary, attacker_controls, "
        "refutation, closed_by",
        "  OBSERVED    boundaries    2 declared, 1 with a control this tree holds whole",
        f"  SKIPPED     second-opinion {tmp_path / 'nope'} is not installed here, so there "
        "is no second opinion to read",
        "  OBSERVED    manifests     pyproject.toml",
        "  INCOMPLETE  coverage      the engine read no file for pyproject.toml: a stack it "
        "did not read reports as a stack with nothing in it",
        "                            commit the file the engine reads for it (pdm.lock, "
        "poetry.lock, requirements.txt, uv.lock), or record a dated risk acceptance with "
        "`ai-eng accept`",
        "  SKIPPED     images        no container image here, so no container lane runs",
        "  SKIPPED     dast          nothing here scanned a running target: that needs a URL "
        "somebody authorised, and this gate never has one",
    ]


def _sarif(results: list[dict]) -> dict:
    return {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "t"}}, "results": results}]}


def test_every_shape_a_sarif_row_can_be_missing_becomes_a_finding_that_still_reads(
    tmp_path, monkeypatch
):
    """Twenty-six mutants of `report` survived, and all of them are what this function does
    when a row is not the shape it hoped for.

    An engine's SARIF is somebody else's output. A row with no locations, a location with no
    artefact, an artefact with no region, a message that is absent, a message that is four
    kilobytes of wrapped text — each is a thing a real engine emits, and each one this
    function turns into a finding a person reads. Nothing asserted any of them, so the
    fallbacks could have been deleted or swapped and the suite would not have moved.

    Driven through the whole function rather than around it: the stub writes the SARIF where
    the lane's own flags say it will be written, so the argument formatting is exercised too.
    """
    from ai_engineering import scan

    lane = scan.Lane(id="t", argv=("engine",), sarif=("--out", "{}"))

    def engine(argv, **kwargs):
        where = Path(argv[argv.index("--out") + 1])
        where.write_text(json.dumps(_sarif(engine.rows)), encoding="utf-8")
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    monkeypatch.setattr(scan.subprocess, "run", engine)

    engine.rows = [
        {
            "message": {"text": "a real finding"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "src/a.py"},
                        "region": {"startLine": 12},
                    }
                }
            ],
        },
        {"message": {"text": "no locations at all"}},
        {"message": {"text": "no artefact"}, "locations": [{"physicalLocation": {"region": {}}}]},
        {
            "ruleId": "RULE-7",
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "src/b.py"},
                        "region": {"startLine": 3},
                    }
                }
            ],
        },
        {"message": {"text": "  wrapped\n   across\tlines  "}, "locations": []},
    ]
    found = scan.report(lane, tmp_path, ["."])

    assert [one.effect for one in found] == [
        "a real finding",
        "no locations at all",
        "no artefact",
        "RULE-7",
        "wrapped across lines",
    ]
    assert [one.decided_by for one in found] == [
        "engine — src/a.py:12",
        "engine — an unnamed file:?",
        "engine — an unnamed file:?",
        "engine — src/b.py:3",
        "engine — an unnamed file:?",
    ]
    # A row with no message falls back to its rule id, which is the fourth one above: an
    # engine that reports a rule and no prose still has to arrive as something a person can
    # look up, and an empty effect there would be a finding that says nothing at all.
    assert found[3].effect == "RULE-7"

    # Six of the seven fields are the same on every one of them, and that is the contract:
    # a scanner names what it saw and answers none of the questions a person must.
    for one in found:
        assert one.state == "INCOMPLETE"
        assert one.boundary == scan.UNANSWERED
        assert one.attacker_controls == scan.UNANSWERED
        assert one.refutation == scan.UNANSWERED
        assert one.closed_by == scan.UNANSWERED


def test_a_message_longer_than_the_bound_is_cut_and_a_lane_with_no_sarif_says_nothing(
    tmp_path, monkeypatch
):
    """Two limits, and the second is the one that matters most.

    The effect is a line in a report, so an engine emitting four kilobytes must not become
    the report. And a lane that was never asked for SARIF returns nothing at all — which the
    docstring is careful to distinguish from "it found nothing", because a lane with no
    machine-readable output is a lane nobody can list findings from.
    """
    from ai_engineering import scan

    def engine(argv, **kwargs):
        where = Path(argv[argv.index("--out") + 1])
        where.write_text(
            json.dumps(_sarif([{"message": {"text": "x" * 500}, "locations": []}])),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    monkeypatch.setattr(scan.subprocess, "run", engine)

    lane = scan.Lane(id="t", argv=("engine",), sarif=("--out", "{}"))
    (cut,) = scan.report(lane, tmp_path, ["."])
    assert len(cut.effect) == 200
    assert cut.effect == "x" * 200

    # Never asked, and no inputs: two separate reasons to return nothing, and neither runs
    # the engine.
    ran = []
    monkeypatch.setattr(scan.subprocess, "run", lambda *a, **k: ran.append(a) or None)
    assert scan.report(scan.Lane(id="t", argv=("engine",)), tmp_path, ["."]) == []
    assert scan.report(lane, tmp_path, []) == []
    assert ran == [], "an engine was run for a lane that cannot report"


def test_an_engine_that_cannot_run_reports_nothing_rather_than_raising(tmp_path, monkeypatch):
    """This runs only when a lane has already failed, so it must never be the thing that
    takes the gate down. An engine that is absent, or that times out on the second run, gives
    an empty list — the verdict was already decided by the exit code and nothing here may
    change it."""
    from ai_engineering import scan

    lane = scan.Lane(id="t", argv=("engine",), sarif=("--out", "{}"))
    for failure in (OSError("gone"), subprocess.TimeoutExpired("engine", 1)):
        monkeypatch.setattr(
            scan.subprocess, "run", lambda *a, _f=failure, **k: (_ for _ in ()).throw(_f)
        )
        assert scan.report(lane, tmp_path, ["."]) == []

    # And a run that writes no SARIF at all, which is what an engine does when it crashes
    # after starting.
    monkeypatch.setattr(
        scan.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="")
    )
    assert scan.report(lane, tmp_path, ["."]) == []


def test_the_whole_security_report_and_the_code_it_exits_with(tmp_path, monkeypatch, capsys):
    """Twenty-six mutants of `baseline` survived, and this function is the security gate.

    What it prints is the report somebody reads to decide whether to ship, and what it
    returns is whether the gate goes red. Both were unasserted as a whole: a line that
    changed its status word, a lane that stopped setting `worst`, a threat model whose count
    drifted — none of it was visible to a test that only checked the exit code of a clean
    run.

    The clean case first, whole and in order, because a report that says the right things in
    the wrong order is a report a person misreads.
    """
    from ai_engineering import outcome, scan

    def clean(lane, root, inputs):
        return outcome.fact(lane.id, "PASS", lane.id, "it ran and found nothing")

    monkeypatch.setattr(scan, "run", clean)
    monkeypatch.setattr(
        scan,
        "cross_check",
        lambda lane, root, inputs: outcome.fact(
            lane.id, "SKIPPED", lane.id, f"{lane.id} is not installed here"
        ),
    )
    monkeypatch.setattr(scan, "model", lambda root: [{"id": "a"}, {"id": "b", "reason": "why"}])
    monkeypatch.setattr(scan, "stacks", lambda root: ["pyproject.toml"])
    monkeypatch.setattr(scan, "unread", lambda root, lane=None: [])
    (tmp_path / "policy").mkdir()
    (tmp_path / "policy" / "threat-model.toml").write_text("", encoding="utf-8")

    assert scan.baseline(tmp_path) == 0
    assert [one for one in capsys.readouterr().out.splitlines() if one.strip()] == [
        "  PASS        secrets       it ran and found nothing",
        "  PASS        semantic      it ran and found nothing",
        "  PASS        dependencies  it ran and found nothing",
        "  OBSERVED    boundaries    2 declared, 1 with a control this tree holds whole",
        "  SKIPPED     skillspector  skillspector is not installed here",
        "  SKIPPED     claude-security claude-security is not installed here",
        "  OBSERVED    manifests     pyproject.toml",
        "  OBSERVED    coverage      the engine read a file for every manifest here",
        "  SKIPPED     images        no container image here, so no container lane runs",
        "  SKIPPED     dast          nothing here scanned a running target: that needs a URL "
        "somebody authorised, and this gate never has one",
    ]


def test_every_way_this_gate_goes_red_and_the_one_way_it_does_not(tmp_path, monkeypatch, capsys):
    """Four states that fail it and two that do not, each asserted on the exit code.

    INCOMPLETE fails exactly as FAIL does, and that is the whole position of this module: a
    lane whose answer nobody has is not a clean one. What must *not* fail it is a scanner
    that is absent — SKIPPED passes, because demanding somebody else's tool would make this
    lane an opinion — and a repository with no threat model, which is declining rather than
    failing.
    """
    from ai_engineering import outcome, scan

    monkeypatch.setattr(scan, "model", lambda root: None)
    monkeypatch.setattr(scan, "stacks", lambda root: [])
    monkeypatch.setattr(scan, "unread", lambda root, lane=None: [])
    monkeypatch.setattr(
        scan,
        "cross_check",
        lambda lane, root, inputs: outcome.fact(lane.id, "SKIPPED", lane.id, "absent"),
    )

    def lanes(status):
        return lambda lane, root, inputs: outcome.fact(lane.id, status, lane.id, "detail")

    # A lane that failed, and a lane that could not run: both red.
    for status in ("FAIL", "INCOMPLETE", "WARN"):
        monkeypatch.setattr(scan, "run", lanes(status))
        monkeypatch.setattr(scan, "report", lambda lane, root, inputs: [])
        assert scan.baseline(tmp_path) == 1, status
        capsys.readouterr()

    # Every lane clean, no threat model on disk: not red, and it says it declined.
    monkeypatch.setattr(scan, "run", lanes("PASS"))
    assert scan.baseline(tmp_path) == 0
    said = capsys.readouterr().out
    assert "SKIPPED     boundaries" in said
    assert "declares no threat model" in said

    # A threat model that is there and cannot be read is a control nobody can read, which is
    # not a pass — and this is the line that separates it from the case above.
    (tmp_path / "policy").mkdir(exist_ok=True)
    (tmp_path / "policy" / "threat-model.toml").write_text("", encoding="utf-8")
    assert scan.baseline(tmp_path) == 1
    assert "INCOMPLETE  boundaries" in capsys.readouterr().out

    # A cross-check that is present and cannot answer is red; absent is not.
    monkeypatch.setattr(scan, "model", lambda root: [])
    monkeypatch.setattr(
        scan,
        "cross_check",
        lambda lane, root, inputs: outcome.fact(
            lane.id, "INCOMPLETE", lane.id, "it is installed and could not answer"
        ),
    )
    assert scan.baseline(tmp_path) == 1
    capsys.readouterr()

    # And a manifest the engine read no file for: the stack was not scanned, and a stack that
    # was not scanned reports as a stack with nothing in it.
    monkeypatch.setattr(
        scan,
        "cross_check",
        lambda lane, root, inputs: outcome.fact(lane.id, "SKIPPED", lane.id, "absent"),
    )
    monkeypatch.setattr(scan, "stacks", lambda root: ["package.json"])
    monkeypatch.setattr(scan, "unread", lambda root, lane=None: ["package.json"])
    assert scan.baseline(tmp_path) == 1
    unread_said = capsys.readouterr().out
    assert "INCOMPLETE  coverage" in unread_said
    assert "a stack it did not read reports as a stack with nothing in it" in unread_said


def test_a_failing_lane_prints_every_finding_with_the_four_fields_nobody_answered(
    tmp_path, monkeypatch, capsys
):
    """A scanner hit that reads as a completed finding is the green nobody earned with the
    sign reversed. So each one arrives INCOMPLETE, names the engine and the file that decided
    it, and lists the four questions no scanner can answer."""
    from ai_engineering import outcome, scan

    monkeypatch.setattr(
        scan,
        "run",
        lambda lane, root, inputs: outcome.fact(
            lane.id, "FAIL" if lane.id == "semantic" else "PASS", lane.id, "detail"
        ),
    )
    monkeypatch.setattr(scan, "model", lambda root: [])
    monkeypatch.setattr(scan, "stacks", lambda root: [])
    monkeypatch.setattr(scan, "unread", lambda root, lane=None: [])
    monkeypatch.setattr(
        scan,
        "cross_check",
        lambda lane, root, inputs: outcome.fact(lane.id, "SKIPPED", lane.id, "absent"),
    )
    monkeypatch.setattr(
        scan,
        "report",
        lambda lane, root, inputs: (
            [
                scan.Finding(
                    boundary=scan.UNANSWERED,
                    attacker_controls=scan.UNANSWERED,
                    effect="a thing it saw",
                    state="INCOMPLETE",
                    decided_by="semgrep — src/a.py:4",
                    refutation=scan.UNANSWERED,
                    closed_by=scan.UNANSWERED,
                )
            ]
            if lane.id == "semantic"
            else []
        ),
    )

    assert scan.baseline(tmp_path) == 1
    printed = [one for one in capsys.readouterr().out.splitlines() if one.strip()]

    assert "  INCOMPLETE  semantic      a thing it saw" in printed
    assert any("decided by semgrep — src/a.py:4" in one for one in printed)
    assert any(
        "nobody has answered: boundary, attacker_controls, refutation, closed_by" in one
        for one in printed
    )


def test_a_tree_with_no_authorised_target_declines_the_dynamic_scan(tmp_path, capsys, monkeypatch):
    """The lane this report does not have, said out loud instead of left silent.

    Every engine pinned here reads files. None of them touches a running service, so a
    repository with a deployed preview got exit zero and a report whose last line was about
    container images — and `ai-security` step 3 tells the model to paste that output. A green
    that means "nothing dynamic was looked at" reads identically to one that means "the
    dynamic surface is clean", and this repository exists to tell those apart.

    Declined, not passed, and not `N/A`: `outcome._FACT_STATUSES` has no such word, and
    SKIPPED is already what this module says when it is refusing to answer rather than
    answering. The decision on where a dynamic scan lives is D-014-11 and the security
    research before it — inside `ai-security`, never a separate skill — and this line is the
    part of it that is a script.
    """

    from ai_engineering import scan

    # The engines are emptied because this is about a lane that is absent, not about the
    # three that are present. Spawning them here would pay their cost twice per gate to
    # prove nothing, which is the defect Task 2 removed from the threat-model suite.
    monkeypatch.setattr(scan, "BASELINE", ())
    monkeypatch.setattr(scan, "CROSS_CHECKS", ())

    assert scan.baseline(tmp_path) == 0
    said = capsys.readouterr().out
    assert "SKIPPED     dast" in said
    assert "running target" in said
    # It is the last word, after the images line, because it is the lane furthest from what
    # this gate can see.
    lines = [one for one in said.splitlines() if one.strip()]
    assert "dast" in lines[-1]
    # And it touches nothing: a repository with no findings still exits zero.
    assert scan.baseline(tmp_path) == 0
