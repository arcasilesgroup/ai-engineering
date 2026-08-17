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
        "  This grants ONE bypass of change_scope_guard, for 15 minutes, "
        "recorded against your name.",
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
    result = exception.main(["--skip", "in a hurry", "--guard", "change_scope_guard"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert capsys.readouterr().out.splitlines()[-1] == (
        "  ✓ granted. The next change_scope_guard block passes, once, and the record says why."
    )
    names = sorted(path.name for path in paths.home().iterdir())
    assert "cache" in names and "CACHE" not in names
    assert [path.name for path in (paths.home() / "cache").iterdir()] == ["bypass.json"]
    grant = json.loads((paths.home() / "cache" / "bypass.json").read_text())
    assert grant["guard"] == "change_scope_guard" and grant["reason"] == "in a hurry"
    event = json.loads(home.chain_path(None).read_text().splitlines()[-1])
    assert event["name"] == "change_scope_guard" and event["cls"] == "bypassed"
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
        "--guard {change_scope_guard,loop_guard}",
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

    asleep = spec._why_not_authority("draft", "owner", "owner", transition)
    assert "'draft'" in asleep and "active" in asleep

    mismatched = spec._why_not_authority("active", "repository owner", "maintainer", transition)
    assert "'repository owner'" in mismatched and "'maintainer'" in mismatched
    assert "the same words" in mismatched

    drifted = spec._why_not_authority(
        "active", "owner", "owner", {"authority_role": "somebody else", "approval_ref": "abc"}
    )
    assert "'somebody else'" in drifted and "'owner'" in drifted

    refused = spec._why_not_authority("active", "agent", "agent", {"authority_role": "agent"})
    assert "'agent'" in refused and "refuses to read" in refused

    # And every branch says something. A diagnostic that falls through to an empty string is
    # the original defect with an extra function in front of it.
    for said in (asleep, mismatched, drifted, refused):
        assert len(said.split()) >= 8, said
