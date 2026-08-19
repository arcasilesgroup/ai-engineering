"""The three verbs that write the record, pinned where mutation testing found them blind.

`ai-eng spec`, `ai-eng decide` and `ai-eng exception` are read by a person and by an agent, so
their exit codes and the exact words they print are behaviour, not decoration: a denial
that changes its wording is a denial the agent no longer recognises. Every test below
names one way one of these three could change what it does — a different code, a different
line, a different command run against the forge — while every other test in the suite
stayed green. Nothing here touches the real home or the real repository.
"""

from __future__ import annotations

import builtins
import hashlib
import json
import os
import subprocess
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_engineering import decide, exception, intent, outcome, paths, spec

TODAY = date.today().isoformat()
INTENT_FIXTURE = Path(__file__).parent / "fixtures" / "intent-v1.json"


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


@pytest.fixture
def home(tmp_path, monkeypatch):
    """The chain, the machine id and the caches, all inside tmp_path."""
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(tmp_path / "home"))
    emit = paths.load("_emit")
    monkeypatch.setattr(emit, "repo_root", lambda start=None: None)
    return emit


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway repository root, so no verb can find the one we are working in."""
    root = tmp_path / "repo"
    (root / "specs").mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=root, check=True)
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "role",
        "GIT_AUTHOR_EMAIL": "role@example.invalid",
        "GIT_COMMITTER_NAME": "role",
        "GIT_COMMITTER_EMAIL": "role@example.invalid",
    }
    subprocess.run(
        ["git", "commit", "--quiet", "--allow-empty", "-m", "baseline"],
        cwd=root,
        check=True,
        env=environment,
    )
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    return root


@pytest.fixture
def approved_repo(repo):
    """The command may write only when canonical Intent records accountable approval."""
    target = repo / "specs" / "000-authority" / "spec.md"
    target.parent.mkdir()
    target_bytes = b'---\nid: "000"\nstatus: superseded\n---\n\n# Authority record\n'
    target.write_bytes(target_bytes)

    record = json.loads(INTENT_FIXTURE.read_text(encoding="utf-8"))["base"]["intent"]
    record["relations"] = [
        {
            "kind": "spec",
            "id": "000",
            "path": "specs/000-authority/spec.md",
            "target_digest": f"sha256:{hashlib.sha256(target_bytes).hexdigest()}",
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
    home = repo / ".ai" / "intent.md"
    home.parent.mkdir()
    home.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert intent.validate(home, repo).outcome == "PASS"
    return repo


@pytest.fixture
def wide(monkeypatch):
    """argparse wraps help to the width of the terminal. Pin the width, or the help text
    a test asserts on depends on the window the developer happened to have open."""
    monkeypatch.setenv("COLUMNS", "200")


def _keyboard(monkeypatch, typed):
    """A terminal that exists and a person typing one word at it. Returns the prompts."""
    prompts = []

    def asked(prompt=""):
        prompts.append(prompt)
        return typed

    monkeypatch.setattr(exception.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(builtins, "input", asked)
    return prompts


# ------------------------------------------------------------------ spec: writing


def test_a_spec_written_without_a_work_item_keeps_its_todo_and_an_empty_ref(tmp_path):
    """Nothing prefills the problem, with or without a --ref, so the TODO must survive: it
    is the line that tells the next reader the problem has not been described yet."""
    body = _fixture_spec(tmp_path, "a-thing").read_text()
    assert "TODO: what is true today, and what about it is a problem." in body
    assert 'ref: ""' in body


def test_a_spec_whose_bytes_are_not_utf8_still_appears_in_the_listing(tmp_path):
    """The listing is the index of the record. One file written by another tool in another
    encoding must not take the whole index down — it is read leniently for that reason."""
    folder = tmp_path / "specs" / "001-a"
    folder.mkdir(parents=True)
    (folder / "spec.md").write_bytes(b"---\nstatus: draft\n---\n\n# Caf\xe9 plan\n")
    (row,) = spec.listing(tmp_path, False)
    assert row.split()[0] == "001-a" and " draft " in row and row.endswith("plan")


def test_a_spec_with_no_status_and_no_title_lists_under_its_own_folder_name(tmp_path):
    """A hand-written spec with no header still has to show up, marked unknown rather than
    guessed at. A row that invented a status would report a draft as decided."""
    folder = tmp_path / "specs" / "001-a"
    folder.mkdir(parents=True)
    (folder / "spec.md").write_text("nothing here\n", encoding="utf-8")
    (row,) = spec.listing(tmp_path, False)
    assert row.split() == ["001-a", "?", "001-a"]


# ------------------------------------------------------------------ spec: the command


def test_spec_new_writes_the_spec_and_prints_the_path_a_reader_can_open(approved_repo, capsys):
    """The printed path is how the person finds what was just written. It is relative to
    the repository, and the command has to say it landed with an exact PASS."""
    result = spec.main(["new", "a-thing"])
    assert type(result) is outcome.Execution
    assert result.outcome == "PASS"
    assert capsys.readouterr().out == "  ✓ specs/001-a-thing/spec.md\n"
    body = (approved_repo / "specs" / "001-a-thing" / "spec.md").read_text()
    assert 'ref: ""' in body and "# A thing" in body


def test_spec_new_records_the_work_item_named_on_the_flag_and_prefills_nothing(
    approved_repo, capsys
):
    """--ref is where the work came from, and that is all it is. The item reaches the
    frontmatter; the heading stays the slug and the problem stays the author's to write."""
    result = spec.main(["new", "a-thing", "--ref", "owner/repo#45"])
    assert type(result) is outcome.Execution
    assert result.outcome == "PASS"
    assert capsys.readouterr().out == "  ✓ specs/001-a-thing/spec.md\n"
    body = (approved_repo / "specs" / "001-a-thing" / "spec.md").read_text()
    assert "# A thing" in body and 'ref: "owner/repo#45"' in body
    assert "TODO: what is true today" in body


def test_spec_show_prints_every_directory_that_matches_and_names_each_one(repo, capsys):
    """It printed the first match and said nothing about the rest, which is how somebody
    reads one spec and acts as though it were the only one that matched — the same
    first-match defect that made a peer product reject branches that did reference a live
    card. A single match is printed on its own, with no heading in front of it."""
    _fixture_spec(repo, "thing")
    _fixture_spec(repo, "other-thing")
    result = spec.main(["show", "00"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    out = capsys.readouterr().out
    assert "001-thing" in out and "002-other-thing" in out
    assert out.count("## Production-ready") == 2
    result = spec.main(["show", "001"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert "1 of" not in capsys.readouterr().out


def test_spec_list_prints_one_row_per_spec_and_says_so_when_there_are_none(repo, capsys):
    """An empty listing that printed nothing reads exactly like a broken command. It says
    there are none and names the command that makes one."""
    result = spec.main(["list"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert capsys.readouterr().out == "  no specs yet — `ai-eng spec new <slug>`\n"
    _fixture_spec(repo, "one")
    _fixture_spec(repo, "two")
    result = spec.main(["list"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    rows = capsys.readouterr().out.splitlines()
    assert [row.split()[0] for row in rows] == ["001-one", "002-two"]


def test_spec_list_all_is_the_only_way_a_superseded_spec_shows_up(repo, capsys):
    """A superseded spec records a decision that has been overturned. It stays out of the
    default listing, and --all is the flag that says the reader asked for it anyway."""
    old = _fixture_spec(repo, "old")
    old.write_text(old.read_text().replace("status: draft", "status: superseded"))
    result = spec.main(["list"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert "no specs yet" in capsys.readouterr().out
    result = spec.main(["list", "--all"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert "001-old" in capsys.readouterr().out


def test_spec_outside_a_repository_says_so_and_is_incomplete(tmp_path, monkeypatch, capsys):
    """There is nowhere to put a spec outside a repository. PASS there would claim a
    record was found or written when nothing was."""
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    result = spec.main(["list"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert capsys.readouterr().out == "not inside a repository\n"


def test_spec_without_an_action_refuses_instead_of_guessing_one(repo):
    """`ai-eng spec` on its own must stop. Falling through to a default action writes or
    prints something the person did not ask for."""
    with pytest.raises(SystemExit):
        spec.main([])


def test_spec_help_names_the_command_and_documents_every_flag(wide, capsys):
    """Help is the only place anybody looks for a flag. A flag missing its line, or a
    usage line naming the wrong command, is a feature that does not exist."""
    for argv, tokens, described in (
        (["--help"], ["usage: ai-eng spec", "new", "show", "list"], []),
        (
            ["new", "--help"],
            ["usage: ai-eng spec new", "slug", "--ref REF"],
            ['a work item, e.g. "owner/repo#45"'],
        ),
        (["list", "--help"], ["usage: ai-eng spec list", "--all"], ["include superseded specs"]),
    ):
        with pytest.raises(SystemExit) as stopped:
            spec.main(argv)
        assert stopped.value.code == 0
        out = capsys.readouterr().out
        for token in tokens:
            assert token in out
        for line in described:
            assert f" {line}\n" in out, "the help line is padded and ends there, not elsewhere"


# ------------------------------------------------------------------ decide: on disk


def test_the_record_has_exactly_one_home_and_the_newest_spec_is_the_last_number(tmp_path):
    """docs/adr and specs/ are the two homes this project promises. A verb that wrote one
    character of either path differently would scatter the record across two trees, and
    recording a decision against the wrong spec files it under a problem it did not solve."""
    assert decide.adr_dir(tmp_path) == tmp_path / "docs" / "adr"
    with pytest.raises(LookupError, match="no spec to record this against"):
        spec.target(tmp_path)
    only = _fixture_spec(tmp_path, "old")
    assert spec.target(tmp_path) == only
    _fixture_spec(tmp_path, "new")
    # Two open specs and nothing named: it refuses instead of taking the last one, which is
    # how two decisions written for spec 003 landed in another session's spec.
    with pytest.raises(LookupError, match="2 specs are open"):
        spec.target(tmp_path)
    assert spec.target(tmp_path, "002").parent.name == "002-new"


@pytest.mark.parametrize(
    ("title", "stem"),
    [("Use one queue!", "0001-use-one-queue"), ("A" * 70, "0001-" + "a" * 60)],
)
def test_an_adr_filename_is_a_clean_slug_capped_at_sixty_characters(tmp_path, title, stem):
    """The filename is what everybody greps. Punctuation left as a trailing dash, or a
    title allowed to run on, gives a name nobody can type or predict."""
    specification = _fixture_spec(tmp_path, "decision-home")
    assert decide.promote(tmp_path, title, "", specification).stem == stem


def test_a_decision_lands_between_the_headings_and_leaves_the_spec_intact(tmp_path):
    """The block goes under `## Decisions`, above the risks, and everything already in the
    file survives. A decision written to the end of the file, or one that ate the
    frontmatter, is a record that no longer parses."""
    path = _fixture_spec(tmp_path, "a-thing")
    decide.append(path, {"decision": "One queue", "date": TODAY})
    body = path.read_text()
    assert body.startswith("---\nid: ")
    assert body.endswith("\n")
    assert "## Decisions" in body.splitlines()
    assert body.index("## Decisions") < body.index("decision: One queue")
    assert body.index("decision: One queue") < body.index("## Accepted risks")
    assert body.count("## Accepted risks") == 1


def test_a_spec_with_no_decisions_heading_keeps_everything_it_already_held(tmp_path):
    """Specs written before this heading existed get one added. Adding it must not cost
    the spec its contents: overwriting the file here would delete the problem statement
    somebody wrote, in the same command that claims to be recording a decision."""
    path = tmp_path / "spec.md"
    path.write_text("# a\n\n## Context\n\nthe problem, as filed.\n", encoding="utf-8")
    decide.append(path, {"decision": "One queue"})
    body = path.read_text()
    assert body.startswith("# a\n")
    assert "the problem, as filed." in body
    assert "## Decisions" in body.splitlines() and "decision: One queue" in body


def test_a_spec_that_names_the_decisions_heading_twice_takes_it_under_the_first(tmp_path):
    """Somebody quoting the heading further down the file must not cost a decision. It
    goes under the first one, deterministically, and nothing raises."""
    path = tmp_path / "spec.md"
    path.write_text("# a\n\n## Decisions\n\nfirst\n\n## Decisions\n\nsecond\n", encoding="utf-8")
    decide.append(path, {"decision": "One queue"})
    body = path.read_text()
    assert body.count("## Decisions") == 2
    assert body.index("decision: One queue") < body.index("first")


def test_an_adr_listing_shows_the_status_of_every_file_including_the_broken_ones(tmp_path):
    """The listing is where somebody checks whether a decision is still live. A file with
    no status is marked unknown, and one written in another encoding does not take the
    listing down with it."""
    folder = tmp_path / "docs" / "adr"
    folder.mkdir(parents=True)
    (folder / "0001-a.md").write_text("---\nstatus: accepted\ndate: x\n---\n\n# 0001. A\n")
    (folder / "0002-b.md").write_text("# 0002. B, with no header at all\n")
    (folder / "0003-c.md").write_bytes(b"---\nstatus: proposed\n---\n\n# 0003. Caf\xe9\n")
    assert decide.listing(tmp_path) == [
        f"  {'0001-a':<44} accepted",
        f"  {'0002-b':<44} ?",
        f"  {'0003-c':<44} proposed",
    ]


# ------------------------------------------------------------------ decide: the command


def test_decide_madr_writes_the_file_and_says_it_grants_no_authority(repo, capsys):
    """A promoted decision is proposed, not accepted: the second line is what stops a
    reader treating a freshly written MADR as something the team agreed to."""
    _fixture_spec(repo, "queue")
    result = decide.main(["Use one queue", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert capsys.readouterr().out.splitlines() == [
        "  ✓ docs/adr/0001-use-one-queue.md",
        "    outcome: PASS. status: proposed; this record grants no authority.",
    ]
    body = (repo / "docs" / "adr" / "0001-use-one-queue.md").read_text()
    assert "# 0001. Use one queue" in body
    assert 'status: "proposed"' in body and 'spec: "001"' in body
    assert 'supersedes: ""' in body and "authority_role:" not in body


def test_proposing_a_supersession_does_not_rewrite_or_authorize_the_old_madr(repo):
    """A proposal may point at the old MADR, but only human authority can transition it."""
    _fixture_spec(repo, "queue")
    result = decide.main(["Use one queue", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    old = repo / "docs" / "adr" / "0001-use-one-queue.md"
    before = old.read_bytes()
    result = decide.main(["Use two queues", "--madr", "--supersede", "0001"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert old.read_bytes() == before
    replacement = (repo / "docs" / "adr" / "0002-use-two-queues.md").read_text()
    assert 'status: "proposed"' in replacement and 'supersedes: "0001"' in replacement


def test_a_madr_proposal_writes_nothing_outside_its_canonical_home(repo):
    """Proposal must not turn a spec edit into authority or create a second record."""
    path = _fixture_spec(repo, "a-thing")
    before = path.read_bytes()
    result = decide.main(["Use one queue", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert path.read_bytes() == before


def test_decide_list_prints_one_row_per_adr_and_says_so_when_there_are_none(repo, capsys):
    """No ADRs is the normal state, not an error, and the line says so — otherwise the
    silence reads as a broken command and somebody promotes a decision that needs no ADR."""
    result = decide.main(["--list"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert capsys.readouterr().out == "  no MADRs yet — most decisions never need one\n"
    _fixture_spec(repo, "decisions")
    result = decide.main(["One", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    result = decide.main(["Two", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    capsys.readouterr()
    result = decide.main(["--list"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    rows = capsys.readouterr().out.splitlines()
    assert [row.split()[0] for row in rows] == ["0001-one", "0002-two"]


def test_a_decision_that_stays_in_its_spec_is_dated_and_carries_a_rationale(repo, capsys):
    """A decision with no date cannot be put in order against the others, and one with no
    rationale is a note. When nobody typed --why the placeholder says so in the diff."""
    _fixture_spec(repo, "a-thing")
    result = decide.main(["Use one queue"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert capsys.readouterr().out == (
        "  ✓ recorded in specs/001-a-thing/spec.md. If it constrains specs that do not exist "
        "yet, promote it with --madr.\n"
    )
    body = (repo / "specs" / "001-a-thing" / "spec.md").read_text()
    assert (
        "```yaml\n"
        "decision: Use one queue\n"
        f"date: {TODAY}\n"
        "rationale: TODO: why, in one sentence\n"
        "```\n"
    ) in body
    result = decide.main(["Use two queues", "--why", "it is cheaper"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert "rationale: it is cheaper" in (repo / "specs" / "001-a-thing" / "spec.md").read_text()


def test_decide_refuses_with_the_line_that_names_the_fix(repo, tmp_path, monkeypatch, capsys):
    """Each refusal has to say what to do next, and each one has its own exit code: 2 for
    a command used wrongly, 1 for a repository that is not ready yet."""
    result = decide.main(["Use one queue"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert capsys.readouterr().out == (
        "  no spec to record this against. `ai-eng spec new <slug>` first\n"
    )
    with pytest.raises(SystemExit) as stopped:
        decide.main([])
    assert stopped.value.code == outcome.invalid_cli_exit()
    assert "a decision needs a title" in capsys.readouterr().err
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)
    result = decide.main(["Use one queue"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert capsys.readouterr().out == "not inside a repository\n"


def test_decide_help_names_the_command_and_documents_every_flag(wide, capsys):
    """The flags are the whole surface of this verb. One missing help line and the person
    reaches for the source, which is the moment the tool stopped being usable."""
    with pytest.raises(SystemExit) as stopped:
        decide.main(["--help"])
    assert stopped.value.code == 0
    out = capsys.readouterr().out
    for token in ("usage: ai-eng decide", "--madr", "--supersede NNNN", "--list", "--why WHY"):
        assert token in out
    assert "--adr" not in out
    for line in ("propose it in docs/adr/", "the rationale, when it stays inside the spec"):
        assert f" {line}\n" in out, "the help line is padded and ends there, not elsewhere"


# ------------------------------------------------------------------ exception: the bypass


def test_with_no_keyboard_nothing_is_granted_and_the_line_says_why(home, monkeypatch, capsys):
    """The one that stops an agent approving its own exception: no terminal, no grant, and
    the reason is printed rather than left for somebody to work out from an exit code."""
    monkeypatch.setattr(exception.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    result = exception.main(["--skip", "in a hurry"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert capsys.readouterr().out == (
        "  a bypass is a person's decision, and there is no keyboard here. Nothing granted.\n"
    )
    assert not (paths.home() / "cache" / "bypass.json").exists()


def test_the_prompt_says_what_is_granted_for_how_long_and_against_whose_name(
    home, monkeypatch, capsys
):
    """Consent is only consent if the person was told what they were consenting to: which
    guard, for how long, for what reason. Anything short of the word yes grants nothing,
    and the refusal is printed so it is not mistaken for a hang."""
    prompts = _keyboard(monkeypatch, "no")
    result = exception.main(["--skip", "in a hurry"])
    assert type(result) is outcome.Result
    assert result.outcome == "CANCELLED"
    assert prompts == ["  Type yes to grant it › "]
    assert capsys.readouterr().out.splitlines() == [
        "  This grants ONE bypass of loop_guard, for 15 minutes, recorded against your name.",
        "  Reason: in a hurry",
        "  nothing granted.",
    ]
    assert not (paths.home() / "cache" / "bypass.json").exists()


def test_a_granted_bypass_is_one_file_one_event_and_says_who_took_it(home, monkeypatch, capsys):
    """The grant is a single file at the path the guard reads, and the event carries the
    reason and the fact that a person took it — that is what makes a bypass visible to
    somebody other than whoever took it. Taking a second one must not fail on the folder
    the first one created."""
    _keyboard(monkeypatch, "yes")
    result = exception.main(["--skip", "in a hurry", "--guard", "loop_guard"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert capsys.readouterr().out.splitlines()[-1] == (
        "  ✓ granted. The next loop_guard block passes, once, and the record says why."
    )
    names = sorted(path.name for path in paths.home().iterdir())
    assert "cache" in names and "CACHE" not in names
    assert [path.name for path in (paths.home() / "cache").iterdir()] == ["bypass.json"]
    grant = json.loads((paths.home() / "cache" / "bypass.json").read_text())
    assert grant["guard"] == "loop_guard" and grant["reason"] == "in a hurry"
    event = json.loads(home.chain_path(None).read_text().splitlines()[-1])
    assert event["name"] == "loop_guard" and event["cls"] == "bypassed"
    assert event["data"] == {"reason": "in a hurry", "granted": "by a person"}
    repeated = exception.main(["--skip", "once more", "--guard", "loop_guard"])
    assert type(repeated) is outcome.Result
    assert repeated.outcome == "PASS"


def test_a_bypass_without_a_reason_is_not_a_bypass(home, monkeypatch):
    """--skip is required because the reason is the record. A grant with no reason is a
    control waived and nothing written down about why."""
    monkeypatch.setattr(exception.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    with pytest.raises(SystemExit) as invalid:
        exception.main([])
    assert invalid.value.code == outcome.invalid_cli_exit()


def test_exception_help_names_the_command_and_documents_the_bypass_flags(wide, capsys):
    """This is the verb a person reaches for while blocked. If its help does not say what
    --skip takes, or which guards can be named, the next move is to disable the guard."""
    with pytest.raises(SystemExit) as stopped:
        exception.main(["--help"])
    assert stopped.value.code == 0
    out = capsys.readouterr().out
    for token in (
        "usage: ai-eng exception",
        "--skip REASON",
        "--guard {loop_guard}",
    ):
        assert token in out
    assert " why this change does not need a plan\n" in out


def test_a_spec_written_with_answers_and_one_written_without_have_the_same_shape(
    approved_repo, capsys, monkeypatch
):
    """EP-010. The record a person was asked questions for and the record nobody was asked
    about have to be the same kind of thing, or an answer changes what the document *is*
    rather than what it says — and a reader cannot tell which they are holding.

    Nothing had ever compared the two: a search for a with-answers and without-answers pair
    across the whole suite found one hit, a specification recording its own absence. It is
    proven the only way it can be, by writing both and diffing the shape.

    `spec new` asks nothing today — no prompt, no interactive branch — so the property holds
    by construction, and that is exactly why it is worth pinning rather than assuming. The
    day somebody adds a question is the day the two could diverge, and this is what notices.

    Built on this file's fixture rather than a new one. Three attempts at standing up a
    governed repository from scratch were refused by the transaction, and the difference
    turned out to be here all along: the Intent has to be `active` and to name a spec that
    exists, which `approved_repo` does and a bare record does not.
    """

    from ai_engineering import accept

    shapes = []
    for asked, slug in ((True, "asked-thing"), (False, "silent-thing")):
        monkeypatch.setattr(accept, "NON_INTERACTIVE", not asked)
        result = spec.main(["new", slug])
        assert result.outcome == "PASS", capsys.readouterr().out
        capsys.readouterr()
        written = next((approved_repo / "specs").glob(f"*-{slug}")) / "spec.md"
        body = written.read_text(encoding="utf-8")
        front = [line.split(":", 1)[0] for line in body.split("---", 2)[1].splitlines() if line]
        shapes.append(front + [line for line in body.splitlines() if line.startswith("## ")])

    assert shapes[0] == shapes[1]
    # And the shape is the template's, so a section added to one path and not the other
    # cannot pass by both records happening to be equally wrong.
    template = spec.TEMPLATE
    expected = [
        line.split(":", 1)[0] for line in template.split("---", 2)[1].splitlines() if line
    ] + [line for line in template.splitlines() if line.startswith("## ")]
    assert shapes[0] == expected


def test_the_refusal_names_which_two_values_disagree():
    """One message covered four different situations and named none of them.

    Measured on this repository: `ai-eng spec new` refused with "the Solution Intent is not
    actively approved by an accountable role" while the Intent was active and approved. The
    real cause was that `authority_role` read `repository owner` and `accountable_role` read
    `repository maintainer` — two names for one person, and the check compares strings. The
    refusal was correct and unreadable, which cost an afternoon here and would cost a
    stranger more. A control that is right and illegible gets worked around instead of fixed.
    """
    from ai_engineering import spec

    transition = {"authority_role": "owner", "approval_ref": "abc"}
    approval = {"approval_ref": "abc"}

    asleep = spec._why_not_authority("draft", "owner", "owner", transition, approval)
    assert "'draft'" in asleep and "active" in asleep

    mismatched = spec._why_not_authority(
        "active", "repository owner", "maintainer", transition, approval
    )
    assert "'repository owner'" in mismatched and "'maintainer'" in mismatched
    assert "the same words" in mismatched

    drifted = spec._why_not_authority(
        "active",
        "owner",
        "owner",
        {"authority_role": "somebody else", "approval_ref": "abc"},
        approval,
    )
    assert "'somebody else'" in drifted and "'owner'" in drifted

    # The fifth, and it is here because it was missing: the guard tests five conditions and
    # this helper had four branches, so an Intent differing only in `approval_ref` fell all
    # the way through and was told its role was one the framework refuses — about the role
    # it accepts. Found by an independent reviewer building that Intent and running the verb.
    moved = spec._why_not_authority(
        "active", "owner", "owner", {"authority_role": "owner", "approval_ref": "def"}, approval
    )
    assert "'def'" in moved and "'abc'" in moved
    assert "refuses to read" not in moved, "the fall-through answered for a named condition"

    refused = spec._why_not_authority("active", "agent", "agent", {"authority_role": "agent"}, {})
    assert "'agent'" in refused and "refuses to read" in refused

    # And the count, so a sixth condition cannot be added to the guard without a branch
    # here. The guard is one boolean expression; every `or` in it is a condition.
    import inspect

    guard = inspect.getsource(spec._authority)
    condition = guard[guard.index("if (") : guard.index("):", guard.index("if ("))]
    assert condition.count(" or ") + 1 == 5, "the guard grew a condition; give it a reason"

    # And every branch says something. A diagnostic that falls through to an empty string is
    # the original defect with an extra function in front of it.
    for said in (asleep, mismatched, drifted, refused):
        assert len(said.split()) >= 8, said


def _help(monkeypatch, capsys, *argv: str) -> list[str]:
    """One subcommand's whole help block, at a fixed width so it is comparable."""
    import pytest as _pytest

    from ai_engineering import spec

    monkeypatch.setenv("COLUMNS", "90")
    with _pytest.raises(SystemExit):
        spec.main([*argv, "--help"])
    return capsys.readouterr().out.rstrip("\n").splitlines()


def test_the_verb_declares_exactly_these_subcommands(monkeypatch, capsys):
    """One hundred and thirty-four mutants of `spec.main` survived, and hardly any were logic.

    They were the parser: a help sentence rewritten, a default changed, a flag's name altered,
    `required` flipped. Forty-two in-process calls to this function could not tell any of it
    apart, because every one of them passed valid arguments and read the outcome — nothing
    looked at what the verb says it accepts.

    The help block is what a stranger reads before choosing a flag, so it is pinned whole. A
    reworded option is then a diff beside the words, which is the only way this stays true.
    """
    lines = _help(monkeypatch, capsys)

    assert lines[0] == "usage: ai-eng spec [-h] {new,show,list,claim,wave,checkpoint} ..."
    assert "positional arguments:" in lines
    assert "  {new,show,list,claim,wave,checkpoint}" in lines


def test_the_claim_subcommand_says_exactly_what_it_needs(monkeypatch, capsys):
    """`claim` is the only subcommand that reaches a remote, and every one of its four
    arguments changes what gets written there. A default this test did not pin is a default
    somebody can move without a diff anybody reads."""
    assert _help(monkeypatch, capsys, "claim") == [
        "usage: ai-eng spec claim [-h] --base BASE --path PATH --role ROLE [--remote REMOTE] item",
        "",
        "positional arguments:",
        "  item",
        "",
        "options:",
        "  -h, --help       show this help message and exit",
        "  --base BASE      the exact SHA this claim is taken against",
        "  --path PATH",
        "  --role ROLE",
        "  --remote REMOTE",
    ]


def test_the_checkpoint_subcommand_says_exactly_what_it_needs(monkeypatch, capsys):
    """Both of its flags are about which snapshot the receipts are computed against, and both
    default to empty — meaning "this branch, and the claim beside it" rather than a remote's."""
    assert _help(monkeypatch, capsys, "checkpoint") == [
        "usage: ai-eng spec checkpoint [-h] [--base BASE] [--item ITEM] [--remote REMOTE]",
        "",
        "options:",
        "  -h, --help       show this help message and exit",
        "  --base BASE      verify this branch against that SHA or ref",
        "  --item ITEM      read the claim from the remote, not here",
        "  --remote REMOTE",
    ]


def test_the_new_and_list_subcommands_say_exactly_what_they_need(monkeypatch, capsys):
    """`new` takes a slug and an optional work item, and the example in its help is the whole
    documentation of what a work item looks like. `list` has one flag and it is the one that
    decides whether superseded specifications are shown."""
    assert _help(monkeypatch, capsys, "new") == [
        "usage: ai-eng spec new [-h] [--ref REF] slug",
        "",
        "positional arguments:",
        "  slug",
        "",
        "options:",
        "  -h, --help  show this help message and exit",
        '  --ref REF   a work item, e.g. "owner/repo#45"',
    ]
    assert _help(monkeypatch, capsys, "list") == [
        "usage: ai-eng spec list [-h] [--all]",
        "",
        "options:",
        "  -h, --help  show this help message and exit",
        "  --all       include superseded specs",
    ]


def test_a_subcommand_missing_a_required_argument_refuses_rather_than_defaulting(
    monkeypatch, capsys
):
    """`required=True` on four of claim's arguments, and nothing had ever removed one to see.

    A claim written with a base, a path or a role missing is a claim the other machine cannot
    act on, so the parser refusing is the whole of the protection. Each is checked on its own,
    because a test that omitted all four would pass with three of the four flags optional.
    """
    import pytest as _pytest

    from ai_engineering import spec

    monkeypatch.setenv("COLUMNS", "90")
    whole = ["claim", "work-1", "--base", "abc", "--path", "src/a.py", "--role", "one"]
    for flag in ("--base", "--path", "--role"):
        where = whole.index(flag)
        without = whole[:where] + whole[where + 2 :]
        with _pytest.raises(SystemExit) as refused:
            spec.main(without)
        assert refused.value.code == 2, flag
        assert flag in capsys.readouterr().err, flag

    # And the positional, which argparse names differently in its complaint.
    with _pytest.raises(SystemExit) as refused:
        spec.main([one for one in whole if one != "work-1"])
    assert refused.value.code == 2
    assert "item" in capsys.readouterr().err


def test_every_way_a_publication_can_fail_says_its_own_code_and_its_own_sentence():
    """Four transaction failures, four codes, four sentences, and nothing had told them apart.

    Thirty-one mutants of `_incomplete_report` and twenty of `_transaction_incomplete` survived
    by rewriting these into each other. They are the only thing a person sees when `spec new`
    refuses, and the difference between them is what they do next: a lock somebody else holds
    is waited on, a filesystem that cannot prove safety is not retryable at all, and a
    collision means the destination stopped being theirs.

    `retryable` is pinned with them, because a refusal that says retry to a filesystem which
    will never support this is a loop rather than an answer.
    """
    from ai_engineering import spec, spec_transaction

    expected = {
        "busy": (
            "SPEC_TRANSACTION_BUSY",
            "another spec transaction holds the canonical Intent lock",
            True,
        ),
        "unsupported": (
            "SPEC_TRANSACTION_UNSUPPORTED",
            "this filesystem cannot prove a safe spec publication",
            False,
        ),
        "collision": (
            "SPEC_PUBLICATION_COLLISION",
            "the reserved spec destination is no longer exclusive",
            True,
        ),
        "unsafe": (
            "SPEC_TRANSACTION_UNSAFE",
            "the spec transaction could not prove an unchanged safe filesystem state",
            True,
        ),
    }
    problems = {
        "busy": spec_transaction.Busy(),
        "unsupported": spec_transaction.Unsupported(),
        "collision": spec_transaction.Collision(),
        "unsafe": spec_transaction.Unsafe(),
    }

    seen = set()
    for kind, problem in problems.items():
        assert spec._transaction_kind(problem) == kind
        report = spec._transaction_incomplete(problem)
        error = report.execution.error
        code, message, retryable = expected[kind]
        assert error.code == code, kind
        assert error.message == message, kind
        assert error.retryable is retryable, kind
        assert report.execution.result.outcome == "INCOMPLETE"
        assert report.lines[0] == f"  INCOMPLETE  {message}"
        seen.add(code)

    assert len(seen) == 4, "two failures share a code, so a reader cannot tell them apart"


def test_a_pending_spec_is_named_and_the_two_kinds_of_pending_are_never_merged():
    """A proven pending path and a possible one are different facts and different instructions.

    Proven means this attempt wrote it, so it can be inspected and removed. Possible means a
    stage failed before anybody could tell whose it is — so the instruction says inspect
    without assuming ownership, and removing it on that basis would be deleting somebody
    else's work. Merging the two is the mistake, and asking for both at once is refused.
    """
    from ai_engineering import spec, spec_transaction

    proven = spec._transaction_incomplete(spec_transaction.Busy(), proven_pending="019-a-thing")
    assert "    pending: specs/019-a-thing/spec.md" in proven.lines
    proven_error = proven.execution
    assert "Inspect or remove specs/019-a-thing/spec.md before retrying" in proven_error.remaining
    assert list(proven_error.next_actions) == [
        "inspect specs/019-a-thing/spec.md; remove it only after proving it is this attempt"
    ]
    assert any(fact.id == "spec-pending" for fact in proven_error.changes)

    possible = spec._transaction_incomplete(spec_transaction.Busy(), possible_pending="020-other")
    assert (
        "    possible pending: specs/020-other/spec.md; inspect only if it exists" in possible.lines
    )
    possible_error = possible.execution
    assert list(possible_error.next_actions) == [
        "if specs/020-other/spec.md exists, inspect it without assuming ownership"
    ]
    assert possible_error.changes == (), "a possible pending path was reported as a change"
    assert any(fact.id == "spec-pending-possible" for fact in possible_error.checks)

    import pytest as _pytest

    with _pytest.raises(ValueError, match="cannot be both proven and possible"):
        spec._incomplete_report("X", "y", proven_pending="a", possible_pending="b")


def test_a_refusal_with_no_pending_path_still_says_nothing_was_published():
    """The plain case, and the line that matters in it. Whatever went wrong, the remaining work
    says no canonical spec was published — because a refusal that listed only the mechanical
    fault would leave a reader wondering whether half of one had landed."""
    from ai_engineering import spec

    report = spec._incomplete_report("SPEC_X", "something went wrong")
    payload = report.execution

    assert payload.remaining == ("No canonical spec was published",)
    assert list(payload.next_actions) == [
        "restore one stable approved Intent snapshot and run spec new again"
    ]
    assert payload.changes == ()
    assert [fact.id for fact in payload.checks] == ["spec-publication"]
    assert report.lines == ("  INCOMPLETE  something went wrong",)


# ---------------------------------------------------------------- what the verb says

# Ninety-one mutants of `spec.main` survived the pass that measured this module, and the
# cause is the one the justfile already records for the guards: the survivors are sentences a
# person reads, and every fixture asserted the outcome word instead of the words. A parser
# whose flags are renamed, whose help sentences are rewritten and whose defaults are moved is
# invisible to a test that passes valid arguments and reads the verdict.


def test_the_verb_and_its_five_subcommands_say_exactly_what_they_accept(monkeypatch, capsys):
    """Every help block, whole, at a fixed width.

    Fixed at `COLUMNS=90` so the wrapping is the same on every machine — otherwise this
    passes here and fails on a narrower terminal for a reason that has nothing to do with the
    parser. The blocks are compared line for line rather than searched, because a flag that
    keeps its name and loses its sentence is a flag nobody can use and `in` cannot see it.
    """
    from ai_engineering import spec

    monkeypatch.setenv("COLUMNS", "90")

    def block(*argv: str) -> list[str]:
        with pytest.raises(SystemExit):
            spec.main([*argv, "--help"])
        return capsys.readouterr().out.rstrip("\n").splitlines()

    assert block() == [
        "usage: ai-eng spec [-h] {new,show,list,claim,wave,checkpoint} ...",
        "",
        "positional arguments:",
        "  {new,show,list,claim,wave,checkpoint}",
        "",
        "options:",
        "  -h, --help            show this help message and exit",
    ]

    assert block("new") == [
        "usage: ai-eng spec new [-h] [--ref REF] slug",
        "",
        "positional arguments:",
        "  slug",
        "",
        "options:",
        "  -h, --help  show this help message and exit",
        '  --ref REF   a work item, e.g. "owner/repo#45"',
    ]

    assert block("list") == [
        "usage: ai-eng spec list [-h] [--all]",
        "",
        "options:",
        "  -h, --help  show this help message and exit",
        "  --all       include superseded specs",
    ]

    # `claim` is the one whose flags are all required and whose `--base` sentence is the
    # whole of what makes a claim a claim: an exact SHA rather than a branch that moves.
    assert block("claim") == [
        "usage: ai-eng spec claim [-h] --base BASE --path PATH --role ROLE [--remote REMOTE] item",
        "",
        "positional arguments:",
        "  item",
        "",
        "options:",
        "  -h, --help       show this help message and exit",
        "  --base BASE      the exact SHA this claim is taken against",
        "  --path PATH",
        "  --role ROLE",
        "  --remote REMOTE",
    ]

    assert block("checkpoint")[:6] == [
        "usage: ai-eng spec checkpoint [-h] [--base BASE] [--item ITEM] [--remote REMOTE]",
        "",
        "options:",
        "  -h, --help       show this help message and exit",
        "  --base BASE      verify this branch against that SHA or ref",
        "  --item ITEM      read the claim from the remote, not here",
    ]


def test_an_unknown_subcommand_exits_the_way_cli_misuse_exits(monkeypatch, capsys):
    """Two exits, and they are not the same thing. A parser refusing an argument is misuse
    and exits 2 by the canonical rule; a verb refusing to act is an outcome. Conflating them
    would let a typo report as a governed refusal."""
    from ai_engineering import outcome, spec

    monkeypatch.setenv("COLUMNS", "90")
    with pytest.raises(SystemExit) as bad:
        spec.main(["nonesuch"])
    assert bad.value.code == outcome.invalid_cli_exit()
    assert "invalid choice" in capsys.readouterr().err

    # And a required flag left out of `claim` is the same class, not a claim that failed.
    with pytest.raises(SystemExit) as missing:
        spec.main(["claim", "item", "--path", "x", "--role", "y"])
    assert missing.value.code == outcome.invalid_cli_exit()
    assert "--base" in capsys.readouterr().err


def test_every_line_this_verb_prints_when_it_cannot_act(tmp_path, monkeypatch, capsys):
    """The body of `main`, which is where its surviving mutants actually live.

    Pinning the help blocks killed almost nothing, and that is worth writing down rather than
    repeating: the help was already reachable through other cases. What nothing reached is
    the five sentences this verb prints when it decides not to do the thing, and each of them
    is the entire output of a run somebody is standing in front of.

    A verdict word tells that person nothing. `INCOMPLETE` over "not inside a repository" and
    `INCOMPLETE` over "specs could not be read safely" are the same word for a mistake and a
    fault, and only the sentence separates them.
    """
    from ai_engineering import spec

    def said() -> list[str]:
        return [one for one in capsys.readouterr().out.splitlines() if one.strip()]

    monkeypatch.setattr(spec.paths, "repo_root", lambda: None)
    assert spec.main(["list"]).outcome == "INCOMPLETE"
    assert said() == ["not inside a repository"]

    # And it is the first thing checked, before any subcommand: every one of the five gets
    # the same sentence rather than its own way of failing.
    for argv in (["show", "1"], ["new", "a-slug"], ["checkpoint"]):
        assert spec.main(argv).outcome == "INCOMPLETE"
        assert said() == ["not inside a repository"], argv

    monkeypatch.setattr(spec.paths, "repo_root", lambda: tmp_path)

    # An empty repository listing is not a failure. It is a state with a next step in it, and
    # the next step is the whole of what makes it useful.
    monkeypatch.setattr(spec, "listing", lambda root, everything: [])
    assert spec.main(["list"]).outcome == "PASS"
    assert said() == ["  no specs yet — `ai-eng spec new <slug>`"]

    # A listing that raises is a different answer, and it carries the reason rather than
    # swallowing it: a directory nobody can read and an empty one are not the same repository.
    def unreadable(root, everything):
        raise OSError("permission denied")

    monkeypatch.setattr(spec, "listing", unreadable)
    assert spec.main(["list"]).outcome == "INCOMPLETE"
    assert said() == ["  INCOMPLETE  specs could not be listed: permission denied"]

    # `--all` reaches the listing rather than being accepted and dropped, which is the shape
    # a flag takes when it stops working and nobody notices.
    seen = []
    monkeypatch.setattr(spec, "listing", lambda root, everything: seen.append(everything) or [])
    spec.main(["list"])
    spec.main(["list", "--all"])
    assert seen == [False, True]


def test_show_finds_a_spec_by_prefix_and_says_so_when_it_cannot(tmp_path, monkeypatch, capsys):
    """`show` matches on the start of a directory name, so `show 7` finds `007-something`.

    Both halves are asserted because the prefix rule is the useful behaviour and the refusal
    is what a person sees when they mistype. The refusal quotes what they asked for — without
    it the message is about no spec in particular.
    """
    from ai_engineering import spec

    monkeypatch.setattr(spec.paths, "repo_root", lambda: tmp_path)
    found = tmp_path / "specs" / "007-a-real-one"
    found.mkdir(parents=True)
    (found / "spec.md").write_text("---\nstatus: draft\n---\n\n# 007\n", encoding="utf-8")
    monkeypatch.setattr(spec, "_canonical_specs", lambda root: [found / "spec.md"])

    assert spec.main(["show", "007"]).outcome in ("PASS", "INCOMPLETE")
    capsys.readouterr()

    assert spec.main(["show", "999"]).outcome == "INCOMPLETE"
    assert [one for one in capsys.readouterr().out.splitlines() if one.strip()] == [
        "  no spec matches '999'"
    ]

    def unreadable(root):
        raise OSError("gone")

    monkeypatch.setattr(spec, "_canonical_specs", unreadable)
    assert spec.main(["show", "007"]).outcome == "INCOMPLETE"
    assert [one for one in capsys.readouterr().out.splitlines() if one.strip()] == [
        "  INCOMPLETE  specs could not be read safely"
    ]


def test_the_two_subcommands_that_reach_a_remote_default_to_origin(tmp_path, monkeypatch):
    """`--remote` has a default, and a default is a decision nobody types.

    Both `claim` and `checkpoint` talk to another machine, so the name they use when nobody
    said one is the difference between a claim two agents can both read and one written where
    the other will never look.
    """
    from ai_engineering import spec

    monkeypatch.setattr(spec.paths, "repo_root", lambda: tmp_path)
    seen: dict[str, object] = {}

    import ai_engineering.checkpoint as checkpoint_module
    import ai_engineering.claim as claim_module

    monkeypatch.setattr(
        claim_module,
        "take",
        lambda root, item, base, paths_, role, remote: seen.update(claim=remote) or "taken",
    )
    monkeypatch.setattr(
        checkpoint_module,
        "verify",
        lambda root, *, base, item, remote: seen.update(checkpoint=remote) or "verified",
    )

    spec.main(["claim", "owner/repo#1", "--base", "a" * 40, "--path", "src", "--role", "writer"])
    spec.main(["checkpoint"])
    assert seen == {"claim": "origin", "checkpoint": "origin"}

    spec.main(["checkpoint", "--remote", "upstream"])
    assert seen["checkpoint"] == "upstream"


def test_the_whole_envelope_a_created_spec_returns(approved_repo, capsys):
    """Forty-five mutants of `_new` survived, and they are the envelope rather than the write.

    The file lands and its bytes are checked elsewhere. What nothing looked at is what the
    verb *says* about the write: the summary, the one change, the three checks it claims, the
    next action and the line it prints. Those are what a person and a machine both read to
    decide whether a governed record exists, and each of the three checks is a distinct
    claim — that the Intent is approved, that its authority did not move under the write, and
    that publication used no-replace semantics. A check whose title drifted onto another
    check's meaning would be an envelope that vouches for the wrong thing.
    """
    from ai_engineering import spec

    result = spec.main(["new", "a-real-slug"])
    printed = [one for one in capsys.readouterr().out.splitlines() if one.strip()]

    assert result.result.outcome == "PASS"
    assert result.summary == "Created governed spec 001-a-real-slug"
    assert printed == ["  ✓ specs/001-a-real-slug/spec.md"]

    assert [(one.id, one.status, one.summary, one.detail) for one in result.changes] == [
        ("spec-created", "APPLIED", "Created governed spec", "specs/001-a-real-slug/spec.md")
    ]
    assert [(one.id, one.status, one.summary) for one in result.checks] == [
        (
            "intent-authority",
            "PASS",
            "Solution Intent is actively approved by its accountable role",
        ),
        ("authority-snapshot", "PASS", "Authority files and parent generations remained unchanged"),
        ("spec-publication", "PASS", "Published the spec with native no-replace semantics"),
    ]
    assert result.checks[2].detail == "specs/001-a-real-slug/spec.md"
    assert list(result.remaining) == []
    assert list(result.next_actions) == ["edit and review specs/001-a-real-slug/spec.md"]

    # And the file is really there, or the envelope above is a description of nothing.
    assert (approved_repo / "specs" / "001-a-real-slug" / "spec.md").is_file()


def test_a_repository_with_no_intent_refuses_and_says_which_file_to_write(repo, capsys):
    """The first refusal in the verb, and the one an ordinary repository meets on day one.

    It used to say "filesystem resolved a missing or differently spelled entry" — true about
    a path and useless about a decision, in the command `init` closes by recommending. So
    what is pinned is the code, that it is not retryable, and that the sentence names the
    file to write and the skill that walks somebody through it.
    """
    from ai_engineering import spec

    result = spec.main(["new", "a-slug"])

    assert result.result.outcome == "INCOMPLETE"
    assert [one.id for one in result.changes] == []
    assert list(result.remaining) == ["No canonical spec was published"]
    assert list(result.next_actions) == [
        "restore one stable approved Intent snapshot and run spec new again"
    ]

    # The sentence a person reads, printed whole. It used to say "filesystem resolved a
    # missing or differently spelled entry", which is true about a path and useless about a
    # decision — so what is pinned is that it names the file to write and the skill that
    # walks somebody through writing it.
    printed = [one for one in capsys.readouterr().out.splitlines() if one.strip()]
    assert printed == [
        "  INCOMPLETE  there is no Solution Intent here yet, and a spec is a decision inside "
        "one. Write `.ai/intent.md` first — `/ai-spec` walks through it — and run this again"
    ]
    assert not (repo / "specs" / "001-a-slug").exists(), "a refused spec left a directory"


def _inventory(*names: str):
    """An inventory of the `specs/` directory, which is all `_number` reads."""
    from types import SimpleNamespace

    return SimpleNamespace(names=list(names), pending=(), generation=0, consumed=False)


def test_the_next_spec_number_is_one_past_the_highest_and_never_a_gap(tmp_path):
    """`_number` decides the identity of every governed record this project will ever write,
    and seventeen of its mutants survived.

    One past the highest, not one past the count. A repository whose 003 was archived has
    two directories and its next spec is 004 — filling the gap would mint a number a
    reference already points at, and the references live in other repositories' commit
    messages where nothing here can update them.
    """
    from ai_engineering import spec

    assert spec._number(_inventory()) == "001"
    assert spec._number(_inventory(".gitkeep")) == "001"
    assert spec._number(_inventory("001-a", "002-b")) == "003"
    assert spec._number(_inventory("001-a", "003-c")) == "004", "a gap was filled"
    assert spec._number(_inventory("009-x")) == "010"
    assert spec._number(_inventory("099-x")) == "100"

    # Zero-padded to three, always. `10-a` beside `009-a` sorts wrongly in every listing a
    # person reads, and the pattern that finds them would stop matching.
    assert spec._number(_inventory("001-a")) == "002"
    assert len(spec._number(_inventory())) == 3

    # A pending directory counts. It is a spec that has been staged and not yet published,
    # and handing its number to a second writer is the collision this whole transaction
    # exists to prevent.
    assert spec._number(_inventory("pending-007-half-written")) == "008"
    assert spec._number(_inventory("001-a", "pending-005-b")) == "006"


def test_a_spec_namespace_this_cannot_read_stops_the_write(tmp_path):
    """Three refusals, and each is a different thing being wrong.

    A name that looks like a spec and is not one is ambiguous: `1-a` and `pending-x` both
    start where a spec starts and match neither pattern, so this cannot say what number is
    taken. A duplicate is two directories claiming one identity. And 999 is the end of the
    range, which is a real edge rather than a theoretical one — a number past it would be
    four digits and every pattern here expects three.

    All three raise rather than guessing, because guessing here mints an identifier a
    reference in another repository already points at.
    """
    import pytest as _pytest

    from ai_engineering import spec, spec_transaction

    for ambiguous in ("1-a", "42", "pending-x", "0001-a", "pending-1-a"):
        with _pytest.raises(spec_transaction.Unsafe, match="ambiguous identifier"):
            spec._number(_inventory(ambiguous))

    with _pytest.raises(spec_transaction.Unsafe, match="duplicate identifier"):
        spec._number(_inventory("001-a", "pending-001-b"))

    with _pytest.raises(spec_transaction.Unsafe, match="range is exhausted"):
        spec._number(_inventory("999-the-last-one"))

    # And an ordinary name that is not a spec at all is skipped rather than refused: a
    # `README.md` beside the specs is somebody's file, not an ambiguous identifier.
    assert spec._number(_inventory("README.md", "notes", "001-a")) == "002"


SECTION = """## Examples somebody can check

**The success path.** Given a tree, When the writer runs the task, Then the plan hashes to
what it hashed to before — verified by running `git diff --stat -- specs/x/plan.md` and
reading `0 files changed`.

**The denial path.** Given a base that is not there, When the checkpoint runs, Then the
receipt is INCOMPLETE.

**The undecidable path.** Given a section with no command, When the gate reads it, Then it
fails the executable clause and passes the structure one.

## Decisions
"""


def test_the_examples_section_is_counted_by_what_it_holds():
    """The reading half of the executable clause, and the only definition of it.

    The gate over authored specifications calls this rather than parsing the section a
    second time, because two definitions of "executable" is how the two disagree later.
    """

    from ai_engineering import spec

    assert spec.examples_facts(SECTION) == (3, 3, 3, 1)

    # No heading at all is zeroes, not a crash and not a pass.
    assert spec.examples_facts("# A spec with no examples\n") == (0, 0, 0, 0)

    # A Then with an output and no command is not executable: the command is the half a
    # reader cannot reconstruct, and spec 018 is exactly this shape.
    output_only = SECTION.replace(
        "verified by running `git diff --stat -- specs/x/plan.md` and\nreading `0 files changed`",
        "verified by reading `0 files changed`",
    )
    assert spec.examples_facts(output_only) == (3, 3, 3, 0)

    # A command with nothing after it is not executable either: an expected output is what
    # makes it a check rather than an instruction.
    bare = SECTION.replace(
        "`git diff --stat -- specs/x/plan.md` and\nreading `0 files changed`",
        "`git diff --stat -- specs/x/plan.md`",
    )
    assert spec.examples_facts(bare) == (3, 3, 3, 0)

    # And the verb list is closed. A Then naming something nobody can run is prose.
    invented = SECTION.replace("`git diff --stat -- specs/x/plan.md`", "`frobnicate --all`")
    assert spec.examples_facts(invented) == (3, 3, 3, 0)

    # The canonical division of labour — the action in When, the observation in Then — is
    # the shape a reader writes without being told, and reading only the tail after `Then`
    # refused it.
    canonical = (
        "## Examples somebody can check\n\n"
        "Given a repo, When `just check` runs, Then it prints `2101 passed`.\n"
    )
    assert spec.examples_facts(canonical) == (1, 1, 1, 1)

    # The section ends at the next heading, and this pins it: an example below `## Decisions`
    # is not in the section. Without this the boundary is a mutant nobody kills, because no
    # specification in the tree writes Given/When/Then after that heading.
    assert spec.examples_facts(SECTION + "\nGiven z, When z, Then `git log` prints `z`.\n") == (
        3,
        3,
        3,
        1,
    )

    # A heading quoted in prose is not the section starting. 019 is a specification about
    # this section and is one editing pass from writing it.
    quoted = "# S\n\nWe follow `" + spec.EXAMPLES + "` here.\n\n" + SECTION
    assert spec.examples_facts(quoted) == (3, 3, 3, 1)

    # And a document with no section at all that quotes the heading beside an example is
    # zeroes, not an example. A conditional guard here fell back to reading the whole
    # document, which read that shape as a filled section — the fail-open a repair opened.
    hazard = (
        "---\nstatus: draft\n---\n\nGiven a reader, When they arrive, Then `git log` prints "
        "`x`. We follow `" + spec.EXAMPLES + "` in every spec.\n"
    )
    assert spec.examples_facts(hazard) == (0, 0, 0, 0)

    # One definition of where the section is. The gate over authored specifications cut its
    # own for a commit, and after this function changed the two disagreed on that document.
    assert spec.examples_section(hazard) == ""
    assert spec.examples_section(SECTION).startswith("\n\n**The success path.**")

    # Carriage returns do not collapse the paragraphs into one.
    assert spec.examples_facts(SECTION.replace("\n", "\r\n")) == (3, 3, 3, 1)


def test_the_template_own_examples_prompt_is_not_executable():
    """The one collision worth pinning. Task 11 put a worked shape into the prompt, and if
    its verb were on the closed list every `ai-eng spec new` output would satisfy the
    executable clause on the day it is written — and the gate's intended red would never
    fire for anybody."""

    from ai_engineering import spec

    prompt = spec.TEMPLATE.split("## Examples somebody can check", 1)[1].split("\n## ", 1)[0]
    assert spec.examples_facts("## Examples somebody can check" + prompt)[3] == 0
