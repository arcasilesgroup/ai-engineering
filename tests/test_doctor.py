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
    """The three states doctor prints, as a pair a table can be compared against."""
    try:
        problem = fn(root)
    except doctor.Undecidable as why:
        return "undecidable", str(why)
    if isinstance(problem, tuple):
        problem = problem[0]  # a check that carries its own cure; the message is the first
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
    assert sorted(numbers) == [n for n in range(1, 22) if n != 5]
    for number, family, title, in_ci, fn in doctor.CHECKS:
        assert family and title and callable(fn) and isinstance(in_ci, bool), number


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
    monkeypatch.setattr(doctor, "coverage", lambda root: ["  PIN  stubbed"])
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
        (lambda rows: [{**rows[0], "data": {"r": "rewritten"}}, rows[1]], "", "it was edited"),
    ],
    ids=["intact", "linkage broken", "body edited after it was hashed"],
)
def test_assertion_6_compares_the_linkage_and_never_recomputes_a_hash(
    home, repo, edit, doctor_says, audit_says
):
    """Assertion 6 checks that each link names the one before it, and nothing else. So an
    event whose body was rewritten after its hash was taken keeps its linkage and reads as
    intact, while audit — walking the same file — calls it edited. Today's behaviour,
    pinned: "the hash chain is intact" is a statement about the linkage only."""
    path = chain(repo, {}, {})
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    path.write_text("".join(json.dumps(row) + "\n" for row in edit(rows)))
    got, detail = verdict(doctor.chain_intact, repo)
    assert (got, doctor_says in detail) == (("fail", True) if doctor_says else ("ok", True))
    problems = audit.verify(repo, anchors=False)
    assert "INTENT_HOME_MISSING" in problems[-1]
    chain_problems = " ".join(problems[:-1])
    assert (audit_says in chain_problems) and bool(chain_problems) == bool(audit_says)


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
    problems = audit.verify(repo, anchors=False)
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
    assert verdict(doctor.data_is_yours, repo) == ("ok", "")
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
    monkeypatch.setattr(doctor, "_anchor_answers", lambda root: None)
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
    monkeypatch.setattr(doctor, "coverage", lambda root: ["  PIN  stubbed"])
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
    monkeypatch.setattr(doctor, "coverage", lambda root: ["  T2  a  BLOCKS  a denial ran here"])
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
    monkeypatch.setattr(doctor, "coverage", lambda root: ["  PIN  stubbed"])
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
    monkeypatch.setattr(doctor, "coverage", lambda root: ["  PIN  stubbed"])
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
    monkeypatch.setattr(doctor, "coverage", lambda root: ["  PIN  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    doctor.main(["--fix"])
    assert invoked == []


def test_which_cures_fix_may_run_is_decided_by_the_verb_and_survives_a_short_one():
    """The allow-list is read out of the cure, so the shape of the string decides whether a
    verb is ever looked up. A cure of one word must answer no rather than index past the end
    of it, and a cure of exactly two words — the shortest real one — must still answer yes,
    or `--fix` silently stops repairing the thing it says it repairs."""
    assert doctor.unattended("ai-eng init") and doctor.unattended(doctor.FIXES[2])
    assert not doctor.unattended("ai-eng update")
    assert not doctor.unattended("init") and not doctor.unattended("")


def test_fix_with_nothing_it_can_repair_says_so_and_writes_nothing(monkeypatch, capsys, invoked):
    """The failure that has no command is the common one — seventeen of the twenty-one —
    and a flag that silently does nothing reads as a flag that ran."""
    monkeypatch.setattr(doctor, "CHECKS", [(4, "The context", "yours", True, lambda root: "TODO")])
    monkeypatch.setattr(doctor, "coverage", lambda root: ["  PIN  stubbed"])
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
    monkeypatch.setattr(doctor, "coverage", lambda root: ["  PIN  stubbed"])
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
    unproven = [s["id"] for s in wiring.table()["surface"] if not s["proven"]]
    assert not [name for name in unproven if "BLOCKS" in rows[name]]
    assert "INERT" in rows["opencode"] and "INERT" in rows["codex-cli"]
    assert "BLOCKS" in rows["claude-code"]
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

    # The live one runs for real. On a machine with no chain yet — every fresh install —
    # the module answers `--version` and cannot anchor, and that is undecidable rather than
    # a broken install. A check that is red by construction is a check somebody silences.
    git(repo, "config", "ai.eng", f"{sys.executable} -m ai_engineering.cli")
    state, detail = verdict(doctor.git_hook_fires, repo)
    assert state == "undecidable", detail
    assert "cannot anchor a commit yet" in detail

    # And with a chain it can anchor, it passes.
    footer = "Ai-Eng-Anchor: repo/machine seq=1 head=0123456789ab"
    real_run = doctor.subprocess.run

    def anchored(argv, *args, **kwargs):
        if list(argv)[:1] == ["git"]:
            return real_run(argv, *args, **kwargs)
        if "--version" in list(argv):
            return SimpleNamespace(returncode=0, stdout="ai-engineering 1.0.0")
        return SimpleNamespace(returncode=0, stdout=f"{footer}\n")

    monkeypatch.setattr(doctor.subprocess, "run", anchored)
    assert verdict(doctor.git_hook_fires, repo)[0] == "ok"
    monkeypatch.undo()
    monkeypatch.setattr(paths, "git_hooks", lambda: ours)

    # Only the anchor's own execution is stood in for. `git config --get` still runs, or
    # the check would be reading a value this test never wrote.
    real = doctor.subprocess.run

    def only_the_anchor(answer, alive=None):
        alive = alive or SimpleNamespace(returncode=0, stdout="ai-engineering 1.0")

        def run(argv, *args, **kwargs):
            if list(argv)[:1] == ["git"]:
                return real(argv, *args, **kwargs)
            # Liveness is a separate question from anchorability, so the stub answers it
            # separately — and answerably, because the dead-module branch is the one this
            # test is named for and hard-coding a live answer removed the only path to it.
            chosen = alive if "--version" in list(argv) else answer
            if isinstance(chosen, BaseException):
                raise chosen
            return chosen

        return run

    # A module that runs and prints the wrong thing is a failure; one that runs and cannot
    # anchor is undecidable. Two different answers, because they have two different cures.
    for wrong in (
        SimpleNamespace(returncode=0, stdout=""),
        SimpleNamespace(returncode=0, stdout="Ai-Eng-Anchor: not/a valid=footer\n"),
        SimpleNamespace(returncode=0, stdout=f"{footer}\n{footer}\n"),
    ):
        monkeypatch.setattr(doctor.subprocess, "run", only_the_anchor(wrong))
        assert verdict(doctor.git_hook_fires, repo)[0] == "fail", wrong
    monkeypatch.setattr(
        doctor.subprocess, "run", only_the_anchor(SimpleNamespace(returncode=1, stdout=""))
    )
    assert verdict(doctor.git_hook_fires, repo)[0] == "undecidable"

    # The state this test is named for: the interpreter is alive and the module is not.
    for dead in (
        SimpleNamespace(returncode=1, stdout=""),
        SimpleNamespace(returncode=0, stdout=""),
        SimpleNamespace(returncode=0, stdout="some other tool 9.9"),
    ):
        monkeypatch.setattr(doctor.subprocess, "run", only_the_anchor(dead, alive=dead))
        state, detail = verdict(doctor.git_hook_fires, repo)
        assert state == "fail", dead
        assert "installed and does not run" in detail, dead

    # And a hang is undecidable rather than a pass that waited — on either call.
    hangs = subprocess.TimeoutExpired(cmd="python", timeout=30)
    monkeypatch.setattr(doctor.subprocess, "run", only_the_anchor(hangs))
    assert verdict(doctor.git_hook_fires, repo)[0] == "undecidable"
    monkeypatch.setattr(doctor.subprocess, "run", only_the_anchor(hangs, alive=hangs))
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
    home, repo
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

    answered = doctor._run_anchor(repo, ["--version"])
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
