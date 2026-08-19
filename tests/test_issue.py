"""The first capability through the admission gate, and the only one whose exit criterion
is an exit code rather than an opinion.

`report issue` printed "planned for P2 and is not implemented" and returned INCOMPLETE.
That was honest, and it becomes a lie the moment anything half-builds it. These tests are
the half that must exist first: one red fixture per forbidden class, written before the
code that rejects it, because a scanner tested only on the input it was written for is a
scanner that agrees with its author.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]

CLEAN = {
    "kind": "bug",
    "title": "doctor prints ok for a chain the verifier rejects",
    "what_happened": "assertion 6 said intact while audit verify exited 1",
    "expected": "one verdict from both readers, or a stated reason for two",
    "steps": ["run ai-eng doctor", "run ai-eng audit verify", "compare the two verdicts"],
}


_ARGUMENTS = (
    "--title",
    CLEAN["title"],
    "--what-happened",
    CLEAN["what_happened"],
    "--expected",
    CLEAN["expected"],
    *[argument for step in CLEAN["steps"] for argument in ("--step", step)],
)


def payload(**overrides) -> dict:
    from ai_engineering import issue

    fields = {**CLEAN, **overrides}
    return issue.build(**fields)


def test_the_payload_carries_the_allow_list_and_nothing_else():
    """EP-024. The field set is closed, it comes from the schema rather than from a second
    list in the code, and every value in it was passed in by a person.

    The forbidden classes are named in specification 012's normative contract: logs, diff,
    source, specs, chain, environment, paths, host, user, email, IP, remotes, client data.
    None of them has a field to arrive in, which is a stronger statement than a filter."""

    from ai_engineering import issue

    built = payload()
    assert set(built) == set(issue.FIELDS)

    schema = json.loads((ROOT / "policy" / "issue-v1.schema.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == set(issue.FIELDS), "one home for the field list"
    assert sorted(schema["required"]) == sorted(issue.FIELDS)

    for forbidden in ("log", "diff", "source", "spec", "chain", "env", "path", "host", "remote"):
        assert not any(forbidden in field for field in issue.FIELDS), forbidden


def test_nothing_is_collected_from_the_machine_or_the_repository(tmp_path, monkeypatch):
    """EP-131. `build` reads its arguments and nothing else.

    The test proves it the only way that can fail: it plants a secret in the working
    directory, a remote in the environment and a hostname in the process, and asserts the
    payload is byte-identical to the one built without them."""

    from ai_engineering import issue

    plain = json.dumps(payload(), sort_keys=True)

    (tmp_path / "leak.txt").write_text("a secret nobody asked this to read", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_REMOTE", "git@github.com:someone/private.git")
    monkeypatch.setenv("USER", "a-person")
    monkeypatch.setattr("socket.gethostname", lambda: "a-laptop.local")

    assert json.dumps(payload(), sort_keys=True) == plain
    assert issue.__version__ in payload()["framework_version"]


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("what_happened", "it failed under /Users/somebody/repos/thing", "MACHINE_PATH"),
        ("what_happened", "reported by somebody@example.com on the call", "PII"),
        ("what_happened", "the config held AKIAIOSFODNN7EXAMPLE as its key", "SECRET"),
    ],
    ids=["machine-path", "personal-data", "secret"],
)
def test_a_forbidden_class_stops_the_report(tmp_path, monkeypatch, field, value, code):
    """EP-027, EP-271. One red fixture per forbidden class.

    A field that carries one is refused, the refusal names the class, and no draft is left
    on disk — a rejected payload that still wrote a file is a payload somebody can send.

    The secret scanner is stood in for, at its pinned version and its real exit meanings,
    reading the directory it is handed. So what this proves is that the payload's own bytes
    reach a scanner and that its FAIL blocks — not that gitleaks recognises an AWS key,
    which is `just security`'s job and not a unit test's.
    """

    from ai_engineering import acceptance_privacy, issue

    root = tmp_path / "repository"
    (root / ".ai").mkdir(parents=True)
    calls: list[tuple] = []

    def scanner(argv, cwd):
        calls.append((argv, Path(cwd)))
        if argv[1] == "version":
            return SimpleNamespace(returncode=0, stdout=acceptance_privacy.GITLEAKS_VERSION)
        seen = "".join(p.read_text(encoding="utf-8") for p in Path(cwd).rglob("*.json"))
        return SimpleNamespace(returncode=1 if "AKIA" in seen else 0, stdout="")

    monkeypatch.setattr(acceptance_privacy, "_run", scanner)

    refused = issue.scan(root, payload(**{field: value}))

    assert refused, "a forbidden class reached the payload and the scan called it clean"
    assert any(code in finding.code for finding in refused), [f.code for f in refused]
    assert not issue.draft_path(root).exists()
    assert calls and calls[-1][0] == acceptance_privacy.GITLEAKS_ARGV, "the scanner was skipped"


def test_a_scanner_that_cannot_answer_refuses_rather_than_passing(tmp_path, monkeypatch):
    """The bound the secret scanner already states, kept at this boundary too.

    `gitleaks_v1` returns INCOMPLETE when the pinned scanner is missing or the wrong
    version. Reading that as clean would turn a bound into a bypass, so it blocks."""

    from ai_engineering import acceptance_privacy, issue

    root = tmp_path / "repository"
    (root / ".ai").mkdir(parents=True)
    monkeypatch.setattr(
        acceptance_privacy,
        "gitleaks_v1",
        lambda directory: acceptance_privacy.Verdict(
            "INCOMPLETE", "ACCEPTANCE_GITLEAKS_UNAVAILABLE", "not installed"
        ),
    )

    refused = issue.scan(root, payload())

    assert [finding.outcome for finding in refused] == ["INCOMPLETE"]


def test_the_draft_is_local_gitignored_and_the_preview_is_the_exact_bytes(tmp_path, capsys):
    """EP-272, EP-273. What a person is shown is what would leave, and its digest.

    A preview that pretty-prints, truncates or reorders is a preview of something else. The
    bytes are hashed, the hash is printed beside them, and the draft lands under `.ai/`,
    whose `.gitignore` excludes everything it does not name."""

    from ai_engineering import issue

    root = tmp_path / "repository"
    (root / ".ai").mkdir(parents=True)
    (root / ".ai" / ".gitignore").write_text("*\n!.gitignore\n!config.toml\n", encoding="utf-8")

    built = payload()
    written = issue.draft(root, built)
    printed = capsys.readouterr().out

    assert written.read_bytes() == issue.exact_bytes(built)
    assert issue.draft_path(root) == written
    assert str(written.relative_to(root)).startswith(".ai/")
    assert issue.digest(built) in printed
    assert json.loads(written.read_text(encoding="utf-8")) == built


@pytest.fixture
def pinned_scanner(monkeypatch):
    """The secret scanner at its pinned version, reading the directory it is handed.

    Standing in for it keeps these tests answering their own question — routing, consent,
    destination — on a machine that has no gitleaks. Whether gitleaks itself recognises a
    given secret is `just security`'s question and it runs the real binary."""

    from ai_engineering import acceptance_privacy

    def scanner(argv, cwd):
        if argv[1] == "version":
            return SimpleNamespace(returncode=0, stdout=acceptance_privacy.GITLEAKS_VERSION)
        # Every file, not only the payload. The scan is asked twice now — once about the
        # directory and once about a secret the product plants in a temporary directory to
        # check the scanner still finds one — and a stand-in that only ever read `*.json`
        # answered the second call clean, which is exactly the tampered scanner the canary
        # exists to catch. A fixture standing in for a working scanner has to behave like one.
        seen = "".join(
            one.read_text(encoding="utf-8", errors="replace")
            for one in Path(cwd).rglob("*")
            if one.is_file()
        )
        found = "AKIA" in seen or acceptance_privacy._CANARY_VALUE in seen
        return SimpleNamespace(returncode=1 if found else 0, stdout="")

    monkeypatch.setattr(acceptance_privacy, "_run", scanner)


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    (root / ".ai").mkdir(parents=True)
    (root / ".ai" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    return root


def _asked(monkeypatch, answer: bool) -> list[str]:
    """Stand in for the controlling terminal and record what it was asked to confirm.

    The list is the evidence for the half that matters more than the answer: a route that
    must never be taken is one nobody is ever offered."""

    from ai_engineering import accept

    seen: list[str] = []

    def reader(expected: str) -> bool:
        seen.append(expected)
        return answer

    monkeypatch.setattr(accept, "controlling_terminal_response", reader)
    return seen


def test_a_security_finding_is_never_offered_a_public_route(
    tmp_path, monkeypatch, capsys, pinned_scanner
):
    """EP-274. A vulnerability never ends in a public issue.

    Refused before the terminal is read, not after: a control that asks first and refuses
    second has already put the wrong route in front of somebody at 2am. The private route
    it prints is the one `SECURITY.md` publishes, and a test binds the two so they cannot
    drift into two different answers."""

    from ai_engineering import issue, report

    asked = _asked(monkeypatch, answer=True)
    root = _repository(tmp_path)
    monkeypatch.setattr(report.paths, "repo_root", lambda start=None: root)

    result = report.main(
        [
            "issue",
            "--kind",
            "security",
            "--submit",
            "--title",
            "the guard can be made to allow a write it must deny",
            "--what-happened",
            "a crafted payload reaches the allow branch of the guard",
            "--expected",
            "the guard denies, because it cannot decide",
            "--step",
            "send the crafted payload",
        ]
    )
    printed = capsys.readouterr().out

    assert result.outcome == "INCOMPLETE"
    assert asked == [], "somebody was offered a public route for a vulnerability"
    assert issue.PRIVATE_ROUTE in printed
    assert issue.PRIVATE_ROUTE in (ROOT / "SECURITY.md").read_text(encoding="utf-8")


def test_submit_without_the_typed_confirmation_sends_nothing(tmp_path, monkeypatch, pinned_scanner):
    """EP-275. Sending is a separate action a person confirms, at a keyboard.

    The phrase carries the payload's own digest, so what is confirmed is one exact payload
    and not "the last thing on screen"."""

    from ai_engineering import issue, report

    asked = _asked(monkeypatch, answer=False)
    root = _repository(tmp_path)
    monkeypatch.setattr(report.paths, "repo_root", lambda start=None: root)

    result = report.main(
        ["issue", "--kind", "bug", "--submit", *_ARGUMENTS],
    )

    assert result.outcome == "INCOMPLETE"
    assert len(asked) == 1

    # The payload that was drafted, read back off disk — not a second `build` of the same
    # arguments. `created_at` is `datetime.now()`, so rebuilding it here produces a different
    # payload whenever the clock ticks between the two calls, and the digest in the phrase is
    # of the first one. That flake sat latent until a slower draft path widened the window
    # and CI caught it; asserting against the bytes a person was actually shown is both the
    # fix and the stronger claim, because the phrase has to match *that* payload.
    drafted = json.loads(issue.draft_path(root).read_text(encoding="utf-8"))
    assert issue.confirmation(drafted)[:20] in asked[0]
    assert issue.digest(drafted)[:16] in asked[0]
    assert drafted["kind"] == "bug" and drafted["title"] == CLEAN["title"]


def test_a_confirmed_submit_stops_at_the_destination_that_does_not_exist(
    tmp_path, monkeypatch, pinned_scanner
):
    """The honest end of this path today.

    A person can confirm, and there is still nowhere to send: no destination is configured
    and this package has no transport. That is INCOMPLETE and it says which, rather than
    PASS for work that did not happen — the defect `update --dry-run` was fixed for one
    wave ago."""

    from ai_engineering import report

    _asked(monkeypatch, answer=True)
    root = _repository(tmp_path)
    monkeypatch.setattr(report.paths, "repo_root", lambda start=None: root)

    result = report.main(["issue", "--kind", "bug", "--submit", *_ARGUMENTS])

    assert result.outcome == "INCOMPLETE"
    assert any("DESTINATION" in fact.detail or "DESTINATION" in fact.id for fact in result.checks)


def test_drafting_alone_never_reads_the_terminal(tmp_path, monkeypatch, pinned_scanner):
    """Submit is a separate action, which means the draft path cannot be a quiet first half
    of it. Nothing asks, so nothing can be answered by accident."""

    from ai_engineering import report

    asked = _asked(monkeypatch, answer=True)
    root = _repository(tmp_path)
    monkeypatch.setattr(report.paths, "repo_root", lambda start=None: root)

    result = report.main(["issue", "--kind", "bug", *_ARGUMENTS])

    assert result.outcome == "PASS"
    assert asked == []


def test_the_declaration_says_where_the_draft_lands():
    """EP-098's declaration, bound to the code that has to obey it.

    `policy/capabilities.toml` declared that `ai-report`'s issue mode writes nowhere, and
    the drafting this wave built writes one file. Nothing enforces the declaration yet — one
    of the fifteen enforces anything, which is what doctor's assertion 23 says — so the two
    could disagree for as long as that stayed true, and the day an executor arrives it would
    deny the command that is doing its job. A declaration nobody checks against the code is
    the same shape as a receipt nobody earned."""

    import tomllib

    from ai_engineering import issue

    manifest = tomllib.loads((ROOT / "policy" / "capabilities.toml").read_text(encoding="utf-8"))
    report = next(item for item in manifest["capabilities"] if item["id"] == "ai-report")
    mode = next(one for one in report["modes"] if one["id"] == "issue")

    root = Path("/somewhere")
    assert mode["write_roots"] == [str(issue.draft_path(root).parent.relative_to(root))]
    assert "preflight.write" in mode["enforcement"]


def test_no_eleventh_verb_and_the_stub_sentence_is_gone():
    """EP-227, EP-228, and the sentence the specification says becomes a lie.

    `report issue` is a subcommand of a verb that already exists. And the promise it used to
    print — "planned for P2 and is not implemented" — must not survive the thing it
    promised, in either direction: a sentence that says unimplemented over working code is
    the same defect as a sentence that says implemented over nothing."""

    verbs = (ROOT / "src" / "ai_engineering" / "cli.py").read_text(encoding="utf-8")
    assert verbs.count('": (\n        "') == 10

    source = (ROOT / "src" / "ai_engineering" / "report.py").read_text(encoding="utf-8")
    assert "report issue is planned for P2" not in source


def _report_help(monkeypatch, capsys, *argv: str) -> list[str]:
    """One subcommand's whole help block, at a fixed width so it is comparable."""
    from ai_engineering import report

    monkeypatch.setenv("COLUMNS", "90")
    with pytest.raises(SystemExit):
        report.main([*argv, "--help"])
    return capsys.readouterr().out.rstrip("\n").splitlines()


def test_the_report_verb_declares_exactly_these_five_subcommands(monkeypatch, capsys):
    """Two hundred and fifty-two mutants lived in this verb, more than any other in the tree,
    and its declared surface is most of them.

    `report` is the only verb that can send something outward, so what it accepts is not a
    convenience — every argument is a field of a payload that may leave the machine, and the
    five required ones are what stop a report being sent half-written. A default moved or a
    choice list widened is invisible to a test that passes valid arguments and reads the
    outcome, which is what every fixture here did.

    Five since specification 020. `blocked` writes one committed file and sends nothing, and
    it is here rather than under its own verb because what it records is a report about this
    run — the one report whose reader is a person who is not at the keyboard.
    """
    assert _report_help(monkeypatch, capsys) == [
        "usage: ai-eng report [-h] {digest,issue,surfaces,intent,blocked} ...",
        "",
        "positional arguments:",
        "  {digest,issue,surfaces,intent,blocked}",
        "",
        "options:",
        "  -h, --help            show this help message and exit",
    ]


def test_the_blocked_subcommand_requires_the_three_a_row_cannot_be_read_without(
    monkeypatch, capsys
):
    """Its declared surface, pinned like the others. `--since` defaults to today because a
    halt happening now is the ordinary case; the other three have no honest default, and a
    row missing any of them is refused by the collector rather than rendered half-blank."""
    assert _report_help(monkeypatch, capsys, "blocked") == [
        "usage: ai-eng report blocked [-h] --what WHAT --why WHY --action ACTION "
        "[--since SINCE]",
        "",
        "options:",
        "  -h, --help       show this help message and exit",
        "  --what WHAT",
        "  --why WHY",
        "  --action ACTION",
        "  --since SINCE",
    ]


def test_the_issue_subcommand_requires_all_five_fields_and_offers_one_flag(monkeypatch, capsys):
    """`--kind` is a closed choice of two and the difference between them decides whether a
    public route is offered at all. The other four are the payload, and `--submit` is the one
    flag that turns a draft into something that leaves."""
    assert _report_help(monkeypatch, capsys, "issue") == [
        "usage: ai-eng report issue [-h] --kind {bug,security} --title TITLE --what-happened",
        "                           WHAT_HAPPENED --expected EXPECTED --step STEP [--submit]",
        "",
        "options:",
        "  -h, --help            show this help message and exit",
        "  --kind {bug,security}",
        "  --title TITLE",
        "  --what-happened WHAT_HAPPENED",
        "  --expected EXPECTED",
        "  --step STEP",
        "  --submit",
    ]


def test_the_other_two_subcommands_say_exactly_what_they_need(monkeypatch, capsys):
    """`digest` takes a window and `surfaces` takes nothing. Both are read-only and neither
    can send anything, which is why they carry no confirmation flag."""
    assert _report_help(monkeypatch, capsys, "digest") == [
        "usage: ai-eng report digest [-h] [--weeks WEEKS]",
        "",
        "options:",
        "  -h, --help     show this help message and exit",
        "  --weeks WEEKS",
    ]
    assert _report_help(monkeypatch, capsys, "surfaces") == [
        "usage: ai-eng report surfaces [-h]",
        "",
        "options:",
        "  -h, --help  show this help message and exit",
    ]


def test_an_issue_missing_any_required_field_is_refused_rather_than_sent_half_written(
    monkeypatch, capsys
):
    """Five required arguments, each removed on its own.

    A report missing its title, or what happened, or what was expected, is one nobody
    receiving it can act on — and `report` is the verb that can send it outward. Omitting all
    five at once would pass with four of them optional, so each is checked alone.
    """
    from ai_engineering import report

    monkeypatch.setenv("COLUMNS", "90")
    whole = [
        "issue",
        "--kind",
        "bug",
        "--title",
        "t",
        "--what-happened",
        "x",
        "--expected",
        "y",
        "--step",
        "z",
    ]
    for flag in ("--kind", "--title", "--what-happened", "--expected", "--step"):
        where = whole.index(flag)
        with pytest.raises(SystemExit) as refused:
            report.main(whole[:where] + whole[where + 2 :])
        assert refused.value.code == 2, flag
        assert flag in capsys.readouterr().err, flag

    # And a kind outside the closed pair is refused rather than treated as a bug, because the
    # two differ in whether a public route is ever offered.
    where = whole.index("--kind")
    with pytest.raises(SystemExit) as refused:
        report.main(whole[: where + 1] + ["incident"] + whole[where + 2 :])
    assert refused.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def _args(**changed):
    """The five fields of a valid report, as the parser hands them over."""
    import argparse

    fields = {
        "kind": "bug",
        "title": "a title",
        "what_happened": "what happened",
        "expected": "what was expected",
        "step": ["one step"],
        "submit": False,
    }
    fields.update(changed)
    return argparse.Namespace(**fields)


def test_every_outcome_of_a_governed_report_says_its_own_summary(tmp_path, capsys):
    """Ninety-nine mutants lived in the one function that decides what a report becomes.

    It has four ends and they are not interchangeable: no repository, a payload the scan
    refused, a vulnerability asked to go public, and a clean draft. Each writes a different
    thing to disk — three of them nothing at all — and each says something different to the
    person. Every fixture here had checked the outcome word and the file, and none had checked
    the summary, which is the sentence that says what happened to their report.
    """
    from ai_engineering import report

    outside = report.report_issue(None, _args())
    assert outside.outcome == "INCOMPLETE"
    assert "nowhere to keep a draft" in capsys.readouterr().out

    clean = report.report_issue(tmp_path, _args())
    assert clean.result.outcome == "PASS"
    assert clean.summary == "Drafted a bug report locally; nothing has been sent"
    assert clean.remaining == (
        "Nothing has been sent. Sending is a separate action a person confirms.",
    )
    assert [fact.id for fact in clean.changes] == ["issue-draft"]
    assert [fact.id for fact in clean.checks] == ["scan", "digest"]
    assert [fact.status for fact in clean.checks] == ["PASS", "OBSERVED"]


def test_a_refused_payload_leaves_no_file_and_names_every_class_it_found(tmp_path, capsys):
    """The refusal that matters most, and the field that proves it: no draft is written.

    The order is the whole control — build, scan the exact bytes, and only then write. A
    version that wrote first and scanned second would leave on disk exactly the artefact
    somebody could still send, which is the one this refusal exists to prevent.
    """
    from ai_engineering import report

    refused = report.report_issue(tmp_path, _args(title="my key is at /Users/somebody/.ssh/id_rsa"))

    assert refused.result.outcome == "INCOMPLETE"
    assert refused.summary.endswith("stopped this report; nothing was written or sent")
    assert refused.summary[0].isdigit(), "the summary does not say how many findings there were"
    assert refused.remaining, "a refusal named no class at all"
    assert all(fact.cure for fact in refused.checks), "a refused field carries no way forward"
    assert all(
        fact.cure == "rewrite the field in your own words, without the value it carried"
        for fact in refused.checks
    )
    assert not list(tmp_path.glob("**/*.json")), "a refused report still wrote a draft"


def test_a_vulnerability_is_refused_before_the_terminal_and_not_after(tmp_path, capsys):
    """Asked to go public, a security finding is routed privately — and the check happens
    before anything is written or any confirmation is asked.

    A control that asked first and refused second has already put the wrong route in front of
    somebody at the end of a long day, so what this asserts is not only the refusal but that
    no draft exists afterwards and the private route is named in the line.
    """
    from ai_engineering import issue as issue_module
    from ai_engineering import report

    routed = report.report_issue(tmp_path, _args(kind="security", submit=True))

    assert routed.result.outcome == "INCOMPLETE"
    assert routed.summary == "A security finding routes to private disclosure; nothing was written"
    assert [fact.id for fact in routed.checks] == ["route"]
    assert routed.checks[0].detail == "ISSUE_SECURITY_ROUTE_IS_PRIVATE"
    assert issue_module.PRIVATE_ROUTE in routed.checks[0].cure
    assert issue_module.PRIVATE_ROUTE in capsys.readouterr().out
    assert not list(tmp_path.glob("**/*.json")), "a refused vulnerability still wrote a draft"

    # And a security report that is *not* asked to go public is drafted like any other, which
    # is the half that stops this refusal from becoming a ban on reporting vulnerabilities.
    drafted = report.report_issue(tmp_path, _args(kind="security"))
    assert drafted.result.outcome == "PASS"
    assert drafted.summary == "Drafted a security report locally; nothing has been sent"
