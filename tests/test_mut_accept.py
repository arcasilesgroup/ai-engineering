"""The two artifacts an auditor is handed: the dated acceptance, and the chain.

Every test here names one way `ai-eng accept` or `ai-eng audit` could hand somebody a
piece of paper that is wrong — a risk with the wrong owner, an expiry that never bites, a
chain that reports itself intact because the check quietly did nothing. The exit codes and
the printed words are pinned on purpose: a person reads them off a terminal and a model
acts on them, so their text is behaviour, not decoration.
"""

from __future__ import annotations

import json
import subprocess
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from ai_engineering import accept, audit, outcome, paths, text

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()

MACHINE = "machine01"
REPO_ID = "therepo"
EVIDENCE_BYTES = b"local evidence\n"
EVIDENCE = f"proof.txt@sha256:{sha256(EVIDENCE_BYTES).hexdigest()}"
SIGNED = [
    "--by",
    "Ada",
    "--justification",
    "it is fenced off",
    "--evidence",
    "proof.txt",
]


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway repository, so no verb can reach the one we are working in."""
    root = tmp_path / "repo"
    (root / "specs").mkdir(parents=True)
    (root / "proof.txt").write_bytes(EVIDENCE_BYTES)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    return root


@pytest.fixture
def wide(monkeypatch):
    """Help text wrapped at 80 columns cannot be compared with what the source says."""
    monkeypatch.setenv("COLUMNS", "200")


@pytest.fixture
def home(tmp_path, monkeypatch):
    """The chain, the machine id and the caches, all inside tmp_path, and no repository."""
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(tmp_path / "home"))
    emit = paths.load("_emit")
    monkeypatch.setattr(emit, "repo_root", lambda start=None: None)
    return emit


@pytest.fixture
def anchored(tmp_path, monkeypatch):
    """A machine that is inside a repository, where the chain of that repository is not
    the chain of no repository. Anything that drops the root reads an empty file."""
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(tmp_path / "home"))
    emit = paths.load("_emit")
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(emit, "repo_root", lambda start=None: None)
    monkeypatch.setattr(emit, "machine_id", lambda: MACHINE)
    monkeypatch.setattr(emit, "repo_id", lambda root=None: "no-repo" if root is None else REPO_ID)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    return root


def _spec(repo: Path, name: str, body: str) -> Path:
    folder = repo / "specs" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "spec.md").write_text(body, encoding="utf-8")
    return folder / "spec.md"


def _links(emit, count: int, session: str = "s1") -> list[dict]:
    out: list[dict] = []
    prev = ""
    for seq in range(1, count + 1):
        event = {
            "ts": f"t{seq}",
            "cls": "allowed",
            "name": "a-hook",
            "session": session,
            "seq": seq,
            "prev": prev,
            "data": {},
        }
        event["hash"] = emit.digest(event)
        prev = event["hash"]
        out.append(event)
    return out


def _write_chain(emit, events: list[dict], root: Path | None = None) -> Path:
    path = emit.chain_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True, timeout=60
    )


# ------------------------------------------------------------------ accept


def test_the_accept_help_names_every_flag_and_what_it_is_for(wide, capsys):
    """The help is where somebody learns that an acceptance needs an end date and a named
    person. Emptied or renamed, the command still runs and nobody is told what to pass."""
    with pytest.raises(SystemExit) as exit_code:
        accept.main(["--help"])
    assert exit_code.value.code == 0
    out = capsys.readouterr().out
    assert "usage: ai-eng accept" in out
    for sentence in (
        "the finding id being accepted",
        "ISO date. After it, pre-push and doctor fail.",
        "the accountable person or role",
        "repository-relative evidence file; its content digest is recorded",
        "which spec it belongs to; needed when more than one is open",
        "list acceptances past their date",
    ):
        # The space before and the newline after: a sentence with something stuck to
        # either end is a different sentence, and `in` alone would not notice.
        assert f" {sentence}\n" in out, sentence


def test_outside_a_repository_it_says_so_and_fails(monkeypatch, capsys):
    """With no repository there is nowhere to write and nothing to read. Exiting zero here
    would let a CI job that runs in the wrong directory report no expired risks."""
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    assert accept.main(["--expired"]) == outcome.result("INCOMPLETE")
    assert capsys.readouterr().out == "not inside a repository\n"


def test_nothing_expired_is_a_pass_and_prints_nothing(repo, capsys):
    """--expired is read by the pre-push hook. If it failed whether or not anything had
    run out, every push would be blocked and the check would be turned off within a day."""
    _spec(repo, "001-a", text.render({"finding": "F-1", "expires": TOMORROW}))
    assert accept.main(["--expired"]) == outcome.result("PASS")
    assert capsys.readouterr().out == ""


def test_the_expired_line_names_the_id_the_finding_the_date_and_the_person(repo, capsys):
    """This line is what somebody acts on. If it lost the id or the owner, or printed the
    literal word None for an acceptance nobody signed, the report names no one to ask."""
    _spec(
        repo,
        "001-a",
        text.render(
            {
                "id": "R-001-01",
                "finding": "F-signed",
                "expires": YESTERDAY,
                "accepted_by": "A Person",
            }
        )
        + text.render({"finding": "F-bare", "expires": YESTERDAY}),
    )
    assert accept.main(["--expired"]) == outcome.result("FAIL")
    assert capsys.readouterr().out == (
        f"  EXPIRED  R-001-01  F-signed  expired {YESTERDAY}  accepted by A Person\n"
        f"  EXPIRED  ?  F-bare  expired {YESTERDAY}  accepted by ?\n"
        "  An acceptance that ran out is not an acceptance. Fix it or renew it "
        "with a reason, up to twice.\n"
    )


@pytest.mark.parametrize(
    "missing", ["--finding", "--expires", "--by", "--justification", "--evidence"]
)
def test_the_five_flags_are_required_and_the_refusal_says_which(repo, capsys, missing):
    """Exit 2 is misuse, not failure, and the sentence is the whole argument for why the
    flags exist. Reworded into noise, the next person passes neither and reads nothing.
    Leaving any one of the five out has to refuse: an unsigned acceptance used to be
    written with `TODO: a person, by name` where the owner goes, and it passed every gate
    this product has, which is the promise in the constitution the code did not keep."""
    typed = {
        "--finding": "F-1",
        "--expires": TOMORROW,
        "--by": "Ada",
        "--justification": "it is fenced off",
        "--evidence": "proof.txt",
    }
    del typed[missing]
    with pytest.raises(SystemExit) as invalid_cli:
        accept.main([word for pair in typed.items() for word in pair])
    assert invalid_cli.value.code == outcome.invalid_cli_exit()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: ai-eng accept" in captured.err
    assert captured.err.endswith(
        "ai-eng accept: error: --finding, --expires, --by, --justification and --evidence "
        "are all required; a risk acceptance needs an owner, expiry, reason and actual "
        "local evidence\n"
    )


def test_with_no_spec_the_refusal_names_the_command_that_makes_one(repo, capsys):
    """A risk with no spec has nowhere to live. The message has to hand over the exact
    next command, or the person writes the risk into a chat window instead."""
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]) == outcome.result(
        "INCOMPLETE"
    )
    assert capsys.readouterr().out == (
        "  no spec to record this against. `ai-eng spec new <slug>` first\n"
        "  A risk with no context is a note, not a decision.\n"
    )


def test_an_acceptance_carries_every_field_it_owes_and_invents_none(repo, capsys):
    """The block is the paper trail: a severity, a named owner, a justification and a
    follow-up. A field renamed is a risk register with holes in it, and the confirmation
    line is what tells the person the expiry was taken as given. An omitted follow-up is
    empty, never a marker: a marker would read as filled in and say nothing true."""
    _spec(repo, "001-a", "# a\n")
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]) == outcome.result(
        "PASS"
    )
    assert capsys.readouterr().out == (
        f"  ✓ recorded in specs/001-a/spec.md — it expires {TOMORROW}, and both "
        f"pre-push and doctor read that date.\n"
    )
    assert accept.blocks(repo)[0][1] == {
        "id": "R-001-01",
        "finding": "F-1",
        "severity": "medium",
        "accepted_by": "Ada",
        "accepted": TODAY,
        "expires": TOMORROW,
        "renewals": "0",
        "justification": "it is fenced off",
        "evidence": EVIDENCE,
        "follow_up": "",
    }


def test_what_was_typed_on_the_command_line_is_what_gets_written(repo):
    """A recorded acceptance that quietly replaces the follow-up somebody typed with a
    TODO is worse than no record: it reads as filled in and says nothing true."""
    _spec(repo, "001-a", "# a\n")
    args = ["--finding", "F-1", "--expires", TOMORROW, "--severity", "high"]
    args += [*SIGNED, "--follow-up", "delete it"]
    assert accept.main(args) == outcome.result("PASS")
    block = accept.blocks(repo)[0][1]
    assert block["severity"] == "high"
    assert block["accepted_by"] == "Ada"
    assert block["justification"] == "it is fenced off"
    assert block["evidence"] == EVIDENCE
    assert block["follow_up"] == "delete it"


def test_the_acceptance_id_takes_the_digits_out_of_the_spec_folder(repo, capsys):
    """The id ties the risk to its spec. Built from the raw folder name it would read
    R-spe-01 for a folder somebody named by hand, and two specs could collide."""
    _spec(repo, "spec-042-note", "# a\n")
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]) == outcome.result(
        "PASS"
    )
    capsys.readouterr()
    assert accept.blocks(repo)[0][1]["id"] == "R-042-01"


def test_the_named_spec_is_the_one_written_to_not_the_newest(repo, capsys):
    """--spec exists so a risk lands on the spec that owns it. Ignored, every acceptance
    piles onto whichever spec was created last and the trail points at the wrong work."""
    _spec(repo, "001-a", "# a\n")
    untouched = _spec(repo, "002-b", "# b\n")
    assert accept.main(
        ["--finding", "F-1", "--expires", TOMORROW, "--spec", "001", *SIGNED]
    ) == outcome.result("PASS")
    assert "recorded in specs/001-a/spec.md" in capsys.readouterr().out
    assert untouched.read_text(encoding="utf-8") == "# b\n"


def test_an_acceptance_a_person_wrote_by_hand_counts_as_the_first_renewal(repo, capsys):
    """The blocks in a spec are hand-editable markdown, so one can arrive without the
    renewals counter. Crashing on it, or restarting the count, is how a risk gets rolled
    forward past the ceiling of two."""
    _spec(repo, "001-a", text.render({"finding": "F-1", "expires": TOMORROW}))
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]) == outcome.result(
        "PASS"
    )
    capsys.readouterr()
    written = [b for _, b in accept.blocks(repo) if "renewals" in b]
    assert len(written) == 1
    assert written[0]["renewals"] == "1"
    assert written[0]["id"] == "R-001-02"


def test_a_spec_with_no_accepted_risks_heading_keeps_everything_it_had(repo, capsys):
    """The heading is added when it is missing. Replacing the file with the heading, or
    splitting the text on whitespace, throws away the spec somebody wrote."""
    _spec(repo, "001-a", "# title\n\nprose a person wrote\n")
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]) == outcome.result(
        "PASS"
    )
    capsys.readouterr()
    after = (repo / "specs" / "001-a" / "spec.md").read_text(encoding="utf-8")
    assert after.startswith("# title\n\nprose a person wrote\n")
    assert "## Accepted risks" in after
    assert after.endswith("\n")


def test_the_block_goes_under_the_first_heading_even_if_the_spec_names_it_twice(repo, capsys):
    """A spec is prose, so the words '## Accepted risks' can appear again further down.
    Splitting on all of them crashes the command, and splitting on the last one files the
    risk under a sentence instead of under the heading."""
    _spec(
        repo,
        "001-a",
        "# title\n\n## Accepted risks\n\nolder prose\n\n"
        '## Notes\n\nthe "## Accepted risks" heading is named again here\n',
    )
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]) == outcome.result(
        "PASS"
    )
    capsys.readouterr()
    after = (repo / "specs" / "001-a" / "spec.md").read_text(encoding="utf-8")
    assert after.index("finding: F-1") < after.index("older prose")
    assert after.endswith("\n")


def test_a_spec_with_bytes_that_are_not_utf8_is_read_not_crashed(repo):
    """Specs get pasted into from anywhere. One stray byte must not stop the scan, or an
    expired acceptance in a neighbouring file is never reported by anything."""
    folder = repo / "specs" / "001-a"
    folder.mkdir(parents=True)
    (folder / "spec.md").write_bytes(
        b"```yaml\nfinding: F-1\nexpires: 2030-01-01\n```\n\xff\xfe not text\n"
    )
    found = accept.blocks(repo)
    assert [b["finding"] for _, b in found] == ["F-1"]
    assert found[0][0] == repo / "specs" / "001-a" / "spec.md"


# ------------------------------------------------------------------ audit


def test_the_audit_help_names_both_switches(wide, capsys):
    """These two switches are what a commit hook and a CI job pass. Undocumented, the next
    person writing either one guesses, and a guess that runs is a guess nobody checks."""
    with pytest.raises(SystemExit) as exit_code:
        audit.main(["--help"])
    assert exit_code.value.code == 0
    out = capsys.readouterr().out
    assert "usage: ai-eng audit" in out
    assert " also check the anchors in git\n" in out
    assert " print the footer for commit-msg\n" in out


def test_bare_audit_verifies_and_an_unknown_action_is_refused(home, capsys):
    """`ai-eng audit` with no words after it is the documented way to check the chain. If
    the action became required, or any word were accepted, a typo would report success."""
    assert audit.main([]) == 0
    assert "links, intact" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exit_code:
        audit.main(["nonsense"])
    assert exit_code.value.code == 2


def test_anchors_is_a_switch_and_not_a_flag_that_swallows_a_word(home, capsys):
    """CI runs `ai-eng audit verify --anchors`. If it took a value, the command would die
    on its arguments and the anchor check would never run anywhere."""
    assert audit.main(["verify", "--anchors"]) == 0
    assert "links, intact" in capsys.readouterr().out


def test_the_anchor_footer_is_the_repository_this_machine_is_in(anchored, capsys):
    """The commit-msg hook pipes this straight into a commit message. A trailing newline
    of its own, or the head of the wrong repository's chain, and every anchor in git
    history points at a record that cannot be checked against anything."""
    emit = paths.load("_emit")
    events = _links(emit, 2)
    _write_chain(emit, events, anchored)
    assert audit.main(["--anchor"]) == 0
    assert capsys.readouterr().out == (
        f"\nAi-Eng-Anchor: {REPO_ID}/{MACHINE} seq=2 head={events[-1]['hash'][:12]}\n"
    )


def test_a_commit_anchoring_a_head_this_chain_never_had_is_reported(anchored, capsys):
    """Git history is replicated; the chain on this laptop is not. Truncate the chain and
    the anchors in old commits are the only thing left that notices. This runs git for
    real, because a check whose command line is wrong finds nothing and says nothing."""
    emit = paths.load("_emit")
    events = _links(emit, 2)
    _write_chain(emit, events, anchored)
    _git(anchored, "init", "-q")
    for name, value in (
        ("user.email", "t@example.invalid"),
        ("user.name", "A Tester"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", str(anchored / "no-hooks")),
    ):
        _git(anchored, "config", name, value)
    _git(
        anchored,
        "commit",
        "--allow-empty",
        "-m",
        "chore: a commit that anchors a link this chain has",
        "-m",
        f"Ai-Eng-Anchor: {REPO_ID}/{MACHINE} seq=2 head={events[-1]['hash'][:12]}",
    )
    _git(
        anchored,
        "commit",
        "--allow-empty",
        "-m",
        "chore: a commit that anchors a link this chain lost",
        "-m",
        f"Ai-Eng-Anchor: {REPO_ID}/{MACHINE} seq=9 head=aaaaaaaaaaaa",
    )

    problems = audit.verify(anchored, True)
    assert len(problems) == 2, problems
    assert "aaaaaaaaaaaa" in problems[0]
    assert "the record was truncated or replaced" in problems[0]
    assert problems[1] == (
        "Solution Intent at .ai/intent.md is INCOMPLETE: INTENT_HOME_MISSING — "
        "Solution Intent is missing at .ai/intent.md"
    )
    assert audit.verify(anchored, False) == [problems[1]], (
        "without --anchors git is not consulted, while Intent is still recomputed"
    )
    assert audit.main(["verify", "--anchors"]) == 1
    assert "BROKEN" in capsys.readouterr().out


def test_a_link_whose_hash_was_deleted_is_reported_once_as_an_edit(anchored):
    """Deleting the hash field is the cheapest way to try to hide an edit. It must be
    reported as one edited link, not also as a broken join, or the count of problems stops
    matching the count of tampered links and nobody can tell how bad it is."""
    emit = paths.load("_emit")
    events = _links(emit, 2)
    del events[0]["hash"]
    events[1]["prev"] = ""
    events[1]["hash"] = emit.digest(events[1])
    _write_chain(emit, events, anchored)
    problems = audit.verify(anchored, False)
    assert len(problems) == 2, problems
    assert "link 1: the hash does not match its own body" in problems[0]
    assert "INTENT_HOME_MISSING" in problems[1]


def test_two_broken_links_are_printed_one_per_line(anchored, capsys):
    """Somebody reads this output, or greps it. Joined by anything other than a newline,
    two findings arrive as one unreadable line and the second is missed."""
    emit = paths.load("_emit")
    events = _links(emit, 2)
    events[1]["seq"] = 5
    events[1]["prev"] = "not the link before it"
    events[1]["hash"] = emit.digest(events[1])
    _write_chain(emit, events, anchored)
    assert audit.main(["verify"]) == 1
    assert capsys.readouterr().out == (
        "  BROKEN  link 2: the sequence jumps to 5\n"
        "  BROKEN  link 2: it does not extend the link before it\n"
        "  INCOMPLETE  Solution Intent at .ai/intent.md is INCOMPLETE: "
        "INTENT_HOME_MISSING — Solution Intent is missing at .ai/intent.md\n"
    )


def test_replay_names_the_reason_the_error_or_the_verb_of_every_event(anchored):
    """Replay is what somebody reads when asked what happened. An event carrying only an
    error, or only a verb, would show a blank column or the word None, and the one line
    that explains the session would be the line that says nothing."""
    emit = paths.load("_emit")
    events = _links(emit, 4)
    for event, data in zip(
        events,
        ({"reason": "a reason"}, {"error": "an error"}, {"verb": "a verb"}, {}),
        strict=True,
    ):
        event["data"] = data
        event["hash"] = emit.digest(event)
    _write_chain(emit, events, anchored)
    assert audit.replay(anchored, "") == [
        "  t1  allowed   a-hook           a reason",
        "  t2  allowed   a-hook           an error",
        "  t3  allowed   a-hook           a verb",
        "  t4  allowed   a-hook           ",
    ]


def test_replay_prints_what_it_found_and_says_so_when_it_found_nothing(anchored, capsys):
    """With no --session, replay covers the whole chain. If it filtered by a session id
    nobody asked for, or printed the rows joined into one, the record would look empty."""
    emit = paths.load("_emit")
    events = _links(emit, 2)
    _write_chain(emit, events, anchored)
    assert audit.main(["replay"]) == 0
    assert capsys.readouterr().out == (
        "  t1  allowed   a-hook           \n  t2  allowed   a-hook           \n"
    )
    assert audit.main(["replay", "--session", "nobody"]) == 0
    assert capsys.readouterr().out == "  nothing recorded for that session\n"
