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
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from ai_engineering import (
    accept,
    acceptance,
    acceptance_privacy,
    audit,
    outcome,
    paths,
    text,
)

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def utc_today() -> str:
    """Read at the moment of the assertion, never at import.

    A module-level constant is the date the suite started, and a run that straddles UTC
    midnight then compares two different days and fails for no reason anybody can act on.
    This suite hit exactly that twice.
    """

    return datetime.now(UTC).date().isoformat()


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


def completed(execution):
    assert type(execution) is outcome.Execution
    assert execution.result == outcome.result("PASS")
    assert execution.changes
    assert execution.changes[0].status == "APPLIED"
    return execution


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway repository, so no verb can reach the one we are working in."""
    root = tmp_path / "repo"
    (root / "specs").mkdir(parents=True)
    (root / ".ai").mkdir()
    # The authority file every record writer locks, exactly as `spec new` does.
    (root / ".ai" / "intent.md").write_bytes(b'{"authority":"local"}\n')
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


def _confirmed(monkeypatch, *, scanner=None) -> None:
    """Stand in for the two boundaries a hermetic test cannot cross: the OS controlling
    terminal and the pinned secret scanner.

    Neither is faked away. The terminal boundary is proved for real by the refusal tests
    below — with no controlling terminal, and with a piped answer, the command returns
    INCOMPLETE — and the scanner is proved by the installed matrix on every supported
    system. What is stubbed here is only the part a test process cannot own.
    """

    monkeypatch.setattr(accept, "controlling_terminal_response", lambda expected: True)
    verdict = scanner or acceptance_privacy.CLEAN
    monkeypatch.setattr(accept.acceptance_privacy, "gitleaks_v1", lambda directory: verdict)


def _published(repo: Path, slug: str) -> dict:
    """The one record the command published, read back from where it actually lives."""

    found = sorted((repo / "specs" / slug).glob("acceptance-r-*/record.json"))
    assert len(found) == 1, found
    return json.loads(found[0].read_text(encoding="utf-8"))


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
        f"  EXPIRED  R-001-01  F-signed  expired {YESTERDAY}  "
        f"recorded in specs/001-a/spec.md (stored legacy)\n"
        f"  EXPIRED  R-001-02  F-bare  expired {YESTERDAY}  "
        f"recorded in specs/001-a/spec.md (derived legacy)\n"
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


def test_an_acceptance_carries_every_field_it_owes_and_invents_none(repo, capsys, monkeypatch):
    """The record is the paper trail: a severity, an accountable role, a justification and a
    follow-up, each bound to the exact bytes they were confirmed against. A field renamed is
    a risk register with holes in it, and the confirmation line is what tells the person the
    expiry was taken as given. An omitted follow-up is empty, never a marker: a marker would
    read as filled in and say nothing true."""
    _confirmed(monkeypatch)
    spec_md = _spec(repo, "001-a", "# a\n")
    stamped = utc_today()
    completed(accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]))
    assert capsys.readouterr().out.splitlines()[-2:] == [
        f"  ✓ published specs/001-a/acceptance-r-001-01/record.json — it expires {TOMORROW}, "
        f"and the push gate reads it.",
        "  This records the bytes you confirmed. It does not claim who confirmed them.",
    ]
    record = _published(repo, "001-a")
    # The stamp is the record's own, bracketed by the two moments around the call, so a run
    # that crosses UTC midnight compares the same day it was written on.
    assert record["accepted"] in {stamped, utc_today()}
    stated = record.pop("record_digest")
    assert record == {
        "schema": "urn:ai-engineering:risk-acceptance:1",
        "schema_version": "1",
        "id": "R-001-01",
        "spec": "001",
        "spec_digest": "sha256:" + sha256(b"# a\n").hexdigest(),
        "finding": "F-1",
        "severity": "medium",
        "authority_role": "Ada",
        "accepted": record["accepted"],
        "expires": TOMORROW,
        "renewals": 0,
        "renews": "",
        "renews_digest": "",
        "justification": "it is fenced off",
        "evidence": {
            "path": "proof.txt",
            "content_digest": "sha256:" + sha256(EVIDENCE_BYTES).hexdigest(),
        },
        "follow_up": "",
    }
    # The self digest is over the record's own canonical projection, so it is recomputed
    # rather than copied out of the file being checked.
    assert stated == acceptance.record_digest(record)
    # The spec it belongs to is never opened for write, which is the whole point of
    # publishing beside it instead of editing into it.
    assert spec_md.read_bytes() == b"# a\n"


def test_what_was_typed_on_the_command_line_is_what_gets_written(repo, monkeypatch):
    """A recorded acceptance that quietly replaces the follow-up somebody typed with a
    TODO is worse than no record: it reads as filled in and says nothing true."""
    _confirmed(monkeypatch)
    _spec(repo, "001-a", "# a\n")
    args = ["--finding", "F-1", "--expires", TOMORROW, "--severity", "high"]
    args += [*SIGNED, "--follow-up", "delete it"]
    completed(accept.main(args))
    record = _published(repo, "001-a")
    assert record["severity"] == "high"
    assert record["authority_role"] == "Ada"
    assert record["justification"] == "it is fenced off"
    assert record["evidence"]["path"] == "proof.txt"
    assert record["follow_up"] == "delete it"


def test_the_acceptance_id_takes_the_digits_out_of_the_spec_folder(repo, capsys, monkeypatch):
    """The id ties the risk to its spec: the digits come from the folder, never from a
    running count, so the forty-second spec's first risk is R-042-01 and not R-001-01.

    A preserved pre-canonical directory is read for history and is not a place to publish
    into. Its ordinals still participate in the namespace — that is proved in the acceptance
    register tests — but the new record lands in the canonical home a person named.
    """
    _confirmed(monkeypatch)
    _spec(repo, "042-note", "# a\n")
    completed(accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]))
    capsys.readouterr()
    assert _published(repo, "042-note")["id"] == "R-042-01"
    # The directory is the identity, in lower case, so the name and the record agree.
    assert (repo / "specs" / "042-note" / "acceptance-r-042-01").is_dir()

    _spec(repo, "spec-043-note", "# b\n")
    assert accept.main(
        ["--finding", "F-2", "--expires", TOMORROW, "--spec", "043", *SIGNED]
    ) == outcome.result("INCOMPLETE")
    assert not list((repo / "specs" / "spec-043-note").glob("acceptance-*"))


def test_the_named_spec_is_the_one_written_to_not_the_newest(repo, capsys, monkeypatch):
    """--spec exists so a risk lands on the spec that owns it. Ignored, every acceptance
    piles onto whichever spec was created last and the trail points at the wrong work."""
    _confirmed(monkeypatch)
    _spec(repo, "001-a", "# a\n")
    untouched = _spec(repo, "002-b", "# b\n")
    completed(accept.main(["--finding", "F-1", "--expires", TOMORROW, "--spec", "001", *SIGNED]))
    assert "published specs/001-a/acceptance-r-001-01/record.json" in capsys.readouterr().out
    assert untouched.read_text(encoding="utf-8") == "# b\n"
    assert not list((repo / "specs" / "002-b").glob("acceptance-*"))


def test_an_earlier_acceptance_of_the_same_finding_counts_as_the_first_renewal(
    repo, capsys, monkeypatch
):
    """Two renewals is the ceiling, so the count has to survive across commands. Restarting
    it is how a risk gets rolled forward past that ceiling one acceptance at a time."""
    _confirmed(monkeypatch)
    _spec(repo, "001-a", "# a\n")
    completed(accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]))
    completed(accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]))
    capsys.readouterr()
    published = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((repo / "specs" / "001-a").glob("acceptance-r-*/record.json"))
    ]
    renewal = next(record for record in published if record["renewals"] == 1)
    assert renewal["id"] == "R-001-02"
    assert renewal["renews"] == "R-001-01"
    assert renewal["renews_digest"].startswith("sha256:")
    # The record it renews is left exactly as it was published.
    original = next(record for record in published if record["renewals"] == 0)
    assert original["id"] == "R-001-01"
    assert original["renews"] == ""


def test_the_spec_is_never_opened_for_write_whatever_it_contains(repo, capsys, monkeypatch):
    """This replaces three tests about where a block landed inside `spec.md` and what that
    insertion preserved. None of that can happen now: no supported system can rewrite a file
    conditionally on it still holding what you read, so the record is published beside the
    spec and the spec is never a write target — whatever headings, prose or duplicate
    headings it happens to contain."""
    _confirmed(monkeypatch)
    body = (
        "# title\n\nprose a person wrote\n\n## Accepted risks\n\nolder prose\n\n"
        '## Notes\n\nthe "## Accepted risks" heading is named again here\n'
    )
    spec_md = _spec(repo, "001-a", body)
    before = spec_md.read_bytes()
    completed(accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]))
    capsys.readouterr()
    assert spec_md.read_bytes() == before
    assert _published(repo, "001-a")["finding"] == "F-1"
    # And nothing was left staged: a refused or completed publication owns its own entry.
    assert not list((repo / "specs" / "001-a").glob("pending-*"))


def test_a_spec_with_bytes_that_are_not_utf8_is_read_not_crashed(repo):
    """Specs get pasted into from anywhere. One stray byte must not stop the scan, or an
    expired acceptance in a neighbouring file is never reported by anything."""
    folder = repo / "specs" / "001-a"
    folder.mkdir(parents=True)
    (folder / "spec.md").write_bytes(
        b"```yaml\nfinding: F-1\nexpires: 2030-01-01\n```\n\xff\xfe not text\n"
    )
    register = acceptance.read(repo)
    assert register.outcome == "PASS", register.as_dict()
    assert [entry.finding for entry in register.entries] == ["F-1"]
    assert register.entries[0].home == "specs/001-a/spec.md"


# ------------------------------------------------------------------ audit


def test_bare_audit_verifies_and_an_unknown_action_is_refused(home, capsys):
    """`ai-eng audit` with no words after it is the documented way to check the chain. If
    the action became required, or any word were accepted, a typo would report success."""
    assert audit.main([]) == outcome.result("INCOMPLETE")
    assert "no repository root can be proven" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exit_code:
        audit.main(["nonsense"])
    assert exit_code.value.code == outcome.invalid_cli_exit()


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
    problems = audit.verify(anchored)
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
    assert audit.main(["verify"]) == outcome.result("FAIL")
    printed = capsys.readouterr().out
    assert printed.startswith(
        "  BROKEN  link 2: the sequence jumps to 5\n"
        "  BROKEN  link 2: it does not extend the link before it\n"
        "  INCOMPLETE  Solution Intent at .ai/intent.md is INCOMPLETE: "
        "INTENT_HOME_MISSING — Solution Intent is missing at .ai/intent.md\n"
    )
    # And the cure follows, counting links rather than complaints: one link is reported
    # broken twice here, and it is one link to answer for, not two.
    assert "1 broken link(s) in 1 run(s): 2" in printed
    assert "ai-eng audit account --range FIRST-LAST" in printed


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
    assert audit._replay(audit.read(anchored), "") == [
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
    assert audit.main(["replay"]) == outcome.result("PASS")
    assert capsys.readouterr().out == (
        "  t1  allowed   a-hook           \n  t2  allowed   a-hook           \n"
    )
    assert audit.main(["replay", "--session", "nobody"]) == outcome.result("PASS")
    assert capsys.readouterr().out == "  nothing recorded for that session\n"


def _surface(monkeypatch, capsys, module, *argv: str) -> list[str]:
    """One verb's whole help block, at a fixed width so it is comparable."""
    import pytest as _pytest

    monkeypatch.setenv("COLUMNS", "90")
    with _pytest.raises(SystemExit):
        module.main([*argv, "--help"])
    return capsys.readouterr().out.rstrip("\n").splitlines()


def test_the_accept_verb_says_exactly_what_it_accepts(monkeypatch, capsys):
    """One hundred and eleven mutants of `accept.main` survived, and its surface is most.

    This is the verb that accepts a risk — the one thing the constitution says a model never
    does — so what it asks for is the whole of the accountability: who, why, until when, and
    against what evidence. A help sentence rewritten or a field quietly made optional is
    invisible to every test that passes valid arguments and reads the outcome.

    `--expires` carries its consequence in its own help, and that is deliberate: a date with
    no stated effect is a date nobody diaries.
    """
    from ai_engineering import accept

    assert _surface(monkeypatch, capsys, accept) == [
        "usage: ai-eng accept [-h] [--finding FINDING] [--severity SEVERITY] [--expires EXPIRES]",
        "                     [--by BY] [--justification JUSTIFICATION] [--evidence EVIDENCE]",
        "                     [--follow-up FOLLOW_UP] [--spec SPEC] [--expired]",
        "",
        "options:",
        "  -h, --help            show this help message and exit",
        "  --finding FINDING     the finding id being accepted",
        "  --severity SEVERITY",
        "  --expires EXPIRES     ISO date. After it, pre-push and doctor fail.",
        "  --by BY               the accountable person or role",
        "  --justification JUSTIFICATION",
        "                        why this is acceptable, in one line",
        "  --evidence EVIDENCE   repository-relative evidence file; its content digest is",
        "                        recorded",
        "  --follow-up FOLLOW_UP",
        "  --spec SPEC           which spec it belongs to; needed when more than one is open",
        "  --expired             list acceptances past their date",
    ]


def test_the_audit_verb_says_exactly_what_it_accepts(monkeypatch, capsys):
    """Three actions and four flags, and the three that matter are the ones that answer for a
    broken chain: which links, why, and who.

    They are optional in the parser and required by the action, which is worth knowing before
    reading either — `account` refuses without them at a controlling terminal rather than in
    argparse, because the phrase a person types is the proof and argparse cannot ask for it.

    It was six flags until specification 022 deleted the anchor. This list is the whole of
    what the verb accepts, so a switch that comes back without a decision reds here.
    """
    from ai_engineering import audit

    assert _surface(monkeypatch, capsys, audit) == [
        "usage: ai-eng audit [-h] [--range RANGE] [--why WHY] [--by BY] [--session SESSION]",
        "                    [--limit LIMIT] [--revalidate FINDING_ID] [--file FILE]",
        "                    [--trigger TRIGGER]",
        "                    [{verify,replay,account}]",
        "",
        "positional arguments:",
        "  {verify,replay,account}",
        "",
        "options:",
        "  -h, --help            show this help message and exit",
        "  --range RANGE         the broken links to answer for, as FIRST-LAST",
        "  --why WHY             why those links are there",
        "  --by BY               the person answering for them",
        "  --session SESSION",
        "  --limit LIMIT         bounded sample size; gates the lane behind the cost policy",
        "  --revalidate FINDING_ID",
        "                        revalidate one finding at finding granularity (spec 030 B-030-3)",
        "  --file FILE           the file the finding lives in",
        "  --trigger TRIGGER     the exact substring the finding flagged",
    ]


def test_an_action_outside_the_three_is_refused_rather_than_run_as_verify(monkeypatch, capsys):
    """The positional is a closed choice, and the closure is what matters: `audit` with a
    misspelled action must not quietly walk the chain as if `verify` had been asked for. A
    person who typed `acount` gets a refusal, not a report they will read as an answer."""
    import pytest as _pytest

    from ai_engineering import audit

    monkeypatch.setenv("COLUMNS", "90")
    with _pytest.raises(SystemExit) as refused:
        audit.main(["acount"])

    assert refused.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
