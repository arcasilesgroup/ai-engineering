"""The record half, as tests that fail.

These nine modules write the things a person is later asked to defend: the spec, the
decision, the dated risk acceptance, the hash chain, and the weekly paragraph read off
them. Every test below names one way that record could lie without anybody noticing, and
goes red the moment it does. Nothing here touches the real home or the real repository.
"""

from __future__ import annotations

import builtins
import json
import re
import subprocess
import time
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_engineering import accept, audit, cli, contract, decide, digest, paths, plan, spec, text

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
A_WEEK_AGO = (date.today() - timedelta(days=7)).isoformat()


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
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    return root


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


def test_one_broken_yaml_block_does_not_hide_the_good_ones_after_it():
    """The risk acceptances are yaml blocks inside markdown. If a typo in the first block
    stopped the scan, an expired acceptance further down the file would never be found."""
    body = "```yaml\n  broken\n```\n\ntext\n\n```yaml\nfinding: F-1\nexpires: 2030-01-01\n```\n"
    assert text.yaml_blocks(body) == [{"finding": "F-1", "expires": "2030-01-01"}]
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
    assert len(accept.blocks(repo)) == 3
    assert accept.main(["--expired"]) == 1, "an expired acceptance has to fail the build"
    assert "EXPIRED" in capsys.readouterr().out


def test_an_acceptance_with_no_end_date_is_refused(repo, capsys):
    """An acceptance with no expiry is not an acceptance, it is a permanent exception
    written in the language of a temporary one."""
    assert accept.main(["--finding", "F-1"]) == 2
    assert "not an acceptance" in capsys.readouterr().out
    assert accept.blocks(repo) == []


def test_the_third_renewal_is_refused_and_writes_nothing(repo, capsys):
    """Two renewals is the ceiling: after that the finding gets fixed or the answer
    changes. If the counter did not hold, a risk could be rolled forward forever."""
    (repo / "specs" / "1234-big").mkdir()
    (repo / "specs" / "1234-big" / "spec.md").write_text("# big\n", encoding="utf-8")
    for expected in range(accept.MAX_RENEWALS + 1):
        assert accept.main(["--finding", "F-1", "--expires", TOMORROW]) == 0
        assert int(accept.blocks(repo)[0][1]["renewals"]) == expected
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW]) == 1
    assert len(accept.blocks(repo)) == accept.MAX_RENEWALS + 1
    assert "That is the ceiling" in capsys.readouterr().out
    assert [b["id"] for _, b in accept.blocks(repo)] == ["R-123-03", "R-123-02", "R-123-01"]


def test_writing_an_acceptance_does_not_eat_the_text_under_its_heading(repo):
    """The block goes under '## Accepted risks'. An insert that split on the heading and
    dropped the tail would silently delete whatever a person had written below it."""
    folder = repo / "specs" / "001-a"
    folder.mkdir()
    body = (
        "# title\n\n## Accepted risks\n\nprose a person wrote\n\n## Production-ready\n\n- [ ] CI\n"
    )
    (folder / "spec.md").write_text(body, encoding="utf-8")
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW, "--by", "A Person"]) == 0
    after = (folder / "spec.md").read_text()
    assert "prose a person wrote" in after and "## Production-ready" in after
    assert after.index("finding: F-1") > after.index("## Accepted risks")
    assert after.index("finding: F-1") < after.index("prose a person wrote")
    block = accept.blocks(repo)[0][1]
    assert block["accepted_by"] == "A Person" and block["accepted"] == TODAY
    assert block["justification"].startswith("TODO")


def test_an_acceptance_with_no_spec_is_refused(repo, capsys):
    """A risk with no context is a note, not a decision, so there is nowhere to put it."""
    assert accept.main(["--finding", "F-1", "--expires", TOMORROW]) == 1
    assert "no spec to attach this to" in capsys.readouterr().out


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


def test_a_whole_chain_verifies_and_the_command_says_how_many(home, capsys):
    """`audit verify` reporting success on an empty or unreadable chain is a green nobody
    earned; it must count the links it actually walked."""
    _write(home, _links(home, 4))
    assert audit.main(["verify"]) == 0
    assert "4 links, intact" in capsys.readouterr().out
    _write(home, _links(home, 2)[:1] + [dict(_links(home, 2)[1], prev="x")])
    assert audit.main(["verify"]) == 1
    assert "BROKEN" in capsys.readouterr().out


def test_replay_filters_to_one_session(home, capsys):
    """Replay is what somebody reads when asked what happened in a session. If the filter
    were ignored, they would be handed every session on the machine instead."""
    events = _links(home, 2)
    events[0]["session"] = "aaa"
    events[1]["session"] = "bbb"
    events[1]["data"] = {"reason": "the reason"}
    _write(home, events)
    assert len(audit.replay(None, "")) == 2
    rows = audit.replay(None, "bbb")
    assert len(rows) == 1 and "the reason" in rows[0]
    assert audit.main(["replay", "--session", "nobody"]) == 0
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
    monkeypatch.setattr(audit.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=log))
    problems = audit.verify(Path("/nowhere"), True)
    assert bool(problems) is (head != "known"), problems
    if problems:
        assert "the record was truncated or replaced" in problems[0]


@pytest.mark.xfail(
    raises=json.JSONDecodeError,
    strict=True,
    reason="audit.read calls json.loads with no guard, so one truncated line makes "
    "`ai-eng audit verify` die with a traceback instead of reporting BROKEN. "
    "doctor.events guards the same read; audit.read does not.",
)
def test_a_truncated_line_is_reported_as_broken_not_as_a_crash(home):
    """A chain is appended to by hooks that can be killed mid-write. A half-written last
    line is exactly when you most want the verifier to speak, and it crashes instead."""
    path = _write(home, _links(home, 2))
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"ts": "t", "cls": "allo\n')
    assert audit.verify(None, False), "a truncated line should be reported, not raise"


# ------------------------------------------------------------------ spec


@pytest.mark.parametrize(
    ("existing", "expected"),
    [
        ((), "001"),
        (("001-a",), "002"),
        (("001-a", "007-b"), "008"),
        (("001-a", "002-b", "003-c"), "004"),
        (("999-z",), "1000"),
        (("notes", "README"), "001"),
    ],
)
def test_a_spec_number_is_never_handed_out_twice(tmp_path, existing, expected):
    """Numbering off the highest, not off the count: delete spec 002 and the next spec
    must still be 003, or two different specs end up sharing a number in the record."""
    (tmp_path / "specs").mkdir()
    for name in existing:
        (tmp_path / "specs" / name).mkdir()
    assert spec.next_number(tmp_path) == expected


@pytest.mark.xfail(
    raises=ValueError,
    strict=True,
    reason="spec.next_number does int() on the first dash-separated chunk of anything the "
    "glob [0-9]*-* matched, so a folder named specs/1st-attempt/ raises ValueError and "
    "`ai-eng spec new` stops working in that repository until somebody renames it.",
)
def test_a_folder_that_is_not_a_spec_does_not_stop_numbering(tmp_path):
    """One hand-made folder under specs/ should be ignored, not turn the next spec into a
    traceback for everybody who works in that repository afterwards."""
    (tmp_path / "specs" / "001-a").mkdir(parents=True)
    (tmp_path / "specs" / "1st-attempt").mkdir()
    assert spec.next_number(tmp_path) == "002"


def test_a_new_spec_carries_all_eight_production_ready_boxes_unticked(tmp_path):
    """Rule 11 is these eight boxes. A template that shipped seven, or shipped one already
    ticked, is a checklist that says a thing was verified when nobody verified it."""
    first = spec.create(tmp_path, "a-thing", "")
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
    assert spec.create(tmp_path, "next", "").parent.name == "002-next"


def test_a_work_item_is_recorded_in_the_frontmatter_and_nothing_else(tmp_path):
    """--ref records where the work came from and prefills nothing. The heading stays the
    slug and the problem stays a TODO, because the section is the author's to write."""
    body = spec.create(tmp_path, "a-thing", "owner/repo#45").read_text()
    assert 'ref: "owner/repo#45"' in body
    assert "# A thing" in body
    assert "TODO: what is true today" in body


def test_a_superseded_spec_is_hidden_from_the_listing_unless_asked_for(tmp_path):
    """The listing is the index. If a superseded spec kept showing, somebody would read a
    decision that has already been overturned and act on it."""
    spec.create(tmp_path, "old", "")
    spec.create(tmp_path, "new", "")
    old = tmp_path / "specs" / "001-old" / "spec.md"
    old.write_text(old.read_text().replace("status: draft", "status: superseded"), encoding="utf-8")
    assert [row.split()[0] for row in spec.listing(tmp_path, False)] == ["002-new"]
    assert [row.split()[0] for row in spec.listing(tmp_path, True)] == ["001-old", "002-new"]
    assert "superseded" in spec.listing(tmp_path, True)[0]


def test_spec_show_matches_by_prefix_and_says_so_when_it_cannot(repo, capsys):
    """`spec show 002` has to find 002-whatever. Falling back to printing some other spec
    is worse than printing nothing."""
    spec.create(repo, "only", "")
    assert spec.main(["show", "001"]) == 0
    assert "# Only" in capsys.readouterr().out
    assert spec.main(["show", "404"]) == 1
    assert "no spec matches" in capsys.readouterr().out
    assert spec.main(["list"]) == 0


# ------------------------------------------------------------------ decide


def test_an_adr_number_follows_the_highest_on_disk(tmp_path):
    """Two ADRs sharing a number is the classic failure of ADR tooling: the second one
    overwrites the first and the decision it recorded is simply gone."""
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    assert decide.next_number(tmp_path) == "0001"
    (tmp_path / "docs" / "adr" / "0007-a.md").write_text("status: accepted\n")
    assert decide.next_number(tmp_path) == "0008"


def test_promoting_a_decision_supersedes_the_old_one_and_points_the_spec_at_it(tmp_path):
    """A promoted decision has to leave a pointer in its spec and flip the ADR it replaced,
    or the repository holds two live ADRs that contradict each other."""
    spec.create(tmp_path, "a-thing", "")
    first = decide.promote(tmp_path, "Use one queue", "")
    assert first.name == "0001-use-one-queue.md"
    second = decide.promote(tmp_path, "Use two queues", "0001")
    assert second.name == "0002-use-two-queues.md"
    assert "status: superseded by 0002" in first.read_text()
    header = text.flat_yaml(second.read_text().split("---\n", 1)[1].split("---\n", 1)[0])
    assert header["spec"] == "001-a-thing" and header["supersedes"] == "0001"
    assert header["status"] == "proposed" and header["date"] == TODAY
    body = (tmp_path / "specs" / "001-a-thing" / "spec.md").read_text()
    assert "adr: 0002" in body and body.index("## Decisions") < body.index("adr: 0002")
    assert "## Accepted risks" in body, "the sections below Decisions were eaten"
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
    assert decide.main(["A choice", "--why", "because"]) == 0
    body = (folder / "spec.md").read_text()
    assert "## Decisions" in body and "decision: A choice" in body and "rationale: because" in body
    assert decide.main([]) == 2
    assert "a decision needs a title" in capsys.readouterr().out


def test_a_decision_with_no_spec_is_refused(repo, capsys):
    """Without a spec there is no context to review the decision in, so it is not written
    somewhere convenient — it is not written at all."""
    assert decide.main(["A choice"]) == 1
    assert "no spec to record this against" in capsys.readouterr().out
    assert decide.main(["--list"]) == 0
    assert "no ADRs yet" in capsys.readouterr().out


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
    assert [e["name"] for e in digest.within(events, 7)] == ["edge", "b"]
    assert len(digest.within(events, 60)) == 3


@pytest.mark.parametrize(("count", "rows"), [(1, 0), (2, 0), (3, 1), (7, 1)])
def test_the_same_verdict_three_times_is_flagged_as_owed_a_script(count, rows):
    """Rule 12's trigger, measured rather than felt. Two is a coincidence; three is a
    judgement that always comes out the same, which means it should be code."""
    events = [_event("loop_guard", "blocked", "same reason") for _ in range(count)]
    found = digest.repeats(events)
    assert len(found) == rows
    if rows:
        assert f"{count}× same verdict each time" in found[0]


def test_a_bypassed_guard_is_named_in_the_report_a_person_reads(home, monkeypatch, capsys):
    """This report is where a bypass becomes visible to somebody other than the person who
    took it. If a bypass could be recorded and never surface here, the record is decorative."""
    monkeypatch.setattr(digest.doctor, "coverage", lambda root: [])
    _write(
        home,
        [
            dict(_event("design_gate", "bypassed", "shipping late"), seq=1),
            dict(_event("design_gate", "bypassed", "shipping late"), seq=2),
            dict(_event("design_gate", "bypassed", "shipping late"), seq=3),
            dict(_event("injection_guard", "blocked", "a payload"), seq=4),
            dict(_event("cli", "error", ""), seq=5),
        ],
    )
    assert digest.main([]) == 0
    out = capsys.readouterr().out
    assert "Bypassed 3 times." in out
    assert "3× design_gate — shipping late" in out
    assert "A guard you bypass three times is a guard to fix or to delete." in out
    assert "Blocked 1 times" in out and "injection_guard — a payload" in out
    assert "loop_guard" in out and "injection_guard" not in out.split("Quiet controls")[1]
    assert "owed a script" in out
    assert json.loads((paths.home() / "cache" / "digest.json").read_text())["read"] <= time.time()


def test_a_quiet_week_says_so_instead_of_reporting_a_clean_bill(home, monkeypatch, capsys):
    """Zero blocks is either a quiet week or a control that has stopped working, and the
    report must not let a reader assume the first one. A week means seven days: a default
    window quietly widened to a month reports a month under a heading that says week."""
    monkeypatch.setattr(digest.doctor, "coverage", lambda root: [])
    assert digest.main([]) == 0
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


# ------------------------------------------------------------------ plan


def test_an_agent_cannot_grant_itself_a_bypass(home, capsys):
    """The whole design gate is that a bypass needs a real keyboard. With no terminal
    attached, nothing may be granted — this is the one that stops a loop self-approving."""
    assert plan.main(["--skip", "in a hurry"]) == 1
    assert "there is no keyboard here" in capsys.readouterr().out
    assert not (paths.home() / "cache" / "bypass.json").exists()


@pytest.mark.parametrize(("typed", "code"), [("yes", 0), ("YES ", 0), ("y", 1), ("", 1)])
def test_a_bypass_is_granted_only_on_the_whole_word_and_is_recorded(
    home, monkeypatch, capsys, typed, code
):
    """Anything short of typing the word is not consent. When it is granted, the grant is
    time boxed and an event says who took it — a silent bypass is the failure being cured.
    The box is the one the person was shown: a grant that outlives the minutes printed on
    the prompt is consent taken for longer than it was given."""
    monkeypatch.setattr(plan.sys, "stdin", type("T", (), {"isatty": staticmethod(lambda: True)})())
    monkeypatch.setattr(builtins, "input", lambda prompt="": typed)
    assert plan.main(["--skip", "in a hurry", "--guard", "loop_guard"]) == code
    promised = int(re.search(r"for (\d+) minutes", capsys.readouterr().out).group(1)) * 60
    grant = paths.home() / "cache" / "bypass.json"
    assert grant.exists() is (code == 0)
    if code == 0:
        data = json.loads(grant.read_text())
        assert data["guard"] == "loop_guard" and data["reason"] == "in a hurry"
        assert 0 < data["expires"] - time.time() <= promised
        events = [json.loads(line) for line in home.chain_path(None).read_text().splitlines()]
        assert events[-1]["cls"] == "bypassed" and events[-1]["name"] == "loop_guard"


def test_a_bypass_can_only_name_a_guard_that_exists(home):
    """Granting a bypass of a guard nobody has heard of writes a grant that unblocks
    nothing and reads, in the record, as if a control had been waived."""
    with pytest.raises(SystemExit):
        plan.main(["--skip", "x", "--guard", "not_a_guard"])


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
    monkeypatch.setattr(digest.doctor, "coverage", lambda root: [])
    assert cli.main(["digest"]) == 0
    capsys.readouterr()
    events = [json.loads(line) for line in home.chain_path(None).read_text().splitlines()]
    assert [e["cls"] for e in events] == ["command"]
    assert events[0]["data"]["verb"] == "digest" and events[0]["data"]["exit"] == 0
    assert events[0]["data"]["ms"] >= 0


def test_a_verb_that_blows_up_is_recorded_before_the_traceback_reaches_the_user(home, monkeypatch):
    """A crash is the event most worth having and the easiest to lose: the process is on
    its way out. If it were emitted after the re-raise it would never be written."""

    def boom(argv):
        raise RuntimeError("nothing was written")

    monkeypatch.setattr(plan, "main", boom)
    with pytest.raises(RuntimeError):
        cli.main(["plan"])
    events = [json.loads(line) for line in home.chain_path(None).read_text().splitlines()]
    assert events[-1]["cls"] == "error"
    assert "nothing was written" in events[-1]["data"]["error"]


def test_an_interrupt_is_a_clean_exit_and_not_an_error(home, monkeypatch, capsys):
    """Somebody pressing control-C has not hit a bug, and turning it into one would fill
    the record with errors nobody caused."""

    def stop(argv):
        raise KeyboardInterrupt

    monkeypatch.setattr(plan, "main", stop)
    assert cli.main(["plan"]) == 130
    assert "nothing was written" in capsys.readouterr().err
    events = [json.loads(line) for line in home.chain_path(None).read_text().splitlines()]
    assert [e["cls"] for e in events] == ["command"]
