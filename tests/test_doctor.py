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

import pytest

from ai_engineering import __version__, audit, contract, doctor, paths, wiring

emit = paths.load("_emit")


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
    assert sorted(numbers) == list(range(1, 22)), "doctor claims twenty-one numbered assertions"
    for number, family, title, in_ci, fn in doctor.CHECKS:
        assert family and title and callable(fn) and isinstance(in_ci, bool), number


PASSES = (1, "The pin", "a check that passes", True, lambda root: None)
FAILS = (2, "The pin", "a check that fails", True, lambda root: "here is what is wrong")
UNKNOWN = (3, "The pin", "a check nothing could answer", True, raises(doctor.Undecidable("why")))
LOCAL = (4, "The pin", "a check a runner cannot answer", False, lambda root: "it ran anyway")


@pytest.mark.parametrize(
    "rows, argv, code, says, never",
    [
        ((PASSES,), [], 0, "1 passed · 0 failed · 0 not evaluated", "FAIL"),
        ((FAILS,), [], 1, "0 passed · 1 failed · 0 not evaluated", " ok "),
        ((UNKNOWN,), [], 0, "Not evaluated is never green", " ok "),
        ((PASSES, FAILS, UNKNOWN), [], 1, "1 passed · 1 failed · 1 not evaluated", ""),
        ((LOCAL,), ["--ci"], 0, "SKIPPED", "FAIL"),
        ((LOCAL,), [], 1, "FAIL", "SKIPPED"),
    ],
    ids=[
        "a clean tree exits zero",
        "one failure exits non-zero",
        "could not evaluate is not a pass",
        "one of each",
        "--ci leaves a local-only check unrun",
        "outside CI that same check runs",
    ],
)
def test_the_three_states_and_what_each_does_to_the_exit_code(
    monkeypatch, capsys, rows, argv, code, says, never
):
    """Counting a check that could not run as one that passed is how somebody reads
    "everything is fine" off a doctor that measured nothing. The --ci rows prove the skip
    is a skip: the local-only check returns a failure, so if it ran the exit code is 1."""
    monkeypatch.setattr(doctor, "CHECKS", list(rows))
    monkeypatch.setattr(doctor, "coverage", lambda root: ["  PIN  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    assert doctor.main(argv) == code
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
    assert doctor.main(["--paths"]) == 0
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
        "line_budget",
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
    problems = " ".join(audit.verify(repo, anchors=False))
    assert (audit_says in problems) and bool(problems) == bool(audit_says)


def test_a_half_written_last_line_is_dropped_by_the_check_that_looks_for_broken_links(home, repo):
    """A crash part-way through a write leaves half a line behind. doctor drops it without
    a word and still reports the chain intact; audit, reading the same file, cannot parse
    it at all. Whoever reads doctor is told the record is fine."""
    path = chain(repo, {}, {})
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"cls": "blo')
    assert len(doctor.events(repo)) == 2
    assert doctor.chain_intact(repo) is None
    with pytest.raises(ValueError):
        audit.read(repo)


def test_a_chain_that_was_never_written_is_not_a_broken_chain(home, repo):
    """No events yet is the state of every fresh install. Reporting that as a broken record
    would teach the first-run user that doctor's red means nothing."""
    assert doctor.events(repo) == []
    assert doctor.chain_intact(repo) is None
    assert emit.chain_path(repo).parent.exists()


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
    """.ai/ holds one committed file and one ignore rule; anything else of ours inside git
    is state leaking into review, and any framework file committed outside its declared
    home is the first step back toward the 528 files this rebuild deleted."""
    (repo / ".ai" / "config.toml").write_text("")
    (repo / ".ai" / ".gitignore").write_text("events.jsonl\n")
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
        ("suite_fresh", {"deterministic_green": True}, "fail", "real-model half"),
        ("suite_fresh", {"deterministic_green": True, "real_model_at": "now"}, "ok", ""),
        ("suite_fresh", {"deterministic_green": True, "real_model_at": "8 days"}, "fail", "dated"),
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
    assert doctor.wiring_present(None) == "Claude Code has no entry"
    settings.write_text('{"hooks": {"PreToolUse": ["ai-engineering"]}}')
    assert doctor.wiring_present(None) is None
    monkeypatch.setattr(paths, "hooks", lambda: tmp_path / "nowhere")
    assert "dispatcher is missing" in (doctor.wiring_present(None) or "")


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
        ("wired", "ok", ""),
    ],
)
def test_assertion_11_a_tilde_in_the_hooks_path_saves_fine_and_fires_nothing(
    repo, setting, want, fragment
):
    """git never expands ~ in core.hooksPath. It saves without complaint, the hooks never
    run, and every commit goes through: a floor that is not there is worse than none,
    because the repository looks configured."""
    folder = repo.parent / "git-hooks"
    folder.mkdir(exist_ok=True)
    if setting == "wired":
        (folder / "pre-commit").write_text("#!/bin/sh\n")
    value = {"unset": "", "tilde": "~/git-hooks", "empty": str(folder), "wired": str(folder)}
    if value[setting]:
        git(repo, "config", "core.hooksPath", value[setting])
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
        (doctor.links_resolve, "records no skill root"),
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
    assert len(lines) == len(wiring.table()["surface"]) + 2
    assert all("INERT" not in line for line in lines)


def test_assertion_13_a_skill_root_that_stopped_resolving_and_a_doctrine_nobody_imports(home, repo):
    """Skills are linked, or copied where links do not work, and the surface's own updater
    can delete either. And a CLAUDE.md that does not import AGENTS.md means the doctrine
    reaches the model in no session at all."""
    receipt = paths.home() / "machine.json"
    receipt.write_text(json.dumps({"wrote": [{"path": str(home / "gone"), "kind": "link"}]}))
    assert "no longer resolve" in verdict(doctor.links_resolve, repo)[1]
    (home / "gone").mkdir()
    (repo / "CLAUDE.md").write_text("do whatever you like\n")
    assert "does not import" in verdict(doctor.links_resolve, repo)[1]
    (repo / "CLAUDE.md").write_text("@./AGENTS.md\n")
    assert verdict(doctor.links_resolve, repo) == ("ok", "")


@pytest.mark.parametrize(
    "age_days, want",
    [(None, "fail"), (2, "fail"), (0, "ok")],
    ids=["never reported", "two days old", "fresh"],
)
def test_assertion_21_a_plugin_that_stopped_loading_reports_nothing_at_all(home, age_days, want):
    """OpenCode drops a malformed plugin with no error and no log, so the only evidence it
    is running is a heartbeat file — and a heartbeat that never expires would report a dead
    plugin as alive forever."""
    (home / ".config" / "opencode").mkdir(parents=True)
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
    if trusted:
        (home / ".codex" / trusted).write_text("{}")
    got, detail = verdict(doctor.surfaces_alive, None)
    assert (got, "INERT" in detail) == (want, want == "fail")


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


@pytest.mark.parametrize(
    "name, count, tracked, want, fragment",
    [
        ("src/ai_engineering/big.py", contract.REPO_CEILING + 1, True, "fail", "ceiling"),
        ("src/ai_engineering/exact.py", contract.REPO_CEILING, True, "ok", ""),
        ("src/ai_engineering/small.py", 10, True, "ok", ""),
        ("specs/001-thing/spec.md", contract.REPO_CEILING + 1, True, "ok", ""),
        ("src/ai_engineering/small.py", 10, False, "undecidable", "counted zero"),
    ],
    ids=[
        "over the ceiling",
        "exactly at it",
        "under it",
        "the record is not the product",
        "nothing tracked",
    ],
)
def test_assertion_5_counts_the_product_and_refuses_to_count_nothing(
    repo, name, count, tracked, want, fragment
):
    """The ceiling is the mechanism that stops a second 436,091-line codebase: not
    discipline, an exit code. Counting zero files is not a pass, and specs and decisions
    are excluded on purpose — the record grows every time a decision is written down."""
    (repo / "src" / "ai_engineering").mkdir(parents=True, exist_ok=True)
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    (repo / name).write_text("x\n" * count)
    if tracked:
        git(repo, "add", "-A")
    got, detail = verdict(doctor.line_budget, repo)
    assert (got, fragment in detail) == (want, True)


def test_assertion_5_says_so_rather_than_passing_outside_the_product_repository(repo):
    """This check only means something where src/ai_engineering is, and every other
    repository has to be told that instead of shown a green it did not earn."""
    assert verdict(doctor.line_budget, repo)[0] == "undecidable"


@pytest.mark.parametrize(
    "body, want",
    [
        ("status: shipped\n\n- [ ] write the runbook\n", "fail"),
        ("status: shipped\n\n- [x] write the runbook\n", "ok"),
        ("status: draft\n\n- [ ] write the runbook\n", "ok"),
        ("status: shipped\n\nNothing here has a box.\n", "ok"),
    ],
    ids=["shipped with an open box", "shipped ticked", "still a draft", "no boxes at all"],
)
def test_assertion_19_and_the_hole_in_it_a_spec_with_no_boxes_is_always_a_pass(repo, body, want):
    """Assertion 19 looks for an unticked box in a spec marked shipped. A spec that never
    had a box passes it, so deleting the production-ready list is a way to ship — the check
    can catch a forgotten item and cannot catch a missing list. status: never sits on the
    first line of a real spec, so the fixture puts frontmatter above it."""
    spec = repo / "specs" / "042-thing" / "spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(f"---\ntitle: a thing\n{body}---\n")
    got, detail = verdict(doctor.production_ready, repo)
    assert (got, "042-thing" in detail) == (want, want == "fail")


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
    lines = doctor.coverage(repo)
    rows = dict(zip([s["id"] for s in wiring.table()["surface"]], lines[1:-1], strict=True))
    unproven = [s["id"] for s in wiring.table()["surface"] if not s["proven"]]
    assert not [name for name in unproven if "BLOCKS" in rows[name]]
    assert "INERT" in rows["opencode"] and "INERT" in rows["codex-cli"]
    assert "BLOCKS" in rows["claude-code"]
    assert "MISMATCH" in lines[0]
    assert doctor.surfaces_alive(None) is not None
