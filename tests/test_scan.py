"""Five ways a scanner lane is INCOMPLETE, and one way it passes.

Specification 014: a missing engine, missing rules, a crash, a timeout or zero inputs each
produce INCOMPLETE with its own fixture. The point of the list is that every one of them is
a way for a lane to report nothing and be read as having found nothing — which is the
failure this whole wave is named after.

Each fixture drives a real subprocess. A lane runner tested against a stubbed runner proves
the branches; it does not prove that a missing binary raises what the code catches.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

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
    assert scan.stacks(bare) == [] and scan.images(bare) == []


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
        assert isinstance(finding.effect, str) and isinstance(finding.decided_by, str)


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
    assert "INCOMPLETE  second-opinion" in printed and "LANE_CRASHED" in printed
