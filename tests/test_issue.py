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
