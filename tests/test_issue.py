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
        seen = "".join(p.read_text(encoding="utf-8") for p in Path(cwd).rglob("*.json"))
        return SimpleNamespace(returncode=1 if "AKIA" in seen else 0, stdout="")

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
    built = issue.build(**CLEAN)
    assert issue.confirmation(built)[:20] in asked[0]
    assert issue.digest(built)[:16] in asked[0]


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
