"""The record half, as tests that fail.

These nine modules write the things a person is later asked to defend: the spec, the
decision, the dated risk acceptance, the hash chain, and the weekly paragraph read off
them. Every test below names one way that record could lie without anybody noticing, and
goes red the moment it does. Nothing here touches the real home or the real repository.
"""

from __future__ import annotations

import builtins
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_engineering import (
    accept,
    acceptance,
    acceptance_privacy,
    audit,
    cli,
    contract,
    decide,
    exception,
    outcome,
    paths,
    report,
    spec,
    spec_transaction,
    text,
)

TODAY = date.today().isoformat()
# The record stores a UTC date; local midnight is not the same instant.
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
SIGNED = [
    "--by",
    "Ada",
    "--justification",
    "it is fenced off",
    "--evidence",
    "proof.txt",
]
A_WEEK_AGO = (date.today() - timedelta(days=7)).isoformat()


def utc_today() -> str:
    """Read at the moment of the assertion, never at import.

    A module-level constant is the date the suite started, and a run that straddles UTC
    midnight then compares two different days and fails for no reason anybody can act on.
    This suite hit exactly that twice.
    """

    return datetime.now(UTC).date().isoformat()


def _fixture_spec(root: Path, slug: str, ref: str = "") -> Path:
    home = root / "specs"
    home.mkdir(exist_ok=True)
    identifiers = [
        int(folder.name[:3])
        for folder in home.iterdir()
        if spec._CANONICAL_SPEC.fullmatch(folder.name)
    ]
    number = f"{max(identifiers, default=0) + 1:03d}"
    target = home / f"{number}-{slug}" / "spec.md"
    target.parent.mkdir()
    target.write_bytes(spec._render(number, slug, ref))
    return target


def completed(execution):
    assert type(execution) is outcome.Execution
    assert execution.result == outcome.result("PASS")
    assert execution.changes and execution.changes[0].status == "APPLIED"
    return execution


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Every path the record writes to, moved inside tmp_path: the chain, the machine id
    and the caches. A test that writes to the real home is a test nobody can run twice."""
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(tmp_path / "home"))
    emit = paths.load("_emit")
    monkeypatch.setattr(emit, "repo_root", lambda start=None: None)
    return emit


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway repository root, so no verb can find the one we are working in."""
    root = tmp_path / "repo"
    (root / "specs").mkdir(parents=True)
    (root / ".ai").mkdir()
    # The authority file every record writer locks, exactly as `spec new` does.
    (root / ".ai" / "intent.md").write_bytes(b'{"authority":"local"}\n')
    (root / "proof.txt").write_bytes(b"local evidence\n")
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    return root


def _confirmed(monkeypatch) -> None:
    """The controlling terminal and the pinned scanner, the two boundaries a test process
    cannot own. Both are proved for real elsewhere: the terminal by the refusal tests, the
    scanner by the installed matrix."""

    monkeypatch.setattr(accept, "controlling_terminal_response", lambda expected: True)
    monkeypatch.setattr(
        accept.acceptance_privacy, "gitleaks_v1", lambda directory: acceptance_privacy.CLEAN
    )


def _records(repo: Path, slug: str) -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((repo / "specs" / slug).glob("acceptance-r-*/record.json"))
    ]


# ------------------------------------------------------------------ text


@pytest.mark.parametrize(
    ("block", "expected"),
    [
        ("name: a\nlicense: \"MIT\"\nother: 'x'\n", {"name": "a", "license": "MIT", "other": "x"}),
        ("a: 1\n\n# a comment\n  # indented comment\nb: 2\n", {"a": "1", "b": "2"}),
        ("d: >-\n  one\n  two\n", {"d": "one two"}),
        ("d: >\n  one\n  two\n", {"d": "one two"}),
        ("d: |\n  one\n  two\n", {"d": "one two"}),
        ("d: |-\n  one\n  two\n", {"d": "one two"}),
        ("a: 1\nd: >-\n  folded\nb: 2\n", {"a": "1", "d": "folded", "b": "2"}),
        ("empty:\n", {"empty": ""}),
    ],
)
def test_a_flat_block_reads_exactly_what_it_says(block, expected):
    """A folded description read as the single character '>' is a skill whose routing text
    silently became empty, and a quoted licence read with its quotes on never matches."""
    assert text.flat_yaml(block) == expected


@pytest.mark.parametrize(
    "block",
    ["  orphan: v\n", "\torphan: v\n", "a sentence\n", "name: a\n- a bullet\n", "9lives: no\n"],
)
def test_a_block_that_is_not_a_flat_mapping_raises_rather_than_guessing(block):
    """A parser that partitions and guesses is how a malformed block passes a gate today
    and fails a person six weeks later. Indented text with no key above it is not data."""
    with pytest.raises(ValueError):
        text.flat_yaml(block)


def test_a_file_with_no_frontmatter_is_a_refusal_not_an_empty_dict(tmp_path):
    """If a missing header read as {} instead of raising, every field check in the skill
    contract would pass over a file that has no header at all."""
    bare = tmp_path / "SKILL.md"
    bare.write_text("# no header here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no frontmatter"):
        text.frontmatter(bare)
    good = tmp_path / "good.md"
    good.write_text("---\nname: a\n---\n\nbody\n", encoding="utf-8")
    assert text.frontmatter(good) == {"name": "a"}


@pytest.mark.parametrize(
    "value",
    [
        "short",
        "w" * 200,  # one token longer than the width: cut in half it comes back altered
        "-".join(["hyphenated"] * 20),  # a hyphen is not a place to break a word either
        ("word " * 60).strip(),
        "x" * (text.WIDTH - len("k: ")),  # exactly the width, which must not wrap
        "x" * (text.WIDTH - len("k: ") + 1),  # one over it, which must
    ],
    ids=["short", "one long token", "hyphenated", "many words", "exactly the width", "one over"],
)
def test_a_value_of_any_shape_survives_being_rendered_and_read_back(value):
    """The fold has to be reversible or the record quietly changes what somebody wrote.
    Continuation lines are indented by exactly two spaces, which is what `flat_yaml` above
    reads as a continuation rather than as a key it cannot parse."""
    block = text.render({"k": value})
    body = block.split("\n", 1)[1].rsplit("```", 2)[0]
    assert text.flat_yaml(body) == {"k": value}
    lines = body.splitlines()
    assert max(len(line) for line in lines) <= text.WIDTH or " " not in value
    assert all(line.startswith("  ") and not line.startswith("   ") for line in lines[1:])
    assert (len(lines) == 1) is (len(f"k: {value}") <= text.WIDTH)


def test_a_block_that_cannot_be_read_is_undecidable_and_never_invisible():
    """A malformed block used to be caught and skipped, so an acceptance whose YAML was a
    little wrong disappeared from the expiry check that both `pre-push` and `doctor` read
    — and the gate went green over a risk that had run out. Silence on a parse failure is
    the exact shape of a false green. The message names the file, or whoever reads the
    refusal is told a record somewhere cannot be read and not which one."""
    body = "```yaml\n  broken\n```\n\ntext\n\n```yaml\nfinding: F-1\nexpires: 2030-01-01\n```\n"
    with pytest.raises(ValueError, match="specs/001-a/spec.md cannot be read: indented line"):
        text.yaml_blocks(body, "specs/001-a/spec.md")
    with pytest.raises(ValueError, match="^a record block cannot be read: "):
        text.yaml_blocks(body)  # called without a name, it still says what happened
    good = "```yaml\nfinding: F-1\nexpires: 2030-01-01\n```\n"
    assert text.yaml_blocks(good) == [{"finding": "F-1", "expires": "2030-01-01"}]
    assert text.flat_yaml(text.render({"a": "1"}).split("\n", 1)[1].rsplit("```", 2)[0]) == {
        "a": "1"
    }


# ------------------------------------------------------------------ accept


def _acceptance(finding: str, expires: str, **extra) -> str:
    return text.render({"finding": finding, "expires": expires, "severity": "low", **extra})


def test_an_acceptance_expires_the_day_after_its_date_not_on_it(repo, capsys):
    """Off by one here either fails a build on the last valid day of an acceptance, or
    lets a finding that ran out yesterday through. The date on the paper is inclusive."""
    (repo / "specs" / "001-a").mkdir()
    (repo / "specs" / "001-a" / "spec.md").write_text(
        _acceptance("F-today", TODAY)
        + _acceptance("F-future", TOMORROW)
        + _acceptance("F-past", YESTERDAY)
        + text.render({"finding": "F-undated"}),
        encoding="utf-8",
    )
    assert [b["finding"] for b in accept.expired(repo)] == ["F-past"]
    assert len(acceptance.read(repo).entries) == 3
    assert accept.main(["--expired"]) == outcome.result("FAIL"), (
        "an expired acceptance has to fail the build"
    )
    assert "EXPIRED" in capsys.readouterr().out


@pytest.mark.parametrize("order", [(0, 1), (1, 0)])
def test_a_renewal_retires_the_block_it_renews_wherever_it_sits(repo, order):
    """Renewing a finding in a later spec used to change nothing: the reader returned the
    expired original and the renewal as two independent results, so the push gate and
    assertion 16 both stayed red on the old block and no renewal anybody ever recorded had
    retired anything. The highest renewal per finding is the live one, and it is the live
    one whichever spec it lives in and whichever order the files are read in."""
    written = [
        _acceptance("F-rolled", YESTERDAY, renewals="0"),
        _acceptance("F-rolled", TOMORROW, renewals="1"),
    ]
    (repo / "specs" / "001-a").mkdir()
    (repo / "specs" / "001-a" / "spec.md").write_text(
        written[order[0]] + written[order[1]] + _acceptance("F-untouched", YESTERDAY),
        encoding="utf-8",
    )
    assert len(acceptance.read(repo).entries) == 3
    assert [b["finding"] for b in accept.expired(repo)] == ["F-untouched"]


def test_a_block_whose_renewal_counter_is_not_a_number_counts_as_none(repo):
    """The blocks are hand-editable markdown, so the counter can arrive as a word. Reading
    it with a bare int() crashes the push gate on a typo somebody made in a spec."""
    (repo / "specs" / "001-a").mkdir()
    (repo / "specs" / "001-a" / "spec.md").write_text(
        _acceptance("F-rolled", YESTERDAY, renewals="once")
        + _acceptance("F-rolled", TOMORROW, renewals="1"),
        encoding="utf-8",
    )
    assert accept.expired(repo) == []


def test_the_first_risk_of_a_spec_is_numbered_one_whatever_the_repository_holds(
    repo, capsys, monkeypatch
):
    """The identifier is supposed to read as the nth risk of its spec. It was minted by
    counting every block in the repository, so the first risk recorded against a new spec
    came out numbered eight — which reads as the eighth risk of that spec and is not a fact
    about anything."""
    _confirmed(monkeypatch)
    (repo / "specs" / "001-old").mkdir()
    (repo / "specs" / "001-old" / "spec.md").write_text("# old\n", encoding="utf-8")
    (repo / "specs" / "002-new").mkdir()
    (repo / "specs" / "002-new" / "spec.md").write_text("# new\n", encoding="utf-8")
    for finding in ("F-a", "F-b"):
        completed(
            accept.main(["--finding", finding, "--expires", TOMORROW, "--spec", "001", *SIGNED])
        )
    completed(accept.main(["--finding", "F-c", "--expires", TOMORROW, "--spec", "002", *SIGNED]))
    capsys.readouterr()
    assert [record["id"] for record in _records(repo, "001-old")] == ["R-001-01", "R-001-02"]
    assert [record["id"] for record in _records(repo, "002-new")] == ["R-002-01"]


def test_a_rationale_of_any_length_survives_being_written_and_read_back(repo, capsys, monkeypatch):
    """A four-hundred-character rationale has to come back exactly as it was typed.

    It used to have to survive a YAML renderer that folded it onto continuation lines so a
    diff could show it; canonical JSON keeps the string whole, so what is left to prove is
    the round trip itself and the schema's byte bound.
    """
    _confirmed(monkeypatch)
    reason = " ".join(f"clause number {n} of the argument" for n in range(14))
    assert 400 < len(reason.encode("utf-8")) <= 2000
    (repo / "specs" / "001-a").mkdir()
    (repo / "specs" / "001-a" / "spec.md").write_text("# a\n", encoding="utf-8")
    args = [
        "--finding",
        "F-1",
        "--expires",
        TOMORROW,
        "--by",
        "Ada",
        "--justification",
        reason,
        "--evidence",
        "proof.txt",
    ]
    completed(accept.main(args))
    capsys.readouterr()
    assert _records(repo, "001-a")[0]["justification"] == reason

    # Over the schema's byte bound it is refused before anything is staged, rather than
    # published into a record the register would then refuse to read forever.
    oversized = list(args)
    oversized[1], oversized[7] = "F-2", "x" * 2001
    assert accept.main(oversized) == outcome.result("INCOMPLETE")
    assert len(_records(repo, "001-a")) == 1
    assert not list((repo / "specs" / "001-a").glob("pending-*"))


def test_a_malformed_block_stops_the_gate_rather_than_disappearing_from_it(repo, capsys):
    """All four callers, in one place: the expiry reader raises, `--expired` refuses and
    exits non-zero — which is what `pre-push` reads — and the write path says nothing was
    written instead of tracebacking on a neighbour somebody typed wrong. Before this, the
    block was skipped, the risk was invisible and every one of them reported green."""
    (repo / "specs" / "001-a").mkdir()
    (repo / "specs" / "001-a" / "spec.md").write_text(
        "```yaml\n  broken\n```\n" + _acceptance("F-past", YESTERDAY), encoding="utf-8"
    )
    assert accept.main(["--expired"]) == outcome.result("INCOMPLETE")
    assert "UNDECIDABLE" in capsys.readouterr().out
    assert accept.main(["--finding", "F-2", "--expires", TOMORROW, *SIGNED]) == outcome.result(
        "INCOMPLETE"
    )
    assert "Nothing was written" in capsys.readouterr().out


def test_an_acceptance_with_no_end_date_is_refused(repo, capsys):
    """An acceptance with no expiry is not an acceptance, it is a permanent exception
    written in the language of a temporary one."""
    with pytest.raises(SystemExit) as invalid_cli:
        accept.main(["--finding", "F-1", *SIGNED])
    assert invalid_cli.value.code == outcome.invalid_cli_exit()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--finding, --expires, --by, --justification and --evidence are all required" in (
        captured.err
    )
    assert acceptance.read(repo).entries == ()


def test_the_third_renewal_is_refused_and_writes_nothing(repo, capsys, monkeypatch):
    """Two renewals is the ceiling: after that the finding gets fixed or the answer
    changes. If the counter did not hold, a risk could be rolled forward forever."""
    _confirmed(monkeypatch)
    (repo / "specs" / "123-big").mkdir()
    (repo / "specs" / "123-big" / "spec.md").write_text("# big\n", encoding="utf-8")
    for expected in range(accept.MAX_RENEWALS + 1):
        completed(accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]))
        assert _records(repo, "123-big")[-1]["renewals"] == expected
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]) == outcome.result(
        "FAIL"
    )
    published = _records(repo, "123-big")
    assert len(published) == accept.MAX_RENEWALS + 1
    assert "That is the ceiling" in capsys.readouterr().out
    assert [record["id"] for record in published] == ["R-123-01", "R-123-02", "R-123-03"]
    # A refused renewal writes nothing at all, final or temporary.
    assert not list((repo / "specs" / "123-big").glob("pending-*"))
    assert (repo / "specs" / "123-big" / "spec.md").read_bytes() == b"# big\n"


def test_publishing_an_acceptance_never_opens_the_spec_for_write(repo, monkeypatch):
    """This replaces the test that checked where a block landed inside `spec.md`.

    Nothing lands inside it any more. The whole point of publishing beside the spec is that
    no supported system can rewrite a file conditionally on it still holding what you read,
    so the safe move is to never make somebody else's prose a write target at all.
    """
    _confirmed(monkeypatch)
    folder = repo / "specs" / "001-a"
    folder.mkdir()
    body = (
        "# title\n\n## Accepted risks\n\nprose a person wrote\n\n## Production-ready\n\n- [ ] CI\n"
    )
    (folder / "spec.md").write_text(body, encoding="utf-8")
    before = (folder / "spec.md").read_bytes()
    stamped = utc_today()
    completed(accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]))
    assert (folder / "spec.md").read_bytes() == before
    record = _records(repo, "001-a")[0]
    assert record["authority_role"] == "Ada"
    assert record["accepted"] in {stamped, utc_today()}
    assert record["justification"] == "it is fenced off"
    # And the record is bound to the exact bytes that were displayed, not to a re-reading.
    assert record["spec_digest"] == "sha256:" + hashlib.sha256(before).hexdigest()


def test_an_acceptance_with_no_spec_is_refused(repo, capsys):
    """A risk with no context is a note, not a decision, so there is nowhere to put it."""
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW, *SIGNED]) == outcome.result(
        "INCOMPLETE"
    )
    assert "no spec to record this against" in capsys.readouterr().out


# ------------------------------------------------------------------ audit


def _links(emit, count: int) -> list[dict]:
    out: list[dict] = []
    prev = ""
    for seq in range(1, count + 1):
        event = {"ts": "t", "cls": "allowed", "name": "n", "seq": seq, "prev": prev, "data": {}}
        event["hash"] = emit.digest(event)
        prev = event["hash"]
        out.append(event)
    return out


def _write(emit, events: list[dict]) -> Path:
    path = emit.chain_path(None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def _jump(event):
    event["seq"] = 5


def _orphan(event):
    event["prev"] = ""


def _edit(event):
    event["data"] = {"tampered": True}


@pytest.mark.parametrize(
    ("mutate", "rehash", "expected"),
    [
        (None, False, None),
        (_jump, True, "the sequence jumps to 5"),
        (_orphan, True, "does not extend the link before it"),
        (_edit, False, "the hash does not match its own body"),
    ],
)
def test_each_way_of_breaking_the_chain_is_reported_as_itself(home, mutate, rehash, expected):
    """Three different tampering stories — a deleted link, a re-parented link, an edited
    body — must not collapse into one vague 'chain broken', or nobody can tell which."""
    events = _links(home, 2)
    if mutate:
        mutate(events[1])
        if rehash:
            events[1]["hash"] = home.digest(events[1])
    _write(home, events)
    problems = audit.verify(None, False)
    if expected is None:
        assert problems == []
    else:
        assert len(problems) == 1, problems
        assert expected in problems[0]


def test_a_whole_chain_verifies_and_the_command_says_how_many(home, tmp_path, monkeypatch, capsys):
    """`audit verify` reporting success on an empty or unreadable chain is a green nobody
    earned; it must count the links it actually walked."""
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(home, "repo_id", lambda root=None: "no-repo")
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    monkeypatch.setattr(audit, "verify_intent", lambda repository: [])
    _write(home, _links(home, 4))
    assert audit.main(["verify"]) == outcome.result("PASS")
    assert "4 links, intact" in capsys.readouterr().out
    _write(home, _links(home, 2)[:1] + [dict(_links(home, 2)[1], prev="x")])
    assert audit.main(["verify"]) == outcome.result("FAIL")
    assert "BROKEN" in capsys.readouterr().out


def test_replay_filters_to_one_session(home, tmp_path, monkeypatch, capsys):
    """Replay is what somebody reads when asked what happened in a session. If the filter
    were ignored, they would be handed every session on the machine instead."""
    events = _links(home, 2)
    events[0]["session"] = "aaa"
    events[0]["hash"] = home.digest(events[0])
    events[1]["session"] = "bbb"
    events[1]["data"] = {"reason": "the reason"}
    events[1]["prev"] = events[0]["hash"]
    events[1]["hash"] = home.digest(events[1])
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(home, "repo_id", lambda root=None: "no-repo")
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    _write(home, events)
    assert len(audit.replay(None, "")) == 2
    rows = audit.replay(None, "bbb")
    assert len(rows) == 1 and "the reason" in rows[0]
    assert audit.main(["replay", "--session", "nobody"]) == outcome.result("PASS")
    assert "nothing recorded" in capsys.readouterr().out


def test_the_anchor_written_into_a_commit_is_one_the_verifier_can_read_back(home, monkeypatch):
    """The commit-msg hook writes this line and audit reads it with a regular expression.
    If the two ever disagree on the format, every anchor in git history stops counting and
    nothing says so — the tamper-evidence quietly becomes decoration."""
    monkeypatch.setattr(home, "repo_id", lambda root=None: "testrepo")
    events = _links(home, 2)
    _write(home, events)
    line = audit.anchor_line(None)
    found = audit.ANCHOR.search(line)
    assert found, line
    assert found.group(3) == "2" and found.group(4) == events[-1]["hash"][:12]


# Not `SIGNED`: this module already binds that name to an acceptance argument list, and
# rebinding it at import time would have replaced it for every test in the file.
COAUTHOR = "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
FOOTER = "Ai-Eng-Anchor: testrepo/abcdef012345 seq=2 head=deadbeefcafe"


def _commit_msg(tmp_path, *, holds=True, body="body.\n", shim=""):
    """Run the real hook over one message and report what it did.

    The stub populates both streams the way the real verb does — progress on stderr, and
    on stdout the footer *plus* the rendered verdict — so a test can tell "took the footer"
    from "took whatever was on stdout"."""

    repo = tmp_path / "clone"
    repo.mkdir()
    for argv in (["init", "-q"], ["config", "ai.managed", "true"]):
        subprocess.run(["git", *argv], cwd=repo, check=True, capture_output=True)

    stub = tmp_path / "stub-eng"
    stub.write_text(
        "#!/bin/sh\n"
        'echo "  RUNNING 1/4  load the verb" >&2\n'
        + (
            f"printf '\\n{FOOTER}\\n'\nprintf '\\u2713 PASS\\nExit code: 0\\n'\n"
            if holds
            else "printf '\\u2717 FAIL\\nReason: a violation\\nExit code: 1\\n'\n"
        ),
        encoding="utf-8",
    )
    stub.chmod(0o755)

    environment = {**os.environ, "AI_ENG": str(stub)}
    if shim:
        # A `git` that fails the way a real one can. Everything the hook asks of git before
        # this point still has to work, so it delegates the rest to the real one.
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        real = shlex.quote(shutil.which("git"))
        (bin_dir / "git").write_text(
            f'#!/bin/sh\ncase "$1" in\n  {shim}\nesac\nexec {real} "$@"\n',
            encoding="utf-8",
        )
        (bin_dir / "git").chmod(0o755)
        environment["PATH"] = f"{bin_dir}{os.pathsep}{environment.get('PATH', '')}"

    # A message that already carries a trailer: 145 of this repository's 298 commits do.
    # The first version of this test wrote one with none — the majority shape, and the one
    # where an anchor appended after a blank line still parses, because it starts a second
    # trailer block and there is no first one to orphan. On a message with a trailer,
    # `git interpret-trailers --parse` then returns the anchor alone and the
    # `Co-Authored-By` GitHub reads for attribution is gone. The test agreed with the
    # defect by picking the input that could not see it.
    original = f"test(x): a probe\n\n{body}\n{COAUTHOR}\n"
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text(original, encoding="utf-8")
    hook = Path(__file__).resolve().parents[1] / "git-hooks" / "commit-msg"
    done = subprocess.run(
        ["bash", str(hook), str(message)],
        cwd=repo,
        capture_output=True,
        text=True,
        env=environment,
    )
    return done, message.read_text(encoding="utf-8"), original, repo


def _trailers(repo, message: str, *, divider: bool = True) -> list[str]:
    parsed = subprocess.run(
        ["git", "interpret-trailers", *([] if divider else ["--no-divider"]), "--parse"],
        cwd=repo,
        input=message,
        capture_output=True,
        text=True,
        check=True,
    )
    return parsed.stdout.splitlines()


@pytest.mark.parametrize("holds", [True, False])
def test_the_commit_msg_hook_appends_the_footer_and_never_the_verdict(tmp_path, holds):
    """The hook itself, executed. Its format was tested and its behaviour never was, and
    every failure that hid in the gap was in the behaviour.

    `audit --anchor` puts its progress on stderr and its verdict on stdout, because the
    verdict is the data every other verb produces. The hook appended stdout wholesale, so a
    chain that does not hold wrote `✗ FAIL / Reason: ... / Exit code: 1` into the commit
    message — and the call ends in `|| true`, so nothing would have said so."""

    done, written, original, repo = _commit_msg(tmp_path, holds=holds)

    # Never a gate, in either direction: a hook that refuses commits is a hook people
    # delete, and the escape they reach for is the one rule 3 forbids.
    assert done.returncode == 0, done.stderr
    assert "Exit code" not in written, written
    assert "PASS" not in written and "FAIL" not in written, written
    if holds:
        assert written.endswith(f"{FOOTER}\n"), written
        # Git has to see it as a trailer, and see the one that was already there. Asserting
        # only that the anchor parses is what let the append that deletes its neighbour go
        # green.
        assert _trailers(repo, written) == [COAUTHOR, FOOTER], written
    else:
        assert written == original
        assert "not anchored" in done.stderr, done.stderr


def test_a_divider_in_the_body_does_not_orphan_the_trailer_beside_the_anchor(tmp_path):
    """Git stops reading a commit message at a bare `---`. Without `--no-divider` the
    anchor lands above it, mid-body, and `--parse` returns the anchor alone — the exact
    defect the placement fix was written to close, reappearing on a different input. No
    commit here carries a divider today, which is why only an attacker of the fix would
    have found it.

    Asserted on the bytes, not through `--parse`: git's default reading stops at the
    divider and finds no trailer block at all, with or without the anchor, so a parse-based
    assertion would be measuring git's divider rule rather than where the hook put the
    line. What has to hold is that the anchor joins the trailer already at the end."""

    done, written, _, repo = _commit_msg(tmp_path, body="Some prose.\n\n---\n\nMore prose.\n")
    assert done.returncode == 0, done.stderr
    assert written.splitlines()[-2:] == [COAUTHOR, FOOTER], written
    assert _trailers(repo, written, divider=False) == [COAUTHOR, FOOTER], written


def test_a_git_that_cannot_place_the_anchor_leaves_the_commit_standing(tmp_path):
    """The footer is not a gate, and the placement fix quietly made it one: under
    `set -euo pipefail` a bare `git interpret-trailers` hands its exit status to the hook,
    and git then refuses the commit. It is not hypothetical — a message file in a directory
    git cannot write its temporary file into exits 128, and a git too old for one of these
    options exits 129, which is what this shim reproduces. Not a config git declines to
    parse: an earlier version of this docstring said so, and that route cannot reach the
    anchor at all, because the hook asks git for `ai.managed` on its fifth line and exits 0
    when that fails. The person's escape from a hook that refuses commits is `--no-verify`,
    which rule 3 forbids and a guard blocks: the hook whose bug forces its own bypass."""

    done, written, original, _ = _commit_msg(
        tmp_path,
        shim='interpret-trailers) echo "error: unknown option \\`in-place\'" >&2; exit 129 ;;',
    )
    assert done.returncode == 0, f"the hook refused the commit: {done.stderr}"
    assert written == original, written
    assert "could not be placed" in done.stderr, done.stderr


@pytest.mark.parametrize("head", ["known", "aaaaaaaaaaaa"])
def test_a_commit_anchoring_a_link_this_chain_has_lost_is_reported(home, monkeypatch, head):
    """Git history is replicated and immutable; the chain on this laptop is neither. If
    somebody truncates or replaces the local chain, the anchors in old commits are what
    notices. A verifier that only walked the local file would find nothing wrong."""
    monkeypatch.setattr(home, "repo_id", lambda root=None: "testrepo")
    events = _links(home, 2)
    _write(home, events)
    anchored = events[-1]["hash"][:12] if head == "known" else head
    log = f"Ai-Eng-Anchor: testrepo/{home.machine_id()} seq=2 head={anchored}\n\x00"
    monkeypatch.setattr(
        audit.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=log),
    )
    problems = audit.verify(Path("/nowhere"), True)
    assert problems[-1] == (
        "Solution Intent at .ai/intent.md is INCOMPLETE: INTENT_HOME_MISSING — "
        "Solution Intent is missing at .ai/intent.md"
    )
    chain_problems = problems[:-1]
    assert bool(chain_problems) is (head != "known"), problems
    if chain_problems:
        assert "the record was truncated or replaced" in chain_problems[0]


def test_a_truncated_line_is_reported_as_broken_not_as_a_crash(home, capsys):
    """A chain is appended to by hooks that can be killed mid-write. A half-written last line
    is when the verifier has to speak, and skipping it would report a cut chain as intact."""
    path = _write(home, _links(home, 2))
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"ts": "t", "cls": "allo\n')
    problems = audit.verify(None, False)
    assert len(problems) == 1 and "link 3" in problems[0]
    assert audit.main(["verify"]) == outcome.result("FAIL")
    assert "intact" not in capsys.readouterr().out


# ------------------------------------------------------------------ spec


@pytest.mark.parametrize(
    ("existing", "expected"),
    [
        ((), "001"),
        (("001-a",), "002"),
        (("001-a", "007-b"), "008"),
        (("001-a", "002-b", "003-c"), "004"),
        (("001-a", "pending-007-b"), "008"),
        (("notes", "README"), "001"),
    ],
)
def test_a_spec_number_is_never_handed_out_twice(existing, expected):
    """Numbering off the highest, not off the count: delete spec 002 and the next spec
    must still be 003, or two different specs end up sharing a number in the record."""
    generation = spec_transaction.Generation("specs", (1, 2), 0, 0, 0)
    inventory = spec_transaction.Inventory(
        tuple(existing),
        tuple(name for name in existing if name.startswith("pending-")),
        generation,
        object(),
    )
    assert spec._number(inventory) == expected


@pytest.mark.parametrize("names", [("999-z",), ("001-a", "001-b"), ("1st-attempt",)])
def test_an_exhausted_or_ambiguous_spec_namespace_refuses(names):
    generation = spec_transaction.Generation("specs", (1, 2), 0, 0, 0)
    inventory = spec_transaction.Inventory(tuple(names), (), generation, object())
    with pytest.raises(spec_transaction.Unsafe):
        spec._number(inventory)


def test_a_new_spec_carries_all_eight_production_ready_boxes_unticked(tmp_path):
    """Rule 11 is these eight boxes. A template that shipped seven, or shipped one already
    ticked, is a checklist that says a thing was verified when nobody verified it."""
    first = _fixture_spec(tmp_path, "a-thing")
    body = first.read_text()
    assert first == tmp_path / "specs" / "001-a-thing" / "spec.md"
    assert [line for line in body.splitlines() if line.startswith("- [ ]")] == [
        f"- [ ] {box}" for box in spec.BOXES
    ]
    assert len(spec.BOXES) == 8
    assert "- [x]" not in body
    header = text.flat_yaml(body.split("---\n", 2)[1])
    assert header == {
        "id": "001",
        "slug": "a-thing",
        "status": "draft",
        "date": TODAY,
        "ref": "",
        "supersedes": "",
    }
    assert "# A thing" in body
    assert _fixture_spec(tmp_path, "next").parent.name == "002-next"


def test_a_work_item_is_recorded_in_the_frontmatter_and_nothing_else(tmp_path):
    """--ref records where the work came from and prefills nothing. The heading stays the
    slug and the problem stays a TODO, because the section is the author's to write."""
    body = _fixture_spec(tmp_path, "a-thing", "owner/repo#45").read_text()
    assert 'ref: "owner/repo#45"' in body
    assert "# A thing" in body
    assert "TODO: what is true today" in body


def test_a_superseded_spec_is_hidden_from_the_listing_unless_asked_for(tmp_path):
    """The listing is the index. If a superseded spec kept showing, somebody would read a
    decision that has already been overturned and act on it."""
    _fixture_spec(tmp_path, "old")
    _fixture_spec(tmp_path, "new")
    old = tmp_path / "specs" / "001-old" / "spec.md"
    old.write_text(old.read_text().replace("status: draft", "status: superseded"), encoding="utf-8")
    assert [row.split()[0] for row in spec.listing(tmp_path, False)] == ["002-new"]
    assert [row.split()[0] for row in spec.listing(tmp_path, True)] == ["001-old", "002-new"]
    assert "superseded" in spec.listing(tmp_path, True)[0]


def test_spec_show_matches_by_prefix_and_says_so_when_it_cannot(repo, capsys):
    """`spec show 002` has to find 002-whatever. Falling back to printing some other spec
    is worse than printing nothing."""
    _fixture_spec(repo, "only")
    result = spec.main(["show", "001"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert "# Only" in capsys.readouterr().out
    result = spec.main(["show", "404"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert "no spec matches" in capsys.readouterr().out
    result = spec.main(["list"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"


# ------------------------------------------------------------------ decide


def test_an_adr_number_follows_the_highest_on_disk(tmp_path):
    """Two ADRs sharing a number is the classic failure of ADR tooling: the second one
    overwrites the first and the decision it recorded is simply gone."""
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    assert decide.next_number(tmp_path) == "0001"
    (tmp_path / "docs" / "adr" / "0007-a.md").write_text("status: accepted\n")
    assert decide.next_number(tmp_path) == "0008"


def test_proposing_a_supersession_preserves_the_old_madr_and_the_spec(tmp_path):
    """A proposal records its predecessor but cannot grant its own transition authority."""
    _fixture_spec(tmp_path, "a-thing")
    target = spec.target(tmp_path)
    spec_before = target.read_bytes()
    first = decide.promote(tmp_path, "Use one queue", "", target)
    assert first.name == "0001-use-one-queue.md"
    first_before = first.read_bytes()
    second = decide.promote(tmp_path, "Use two queues", "0001", target)
    assert second.name == "0002-use-two-queues.md"
    assert first.read_bytes() == first_before
    header = text.flat_yaml(second.read_text().split("---\n", 1)[1].split("---\n", 1)[0])
    assert header["spec"] == "001" and header["supersedes"] == "0001"
    assert header["status"] == "proposed" and header["date"] == TODAY
    assert target.read_bytes() == spec_before
    assert [row.split()[0] for row in decide.listing(tmp_path)] == [
        "0001-use-one-queue",
        "0002-use-two-queues",
    ]


def test_a_decision_recorded_against_a_spec_with_no_decisions_heading_still_lands(repo, capsys):
    """Specs written before this heading existed, or by hand, must not swallow the
    decision silently — the whole point is that it is in the diff."""
    folder = repo / "specs" / "001-a"
    folder.mkdir()
    (folder / "spec.md").write_text("# a\n", encoding="utf-8")
    result = decide.main(["A choice", "--why", "because"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    body = (folder / "spec.md").read_text()
    assert "## Decisions" in body and "decision: A choice" in body and "rationale: because" in body
    with pytest.raises(SystemExit) as stopped:
        decide.main([])
    assert stopped.value.code == outcome.invalid_cli_exit()
    assert "a decision needs a title" in capsys.readouterr().err


def test_a_decision_with_no_spec_is_refused(repo, capsys):
    """Without a spec there is no context to review the decision in, so it is not written
    somewhere convenient — it is not written at all."""
    result = decide.main(["A choice"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert "no spec to record this against" in capsys.readouterr().out
    result = decide.main(["--list"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert "no MADRs yet" in capsys.readouterr().out


# ------------------------------------------------------------------ digest


def _event(name: str, cls: str, reason: str = "", ts: str | None = None) -> dict:
    return {"name": name, "cls": cls, "ts": ts or TODAY, "session": "s", "data": {"reason": reason}}


def test_only_events_inside_the_window_are_counted(tmp_path):
    """A digest that quietly included last month's events would report a control as busy
    long after it stopped firing. The far edge is inclusive: a seven-day window that
    dropped the event seven days old would lose one day of the record every week."""
    old = (date.today() - timedelta(days=30)).isoformat()
    events = [
        _event("a", "blocked", ts=old),
        _event("edge", "blocked", ts=A_WEEK_AGO),
        _event("b", "blocked"),
    ]
    assert [e["name"] for e in report.within(events, 7)] == ["edge", "b"]
    assert len(report.within(events, 60)) == 3


@pytest.mark.parametrize(("count", "rows"), [(1, 0), (2, 0), (3, 1), (7, 1)])
def test_the_same_verdict_three_times_is_flagged_as_owed_a_script(count, rows):
    """Rule 12's trigger, measured rather than felt. Two is a coincidence; three is a
    judgement that always comes out the same, which means it should be code."""
    events = [_event("loop_guard", "blocked", "same reason") for _ in range(count)]
    found = report.repeats(events)
    assert len(found) == rows
    if rows:
        assert f"{count}× same verdict each time" in found[0]


def test_a_bypassed_guard_is_named_in_the_report_a_person_reads(home, monkeypatch, capsys):
    """This report is where a bypass becomes visible to somebody other than the person who
    took it. If a bypass could be recorded and never surface here, the record is decorative."""
    monkeypatch.setattr(report.doctor, "coverage", lambda root: [])
    _write(
        home,
        [
            dict(_event("change_scope_guard", "bypassed", "shipping late"), seq=1),
            dict(_event("change_scope_guard", "bypassed", "shipping late"), seq=2),
            dict(_event("change_scope_guard", "bypassed", "shipping late"), seq=3),
            dict(_event("injection_guard", "blocked", "a payload"), seq=4),
            dict(_event("cli", "error", ""), seq=5),
        ],
    )
    completed(report.main(["digest"]))
    out = capsys.readouterr().out
    assert "Bypassed 3 times." in out
    assert "3× change_scope_guard — shipping late" in out
    assert "A guard you bypass three times is a guard to fix or to delete." in out
    assert "Blocked 1 times" in out and "injection_guard — a payload" in out
    assert "loop_guard" in out and "injection_guard" not in out.split("Quiet controls")[1]
    assert "owed a script" in out
    assert json.loads((paths.home() / "cache" / "digest.json").read_text())["read"] <= time.time()


def test_a_quiet_week_says_so_instead_of_reporting_a_clean_bill(home, monkeypatch, capsys):
    """Zero blocks is either a quiet week or a control that has stopped working, and the
    report must not let a reader assume the first one. A week means seven days: a default
    window quietly widened to a month reports a month under a heading that says week."""
    monkeypatch.setattr(report.doctor, "coverage", lambda root: [])
    completed(report.main(["digest"]))
    out = capsys.readouterr().out
    assert f"Week of {A_WEEK_AGO}" in out
    assert "a control that is no longer firing" in out
    assert "Commands: none" in out and "Errors: 0" in out


# ------------------------------------------------------------------ contract


VALID_HEADER = "name: ai-thing\ndescription: Does one thing. Not for two — use /ai-other.\n"


def _skill(root: Path, header: str = VALID_HEADER, body: str = "A body.\n") -> Path:
    folder = root / "ai-thing"
    folder.mkdir(exist_ok=True)
    path = folder / "SKILL.md"
    path.write_text(f"---\n{header}---\n\n{body}", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (VALID_HEADER, None),
        (VALID_HEADER + "license: MIT\nversion: 1\n", None),
        (VALID_HEADER + "colour: red\n", "['colour'] are not in the contract"),
        (VALID_HEADER.replace("ai-thing", "ai-other", 1), "the name field says 'ai-other'"),
        ("name: ai-thing\n", "no description"),
        (VALID_HEADER.replace("Not for two — use /ai-other.", "and nothing else."), "'Not for X"),
        (VALID_HEADER + "context: fork\n", "context: fork without background: false"),
        (VALID_HEADER + "context: fork\nbackground: false\n", None),
        (VALID_HEADER + "background: false\n", None),
        (VALID_HEADER + "when_to_use: whenever\n", "shares the description's character budget"),
        (VALID_HEADER + "disable-model-invocation: true\n", None),
    ],
)
def test_every_clause_of_the_skill_contract_has_its_own_verdict(tmp_path, header, expected):
    """Each of these is a rule the product states in prose somewhere. A rule that only
    exists as a sentence is the failure family this repository exists to kill."""
    found = contract.audit_one(_skill(tmp_path, header))
    if expected is None:
        assert found == []
    else:
        assert any(expected in problem for problem in found), found


@pytest.mark.parametrize("word", contract.JARGON)
def test_each_banned_word_is_caught_wherever_it_sits(tmp_path, word):
    """Rule 9: written so somebody who does not code can follow. A check that only looked
    at the description would let the same word through in the body underneath it."""
    found = contract.audit_one(_skill(tmp_path, body=f"We {word.upper()} the thing.\n"))
    assert len(found) == 1 and repr(word) in found[0]


def test_a_skill_over_the_line_cap_is_a_procedure_that_should_be_a_script(tmp_path):
    """Eighty lines is the cap, and it is inclusive: a file of exactly eighty is legal and
    eighty-one is not. One line over has to be caught, or the cap is a suggestion and the
    file grows into the 528-file version this rebuild replaced — and one line under has to
    pass, or the cap silently becomes seventy-nine and every skill at the limit is red."""

    def skill_of(lines: int) -> Path:
        """A SKILL.md of exactly `lines` lines, header and blank line included."""
        return _skill(tmp_path, body="\n".join("line" for _ in range(lines - 5)) + "\n")

    at_the_cap = skill_of(contract.CEILING)
    assert len(at_the_cap.read_text().splitlines()) == contract.CEILING
    assert contract.audit_one(at_the_cap) == []
    found = contract.audit_one(skill_of(contract.CEILING + 1))
    assert any(f"Over {contract.CEILING} means" in problem for problem in found)


def test_a_skill_with_no_header_is_reported_and_not_read_further(tmp_path):
    """Reading fields out of a file that has no header would hand back an empty dict and
    every later check would pass on nothing."""
    folder = tmp_path / "ai-thing"
    folder.mkdir()
    (folder / "SKILL.md").write_text("# no header\n", encoding="utf-8")
    found = contract.audit_one(folder / "SKILL.md")
    assert len(found) == 1 and "no frontmatter" in found[0]
    assert contract.audit(tmp_path) == found
    assert contract.audit(tmp_path / "nothing-here") == [
        f"no skills found under {tmp_path / 'nothing-here'}"
    ]


def test_a_description_over_the_budget_is_named_with_its_length(tmp_path):
    """The description is the routing decision and it is billed on every session. Over the
    budget it gets truncated by the surface, so the 'Not for' clause is the part lost."""
    clause = " Not for other things — use /ai-other."

    def described(length: int) -> Path:
        text = "x" * (length - len(clause)) + clause
        assert len(text) == length
        return _skill(tmp_path, f"name: ai-thing\ndescription: {text}\n")

    assert contract.audit_one(described(contract.DESCRIPTION_MAX)) == [], "the budget is inclusive"
    found = contract.audit_one(described(contract.DESCRIPTION_MAX + 1))
    assert len(found) == 1 and f"over {contract.DESCRIPTION_MAX}" in found[0]


def test_the_line_count_leaves_out_the_record_and_counts_everything_else(tmp_path):
    """The ceiling only means something if the count is honest: the record grows by design
    and is excluded, and anything we chose to write is counted."""
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "specs" / "001-a").mkdir(parents=True)
    (tmp_path / "specs" / "001-a" / "spec.md").write_text("a\n" * 50)
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "adr" / "0001-a.md").write_text("a\n" * 40)
    (tmp_path / "LICENSE").write_text("l\n" * 30)
    (tmp_path / "README.md").write_text("r\n" * 4)
    (tmp_path / "thing.py").write_text("x = 1\n" * 3)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True, capture_output=True)
    assert contract.repo_lines(tmp_path) == 7


# ------------------------------------------------------------------ exception


def test_an_agent_cannot_grant_itself_a_bypass(home, capsys):
    """The whole design gate is that a bypass needs a real keyboard. With no terminal
    attached, nothing may be granted — this is the one that stops a loop self-approving."""
    result = exception.main(["--skip", "in a hurry"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert "there is no keyboard here" in capsys.readouterr().out
    assert not (paths.home() / "cache" / "bypass.json").exists()


@pytest.mark.parametrize(
    ("typed", "status"),
    [("yes", "PASS"), ("YES ", "PASS"), ("y", "CANCELLED"), ("", "CANCELLED")],
)
def test_a_bypass_is_granted_only_on_the_whole_word_and_is_recorded(
    home, monkeypatch, capsys, typed, status
):
    """Anything short of typing the word is not consent. When it is granted, the grant is
    time boxed and an event says who took it — a silent bypass is the failure being cured.
    The box is the one the person was shown: a grant that outlives the minutes printed on
    the prompt is consent taken for longer than it was given."""
    monkeypatch.setattr(
        exception.sys, "stdin", type("T", (), {"isatty": staticmethod(lambda: True)})()
    )
    monkeypatch.setattr(builtins, "input", lambda prompt="": typed)
    result = exception.main(["--skip", "in a hurry", "--guard", "loop_guard"])
    assert type(result) is outcome.Result
    assert result.outcome == status
    promised = int(re.search(r"for (\d+) minutes", capsys.readouterr().out).group(1)) * 60
    grant = paths.home() / "cache" / "bypass.json"
    assert grant.exists() is (status == "PASS")
    if status == "PASS":
        data = json.loads(grant.read_text())
        assert data["guard"] == "loop_guard" and data["reason"] == "in a hurry"
        assert 0 < data["expires"] - time.time() <= promised
        events = [json.loads(line) for line in home.chain_path(None).read_text().splitlines()]
        assert events[-1]["cls"] == "bypassed" and events[-1]["name"] == "loop_guard"


def test_a_bypass_can_only_name_a_guard_that_exists(home):
    """Granting a bypass of a guard nobody has heard of writes a grant that unblocks
    nothing and reads, in the record, as if a control had been waived."""
    with pytest.raises(SystemExit) as invalid:
        exception.main(["--skip", "x", "--guard", "not_a_guard"])
    assert invalid.value.code == outcome.invalid_cli_exit()


# ------------------------------------------------------------------ cli


def test_the_verb_table_is_the_whole_surface():
    """An entry point does not exist until it is in this table, because the table is what
    emits. A verb listed here with no module is a command that dies on first use."""
    import importlib

    assert len(cli.VERBS) == 10
    for verb in cli.VERBS:
        assert callable(importlib.import_module(f"ai_engineering.{verb}").main)


@pytest.mark.parametrize("argv", [[], ["--help"], ["-h"], ["help"]])
def test_asking_for_help_lists_every_verb_and_exits_zero(argv, capsys):
    """Help that crashed, or that listed nine of ten verbs, hides a command from the only
    place anybody looks for it."""
    assert cli.main(argv) == 0
    out = capsys.readouterr().out
    assert all(verb in out for verb in cli.VERBS)


def test_a_stream_that_cannot_spell_a_tick_gets_a_line_rather_than_a_traceback(
    tmp_path, monkeypatch
):
    """Windows hands a bare print() a cp1252 stream, and `ai-eng spec new` writes a tick in
    its success line. The first time the install matrix ever ran, that ended the Windows leg
    in a UnicodeEncodeError with the spec already on disk — so the verb had done its work
    and reported a crash. Rich's path was never affected, which is why nothing local saw it."""
    import io

    authority = tmp_path / "specs" / "000-authority" / "spec.md"
    authority.parent.mkdir(parents=True)
    authority_bytes = b'---\nid: "000"\nstatus: superseded\n---\n\n# Authority\n'
    authority.write_bytes(authority_bytes)
    record = json.loads(
        (Path(__file__).parent / "fixtures" / "intent-v1.json").read_text(encoding="utf-8")
    )["base"]["intent"]
    record["relations"] = [
        {
            "kind": "spec",
            "id": "000",
            "path": "specs/000-authority/spec.md",
            "target_digest": f"sha256:{hashlib.sha256(authority_bytes).hexdigest()}",
        }
    ]
    record["lifecycle"] = {
        "status": "active",
        "transitions": [
            {
                "from": "draft",
                "to": "active",
                "changed_at": "2026-08-14T10:00:00Z",
                "authority_role": "repository maintainer",
                "approval_ref": "change-request-17",
            }
        ],
        "approval": {
            "authority_role": "repository maintainer",
            "approval_ref": "change-request-17",
            "approved_at": "2026-08-14T10:00:00Z",
        },
    }
    intent_home = tmp_path / ".ai" / "intent.md"
    intent_home.parent.mkdir()
    intent_home.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    narrow = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    stdout, cwd = sys.stdout, Path.cwd()
    try:
        os.chdir(tmp_path)
        sys.stdout = narrow
        assert cli.main(["spec", "new", "a-thing"]) == 0
    finally:
        sys.stdout, _ = stdout, os.chdir(cwd)
    assert (tmp_path / "specs" / "001-a-thing" / "spec.md").exists()


def test_an_unknown_verb_exits_non_zero_and_says_so_on_stderr(capsys):
    """Exiting zero on a typo makes a script that calls `ai-eng` believe a gate ran."""
    assert cli.main(["nope"]) == 2
    captured = capsys.readouterr()
    # The complaint is on stderr and the verb list is on stdout: `ai-eng nope | grep spec`
    # still finds the verb you meant, and `2>/dev/null` still hides the scolding.
    assert "there is no verb 'nope'" in captured.err
    assert "there is no verb" not in captured.out
    assert all(verb in captured.out for verb in cli.VERBS)
    assert cli.main(["--version"]) == 0
    assert "ai-engineering" in capsys.readouterr().out


def test_a_verb_that_runs_is_recorded_with_its_exit_code(home, monkeypatch, capsys):
    """The table records that it ran. Without that event the digest cannot tell a week
    when nothing was blocked from a week when nothing was used."""
    monkeypatch.setattr(report.doctor, "coverage", lambda root: [])
    assert cli.main(["report", "digest"]) == 0
    capsys.readouterr()
    events = [json.loads(line) for line in home.chain_path(None).read_text().splitlines()]
    assert [e["cls"] for e in events] == ["command"]
    assert events[0]["data"]["verb"] == "report" and events[0]["data"]["exit"] == 0
    assert events[0]["data"]["ms"] >= 0


def test_a_verb_that_blows_up_is_recorded_before_the_traceback_reaches_the_user(home, monkeypatch):
    """A crash is the event most worth having and the easiest to lose: the process is on
    its way out. If it were emitted after the re-raise it would never be written."""

    def boom(argv):
        raise RuntimeError("nothing was written")

    monkeypatch.setattr(exception, "main", boom)
    with pytest.raises(RuntimeError):
        cli.main(["exception"])
    events = [json.loads(line) for line in home.chain_path(None).read_text().splitlines()]
    assert events[-1]["cls"] == "error"
    assert "nothing was written" in events[-1]["data"]["error"]


def test_an_interrupt_is_a_clean_exit_and_not_an_error(home, monkeypatch, capsys):
    """Somebody pressing control-C has not hit a bug, and turning it into one would fill
    the record with errors nobody caused."""

    def stop(argv):
        raise KeyboardInterrupt

    monkeypatch.setattr(exception, "main", stop)
    assert cli.main(["exception"]) == 130
    assert "nothing was written" in capsys.readouterr().err
    events = [json.loads(line) for line in home.chain_path(None).read_text().splitlines()]
    assert [e["cls"] for e in events] == ["command"]
