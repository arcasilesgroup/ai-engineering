"""Doctor, which is the file a person reads to decide whether they are protected.

A wrong green here is the failure this product exists to cure, so every test below builds
its own machine and its own throwaway repository under tmp_path. Doctor run against this
checkout answers differently on every laptop, and an answer that depends on whose laptop
it ran on proves nothing about the code.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import types
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.style import Style

from ai_engineering import __version__, audit, cli, doctor, outcome, paths, wiring

emit = paths.load("_emit")


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A machine of this test's own. Everything doctor reports is derived from what is
    installed under HOME, so a test that finds the real ~/.claude passes for a reason
    that has nothing to do with the code under test."""
    fake = tmp_path / "home"
    (fake / ".ai-engineering" / "cache").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake))
    monkeypatch.setenv("USERPROFILE", str(fake))
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(fake / ".ai-engineering"))
    return fake


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / ".ai").mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
    return root


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def verdict(fn, root: Path | None) -> tuple[str, str]:
    """The three states doctor prints, as a pair a table can be compared against.

    A fourth answer arrived with `Noted`: a pass that publishes what it observed. It is a
    non-empty string and would read as a failure here, exactly as it would in the runner —
    which is why both places test for it before testing for truthiness, and why this helper
    reports it as `ok` with its text rather than inventing a fourth word. A table comparing
    against `("ok", "")` is asking whether the check passed, and it did.
    """
    try:
        problem = fn(root)
    except doctor.Undecidable as why:
        return "undecidable", str(why)
    if isinstance(problem, tuple):
        problem = problem[0]  # a check that carries its own cure; the message is the first
    if isinstance(problem, doctor.Noted):
        return "ok", str(problem)
    return ("fail", problem) if problem else ("ok", "")


def raises(error: Exception):
    def check(root):
        raise error

    return check


def chain(root: Path, *events: dict) -> Path:
    path = emit.chain_path(root)
    emit.append(path, [{"cls": "blocked", "name": "loop_guard", "data": {}, **e} for e in events])
    return path


# ------------------------------------------------------------------ the registry


def test_every_assertion_has_a_unique_number_a_family_and_a_sentence():
    """Two checks sharing a number print as one line item, and the second one is invisible
    to whoever reads the output — including the person who wrote it."""
    numbers = [row[0] for row in doctor.CHECKS]
    # 5 is retired, not renumbered: the numbers are cited in prose all over this repository
    # and moving them would silently repoint every one of those citations. It was the line
    # ceiling, and the test plane owns that assertion now.
    assert sorted(numbers) == [n for n in range(1, 28) if n != 5]
    for number, family, title, in_ci, fn in doctor.CHECKS:
        assert family
        assert title
        assert callable(fn)
        assert isinstance(in_ci, bool), number


def test_each_family_is_printed_once_and_in_the_declared_order(home, repo, monkeypatch, capsys):
    """The registry is sorted by assertion number and the numbers are cited in prose all
    over this repository, so the families interleave. Printing a heading whenever the
    family changes gave six families nine headings — `The wiring` four times, `The record`
    three — and a report that reads as though it lost its place."""
    monkeypatch.setattr(paths, "repo_root", lambda start=None: repo)
    doctor.main([])
    printed = [line for line in capsys.readouterr().out.splitlines() if line in doctor.FAMILIES]
    assert printed == list(doctor.FAMILIES)
    assert len(printed) == len(set(printed))


def test_a_family_nobody_ordered_is_printed_last_rather_than_dropped(monkeypatch):
    """Catches the ordering being applied by filtering the declared list, which loses every
    check whose family somebody added without touching FAMILIES."""
    monkeypatch.setattr(
        doctor, "CHECKS", [(1, "The pin", "t", True, lambda root: None), (2, "New", "t", True, str)]
    )
    assert doctor.families() == ["The pin", "New"]


def test_every_family_in_the_registry_is_one_the_order_names():
    """The list above is the order; this is what stops a family being added to a check and
    landing at the bottom of the screen because nobody updated it."""
    assert {row[1] for row in doctor.CHECKS} == set(doctor.FAMILIES)


PASSES = (1, "The pin", "a check that passes", True, lambda root: None)
FAILS = (2, "The pin", "a check that fails", True, lambda root: "here is what is wrong")
UNKNOWN = (3, "The pin", "a check nothing could answer", True, raises(doctor.Undecidable("why")))
LOCAL = (4, "The pin", "a check a runner cannot answer", False, lambda root: "it ran anyway")


@pytest.mark.parametrize(
    "rows, argv, status, says, never",
    [
        ((PASSES,), [], "PASS", "1 passed · 0 failed · 0 not evaluated", "FAIL"),
        ((FAILS,), [], "FAIL", "0 passed · 1 failed · 0 not evaluated", " ok "),
        ((UNKNOWN,), [], "INCOMPLETE", "Not evaluated is never green", " ok "),
        (
            (PASSES, FAILS, UNKNOWN),
            [],
            "FAIL",
            "1 passed · 1 failed · 1 not evaluated",
            "",
        ),
        ((LOCAL,), ["--ci"], "INCOMPLETE", "SKIPPED", "FAIL"),
        ((LOCAL,), [], "FAIL", "FAIL", "SKIPPED"),
    ],
    ids=[
        "a clean tree is PASS",
        "one failure is FAIL",
        "could not evaluate is not a pass",
        "one of each",
        "--ci leaves a local-only check unrun",
        "outside CI that same check runs",
    ],
)
def test_the_contract_states_and_their_exact_outcomes(
    monkeypatch, capsys, rows, argv, status, says, never
):
    """Counting a check that could not run as one that passed is how somebody reads
    "everything is fine" off a doctor that measured nothing. The --ci rows prove the skip
    is a skip: the local-only check returns a failure, so if it ran the outcome is FAIL."""
    monkeypatch.setattr(doctor, "CHECKS", list(rows))
    monkeypatch.setattr(doctor, "coverage", lambda root, **_: ["  PIN  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    result = doctor.main(argv)
    assert type(result) is outcome.Execution
    assert result.outcome == status
    assert result.checks
    out = capsys.readouterr().out
    assert says in out
    assert not never or never not in out


def test_a_check_that_crashes_stops_the_run_instead_of_scoring_a_pass(monkeypatch, capsys):
    """Undecidable is the only exception doctor knows about. Anything else must not end up
    inside the passed count, because a check that blew up measured nothing."""
    monkeypatch.setattr(doctor, "CHECKS", [(1, "The pin", "t", True, raises(RuntimeError("x")))])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    with pytest.raises(RuntimeError):
        doctor.main([])
    assert "passed" not in capsys.readouterr().out


def test_paths_prints_one_home_per_file_class_and_all_of_them_are_this_machine(
    home, monkeypatch, capsys
):
    """Every file class has one home and doctor prints it. If any of these resolved
    outside the configured framework home, a test here would be writing into a real one."""
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    result = doctor.main(["--paths"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    out = capsys.readouterr().out
    for label, where in (
        ("guards", paths.hooks()),
        ("git hooks", paths.git_hooks()),
        ("skills", paths.home() / "skills"),
        ("record", emit.chain_path(None)),
        ("receipt", wiring.receipt_path()),
    ):
        assert f"  {label:<14}{where}" in out, label
    assert str(home) in out


@pytest.mark.parametrize(
    "name",
    [
        "pin_matches",
        "git_hook_fires",
        "acceptances_current",
        "polarity",
        "data_is_yours",
        "doctrine",
        "branch_protection",
        "production_ready",
    ],
)
def test_outside_a_working_copy_none_of_these_is_green(name):
    """Nine checks mean nothing without a repository. Each has to say so: one that quietly
    returns None there reports ok while looking at nothing at all."""
    with pytest.raises(doctor.Undecidable):
        getattr(doctor, name)(None)


# ------------------------------------------------------------------ the record


@pytest.mark.parametrize(
    "edit, doctor_says, audit_says",
    [
        (lambda rows: rows, "", ""),
        (lambda rows: [rows[0], {**rows[1], "prev": "0" * 64}], "does not extend", "not extend"),
        (
            lambda rows: [{**rows[0], "data": {"r": "rewritten"}}, rows[1]],
            "it was edited",
            "it was edited",
        ),
    ],
    ids=["intact", "linkage broken", "body edited after it was hashed"],
)
def test_the_two_readers_of_the_chain_reach_the_same_verdict(
    home, repo, edit, doctor_says, audit_says
):
    """This used to pin the opposite, and its own docstring named the tension it was
    documenting: assertion 6 walked linkage only, so an event whose body was rewritten
    after its hash was taken read as intact here while `audit` — walking the same file —
    called it edited.

    That is a false green in the direction that matters. `ai-eng doctor` is the summary
    screen; `ai-eng audit verify` is the command somebody runs when they already suspect
    something. Measured on the operator's machine, the verifier exited 1 on 22 broken links
    while this printed "the hash chain is intact and writable".

    Assertion 6 asks the verifier now rather than re-implementing half of it, so the two
    cannot part company again — which is the same finding as the plugin's three copies of
    one substitution, one file over."""
    path = chain(repo, {}, {})
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    path.write_text("".join(json.dumps(row) + "\n" for row in edit(rows)))
    got, detail = verdict(doctor.chain_intact, repo)
    assert (got, doctor_says in detail) == (("fail", True) if doctor_says else ("ok", True))
    problems = audit.verify(repo)
    assert "INTENT_HOME_MISSING" in problems[-1]
    chain_problems = " ".join(problems[:-1])
    assert audit_says in chain_problems
    assert bool(chain_problems) == bool(audit_says)


def test_a_half_written_last_line_is_reported_by_both_readers_of_the_chain(home, repo):
    """A crash part-way through a write leaves half a line behind. doctor used to drop it
    without a word and report the chain intact, and audit, reading the same file, could not
    parse it at all — so the one reader that spoke crashed and the one that ran every session
    called a cut record clean. Both now name the link, and neither passes."""
    path = chain(repo, {}, {})
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"cls": "blo')
    assert len(doctor.events(repo)) == 2
    assert "link 3" in (doctor.chain_intact(repo) or "")
    problems = audit.verify(repo)
    assert len(problems) == 2
    assert "link 3" in problems[0]
    assert "INTENT_HOME_MISSING" in problems[1]


def test_a_chain_that_was_never_written_is_not_a_broken_chain_and_is_not_a_pass_either(home, repo):
    """No events yet is the state of every fresh install, so it is not a failure. It is not
    a pass either: there is nothing to be intact and nothing has been written, and this
    check returned ok for it — having proved only that a directory can be created. Of the
    twenty-one assertions run against an empty repository it was the only one that measured
    nothing and called it clean, which is this product's own definition of the failure."""
    assert doctor.events(repo) == []
    with pytest.raises(doctor.Undecidable, match="nothing has been written"):
        doctor.chain_intact(repo)
    assert emit.chain_path(repo).parent.exists()


def test_doctor_cannot_call_a_chain_intact_that_the_verifier_calls_broken(home, repo):
    """Two readers of one file, and they disagreed. Assertion 6 walked `prev` and `hash`
    only, so a link sealed as `outcome: "edited"` — the literal tamper marker, whose hashes
    all match because it was sealed truthfully — passed it. `ai-eng audit verify` refused
    the same file.

    Measured on the operator's machine: `audit verify` exits 1 on 22 broken links while
    `doctor` prints `ok  The hash chain is intact and writable`. The greener of the two
    verdicts is the one on the summary screen, which is the direction that makes it a
    defect rather than a curiosity.

    Assertion 6 asks the verifier now, so the two cannot part company again."""

    path = chain(repo, {}, {}, {})
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[1]["data"] = {"outcome": "edited", "error": emit.EDITED, "claimed": {}}
    rows[1]["hash"] = emit.digest(rows[1])
    rows[2]["prev"] = rows[1]["hash"]
    rows[2]["hash"] = emit.digest(rows[2])
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    said = doctor.chain_intact(repo)
    assert said
    assert "link 2" in said, f"doctor called a sealed-as-edited chain intact: {said!r}"
    assert [w for w in audit.verify(repo) if "link 2" in w], "the verifier agrees"


def test_a_buffer_that_stopped_being_sealed_is_reported(home, repo):
    """Half of "survives losing the laptop" is the seal, and nothing measured whether it
    still runs. Measured on the operator's machine: the durable chain held 987 links and
    stopped on 2026-08-12, while the in-clone buffer had grown past 4,500 unsealed lines
    and was still growing. `flush()` has exactly one caller outside the suite, on
    `SessionEnd`/`Stop` — so if that path stops firing, every event since sits in a file
    inside the clone, outside the hash chain, and no assertion says a word.

    A buffer is not a failure: it is where events live between seals. A buffer whose oldest
    line has been waiting longer than any session lasts is a seal that stopped."""

    (repo / ".ai").mkdir(exist_ok=True)
    (repo / ".ai" / "config.toml").write_text("[pin]\nversion='1'\n")
    buffer = emit.buffer_path(repo)

    # Written here rather than through `emit`, which resolves the root from the working
    # directory: the buffer under test has to be this repository's, not the one the suite
    # happens to run in.
    fresh = {"ts": emit.now(), "cls": "blocked", "name": "loop_guard", "data": {}}
    buffer.write_text(json.dumps(fresh) + "\n", encoding="utf-8")
    assert doctor.buffer_sealed(repo) is None, "a buffer written moments ago is not a finding"

    buffer.write_text(
        json.dumps({**fresh, "ts": "2020-01-01T00:00:00.000+00:00"}) + "\n", encoding="utf-8"
    )
    said = doctor.buffer_sealed(repo)
    assert said and "unsealed" in said, said
    assert "2020-01-01" in said, said


def test_twenty_declared_capabilities_report_which_half_of_them_is_enforced(home, repo):
    """`policy/capabilities.toml` declares twenty capabilities with read roots, write
    roots, exec allowlists, network hosts, secrets and human gates, and for a long time
    `preflight` validated every one of them and then refused, because no executor existed.

    What nothing did was say so. No assertion, no README line, no verb mentioned it, so a
    reader of six governed fields per capability had no way to learn that none of them
    stopped anything. A declaration nobody enforces and nobody flags is the shape of a false
    green, and the constitution's first duty is to expose that rather than hide it.

    Half of it is enforced now, by `executor.Sandbox`, and the sentence had to move with the
    code or it would have become the same defect pointing the other way — a warning that
    overstates is read once and then discounted, which costs exactly as much as one that
    understates."""

    # Still undecidable and still not FAIL, and the reason is unchanged: what remains open is
    # a measurement about somebody else's software that has never been taken, not a violation
    # this check executed and found. It prints under a heading whose last line is "None of
    # these is a pass." As a failure it made `doctor` red on every machine forever, which is
    # a red nobody can clear and so a red everybody learns to scroll past.
    got, detail = verdict(doctor.capabilities_enforced, repo)
    assert got == "undecidable"
    assert detail.startswith("20 "), detail

    # Both halves, in one sentence. Either alone is a claim a reader would act wrongly on.
    assert "only this framework's own actions are enforced" in detail, detail
    assert "one taken by a surface is not" in detail, detail
    assert "nothing here reads one" in detail, detail


def test_assertion_16_reports_could_not_evaluate_over_a_block_nobody_can_read(home, repo):
    """It read every acceptance through a parser that caught its own failure and moved on,
    so a block with slightly wrong YAML was invisible here and the check reported ok over a
    risk that had expired. Could-not-evaluate is an answer and prints a question mark;
    invisible is a green nobody earned."""
    (repo / "specs" / "001-a").mkdir(parents=True)
    (repo / "specs" / "001-a" / "spec.md").write_text("```yaml\n  broken\n```\n")
    got, detail = verdict(doctor.acceptances_current, repo)
    assert got == "undecidable"
    assert "001-a/spec.md cannot be read" in detail


@pytest.mark.parametrize(
    "archived, want", [(None, "ok"), (2, "ok"), (9, "fail")], ids=["none", "level", "ahead"]
)
def test_assertion_10_a_head_below_the_last_archived_one_means_the_record_was_reset(
    home, repo, archived, want
):
    """The archive remembers how far the chain had got. A head below that number is a file
    that was truncated or started again, which is what deleting evidence looks like."""
    chain(repo, {}, {})
    if archived is not None:
        path = paths.home() / "state" / emit.repo_id(repo) / "archived.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"seq": archived}))
    assert verdict(doctor.continuity, repo)[0] == want


@pytest.mark.parametrize(
    "events, want",
    [
        ([{"data": {"fp": "abc"}}, {"data": {"fp": "abc"}}], "fail"),
        ([{"data": {}}, {"data": {}}], "ok"),
        (
            [{"cls": "allowed", "data": {"fp": "abc"}}, {"cls": "allowed", "data": {"fp": "abc"}}],
            "ok",
        ),
        ([{"data": {"fp": "abc"}}], "ok"),
        (
            [{"cls": "bypassed", "data": {"fp": "a"}}, {"cls": "bypassed", "data": {"fp": "a"}}],
            "fail",
        ),
    ],
    ids=[
        "one call decided twice",
        "no identifier means two calls",
        "allowed is not a decision",
        "deciding once is not deciding twice",
        "a bypass is a decision too",
    ],
)
def test_assertion_15_only_a_call_the_surface_named_can_be_called_a_repeat(
    home, repo, events, want
):
    """Without an identifier from the surface, two decisions over identical arguments are
    two different calls: a retry loop looks exactly like a double delivery. Counting those
    as repeats is what blinded the rule this check replaced."""
    chain(repo, *events)
    assert verdict(doctor.no_double_decision, repo)[0] == want


@pytest.mark.parametrize(
    "allowed, decided, cls, want, fragment",
    [
        (49, 0, "blocked", "undecidable", "too few to judge"),
        (50, 0, "blocked", "fail", "recording noise"),
        (45, 5, "blocked", "ok", ""),
        (45, 5, "bypassed", "ok", ""),
        (45, 5, "command", "ok", ""),
    ],
    ids=[
        "too few to judge",
        "all noise",
        "one in ten was a decision",
        "a bypass was decided too",
        "so was a command",
    ],
)
def test_assertion_8_a_record_where_nothing_was_ever_decided(
    home, repo, allowed, decided, cls, want, fragment
):
    """Under fifty events there is nothing to judge and doctor says so instead of passing.
    Over it, a record that is almost all "a hook ran" is noise in the costume of an audit
    trail — and the one-in-ten boundary is the line, so it is tested at the line. All three
    classes that mean something was decided count, or the ratio reads low for a machine
    that was busy deciding."""
    rows = [{"cls": "allowed", "name": "n"}] * allowed + [{"cls": cls, "name": "n"}] * decided
    emit.append(emit.chain_path(repo), rows)
    got, detail = verdict(doctor.signal_ratio, repo)
    assert (got, fragment in detail) == (want, True)


@pytest.mark.parametrize(
    "days, want",
    [(-1, "fail"), (30, "ok")],
    ids=["expired yesterday", "expires next month"],
)
def test_assertion_16_an_acceptance_that_ran_out_is_not_an_acceptance(repo, days, want):
    """A dated acceptance is what an engineering lead hands an auditor. The day after its
    date it is a note, and both doctor and pre-push have to say so on that day."""
    spec = repo / "specs" / "001-thing" / "spec.md"
    spec.parent.mkdir(parents=True)
    when = (date.today() + timedelta(days=days)).isoformat()
    spec.write_text(f"```yaml\nid: R-001-01\nfinding: a pip CVE\nexpires: {when}\n```\n")
    assert verdict(doctor.acceptances_current, repo)[0] == want


def test_assertions_17_and_18_the_record_is_committed_and_the_state_is_not(repo):
    """.ai/ holds the pin, Intent and ignore rule; anything else of ours inside git is
    state leaking into review, and any framework file committed outside its declared home
    is the first step back toward the 528 files this rebuild deleted."""
    corpus = json.loads((Path(__file__).parent / "fixtures" / "intent-v1.json").read_text())
    canonical = corpus["base"]
    (repo / ".ai" / "config.toml").write_text("")
    (repo / ".ai" / ".gitignore").write_text("events.jsonl\n")
    (repo / ".ai" / "intent.md").write_text(json.dumps(canonical["intent"]))
    for file in canonical["repository"]["files"]:
        target = repo / file["path"]
        target.parent.mkdir(parents=True)
        target.write_text(file["content"])
    git(repo, "add", "-A")
    assert verdict(doctor.polarity, repo) == ("ok", "")
    passed, published = verdict(doctor.data_is_yours, repo)
    # `EP-290` asks for the count and not only the refusal, so the pass is asserted to carry
    # one. Before `Noted` there was no channel for it and this line could only read `("ok",
    # "")` — the same silence a check that inventoried nothing would have produced.
    assert passed == "ok"
    assert "tracked files inventoried" in published
    (repo / ".ai" / "notes.md").write_text("scratch\n")
    (repo / ".ai-engineering").mkdir()
    (repo / ".ai-engineering" / "scripts.py").write_text("")
    git(repo, "add", "-A")
    assert "notes.md" in verdict(doctor.polarity, repo)[1]
    assert "scripts.py" in verdict(doctor.data_is_yours, repo)[1]


# ------------------------------------------------------------------ the controls


@pytest.mark.parametrize(
    "name, result, want, fragment",
    [
        ("guards_alive", None, "undecidable", "never written a result"),
        ("suite_fresh", None, "undecidable", "never written a result"),
        ("guards_alive", {"at": 0}, "fail", "days ago"),
        ("guards_alive", {"at": "now", "guards": {"loop_guard": False}}, "fail", "loop_guard"),
        ("guards_alive", {"at": "now", "guards": {"loop_guard": True}}, "ok", ""),
        ("guards_alive", {"at": "8 days", "guards": {}}, "fail", "8 days ago"),
        ("guards_alive", {"at": "6 days", "guards": {}}, "ok", ""),
        ("suite_fresh", {"deterministic_green": False}, "fail", "deterministic half"),
        ("suite_fresh", {"deterministic_green": True}, "undecidable", "never run here"),
        ("suite_fresh", {"deterministic_green": True, "real_model_at": "now"}, "ok", ""),
        ("suite_fresh", {"deterministic_green": True, "real_model_at": "8 days"}, "fail", "7 days"),
        ("suite_fresh", {"deterministic_green": True, "real_model_at": "6 days"}, "ok", ""),
    ],
)
def test_assertions_7_and_9_a_suite_that_stopped_running_turns_doctor_red(
    home, name, result, want, fragment
):
    """The adversarial suite writes its result where these two read it, so a suite that
    rotted, or that could no longer make a named guard fire, cannot go quietly green. Both
    windows are seven days and both are tested either side of it: a window quietly widened
    to a month is a suite that stopped running three weeks ago reading green."""

    def when(v):
        if v == "now":
            return time.time()
        return time.time() - float(v.split()[0]) * 86400 if isinstance(v, str) else v

    if result is not None:
        stamped = {k: when(v) for k, v in result.items()}
        (paths.home() / "cache" / "suite.json").write_text(json.dumps(stamped))
    got, detail = verdict(getattr(doctor, name), None)
    assert (got, fragment in detail) == (want, True)


@pytest.mark.parametrize("ok, want", [(True, "ok"), (False, "fail")])
def test_assertion_20_a_destination_that_answers_is_not_a_destination_that_delivered(
    home, repo, monkeypatch, ok, want
):
    """With no endpoint configured there is nothing to prove, so this cannot be evaluated.
    With one, a 200 that rejected the records is a failure: believing you have
    observability while sending into a void is worse than having none."""
    assert verdict(doctor.destination_real, repo)[0] == "undecidable"
    (repo / ".ai" / "config.toml").write_text('[observability]\nendpoint = "http://x"\n')
    monkeypatch.setattr(paths.load("_otlp"), "probe", lambda: (ok, "404, 3 rejected"))
    got, detail = verdict(doctor.destination_real, repo)
    assert (got, "404" in detail) == (want, want == "fail")


# ------------------------------------------------------------------ the wiring


def test_assertion_2_a_surface_with_no_entry_in_its_own_settings_file_is_named(
    home, tmp_path, monkeypatch
):
    """A settings file that exists proves nothing: the file the surface reads has to carry
    our entry, and foreign content in it means the guards were never registered. A surface
    we never write to is not named even when it reads a settings file — VS Code Copilot
    reads Claude Code's — because there was never an entry of ours to find there."""
    settings = tmp_path / "settings.json"
    settings.write_text('{"hooks": {"PreToolUse": []}}')
    rows = [
        {"name": "Claude Code", "settings": str(settings), "writer": "json_claude"},
        {"name": "Zed", "settings": "", "writer": "none"},
        {"name": "VS Code Copilot", "settings": str(settings), "writer": "none"},
    ]
    monkeypatch.setattr(wiring, "detect", lambda only=None: rows)
    assert (doctor.wiring_present(None) or "").startswith("Claude Code has no entry")
    settings.write_text('{"hooks": {"PreToolUse": ["/some/where/chain.py"]}}')
    assert doctor.wiring_present(None) is None
    monkeypatch.setattr(paths, "hooks", lambda: tmp_path / "nowhere")
    # A pair, because this branch carries its own empty cure: rewiring cannot restore a
    # dispatcher that ships inside the wheel, so this one must not inherit the number's.
    assert doctor.resolve(2, doctor.wiring_present(None)) == (
        f"the dispatcher is missing at {tmp_path / 'nowhere' / 'chain.py'}",
        "",
    )


@pytest.mark.parametrize(
    "name, kind, fragment",
    [
        ("ghost", None, "is not classified"),
        ("ghost", "telemetry", "which can block"),
        ("ghost", "guard", ""),
        ("autoformat", "telemetry", ""),
    ],
    ids=["unclassified", "telemetry where it can block", "a guard", "autoformat is exempt"],
)
def test_assertion_3_a_hook_on_a_blocking_event_that_is_not_a_guard(
    monkeypatch, name, kind, fragment
):
    """A hook that can deny a tool call and fails open is not a control. This is the second
    of the two contracts, checked at the user's machine rather than only in our CI. One hook
    is exempt by name — autoformat rewrites a file after the call and denies nothing — and
    the exemption is named here so removing it turns every machine red at once."""
    ghost = types.ModuleType(name)

    def run(payload=None):
        return None

    if kind:
        run.hook_class = kind
    ghost.run = run
    monkeypatch.setitem(sys.modules, name, ghost)
    monkeypatch.setattr(paths.load("chain"), "TABLE", {"PreToolUse": [(name, "*")]})
    problem = doctor.classes_are_honest(None) or ""
    assert fragment in problem
    assert bool(problem) == bool(fragment)


@pytest.mark.parametrize(
    "setting, want, fragment",
    [
        ("unset", "undecidable", "no floor"),
        ("tilde", "fail", "tilde"),
        ("empty", "fail", "no pre-commit"),
        ("empty, relatively", "fail", "no pre-commit"),
        ("somebody else's", "fail", "not the directory this install wires"),
        ("ours", "ok", ""),
        ("ours, relatively", "ok", ""),
    ],
)
def test_assertion_11_the_floor_has_to_be_the_one_this_install_wired(
    home, repo, monkeypatch, setting, want, fragment
):
    """git never expands ~ in core.hooksPath. It saves without complaint, the hooks never
    run, and every commit goes through: a floor that is not there is worse than none,
    because the repository looks configured.

    A pre-commit at that path proves something lives there and never that it is ours.
    Several other tools manage git hooks, and any of them left this green over a repository
    where none of our floor runs. The relative case is not decoration: it is the form this
    repository's own bootstrap writes, and a string comparison would fail it."""
    ours = repo.parent / "wheel" / "git-hooks"
    theirs = repo.parent / "husky"
    for folder in (ours, theirs):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "pre-commit").write_text("#!/bin/sh\n")
    monkeypatch.setattr(paths, "git_hooks", lambda: ours)
    empty = repo.parent / "nothing"
    empty.mkdir(exist_ok=True)
    value = {
        "unset": "",
        "tilde": "~/git-hooks",
        "empty": str(empty),
        "empty, relatively": os.path.relpath(empty, repo),
        "somebody else's": str(theirs),
        "ours": str(ours),
        "ours, relatively": os.path.relpath(ours, repo),
    }
    if value[setting]:
        git(repo, "config", "core.hooksPath", value[setting])
    # The anchor half of this assertion is exercised on its own below. Here it is wired the
    # way `init` wires it and its liveness is stood in for, so a case that is about the
    # hooks path is decided by the hooks path — and never by whether this machine happens
    # to hold a chain that can be anchored.
    git(repo, "config", "ai.eng", f"{sys.executable} -m ai_engineering.cli")
    monkeypatch.setattr(doctor, "_cli_answers", lambda root: None)
    got, detail = verdict(doctor.git_hook_fires, repo)
    assert (got, fragment in detail) == (want, True)


def test_a_git_that_cannot_be_run_leaves_the_check_unevaluated_rather_than_green(repo, monkeypatch):
    """When git itself will not execute, doctor learned nothing about the hooks path. An
    empty answer read as "no problem" is exactly the green nobody earned."""

    def boom(*args, **kwargs):
        raise OSError("git is not on the PATH")

    monkeypatch.setattr(doctor.subprocess, "run", boom)
    assert verdict(doctor.git_hook_fires, repo)[0] == "undecidable"


@pytest.mark.parametrize(
    "pin, want, fragment",
    [
        (None, "undecidable", "nothing is pinned"),
        ("0.0.1", "fail", __version__),
        (__version__, "ok", ""),
    ],
    ids=["nothing pinned", "pinned to another wheel", "the wheel that is running"],
)
def test_assertion_12_the_wheel_running_is_the_wheel_this_repository_pinned(
    repo, home, pin, want, fragment
):
    """A repository pinned to a version nobody has installed is running whatever happened
    to be on the PATH, which is the difference between a control and a coincidence."""
    if pin:
        (repo / ".ai" / "config.toml").write_text(f'[framework]\nversion = "{pin}"\n')
    got, detail = verdict(doctor.pin_matches, repo)
    assert (got, fragment in detail) == (want, True)


def test_assertion_12_also_catches_an_entry_left_pointing_at_an_install_that_moved(
    repo, home, monkeypatch
):
    """Nothing is ever copied out of the wheel, so every entry is a path into it. When the
    interpreter moves, an old entry still says ai-engineering, still looks installed, and
    calls a file that is gone."""
    (repo / ".ai" / "config.toml").write_text(f'[framework]\nversion = "{__version__}"\n')
    settings = home / "settings.json"
    settings.write_text('{"command": "python /somewhere/else/ai-engineering/chain.py"}')
    live = home / "live.json"
    live.write_text(json.dumps({"command": f"ai-engineering {paths.hooks()}/chain.py"}))
    rows = [
        {"name": "Zed", "settings": ""},
        {"name": "Cursor", "settings": str(home / "never-written.json")},
        {"name": "OpenCode", "settings": str(live)},
        {"name": "Claude Code", "settings": str(settings)},
    ]
    monkeypatch.setattr(wiring, "detect", lambda only=None: rows)
    assert "another install" in verdict(doctor.pin_matches, repo)[1]
    assert "OpenCode" not in verdict(doctor.pin_matches, repo)[1]


@pytest.mark.parametrize(
    "assertion, fragment",
    [
        (doctor.wiring_present, "no surface that takes a guard entry"),
        (doctor.links_resolve, "no surface with a skills root is installed here"),
        (doctor.surfaces_alive, "no surface is installed here"),
    ],
    ids=["2 the guard entries", "13 the skill roots", "21 the liveness"],
)
def test_three_assertions_that_used_to_pass_by_iterating_an_empty_list(
    home, repo, assertion, fragment
):
    """Decline the machine half of `ai-eng init`, or pass --no-global, and the project half
    still wires the repository: core.hooksPath is set and ai.managed goes true. No receipt
    is written and no surface is installed, and these three then looped over nothing and
    printed ok — a governed repository on a machine with no guards, reporting a green
    wiring section that had earned nothing. An empty loop is not a passing check, it is a
    question nobody asked, and this doctor already had the state for that answer."""
    got, detail = verdict(assertion, repo)
    assert got == "undecidable"
    assert fragment in detail


def break_the_guard_entry(home, repo, monkeypatch) -> None:
    settings = home / "settings.json"
    settings.write_text('{"hooks": {"PreToolUse": []}}')
    rows = [{"name": "Claude Code", "settings": str(settings), "writer": "json_claude"}]
    monkeypatch.setattr(wiring, "detect", lambda only=None: rows)


def break_the_hooks_path(home, repo, monkeypatch) -> None:
    git(repo, "config", "core.hooksPath", str(repo / "no-hooks-here"))


def break_the_skills_link(home, repo, monkeypatch) -> None:
    """A surface that is here with a skills root holding none of ours. It used to be a
    receipt row pointing at a directory that did not exist, which stopped being the question
    the moment the check started looking inside the root instead of at it."""
    (home / ".claude" / "skills").mkdir(parents=True)


def break_the_pin(home, repo, monkeypatch) -> None:
    (repo / ".ai" / "config.toml").write_text('[framework]\nversion = "0.0.1"\n')


@pytest.mark.parametrize(
    "number, assertion, arrange, cure",
    [
        (2, doctor.wiring_present, break_the_guard_entry, "ai-eng init --global --no-project"),
        (11, doctor.git_hook_fires, break_the_hooks_path, "ai-eng init --project"),
        (13, doctor.links_resolve, break_the_skills_link, "ai-eng init --global --no-project"),
        (12, doctor.pin_matches, break_the_pin, "ai-eng update"),
    ],
    ids=["2 the guard entry", "11 the hooks path", "13 the skills link", "12 the pin"],
)
def test_every_failure_a_command_can_repair_names_that_command(
    home, repo, monkeypatch, number, assertion, arrange, cure
):
    """ADR 0003 as an exit code. Not one check in this file named a command to run; these
    four have a cure, so they carry it, and adding a fifth check with a cure and no command
    fails here. The set is named in this list rather than inferred, because "does this check
    have a cure" is a judgement no script can make.

    The cure is a field and no longer a sentence at the end of the message: prose could say
    `ai-eng init --global` to a reader and nothing could run it, so `--fix` would have had
    to parse English out of a failure message to know what to do."""
    arrange(home, repo, monkeypatch)
    got, detail = verdict(assertion, repo)
    assert got == "fail", detail
    # The exact verb, not the shape of one: a cure reading `ai-eng frobnicate` matches any
    # pattern for "names a command" and repairs nothing.
    assert doctor.resolve(number, assertion(repo))[1] == cure
    # And it is not left in the prose as well, because two homes for one fact is how the
    # message and the flag come to disagree about what to run.
    assert "ai-eng" not in detail, detail


@pytest.mark.parametrize(
    ("line", "style"),
    [
        ("  T2   claude-code      BLOCKS    a denial has executed here", "ok"),
        ("  T2   codex-cli        INERT     installed and unapproved", "warn"),
        ("  T2   cursor           UNPROVEN  not installed here", "warn"),
        ("  T3   pi               ADVISES   reads the skills", "muted"),
        ("  PIN  wheel 1.0.0 = pinned 0.9.0  MISMATCH", "fail"),
        ("  OPEN  --no-verify from your own shell", "warn"),
        ("  a row with none of the vocabulary in it", ""),
    ],
)
def test_a_coverage_row_takes_its_colour_from_the_word_in_it_and_not_from_a_column(line, style):
    """The colour used to be looked up by the row's last token, so it was one column-width
    edit away from being wrong about what the row said. Driven directly, because the suite
    reads the undecorated stream where a wrong style and a right one are the same bytes."""
    assert doctor.tint(line) == style


def test_the_help_explains_every_flag_including_the_one_that_writes(monkeypatch, capsys):
    """`--help` is the only documentation reachable without a browser, and `--fix` is the
    one flag on this verb that changes the machine — a flag that writes and does not say so
    where a person looks for what a flag does is the failure this product is about."""
    monkeypatch.setenv("COLUMNS", "200")
    with pytest.raises(SystemExit) as stopped:
        doctor.main(["--help"])
    assert stopped.value.code == 0
    text = capsys.readouterr().out
    assert text.startswith("usage: ai-eng doctor ")
    for phrase in (
        "only the checks a runner can answer",
        "print where every file class lives",
        "run the cures the failures name",
    ):
        assert phrase in text, phrase


def test_a_failure_whose_number_carries_no_cure_resolves_to_an_empty_one(monkeypatch):
    """Seventeen of the twenty-one are this case. An absent cure has to arrive as the empty
    string and not as None: it is printed, compared and put in a dict, and None survives
    all three while changing what the `you:` line means."""
    assert doctor.resolve(99, "something broke") == ("something broke", "")


def stub(monkeypatch, rows):
    """A doctor whose twenty-one checks are whatever this test needs, run outside any
    repository so nothing on the machine can change the answer."""
    monkeypatch.setattr(doctor, "CHECKS", rows)
    monkeypatch.setattr(doctor, "coverage", lambda root, **_: ["  PIN  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)


@pytest.mark.parametrize(
    ("rows", "title", "count", "line"),
    [
        (
            [
                (7, "The controls", "a", True, lambda root: "broken"),
                (4, "The context", "b", True, lambda root: "broken"),
            ],
            "FAILED",
            "0 passed · 2 failed · 0 not evaluated",
            "needs a person  2   assertions 4, 7",
        ),
        (
            [(4, "The context", "b", True, lambda root: None)],
            "OK",
            "1 passed · 0 failed · 0 not evaluated",
            "",
        ),
    ],
    ids=["two on a person, in order", "nothing failed"],
)
def test_the_verdict_names_the_assertions_a_person_has_to_go_and_read(
    monkeypatch, capsys, rows, title, count, line
):
    """The count is not enough: "2 need a person" over twenty-one rows that have scrolled
    past sends somebody back up the screen to find which two. They are listed, sorted, and
    the word agrees with the number — a panel reading "1 assertions" was written by nobody.

    The title is asserted with its frame. `"FAILED" in out` passes on a title that reads
    XXFAILEDXX, which is exactly the mutant it was supposed to catch."""
    stub(monkeypatch, rows)
    doctor.main([])
    out = capsys.readouterr().out
    assert f"╭─ {title} ─" in out
    # The count row carries no label, so it starts immediately after the frame: a label
    # there pushes it sixteen columns right and stops it lining up with the two under it.
    assert f"│ {count} " in out
    assert (line in out) if line else ("needs a person" not in out and "FAILED" not in out)


def test_the_whole_report_is_data_and_none_of_it_is_chrome(monkeypatch, capsys):
    """`ai-eng doctor > report.txt` has to yield the report. Every line of this verb is the
    report — there is no progress and no question — so anything reaching stderr is a line
    that will be missing from the file somebody opens, and this is the one assertion that
    holds all thirty of them at once.

    The unanswered block is written out whole because it is where a skipped check and a
    check that refused to answer end up side by side, each with the reason it gave."""
    stub(
        monkeypatch,
        [
            (1, "The context", "ran", True, lambda root: None),
            (2, "The context", "local only", False, lambda root: None),
            (3, "The context", "refused", True, raises(doctor.Undecidable("no endpoint"))),
        ],
    )
    result = doctor.main(["--ci"])
    assert type(result) is outcome.Execution
    assert result.outcome == "INCOMPLETE"
    assert [fact.status for fact in result.checks[:3]] == ["PASS", "SKIPPED", "INCOMPLETE"]
    caught = capsys.readouterr()
    assert caught.err == "", "a line of the report went to the wrong stream"
    assert (
        "\nNot evaluated — 2 of 3 could not be answered here\n"
        "   2  local only\n"
        "      needs a real working copy\n"
        "   3  refused\n"
        "      no endpoint\n"
        "  None of these is a pass. Not evaluated is never green.\n"
    ) in caught.out


def test_the_three_muted_kinds_of_line_under_the_report_are_dressed_as_such(
    monkeypatch, capsys, coloured
):
    """The legend, the reasons under the unanswered rows and the sentence that says none of
    them is a pass. Undecorated all three are ordinary text in a screen that is mostly
    ordinary text, and the last one is a warning — the whole point of printing it."""
    stub(monkeypatch, [(3, "The context", "refused", True, raises(doctor.Undecidable("why")))])
    monkeypatch.setattr(
        doctor, "coverage", lambda root, **_: ["  T2  a  BLOCKS  a denial ran here"]
    )
    doctor.main([])
    out = capsys.readouterr().out
    styles = doctor.ui.THEME.styles
    assert styles["muted"].render(doctor.LEGEND[0]) in out
    assert styles["muted"].render("      why") in out
    assert styles["warn"].render("  None of these is a pass. Not evaluated is never green.") in out
    # And the coverage row wears what its own word chose. This is the only place the two
    # halves meet: `tint` picks the style and this loop is what applies it.
    assert styles["ok"].render("  T2  a  BLOCKS  a denial ran here") in out
    doctor.ui.reset()


@pytest.mark.parametrize(
    ("problem", "colour"), [(lambda root: "broken", "red"), (lambda root: None, "#00D4AA")]
)
def test_the_verdict_frame_takes_its_colour_from_the_answer(
    monkeypatch, capsys, problem, colour, coloured
):
    """Undecorated the two verdicts are the same box, so the colour is the one part of this
    that the rest of the suite cannot see — and it is the part read first."""
    stub(monkeypatch, [(4, "The context", "b", True, problem)])
    doctor.main([])
    assert Style.parse(colour).render("─").split("─")[0] in capsys.readouterr().out
    doctor.ui.reset()


@pytest.fixture
def invoked(monkeypatch):
    """Every argv `--fix` hands to the CLI, and nothing actually runs. The commands it
    names write to a machine, and a test that lets them run is a test that installs this
    product onto whoever is running the suite."""
    calls = []
    monkeypatch.setattr(cli, "main", lambda argv: calls.append(list(argv)) or 0)
    return calls


def test_fix_runs_the_verb_that_already_carries_the_consent_and_then_asks_again(
    monkeypatch, capsys, invoked
):
    """ADR 0003's whole argument, as an assertion. `--fix` names a verb and does not
    reimplement it, so the gates that verb carries are still in front of the write — and it
    re-runs the diagnosis afterwards, because a repair nobody re-measured is a claim.

    The stub check keeps failing, so the second pass fails too: `--fix` reports what is
    true after the attempt and never what it hoped for."""
    monkeypatch.setattr(doctor, "CHECKS", [(2, "The pin", "wiring", True, lambda root: "broken")])
    monkeypatch.setattr(doctor, "coverage", lambda root, **_: ["  PIN  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    result = doctor.main(["--fix"])
    assert type(result) is outcome.Execution
    assert result.outcome == "FAIL"
    assert result.checks
    # -y is appended and --no-project is not: one is how a cure runs unattended, the other
    # is in the cure itself, so repairing a machine cannot set up a stray repository.
    assert invoked == [["init", "--global", "--no-project", "-y"]]
    out = capsys.readouterr().out
    assert out.count("   2  FAIL     wiring") == 2, "the second pass never ran"
    # The blank line above it is part of the assertion: it is written to the same stream as
    # the command, and a repair whose commands land on stderr is a repair missing from the
    # transcript somebody pastes into a bug report.
    assert "\n\n  running ai-eng init --global --no-project -y\n" in out


def test_fix_runs_each_distinct_cure_once_however_many_checks_named_it(
    monkeypatch, capsys, invoked
):
    """Three failures, two commands. Running `init --global` once per check that wants it
    is three installs, and the third one is where a duplicated guard entry comes from."""
    monkeypatch.setattr(
        doctor,
        "CHECKS",
        [
            (2, "The pin", "a", True, lambda root: "broken"),
            (13, "The pin", "b", True, lambda root: "broken"),
            (11, "The pin", "c", True, lambda root: "broken"),
        ],
    )
    monkeypatch.setattr(doctor, "coverage", lambda root, **_: ["  PIN  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    doctor.main(["--fix"])
    assert invoked == [["init", "--global", "--no-project", "-y"], ["init", "--project", "-y"]]


def test_a_cure_whose_verb_asks_a_person_something_is_printed_and_never_run(monkeypatch, invoked):
    """`ai-eng update` refuses on a dirty tree, refuses without a keyboard and asks for a
    typed y, and those three gates are the whole reason ADR 0003 is allowed to exist. `--fix`
    runs its cures through cli.main with nobody in front of them, so running this one stopped
    the repair mid-way for a keystroke, or read update's own refusal as a failed repair and
    abandoned the rest. Assertion 12 still names the command; a person types it."""
    monkeypatch.setattr(
        doctor, "CHECKS", [(12, "The pin", "pin", True, lambda root: ("stale", "ai-eng update"))]
    )
    monkeypatch.setattr(doctor, "coverage", lambda root, **_: ["  PIN  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    doctor.main(["--fix"])
    assert invoked == []


def test_which_cures_fix_may_run_is_decided_by_the_verb_and_survives_a_short_one():
    """The allow-list is read out of the cure, so the shape of the string decides whether a
    verb is ever looked up. A cure of one word must answer no rather than index past the end
    of it, and a cure of exactly two words — the shortest real one — must still answer yes,
    or `--fix` silently stops repairing the thing it says it repairs."""
    assert doctor.unattended("ai-eng init")
    assert doctor.unattended(doctor.FIXES[2])
    assert not doctor.unattended("ai-eng update")
    assert not doctor.unattended("init") and not doctor.unattended("")


def test_fix_with_nothing_it_can_repair_says_so_and_writes_nothing(monkeypatch, capsys, invoked):
    """The failure that has no command is the common one — seventeen of the twenty-one —
    and a flag that silently does nothing reads as a flag that ran."""
    monkeypatch.setattr(doctor, "CHECKS", [(4, "The context", "yours", True, lambda root: "TODO")])
    monkeypatch.setattr(doctor, "coverage", lambda root, **_: ["  PIN  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    result = doctor.main(["--fix"])
    assert type(result) is outcome.Execution
    assert result.outcome == "FAIL"
    assert result.checks
    assert invoked == []
    assert (
        "\n  Nothing that failed here has a command --fix runs for you.\n"
    ) in capsys.readouterr().out


def test_a_cure_that_exits_non_zero_stops_the_rest_instead_of_reporting_a_clean_run(
    monkeypatch, capsys
):
    """A repair that failed and a repair that was never attempted are different things, and
    running the second command over the wreckage of the first is how one broken install
    becomes two. A child's integer exit is not canonical proof, so doctor is INCOMPLETE."""
    monkeypatch.setattr(cli, "main", lambda argv: 3)
    monkeypatch.setattr(
        doctor,
        "CHECKS",
        [
            (2, "The pin", "a", True, lambda root: "broken"),
            (11, "The pin", "b", True, lambda root: "broken"),
        ],
    )
    monkeypatch.setattr(doctor, "coverage", lambda root, **_: ["  PIN  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    result = doctor.main(["--fix"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    out = capsys.readouterr().out
    assert "  it exited 3. The rest is not attempted." in out
    assert out.count("   2  FAIL     a") == 1, "it asked again after a repair that failed"


def test_the_command_a_repair_runs_and_the_one_that_failed_are_dressed_apart(
    monkeypatch, capsys, coloured
):
    """`--fix` prints two kinds of line: the command it is about to run, which is what a
    person re-runs by hand when it goes wrong, and the sentence saying one exited non-zero.
    Undecorated they are two runs of ordinary text, and the second is the one that matters."""
    monkeypatch.setattr(cli, "main", lambda argv: 3)
    stub(monkeypatch, [(11, "The pin", "a", True, lambda root: "broken")])
    result = doctor.main(["--fix"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    out = capsys.readouterr().out
    styles = doctor.ui.THEME.styles
    assert styles["cmd"].render("  running ai-eng init --project -y") in out
    assert styles["fail"].render("  it exited 3. The rest is not attempted.") in out
    doctor.ui.reset()


def test_a_missing_dispatcher_names_no_cure_because_no_command_puts_it_back(
    home, repo, monkeypatch, tmp_path
):
    """The dispatcher lives inside the wheel and is never copied out, so no `ai-eng` verb
    can restore it. Printing one anyway would be the same defect as the `doctor` check
    nobody wrote, committed by the commit that went round deleting those."""
    monkeypatch.setattr(paths, "hooks", lambda: tmp_path / "nowhere")
    got, detail = verdict(doctor.wiring_present, repo)
    assert (got, "dispatcher is missing" in detail) == ("fail", True)
    assert "`ai-eng" not in detail


def test_the_summary_counts_an_unanswerable_wiring_section_as_not_evaluated(
    home, repo, monkeypatch, capsys
):
    """The three above have to reach the printed summary as "not evaluated" rather than
    disappearing into the passed count, which is the number a person actually reads."""
    monkeypatch.setattr(paths, "repo_root", lambda start=None: repo)
    monkeypatch.setattr(
        doctor,
        "CHECKS",
        [row for row in doctor.CHECKS if row[4] in (doctor.wiring_present, doctor.links_resolve)],
    )
    doctor.main([])
    out = capsys.readouterr().out
    assert "0 passed · 0 failed · 2 not evaluated" in out
    assert " ok " not in out


def test_the_coverage_line_survives_a_machine_with_nothing_installed(home, repo):
    """coverage() reads assertion 21 to mark a surface INERT. Now that 21 refuses to answer
    on an empty machine, the coverage line has to keep printing rather than take the
    exception with it — every row there already reads UNPROVEN for the same reason."""
    lines = doctor.coverage(repo)
    assert len(lines) == 1 + len(wiring.table()["surface"]) + len(doctor.OPEN)
    assert all("INERT" not in line for line in lines)


def test_assertion_13_a_skills_root_holding_none_of_ours_and_a_doctrine_nobody_imports(home, repo):
    """Skills are linked, or copied where links do not work, and the surface's own updater
    can delete either. And a CLAUDE.md that does not import AGENTS.md means the doctrine
    reaches the model in no session at all.

    The root is the room and the links are what is in it. This asked whether the room
    exists, which it does — the surface made it, and it goes on existing because it holds
    skills that belong to the user — so every link of ours could be deleted under a check
    titled `Every symlink resolves` reporting ok."""
    store = paths.home() / "skills"
    (store / "ai-spec").mkdir(parents=True)
    root = home / ".claude" / "skills"
    root.mkdir(parents=True)
    (root / "theirs").mkdir()
    assert "hold none of ours" in verdict(doctor.links_resolve, repo)[1]

    (root / "ai-spec").symlink_to(store / "ai-spec")
    (repo / "CLAUDE.md").write_text("do whatever you like\n")
    assert "does not import" in verdict(doctor.links_resolve, repo)[1]
    (repo / "CLAUDE.md").write_text("@./AGENTS.md\n")
    assert verdict(doctor.links_resolve, repo) == ("ok", "")

    (root / "ai-spec").unlink()
    assert "hold none of ours" in verdict(doctor.links_resolve, repo)[1]


@pytest.mark.parametrize(
    "age_days, want",
    [(None, "fail"), (2, "fail"), (0, "ok")],
    ids=["never reported", "two days old", "fresh"],
)
def test_assertion_21_a_plugin_that_stopped_loading_reports_nothing_at_all(home, age_days, want):
    """OpenCode drops a malformed plugin with no error and no log, so the only evidence it
    is running is a heartbeat file — and a heartbeat that never expires would report a dead
    plugin as alive forever."""
    # Wired, then asked whether it is running. Unwired, it is a different failure with a
    # different cure, and the answer this test is about never comes up.
    (home / ".config" / "opencode").mkdir(parents=True)
    wiring.ts_opencode(wiring.expand("~/.config/opencode/plugins/ai-engineering.ts"))
    if age_days is not None:
        beat = paths.home() / "cache" / "opencode-heartbeat"
        beat.write_text("")
        os.utime(beat, (time.time() - age_days * 86400,) * 2)
    assert verdict(doctor.surfaces_alive, None)[0] == want


@pytest.mark.parametrize("trusted, want", [(None, "fail"), ("trust.json", "ok")])
def test_assertion_21_an_untrusted_codex_hook_is_installed_and_inert(home, trusted, want):
    """Codex skips a hook nobody approved with no prompt and no log, so installed-and-inert
    looks exactly like installed-and-working until somebody runs /hooks."""
    (home / ".codex").mkdir()
    wiring.json_codex(home / ".codex" / "hooks.json")
    if trusted:
        (home / ".codex" / trusted).write_text("{}")
    got, detail = verdict(doctor.surfaces_alive, None)
    assert (got, "INERT" in detail) == (want, want == "fail")


def test_assertion_21_stops_offering_to_approve_an_entry_nobody_has_written(home):
    """It told you to type /hooks in Codex to approve a guard that was not there to approve.
    Approving an entry nobody has written is not a thing a person can do, so the command
    that writes it comes first — which is ADR 0003's rule, on a shape spec 007 wrote it
    before seeing."""
    (home / ".codex").mkdir()
    got, detail = verdict(doctor.surfaces_alive, None)
    assert got == "fail"
    assert "no entry of ours, so nothing can run" in detail
    assert "INERT" not in detail, "it offered /hooks for an entry that is not there"
    assert doctor.resolve(21, doctor.surfaces_alive(None))[1] == doctor.FIXES[2]


@pytest.mark.parametrize(
    "gh, reply, want, fragment",
    [
        (None, (0, ""), "undecidable", "gh is not installed"),
        ("/usr/bin/gh", (1, ""), "undecidable", "did not succeed"),
        ("/usr/bin/gh", (0, '{"required_status_checks": {"contexts": []}}'), "fail", "T0"),
        ("/usr/bin/gh", (0, '{"required_status_checks": {"contexts": ["CI"]}}'), "ok", ""),
    ],
    ids=["no gh", "the API refused", "no required check", "one required check"],
)
def test_assertion_14_a_default_branch_anybody_can_push_to(
    repo, monkeypatch, gh, reply, want, fragment
):
    """T0 is the only layer nothing typed locally can skip, and it exists on the server or
    not at all. Asking and being refused is not the same as asking and hearing yes, so a
    token that cannot see the setting has to read as not evaluated."""
    monkeypatch.setattr(doctor.shutil, "which", lambda name: gh)
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *a, **k: types.SimpleNamespace(returncode=reply[0], stdout=reply[1]),
    )
    got, detail = verdict(doctor.branch_protection, repo)
    assert (got, fragment in detail) == (want, True)


# ------------------------------------------------------------------ the context


def test_assertion_1_a_skill_that_breaks_the_contract_is_named_on_the_users_machine(
    tmp_path, monkeypatch
):
    """The skills are checked in our CI and again where they are installed, because the
    copy that ships is the one that can drift and drift there reaches every session."""
    skill = tmp_path / "skills" / "ai-thing" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    monkeypatch.setattr(paths, "skills", lambda: tmp_path / "skills")
    skill.write_text("---\nname: ai-thing\ndescription: does things\n---\n")
    assert "Not for" in (doctor.skills_contract(None) or "")
    skill.write_text("---\nname: ai-thing\ndescription: does things. Not for x — use /ai-y\n---\n")
    # The routing corpus is part of the contract now, so a skill with a correct header and
    # nothing that can judge its routing is still incomplete — which is the whole point of
    # D-012-01: every check above this one is about the file's shape.
    assert "no corpus.md" in (doctor.skills_contract(None) or "")
    (skill.parent / "corpus.md").write_text(
        "# Corpus\n\n## Routes here\n\n- a thing — it is the thing\n\n"
        "## Refuses\n\n- another thing — use `/ai-y`\n"
    )
    # The skill must also read as craft-clean (spec 032): an artifact it produces and an
    # anti-rationalization entry, or the doctor reports the craft rules, not None.
    skill.write_text(
        "---\nname: ai-thing\ndescription: does things. Not for x — use /ai-y\n---\n"
        "# Do the thing\n\n## What it produces\n\n`out/result.md`\n\n## What this is not\n\n"
        '- "It\'s simple" — then it is fast to prove; do it now.\n'
    )
    assert doctor.skills_contract(None) is None


@pytest.mark.parametrize(
    "agents, identity, want, fragment",
    [
        (None, "we build things", "fail", "AGENTS.md is missing"),
        ("line\n" * 151, "we build things", "fail", "150 lines"),
        ("line\n", None, "fail", "identity was never written"),
        ("line\n", "TODO: say what this is", "fail", "TODO:"),
        ("line\n", "we build things", "ok", ""),
    ],
    ids=["no doctrine", "over the budget", "no identity", "not filled in", "both present"],
)
def test_assertion_4_the_always_loaded_budget_and_the_identity_behind_it(
    repo, agents, identity, want, fragment
):
    """AGENTS.md is loaded in every session in every repository forever, so its length is a
    cost paid on every call. A CONSTITUTION.md still holding TODO: markers is a template,
    not an identity, and no gate can tell the difference for you."""
    if agents:
        (repo / "AGENTS.md").write_text(agents)
    if identity:
        (repo / "CONSTITUTION.md").write_text(identity)
    got, detail = verdict(doctor.doctrine, repo)
    assert (got, fragment in detail) == (want, True)


BOXES = "## Production-ready\n\n"


@pytest.mark.parametrize(
    "body, want",
    [
        (f"status: shipped\n\n{BOXES}- [ ] write the runbook\n", "fail"),
        (f"status: shipped\n\n{BOXES}- [x] write the runbook\n", "fail"),
        (f"status: shipped\n\n{BOXES}- [x] the runbook: `just runbook`\n", "ok"),
        (f"status: shipped\n\n{BOXES}- [x] Traces — not applicable, no second hop\n", "ok"),
        (f"status: draft\n\n{BOXES}- [x] write the runbook\n", "ok"),
        ("status: shipped\n\nNothing here has a box.\n", "ok"),
        (f"status: shipped\n\n- [x] a box above the heading\n{BOXES}- [x] `ok`\n", "ok"),
    ],
    ids=[
        "shipped with an open box",
        "shipped ticked, and nothing beside the tick",
        "shipped ticked, with a command",
        "shipped ticked, and honestly not applicable",
        "still a draft",
        "no boxes at all",
        "a tick outside the section is not this check's business",
    ],
)
def test_assertion_19_reads_the_tick_and_what_was_written_beside_it(repo, body, want):
    """It searched a shipped spec for an unticked box and never read a ticked one, so it
    enforced that the question was answered and never that the answer said anything. Three
    of the eight boxes in this repository's own shipped spec claimed a control and named no
    command, and /ai-ship carried a sentence asking for one with no assertion behind it.

    A spec that never had a box still passes, which is the hole this check has always had:
    deleting the list is a way to ship. status: never sits on the first line of a real
    spec, so the fixture puts frontmatter above it."""
    spec = repo / "specs" / "042-thing" / "spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(f"---\ntitle: a thing\n{body}---\n")
    got, detail = verdict(doctor.production_ready, repo)
    assert (got, "042-thing" in detail) == (want, want == "fail")


@pytest.mark.parametrize(
    "line, want",
    [
        ("TODO: why this is acceptable, in one sentence", "fail"),
        ("  - TODO: what has to happen before it expires", "fail"),
        ("3. TODO: the third real option", "fail"),
        ("`ai-eng accept` used to write `TODO: a person, by name` here", "ok"),
    ],
    ids=["at the start", "under a list marker", "under a numbered one", "quoted inline"],
)
def test_a_shipped_spec_may_not_carry_a_marker_nobody_replaced(repo, line, want):
    """The template ships a marker in every section and `ai-eng accept` used to write three
    more into the record whenever a person or a reason was omitted, while assertion 16
    compares only the expiry date. The second case is the one that matters: the unanchored
    form assertion 4 uses has exactly one red across every spec in this tree, and it is the
    document that proposed this rule, which quotes the literal strings as evidence. A gate
    whose only red is the spec arguing for it is a trap, not a gate."""
    spec = repo / "specs" / "042-thing" / "spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(f"---\ntitle: a thing\nstatus: shipped\n---\n\n{line}\n\n{BOXES}- [x] `ok`\n")
    assert verdict(doctor.production_ready, repo)[0] == want


# ------------------------------------------------------------------ the coverage line


def test_a_surface_that_is_not_installed_here_reads_unproven_and_never_covered(home, repo):
    """Nothing is installed on this machine, so the honest line for every surface —
    including the one where a denial really has executed — is UNPROVEN."""
    lines = doctor.coverage(repo)
    assert all("BLOCKS" not in line for line in lines)
    assert sum("not installed" in line for line in lines) == len(wiring.table()["surface"])


def test_no_surface_reads_as_covered_where_no_denial_has_ever_executed(home, repo):
    """The coverage line is the honesty layer. proven = false in the wiring table means
    nobody has watched that surface refuse anything, and installing it cannot turn that
    into BLOCKS. The two surfaces that fail silently read INERT — and the same silence
    fails assertion 21, which is where the exit code comes from."""
    for surface in wiring.table()["surface"]:
        target = home / surface["detect"].removeprefix("~/")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix:
            target.write_text("{}\n")
        else:
            target.mkdir(exist_ok=True)
    # Wired, and not merely present. Making the vendor's directory used to be enough for a
    # row to read BLOCKS, which is how the honesty layer certified four surfaces on a
    # machine `ai-eng uninstall` had emptied a second earlier.
    for surface in wiring.table()["surface"]:
        if surface["writer"] != "none":
            wiring.WRITERS[surface["writer"]](wiring.expand(surface["settings"]))
    lines = doctor.coverage(repo)
    ids = [s["id"] for s in wiring.table()["surface"]]
    rows = dict(zip(ids, lines[1 : 1 + len(ids)], strict=True))
    # Not one row, now: the word comes from an enforcement receipt and this repository has
    # never written one. claude-code reads UNPROVEN here not because it lost a capability
    # but because nobody ever receipted the denial it is perfectly able to execute — which
    # is the sentence spec 010 wrote about three surfaces, arriving for all eight.
    assert not [name for name in ids if "BLOCKS" in rows[name]]
    assert "INERT" in rows["opencode"] and "INERT" in rows["codex-cli"]
    assert "no denial has ever run here" in rows["claude-code"]
    assert "MISMATCH" in lines[0]
    assert doctor.surfaces_alive(None) is not None


def test_assertion_11_rejects_a_live_interpreter_with_a_dead_ai_eng_module(home, repo, monkeypatch):
    """A configured anchor is a string somebody wrote. This runs it.

    The state this cures was found on a real machine: an editable install whose `.pth`
    pointed at a deleted worktree, so the interpreter was alive, `ai_engineering.cli` was
    dead, `git config --get ai.eng` answered, and every hook that resolved the CLI through
    it failed on a repository somebody had just installed into. Assertion 11 said the wiring
    was fine, because the string was there.

    What it will not do is execute whatever the value happens to hold. A configured command
    that gets run is a configured command that can be anything, on a machine that may
    already be doing what an injected instruction told it to — so the value must decompose
    to exactly this interpreter and this module, and that argument list is the only thing
    this check ever runs.
    """

    ours = repo.parent / "wheel" / "git-hooks"
    ours.mkdir(parents=True, exist_ok=True)
    (ours / "pre-commit").write_text("#!/bin/sh\n")
    monkeypatch.setattr(paths, "git_hooks", lambda: ours)
    git(repo, "config", "core.hooksPath", str(ours))

    # No anchor at all is undecidable: the hooks have no CLI to resolve.
    assert verdict(doctor.git_hook_fires, repo)[0] == "undecidable"

    # A value that is not this interpreter and this module is refused without being run.
    for foreign in (
        "ai-eng",
        "/usr/bin/python3 -m ai_engineering.cli",
        f"{sys.executable} -m ai_engineering.cli; rm -rf /",
        f"{sys.executable} -c 'print(1)'",
        f"sh -c '{sys.executable} -m ai_engineering.cli'",
    ):
        git(repo, "config", "ai.eng", foreign)
        state, detail = verdict(doctor.git_hook_fires, repo)
        assert state == "fail", foreign
        assert "does not name this interpreter and this module" in detail, foreign
        assert doctor.resolve(11, doctor.git_hook_fires(repo))[1] == "ai-eng init --project"

    # On a machine with no chain yet — every fresh install — the module answers `--version`
    # and that is the whole of what this assertion asks now. It used to ask a fourth
    # question, whether the CLI could sign a commit footer, and answer `undecidable` when it
    # could not; specification 022 deleted the footer, so a fresh machine reads `ok` here and
    # the state of the chain is `audit verify`'s business rather than the wiring check's.
    #
    # Only liveness is stood in for, and only because it is ambient: inside the mutation
    # harness's sandbox the child cannot import the package, so this block reported a dead
    # module and took the whole gate's baseline with it. A dead module is asserted below,
    # where it is the subject rather than the weather.
    git(repo, "config", "ai.eng", f"{sys.executable} -m ai_engineering.cli")
    live = doctor.subprocess.run

    def answering(argv, *args, **kwargs):
        if "--version" in list(argv):
            return SimpleNamespace(returncode=0, stdout="ai-engineering 1.0.0")
        return live(argv, *args, **kwargs)

    monkeypatch.setattr(doctor.subprocess, "run", answering)
    state, detail = verdict(doctor.git_hook_fires, repo)
    monkeypatch.undo()
    monkeypatch.setattr(paths, "git_hooks", lambda: ours)
    assert state == "ok", detail

    # Only `git config --get` is left running for real, or the check would be reading a
    # value this test never wrote. The rest of what this block used to stand in for was the
    # anchor's own execution, and there is no anchor.
    real = doctor.subprocess.run

    def only_the_cli(answer, alive=None):
        alive = alive or SimpleNamespace(returncode=0, stdout="ai-engineering 1.0")

        def run(argv, *args, **kwargs):
            if list(argv)[:1] == ["git"]:
                return real(argv, *args, **kwargs)
            chosen = alive if "--version" in list(argv) else answer
            if isinstance(chosen, BaseException):
                raise chosen
            return chosen

        return run

    # The state this test is named for: the interpreter is alive and the module is not.
    for dead in (
        SimpleNamespace(returncode=1, stdout=""),
        SimpleNamespace(returncode=0, stdout=""),
        SimpleNamespace(returncode=0, stdout="some other tool 9.9"),
    ):
        monkeypatch.setattr(doctor.subprocess, "run", only_the_cli(dead, alive=dead))
        state, detail = verdict(doctor.git_hook_fires, repo)
        assert state == "fail", dead
        assert "installed and does not run" in detail, dead

    # And a hang is undecidable rather than a pass that waited.
    hangs = subprocess.TimeoutExpired(cmd="python", timeout=30)
    monkeypatch.setattr(doctor.subprocess, "run", only_the_cli(hangs, alive=hangs))
    assert verdict(doctor.git_hook_fires, repo)[0] == "undecidable"

    # A path with a space in it is the default Windows install, and it used to make this
    # assertion permanently red with a cure that rewrote the same unreadable value.
    for spaced in (
        "/Users/My Name/.venv/bin/python",
        r"C:\Program Files\Python312\python.exe",
    ):
        assert doctor._interpreter_of(f"{spaced} -m ai_engineering.cli") == spaced


def test_an_undecidable_assertion_prints_the_cure_it_carries(capsys):
    """`INCOMPLETE` and `INCOMPLETE, and here is the command that settles it` were the same
    state, so a check whose answer was one command away had to be reported as a failure to
    say so. This is the rendering half of that, which nothing else drives."""

    from ai_engineering import ui

    ui.reset()
    raised = doctor.Undecidable("the chain is not in a state to sign one", "ai-eng init --project")
    assert str(raised) == "the chain is not in a state to sign one"
    assert raised.cure == "ai-eng init --project"
    ui.verdict(11, "unknown", "A git hook actually fires", f"could not evaluate: {raised}")
    ui.cure("INCOMPLETE", raised.cure)
    printed = capsys.readouterr().out
    assert "could not evaluate: the chain is not in a state to sign one" in printed
    assert "fix: ai-eng init --project" in printed

    # An Undecidable with no cure prints none, rather than a line promising one.
    assert doctor.Undecidable("nothing to be done here").cure == ""


def test_the_anchor_check_runs_the_installed_module_and_never_the_repository_it_diagnoses(
    home, repo, monkeypatch
):
    """The hole a review opened in this check, kept shut.

    `python -m` puts the child's working directory on `sys.path`, and the working directory
    here is somebody's repository. So a repository containing a top-level `ai_engineering/`
    package had its own `cli.py` executed by `ai-eng doctor` — and could print a well-formed
    anchor footer to make the assertion that runs it report ok. The reviewer planted exactly
    that and watched it work: the marker file was written and assertion 11 went green.

    `PYTHONSAFEPATH` removes the implicit path entry, so the module that answers is the one
    that is installed. This test is the plant, and it must find nothing.
    """

    planted = repo / "ai_engineering"
    planted.mkdir()
    marker = repo / "the-plant-ran"
    (planted / "__init__.py").write_text("", encoding="utf-8")
    (planted / "cli.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
        "print('Ai-Eng-Anchor: repo/machine seq=1 head=0123456789ab')\n"
        "print('ai-engineering 9.9.9')\n",
        encoding="utf-8",
    )

    # The child needs a real package to answer with, and inside the mutation sandbox there
    # is none on its path. Naming it explicitly leaves the subject exactly where it was:
    # the plant is in the working directory, and `PYTHONSAFEPATH` is what keeps it out.
    monkeypatch.setenv("PYTHONPATH", os.environ.get("AI_ENG_REAL_SRC") or str(ROOT / "src"))

    answered = doctor._run_cli(repo, ["--version"])
    assert not marker.exists(), "the repository being diagnosed executed its own code"
    assert answered.returncode == 0
    assert "ai-engineering" in answered.stdout
    assert "9.9.9" not in answered.stdout

    # And the flag is what does it, stated where somebody would otherwise remove it.
    assert "PYTHONSAFEPATH" in (ROOT / "src" / "ai_engineering" / "doctor.py").read_text(
        encoding="utf-8"
    )
    assert "PYTHONSAFEPATH" in (ROOT / "src" / "ai_engineering" / "wiring.py").read_text(
        encoding="utf-8"
    )


def test_a_router_somebody_edited_or_removed_is_reported_and_never_repaired(
    home, repo, tmp_path, monkeypatch
):
    """Assertion 24. A router is a file this installer wrote into somebody's home, so it owes
    the same answer as everything else it wrote: is it there, and is it ours.

    Reported and not repaired. `--fix` rewriting a file a person deleted would be the
    installer overruling them, and this check has no cure that runs unattended for exactly
    that reason — the cure it names is a command a person chooses to type."""

    from ai_engineering import wiring

    commands = tmp_path / "commands"
    surface = {"id": "invented", "commands": str(commands), "skills": ""}
    # Declared in the table, because the check builds the path it opens from the table and
    # takes only a file name from the receipt. A surface nobody declared has no router root,
    # which is the point: the recorded string is never used as a path.
    monkeypatch.setattr(wiring, "table", lambda: {"surface": [surface]})
    written = wiring.install_routers([surface])
    wiring.record(written)

    assert doctor.routers_intact(repo) is None

    Path(written[0]["path"]).unlink()
    Path(written[1]["path"]).write_text("mine now\n", encoding="utf-8")
    said = doctor.routers_intact(repo)

    assert isinstance(said, tuple)
    assert "1 removed" in said[0]
    assert "1 edited" in said[0]
    assert str(len(written)) in said[0]


def test_a_machine_with_no_router_says_it_could_not_evaluate_rather_than_ok(home, repo):
    """Seven of the eight surfaces declare no command root, so most machines have no router
    at all. Nothing written is not the same as nothing wrong, and an ok here would be a pass
    over a question nobody asked."""

    with pytest.raises(doctor.Undecidable):
        doctor.routers_intact(repo)


def test_a_receipt_pointing_somewhere_else_is_reported_and_never_opened(
    home, repo, tmp_path, monkeypatch
):
    """The path SonarCloud called a BLOCKER, bounded rather than argued away.

    Assertion 24 reads a path out of the machine receipt and hashes whatever it finds there.
    The receipt is a file on disk, so somebody who can rewrite it could point the check at
    any file on the machine and learn whether its digest matched — an oracle. "They are
    already inside" is true and is the argument that ends with a check nobody bounded.

    Two conditions leave only what the installer's own naming produces, and neither can be
    satisfied by editing the receipt alone: the entry has to be `ai-<something>.md`, and it
    has to be a regular file rather than a link to one."""
    from ai_engineering import wiring

    commands = tmp_path / "commands"
    surface = {"id": "invented", "commands": str(commands), "skills": ""}
    monkeypatch.setattr(wiring, "table", lambda: {"surface": [surface]})
    written = wiring.install_routers([surface])
    wiring.record(written)
    assert doctor.routers_intact(repo) is None

    secret = tmp_path / "id_rsa"
    secret.write_text("a private key\n", encoding="utf-8")
    wiring.record([{"path": str(secret), "kind": "router", "how": "generated deadbeef"}])

    said = doctor.routers_intact(repo)
    assert isinstance(said, tuple)
    assert "outside" in said[0]
    assert "id_rsa" in said[0]

    # And a link wearing a router's name is refused for the same reason.
    link = commands / "ai-linked.md"
    link.symlink_to(secret)
    wiring.record([{"path": str(link), "kind": "router", "how": "generated deadbeef"}])
    again = doctor.routers_intact(repo)
    assert isinstance(again, tuple) and "ai-linked.md" in again[0]

    # Both kinds of link, because only one of them was read. `is_symlink()` is False for a
    # hard link, so `os.link` put the whole oracle back inside a declared command root: the
    # right digest reported nothing and a wrong one reported `1 edited`, naming the file. An
    # independent reviewer built exactly this. It is refused as astray now, and the report
    # never opens it, so neither answer distinguishes anything.
    import os

    hard = commands / "ai-oracle.md"
    os.link(secret, hard)
    wiring.record([{"path": str(hard), "kind": "router", "how": "generated deadbeef"}])
    hardened = doctor.routers_intact(repo)
    assert isinstance(hardened, tuple)
    assert "ai-oracle.md" in hardened[0]
    assert "edited" not in hardened[0], "a hard link was hashed instead of being refused"


def test_a_second_handler_for_a_declared_capability_is_named_and_a_clean_repository_is_not(repo):
    """`EP-164`: `ai-spec` pinned to one mode was pinned by a test reading the manifest's own
    content, which says nothing about elsewhere — and elsewhere is where a second handler
    lives.

    A capability is a name a surface routes on, so a second `SKILL.md` calling itself
    `ai-spec` is a second answer to the same request, chosen by the surface's search order
    rather than by anything this framework recorded.

    Four cases, and the clean one first, because a check that failed on every repository
    would look identical from the outside to one that works.
    """

    (repo / "README.md").write_text("a repository\n", encoding="utf-8")
    git(repo, "add", "-A")
    got, _ = verdict(doctor.one_handler_each, repo)
    assert got == "ok", "a repository with no second handler was reported as having one"

    # Untracked is somebody's working directory and not this check's business.
    rogue = repo / ".claude" / "skills" / "ai-spec"
    rogue.mkdir(parents=True)
    (rogue / "SKILL.md").write_text("---\nname: ai-spec\n---\n", encoding="utf-8")
    assert verdict(doctor.one_handler_each, repo)[0] == "ok"

    # Committed, and it is now a handler this repository ships.
    git(repo, "add", "-A")
    got, detail = verdict(doctor.one_handler_each, repo)
    assert got == "fail"
    assert "ai-spec" in detail
    assert ".claude/skills/ai-spec/SKILL.md" in detail
    assert "search order" in detail

    # Found by the name it calls itself, not by the directory it sits in: a directory renamed
    # to hide a duplicate still routes, because the surface reads the frontmatter.
    hidden = repo / "vendor" / "notes"
    hidden.mkdir(parents=True)
    (hidden / "SKILL.md").write_text("---\nname: ai-review\n---\n", encoding="utf-8")
    git(repo, "add", "-A")
    detail = verdict(doctor.one_handler_each, repo)[1]
    assert "ai-review" in detail and "vendor/notes/SKILL.md" in detail

    # And a skill that is nobody's declared capability is somebody's own work, left alone.
    (hidden / "SKILL.md").write_text("---\nname: their-own-skill\n---\n", encoding="utf-8")
    (rogue / "SKILL.md").unlink()
    git(repo, "add", "-A")
    assert verdict(doctor.one_handler_each, repo)[0] == "ok"


def test_the_second_handler_check_answers_nothing_rather_than_guessing(monkeypatch):
    """Outside a repository there is no inventory, and a manifest that cannot be read is not
    a manifest declaring nothing. Both are undecidable, and the second is the one that would
    otherwise pass loudly: an empty set of declared ids matches no handler at all."""

    from ai_engineering import capability

    assert verdict(doctor.one_handler_each, None)[0] == "undecidable"

    def broken(_source):
        raise ValueError("unreadable")

    monkeypatch.setattr(capability, "_validated", broken)
    got, detail = verdict(doctor.one_handler_each, Path.cwd())
    assert got == "undecidable"
    assert "could not be read" in detail


def test_the_paths_flag_prints_five_homes_and_asks_nothing_else(monkeypatch, capsys):
    """Eighty-nine mutants of `doctor.main` survived, and this is the half of it a person
    pipes into a script.

    Five file classes, each with the one path it lives at. The labels are what a reader greps
    for and the paths are what they act on, so both are asserted — and so is the fact that
    nothing else runs: `--paths` is a question about where things are, and a diagnosis that
    answered it by executing twenty-six checks would be answering a different question
    slowly.
    """
    ran = []
    monkeypatch.setattr(
        doctor, "CHECKS", [(1, "The record", "would have run", True, lambda root: ran.append(1))]
    )

    assert doctor.main(["--paths"]).outcome == "PASS"
    printed = [one for one in capsys.readouterr().out.splitlines() if one.strip()]

    assert [one.split()[0] for one in printed] == ["guards", "git", "skills", "record", "receipt"]
    assert len(printed) == 5, printed
    assert all(
        one.endswith(("/", "json", "jsonl", "py", "skills")) or "/" in one for one in printed
    )
    assert ran == [], "--paths ran a check"


def test_the_ci_flag_skips_what_a_runner_cannot_answer_and_says_which(monkeypatch, capsys):
    """`--ci` is the shape a false green would take if it were quiet about it.

    A runner has no working copy for some questions, and the honest answer is that they were
    not asked. What must never happen is that they read as passes — so each one prints as
    skipped, carries the reason, and arrives in the envelope as a SKIPPED fact rather than
    being left out of it.
    """
    asked = []

    def only_local(root):
        asked.append("local")
        return None

    def anywhere(root):
        asked.append("ci")
        return None

    monkeypatch.setattr(
        doctor,
        "CHECKS",
        [
            (1, "The record", "needs a working copy", False, only_local),
            (2, "The record", "runs anywhere", True, anywhere),
        ],
    )

    result = doctor.main(["--ci"])
    printed = capsys.readouterr().out

    assert asked == ["ci"], "a check a runner cannot answer was asked anyway"
    assert "needs a real working copy" in printed
    facts = {one.id: one for one in result.checks} if hasattr(result, "checks") else {}
    if facts:
        assert facts["assertion-1"].status == "SKIPPED"
        assert facts["assertion-1"].detail == "needs a real working copy"
        assert facts["assertion-2"].status != "SKIPPED"

    # Without the flag, both are asked.
    asked.clear()
    doctor.main([])
    assert sorted(asked) == ["ci", "local"]


def test_every_way_the_cli_can_fail_to_answer_is_its_own_sentence(monkeypatch, tmp_path):
    """Thirty-six mutants of `_cli_answers` survived, and this check exists because of a
    machine found with a live interpreter and a dead module.

    Five outcomes. Nothing configured is undecidable, because nothing was asked rather than
    answered wrongly; the other three failures are failures, because each names something a
    person can repair. Each returns a different sentence, and the sentence is what the person
    acts on, so the sentences are asserted rather than the shape of the return value.

    It had six until specification 022. The two that went were about signing a commit footer,
    and the footer is deleted.
    """
    from ai_engineering import doctor as under

    def answers(configured="", interpreter=None, version=None, anchor=None):
        monkeypatch.setattr(under, "git", lambda root, *a: configured)
        monkeypatch.setattr(under, "_interpreter_of", lambda value: interpreter)

        def run(root, argv):
            got = version if argv[0] == "--version" else anchor
            if isinstance(got, Exception):
                raise got
            return got

        monkeypatch.setattr(under, "_run_cli", run)
        return verdict(under._cli_answers, tmp_path)

    ok = SimpleNamespace(returncode=0, stdout="ai-engineering 1.0.0")

    # Nothing configured: undecidable, because nothing was asked rather than answered wrongly.
    state, said = answers()
    assert state == "undecidable"
    assert "ai.eng is not set here" in said

    # Configured, and naming a different interpreter. What the hooks run is not what this
    # install would run, which is a failure and not a question.
    state, said = answers(
        configured="/somewhere/python -m ai_engineering.cli", interpreter="/other"
    )
    assert state == "fail"
    assert "does not name this interpreter and this module" in said

    # The exact machine this check was written for: installed, and it does not run.
    state, said = answers(
        configured="x",
        interpreter=sys.executable,
        version=SimpleNamespace(returncode=1, stdout=""),
    )
    assert state == "fail"
    assert "installed and does not run" in said

    # It runs and answers something else entirely — a different tool on the same name.
    state, said = answers(
        configured="x",
        interpreter=sys.executable,
        version=SimpleNamespace(returncode=0, stdout="some other tool 2.0"),
    )
    assert state == "fail"

    # And the whole of what remains: it runs and answers as this tool. Nothing else is asked
    # here, because the fourth question this used to put — can it sign a commit footer — went
    # with the footer in specification 022.
    state, said = answers(configured="x", interpreter=sys.executable, version=ok)
    assert state == "ok", said


def test_the_tracked_inventory_is_refused_rather_than_returned_short(tmp_path, monkeypatch):
    """Eighteen mutants of `tracked_files` survived, and every reader of it decides what is
    committed where.

    `-z` exists because a filename may contain a newline, and a splitter that used one would
    turn one file into two — which, in the check that finds framework files outside their
    homes, invents a stray that is not there and hides the one that is. So the separator is
    asserted with a name that would break a line-splitter. The reader is now the shared
    `paths.git_lines` (spec 044); the refusals below run it directly, and the wrapper's own
    translation is exercised beside them.
    """
    from ai_engineering import doctor as under, paths as product_paths

    real_run = under.subprocess.run

    def answers(stdout=b"", code=0, error=None):
        def run(argv, **kwargs):
            if error is not None:
                raise error
            if code:
                return SimpleNamespace(returncode=code, stdout=b"", stderr=b"")
            return SimpleNamespace(returncode=0, stdout=stdout, stderr=b"")

        monkeypatch.setattr(product_paths.subprocess, "run", run)

    answers(b"a.py\0b/c.py\0")
    assert under.tracked_files(tmp_path) == ["a.py", "b/c.py"]

    # A newline inside a name. The only separator is the NUL, and this is why.
    answers(b"one\ntwo.py\0plain.py\0")
    assert under.tracked_files(tmp_path) == ["one\ntwo.py", "plain.py"]

    # Nothing tracked at all is an empty inventory and not a refusal: a fresh repository is
    # a real state, and refusing it would make this red by construction.
    answers(b"")
    assert under.tracked_files(tmp_path) == []

    for why, kwargs in (
        ("git is not installed", {"error": FileNotFoundError("git")}),
        ("git timed out", {"error": subprocess.TimeoutExpired("git", 10)}),
        ("git failed", {"code": 128}),
    ):
        answers(**kwargs)
        with pytest.raises(under.Undecidable, match="could not inventory tracked files"):
            under.tracked_files(tmp_path)
        assert why, "every refusal above is named, so the reason is in the failure output"


def test_the_inventory_asks_about_the_repository_it_was_handed(tmp_path, monkeypatch):
    """`-C <root>`, and it is the argument that decides which repository is answered about.

    Without it this reads whatever repository the process happens to be standing in — which,
    for a diagnosis run from inside one repository about another, is a report about the wrong
    tree that looks exactly like a report about the right one.
    """
    from ai_engineering import doctor as under, paths as product_paths

    seen = []
    monkeypatch.setattr(
        product_paths.subprocess,
        "run",
        lambda argv, **kw: (
            seen.append(argv) or SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        ),
    )

    under.tracked_files(tmp_path)

    assert seen[0][:4] == ["git", "-C", str(tmp_path), "ls-files"]
    assert "-z" in seen[0], "the separator that makes a newline in a name safe is gone"
    assert "--cached" in seen[0]


def test_the_inventory_asks_about_the_repository_it_was_handed(tmp_path, monkeypatch):
    """`-C <root>`, and it is the argument that decides which repository is answered about.

    Without it this reads whatever repository the process happens to be standing in — which,
    for a diagnosis run from inside one repository about another, is a report about the wrong
    tree that looks exactly like a report about the right one.
    """
    from ai_engineering import doctor as under

    seen = []
    monkeypatch.setattr(
        under.subprocess,
        "run",
        lambda argv, **kw: (
            seen.append(argv) or SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        ),
    )

    under.tracked_files(tmp_path)

    assert seen[0][:4] == ["git", "-C", str(tmp_path), "ls-files"]
    assert "-z" in seen[0], "the separator that makes a newline in a name safe is gone"
    assert "--cached" in seen[0]


def test_the_one_word_the_whole_diagnosis_collapses_to():
    """Twelve mutants of `_terminal_result` survived, and every one of the twenty-six
    assertions arrives here to become a single word and an exit code.

    Four states in a strict order — FAIL, then INCOMPLETE, then WARN, then PASS — and the
    order is the entire meaning. A failed assertion beside an unanswered one is a failure:
    the thing that was found does not stop being found because something else could not be
    asked. And an unanswered assertion beside a warning is INCOMPLETE, because a question
    nobody could ask outranks a state somebody chose to accept.

    Everything below is asserted as the outcome word rather than as a shape, because the
    word is what the person and the exit code both come from.
    """
    from ai_engineering import doctor as under

    def word(**kwargs):
        base = {"failed": [], "unanswered": [], "coverage_lines": [], "coverage_unknown": False}
        return under._terminal_result(**{**base, **kwargs}).outcome

    assert word() == "PASS"

    # Each of the three that fail, alone.
    assert word(failed=[7]) == "FAIL"
    assert word(readiness_failed=True) == "FAIL"
    assert word(surface_failed=True) == "FAIL"

    # And the fourth, which arrives as a word inside the coverage table rather than a flag:
    # a surface whose settings and receipt disagree is a mismatch, and a mismatch is a
    # failure however green everything around it is.
    assert word(coverage_lines=["  claude-code   MISMATCH   the entry is not ours"]) == "FAIL"

    # Unanswered, and the coverage table that could not be built.
    assert word(unanswered=[(3, "a title", "why")]) == "INCOMPLETE"
    assert word(coverage_unknown=True) == "INCOMPLETE"

    # Warned, and the three words that mean somebody has not proved something rather than
    # that something is wrong.
    assert word(surface_warned=True) == "WARN"
    for said in ("INERT", "UNPROVEN", "OPEN"):
        assert word(coverage_lines=[f"  cursor   {said}   nothing has denied here"]) == "WARN", said

    # The precedence, which is the part a rewrite would get wrong quietly.
    assert word(failed=[1], unanswered=[(2, "t", "w")]) == "FAIL"
    assert word(failed=[1], surface_warned=True) == "FAIL"
    assert word(unanswered=[(2, "t", "w")], surface_warned=True) == "INCOMPLETE"
    assert word(coverage_unknown=True, coverage_lines=["  x   UNPROVEN   y"]) == "INCOMPLETE"
    assert word(failed=[1], coverage_lines=["  x   UNPROVEN   y"]) == "FAIL"

    # A word that is none of the five it looks for changes nothing, or every line of prose in
    # that table would be able to move the verdict.
    assert word(coverage_lines=["  claude-code   PROVEN   a denial executed here"]) == "PASS"
    assert word(coverage_lines=["  a line with no capitals at all"]) == "PASS"


def test_the_diagnosis_exits_non_zero_whenever_it_did_not_pass():
    """The half of the same decision a script reads. A verdict that printed FAIL and exited
    zero would be the false green this product is named after, arriving in the command whose
    entire job is to say whether the system is healthy."""
    from ai_engineering import doctor as under

    for word, expected in (("PASS", 0), ("WARN", 0), ("INCOMPLETE", 1), ("FAIL", 1)):
        got = under._terminal_result(
            failed=[1] if word == "FAIL" else [],
            unanswered=[(1, "t", "w")] if word == "INCOMPLETE" else [],
            coverage_lines=[],
            coverage_unknown=False,
            surface_warned=word == "WARN",
        )
        assert got.outcome == word
        assert (got.exit_code != 0) == bool(expected), (word, got.exit_code)


def test_the_fix_flag_runs_what_the_failures_named_and_never_invents_a_cure(monkeypatch, capsys):
    """ADR 0003 decided this shape and eighteen of its mutants survived: **a check reports and
    never writes; a check that knows the cure carries the command; `--fix` may invoke that
    command and may not reimplement it.**

    So what is asserted is that every command it runs came out of a cure, that each distinct
    one runs exactly once however many checks named it, and that they run in this process
    through `cli.main` rather than through a shell — `ai-eng` is on the PATH of the person who
    typed it and not necessarily of whatever would run it here, and a repair that fails
    because it could not find itself is worse than no repair.
    """
    from ai_engineering import cli
    from ai_engineering import doctor as under

    ran: list[list[str]] = []
    monkeypatch.setattr(cli, "main", lambda argv: ran.append(argv) or 0)
    monkeypatch.setattr(under, "main", lambda argv: outcome.result("PASS"))

    # Two checks naming one cure, and a third naming another: two runs, not three.
    under.repair({1: "ai-eng init", 4: "ai-eng init", 7: "ai-eng update"}, ["--fix"])
    assert ran == [["init", "-y"], ["update"]]

    # `-y` is added for `init` and for nothing else, because that is the one verb whose
    # defaults destroy nothing — the picker arrives with nothing ticked.
    assert under.UNATTENDED == {"init": ["-y"]}

    # No cures is no commands. A `--fix` over a clean diagnosis must not run anything.
    ran.clear()
    under.repair({}, ["--fix"])
    assert ran == []


def test_a_cure_that_fails_stops_the_rest_and_says_so(monkeypatch, capsys):
    """The order matters and so does stopping. A second cure run after the first failed is a
    repair operating on a machine whose state nobody knows, and the honest answer is
    INCOMPLETE with the exit code in it rather than carrying on."""
    from ai_engineering import cli
    from ai_engineering import doctor as under

    ran: list[list[str]] = []
    monkeypatch.setattr(
        cli, "main", lambda argv: ran.append(argv) or (2 if argv[0] == "init" else 0)
    )
    monkeypatch.setattr(under, "main", lambda argv: outcome.result("PASS"))

    result = under.repair({1: "ai-eng init", 2: "ai-eng update"}, ["--fix"])

    assert result.outcome == "INCOMPLETE"
    assert ran == [["init", "-y"]], "the rest was attempted after a cure failed"
    assert "it exited 2. The rest is not attempted." in capsys.readouterr().out


def test_the_second_pass_carries_no_fix_and_a_repair_that_changed_nothing_says_so(
    monkeypatch, capsys
):
    """Two properties that keep `--fix` from being a loop.

    The second pass has no `--fix` in it, so this recurses exactly once. And when the answer
    is still red, it says that what is left is not something these commands reach — because
    two of the cures cannot reach every shape of their failure, and a repair that invited a
    second run of the same command would be a person typing the same thing forever.
    """
    from ai_engineering import cli
    from ai_engineering import doctor as under

    seen: list[list[str]] = []
    monkeypatch.setattr(cli, "main", lambda argv: 0)
    monkeypatch.setattr(under, "main", lambda argv: seen.append(argv) or outcome.result("FAIL"))

    result = under.repair({1: "ai-eng init"}, ["--fix", "--ci"])

    assert seen == [["--ci"]], "the second pass carried --fix and would recurse"
    assert result.outcome == "FAIL"
    said = capsys.readouterr().out
    assert "Still failing" in said
    assert "running --fix again will run the same ones" in said

    # And when it passes, it says nothing extra: a repair that worked does not need a warning.
    seen.clear()
    monkeypatch.setattr(under, "main", lambda argv: seen.append(argv) or outcome.result("PASS"))
    capsys.readouterr()
    assert under.repair({1: "ai-eng init"}, ["--fix"]).outcome == "PASS"
    assert "Still failing" not in capsys.readouterr().out


def test_every_surface_state_arrives_as_a_sentence_and_never_as_a_code(tmp_path, monkeypatch):
    """Seventeen mutants of `surface_states` survived, and this is twenty-four rows of the
    output somebody reads to decide whether a surface is proved.

    Eight codes, eight sentences, and the sentences are the point: `SURFACE_RECEIPT_STALE`
    tells a person nothing, and "the receipt is older than a proof is allowed to be" tells
    them what to do. A code that lost its sentence would fall back to the code and the row
    would still print, which is exactly the kind of degradation nothing notices.

    The age travels with it. A receipt is evidence about a moment, and a row that said
    something executed without saying when is a claim with no shelf life.
    """
    from datetime import UTC, datetime

    from ai_engineering import doctor as under
    from ai_engineering import surface as surfaces

    def rows(*items):
        monkeypatch.setattr(
            surfaces, "read", lambda root, *, now: SimpleNamespace(rows=list(items))
        )

    seen = []
    for code in (
        surfaces.PROVEN,
        surfaces.NOT_APPLICABLE,
        surfaces.RECEIPT_MISSING,
        surfaces.RECEIPT_STALE,
        surfaces.RECEIPT_MISMATCH,
        surfaces.CANNOT_ENFORCE,
        surfaces.WARNED,
        surfaces.REFUSED_EXCUSE,
    ):
        rows(
            SimpleNamespace(
                surface="opencode", state="enforcement", outcome="PASS", code=code, age_seconds=None
            )
        )
        (fact,) = under.surface_states(tmp_path, now=datetime.now(UTC))
        seen.append(fact.detail)
        assert fact.detail != code, f"{code} printed itself instead of a sentence"
        assert fact.id == "surface-opencode-enforcement"
        assert fact.summary == "opencode · enforcement"

    assert len(set(seen)) == 8, "two codes share a sentence, so two states read the same"

    # An age, when there is one. Evidence about a moment that does not say which moment is a
    # claim with no shelf life.
    rows(
        SimpleNamespace(
            surface="claude-code",
            state="discovery",
            outcome="PASS",
            code=surfaces.PROVEN,
            age_seconds=42,
        )
    )
    (aged,) = under.surface_states(tmp_path, now=datetime.now(UTC))
    assert aged.detail.endswith(" · 42s old")

    # A code nobody wrote a sentence for still prints, as itself. Dropping the row would be
    # an omission, and to anything counting an omitted row reads like a question that was not
    # worth asking.
    rows(
        SimpleNamespace(
            surface="zed",
            state="invocation",
            outcome="INCOMPLETE",
            code="SURFACE_SOMETHING_NEW",
            age_seconds=None,
        )
    )
    (unknown,) = under.surface_states(tmp_path, now=datetime.now(UTC))
    assert unknown.detail == "SURFACE_SOMETHING_NEW"

    # And outside a repository there is nothing to read rather than twenty-four unproven
    # rows: no receipts exist to be missing.
    assert under.surface_states(None, now=datetime.now(UTC)) == []


def test_the_coverage_table_says_pin_first_and_never_calls_an_unwired_surface_covered(
    tmp_path, monkeypatch
):
    """Thirteen mutants of `coverage` survived, and this table is the honesty layer.

    Its first line is the pin, and the word after it decides the whole verdict: `MISMATCH`
    is scanned for by `_terminal_result` and turns the diagnosis red. A wheel and a pin that
    disagree mean the hooks on this machine are not the ones this repository thinks it has.

    Then a row per surface, with the tier first. The bug this function was corrected for is
    in the docstring and is worth a case: `surfaces_alive` returns a tuple as soon as any
    surface is unwired, and a substring test against a tuple is never true — so two surfaces
    that fail *silently* printed as covered on a machine where another assertion was telling
    the person they were dead.
    """
    from datetime import UTC, datetime

    from ai_engineering import __version__, wiring
    from ai_engineering import doctor as under

    monkeypatch.setattr(
        under.paths,
        "load",
        lambda name: SimpleNamespace(config=lambda root: {"framework": {"version": __version__}}),
    )
    monkeypatch.setattr(wiring, "detect", lambda: [])
    monkeypatch.setattr(wiring, "wired", lambda: ([], []))
    monkeypatch.setattr(under, "enforced", lambda root, *, now: set())
    monkeypatch.setattr(under, "surfaces_alive", lambda root: ("opencode is inert", "a cure"))

    lines = under.coverage(tmp_path, now=datetime.now(UTC))

    assert lines[0].startswith("  PIN  wheel ")
    assert lines[0].endswith("  OK"), lines[0]
    assert "MISMATCH" not in lines[0]

    # The pin disagreeing is the one word in this table that makes the run red.
    monkeypatch.setattr(
        under.paths,
        "load",
        lambda name: SimpleNamespace(config=lambda root: {"framework": {"version": "0.0.1"}}),
    )
    mismatched = under.coverage(tmp_path, now=datetime.now(UTC))
    assert mismatched[0].endswith("  MISMATCH")
    assert (
        under._terminal_result(
            failed=[], unanswered=[], coverage_lines=mismatched[:1], coverage_unknown=False
        ).outcome
        == "FAIL"
    )

    # A tuple from `surfaces_alive` is read as its message. Without this, the substring test
    # below it is never true and an inert surface reads as covered.
    assert any("opencode" in one for one in lines[1:])
    assert len(lines) > len(under.OPEN), "the per-surface rows are gone"


def test_nothing_installed_leaves_every_row_unproven_rather_than_undecided(tmp_path, monkeypatch):
    """`surfaces_alive` raises when nothing is installed, and the answer is not a missing
    table: every row already reads UNPROVEN, which is the honest word for a machine this
    framework has never been wired into. Swallowing the exception into an empty table would
    replace twenty-four honest rows with silence."""
    from datetime import UTC, datetime

    from ai_engineering import __version__, wiring
    from ai_engineering import doctor as under

    monkeypatch.setattr(
        under.paths,
        "load",
        lambda name: SimpleNamespace(config=lambda root: {"framework": {"version": __version__}}),
    )
    monkeypatch.setattr(wiring, "detect", lambda: [])
    monkeypatch.setattr(wiring, "wired", lambda: ([], []))
    monkeypatch.setattr(under, "enforced", lambda root, *, now: set())

    def nothing(root):
        raise under.Undecidable("nothing is installed here")

    monkeypatch.setattr(under, "surfaces_alive", nothing)

    lines = under.coverage(tmp_path, now=datetime.now(UTC))

    assert len(lines) > 1, "an undecidable liveness check emptied the table"
    assert any("UNPROVEN" in one for one in lines), lines


def test_a_production_ready_box_carries_its_age_beside_its_verdict(tmp_path, monkeypatch):
    """Eleven mutants of `readiness_facts` survived, and the age is the whole reason this
    function reports more than a verdict.

    A receipt has two ways of meaning nothing and only one shows up as a failure: it can say
    the wrong thing, or it can say the right thing about a run from six months ago. The
    second reads green in every summary that only counts outcomes, which is why the age sits
    beside the verdict on every row rather than in a separate report nobody opens.

    A box with no receipt at all says "no receipt to age" rather than showing a zero. Zero is
    a number, and a number here means somebody measured something.
    """
    from datetime import UTC, datetime

    from ai_engineering import doctor as under
    from ai_engineering import readiness

    monkeypatch.setattr(
        readiness,
        "read",
        lambda root, *, now: SimpleNamespace(
            result=SimpleNamespace(outcome="INCOMPLETE"),
            code="READINESS_UNPROVEN",
            boxes=[
                SimpleNamespace(
                    id="ci", label="CI/CD", outcome="PASS", code="PROVEN", age_seconds=90
                ),
                SimpleNamespace(
                    id="logs",
                    label="Logs",
                    outcome="INCOMPLETE",
                    code="NO_RECEIPT",
                    age_seconds=None,
                ),
            ],
        ),
    )

    facts = under.readiness_facts(tmp_path, now=datetime.now(UTC))

    assert [one.id for one in facts] == ["readiness", "readiness-ci", "readiness-logs"]
    assert facts[0].status == "INCOMPLETE"
    assert facts[0].detail == "READINESS_UNPROVEN"
    assert facts[1].detail == "PROVEN · 90s old"
    assert facts[2].detail == "NO_RECEIPT · no receipt to age"
    assert facts[1].summary == "CI/CD", "the label a person reads was replaced by the id"

    # Outside a repository there is one honest row and not eight unproven ones: there are no
    # receipts to be missing, which is a different answer from receipts that say nothing.
    (alone,) = under.readiness_facts(None, now=datetime.now(UTC))
    assert alone.status == "INCOMPLETE"
    assert alone.detail == "there is no repository here to read receipts from"


def test_doctor_asserts_the_hooks_template_is_owned_and_removable(home):
    """D-024-01 observability half: the machine's hooks template and its global key are a
    state doctor can see. Three states: installed and owned is ok; a receipt row with no
    template is a removable gap; a template with no receipt row is not ours to explain."""

    import shutil

    template = paths.home() / "hooks-template"
    shipped = paths.git_hooks()
    subprocess.run(["mkdir", "-p", str(template)], check=True)
    for name in ("pre-commit", "commit-msg", "pre-push"):
        shutil.copy2(shipped / name, template / name)
    subprocess.run(["git", "config", "--global", "init.templateDir", str(template)], check=True)
    wiring.record([{"path": str(template), "kind": "hooks-template", "how": "written"}])

    assert verdict(doctor.hooks_template_owned, None) == ("ok", "")

    # The template is deleted, the key stays: the row and the key exist, the dir does not.
    shutil.rmtree(template)
    problem, cure = doctor.hooks_template_owned(None)
    assert "disagree" in problem
    assert "ai-eng uninstall" in cure
