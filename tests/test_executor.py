"""The five requirements that collapsed into one job, and what actually enforces them now.

`EP-078`, `EP-137`, `EP-138`, `EP-162` and `EP-165` were five separate rows in the ledger
with one blocker between them: `capability.preflight` validated fifteen capabilities' worth
of read roots, write roots, exec allowlists, hosts, secrets and human gates, and then
returned `CAPABILITY_ENFORCEMENT_UNAVAILABLE` on every path. Nothing could be made to pass,
so nothing could be made to fail either, and a control that cannot fail is not a control.

Every test here does the operation. A test that called `preflight` and read the verdict
would prove the same thing the old code proved: that a declaration parses. What has to be
shown is that the file does not get written, the process does not start, and the token does
not come back — and the only way to show that is to try.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ai_engineering import capability, executor


def sandbox(tmp_path: Path, capability_id="ai-note", mode_id="default", **extra):
    root = tmp_path / "repo"
    root.mkdir(exist_ok=True)
    return executor.Sandbox(capability_id, mode_id, root, **extra)


def yes(_action):
    return True


def test_a_declared_write_happens_and_an_undeclared_one_does_not(tmp_path):
    """The pair that has to hold together, and neither half means anything alone.

    `ai-note` declares `docs/notes` and nothing else. A test showing only the refusal would
    pass against a sandbox that refuses everything, which is the failure mode this file
    exists to avoid — a fail-closed control that closed on everything would look identical
    from outside.
    """

    box = sandbox(tmp_path, confirm=yes)

    written = box.write("docs/notes/finding.md", b"a note")
    assert written.read_bytes() == b"a note"
    assert written == box.root / "docs" / "notes" / "finding.md"

    with pytest.raises(executor.Refused) as refusal:
        box.write("src/pwn.py", b"import os")
    assert refusal.value.result.code == "CAPABILITY_ACTION_UNDECLARED"
    assert not (box.root / "src" / "pwn.py").exists(), "a refused write still landed"


def test_the_human_gate_is_asked_before_the_operation_and_a_no_stops_it(tmp_path):
    """`ai-note` declares `human_gate = "before_write"`, and until now that was a string.

    Three states, because two of them are usually conflated: nobody present, somebody who
    said no, and somebody who said yes. The first two must both refuse.

    The ordering is checked here too, and it runs the other way from what a reader might
    expect: an out-of-scope action never reaches the gate at all. A prompt that mostly
    precedes a refusal is a prompt people learn to dismiss, which is how a gate stops being
    one — so the declaration refuses first and only a real, in-scope write asks anybody.
    """

    asked: list[str] = []

    absent = sandbox(tmp_path)
    with pytest.raises(executor.Refused) as refusal:
        absent.write("docs/notes/a.md", b"x")
    assert refusal.value.result.code == "CAPABILITY_HUMAN_GATE_UNCONFIRMED"

    refused = sandbox(tmp_path, confirm=lambda action: asked.append(action.path) or False)
    with pytest.raises(executor.Refused) as refusal:
        refused.write("docs/notes/a.md", b"x")
    assert refusal.value.result.code == "CAPABILITY_HUMAN_GATE_UNCONFIRMED"
    assert asked == ["docs/notes/a.md"], "the gate was not asked, or was asked twice"
    assert not (refused.root / "docs" / "notes" / "a.md").exists()

    # An out-of-scope write is refused by the declaration and nobody is asked about it.
    asked.clear()
    with pytest.raises(executor.Refused) as refusal:
        refused.write("src/pwn.py", b"x")
    assert refusal.value.result.code == "CAPABILITY_ACTION_UNDECLARED"
    assert asked == [], "a person was asked to confirm an action that was refused anyway"

    # And a read is not gated by `before_write`, or the gate word would mean nothing.
    (absent.root / "docs" / "notes").mkdir(parents=True, exist_ok=True)
    (absent.root / "docs" / "notes" / "b.md").write_text("here", encoding="utf-8")
    assert absent.read("docs/notes/b.md") == b"here"


def test_a_symlink_out_of_the_root_is_refused_at_the_moment_of_the_operation(tmp_path):
    """The difference between deciding beside an operation and deciding by one.

    `docs/notes/escape.md` is a declared path by every string check there is. It is also a
    symlink to a file outside the root. The declaration cannot see that and the operation
    can, which is why the resolution happens here rather than in the manifest reader.
    """

    box = sandbox(tmp_path, confirm=yes)
    outside = tmp_path / "outside.md"
    outside.write_text("somebody else's file", encoding="utf-8")
    (box.root / "docs" / "notes").mkdir(parents=True)
    (box.root / "docs" / "notes" / "escape.md").symlink_to(outside)

    with pytest.raises(executor.Refused) as refusal:
        box.write("docs/notes/escape.md", b"overwritten")
    assert refusal.value.result.code == "CAPABILITY_ENFORCEMENT_UNAVAILABLE"
    assert outside.read_text(encoding="utf-8") == "somebody else's file"

    with pytest.raises(executor.Refused):
        box.read("docs/notes/escape.md")

    # A linked *directory* is the same attack one level up, and a check on the final
    # component alone would let it through.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (box.root / "docs" / "notes" / "linked").symlink_to(elsewhere)
    with pytest.raises(executor.Refused):
        box.write("docs/notes/linked/new.md", b"x")
    assert not (elsewhere / "new.md").exists()


def test_dot_dot_never_reaches_the_filesystem(tmp_path):
    """Refused by the declaration's own path grammar before resolution is even reached, and
    asserted here anyway: the two checks are in different modules and either could be
    removed without the other's tests noticing."""

    box = sandbox(tmp_path, confirm=yes)
    (tmp_path / "secrets.txt").write_text("s", encoding="utf-8")

    for attempt in ("../secrets.txt", "docs/notes/../../../secrets.txt", "/etc/passwd"):
        with pytest.raises(executor.Refused):
            box.write(attempt, b"x")
    assert (tmp_path / "secrets.txt").read_text(encoding="utf-8") == "s"


def test_only_an_allowlisted_executable_runs_and_it_runs_without_a_shell(tmp_path):
    """`ai-review` declares `git` and nothing else, and `human_gate = "never"`.

    The refused half matters more than the allowed half: an executor that ran anything would
    make the allowlist a comment. And the argv is passed as a list to a resolved binary, so
    the shell metacharacters below are arguments to `git` rather than a second command.
    """

    box = sandbox(tmp_path, "ai-review", "default")

    done = box.run("git", "status", "--short")
    assert done.returncode != 0 or isinstance(done.stdout, str)

    with pytest.raises(executor.Refused) as refusal:
        box.run("curl", "https://evil.example")
    assert refusal.value.result.code == "CAPABILITY_ACTION_UNDECLARED"

    with pytest.raises(executor.Refused):
        box.run("git; rm -rf /")
    with pytest.raises(executor.Refused):
        box.run()


def test_a_secret_is_handed_over_only_where_it_is_declared_and_never_logged(tmp_path, monkeypatch):
    """`ai-report issue` declares `github.token`; `ai-note default` declares nothing.

    The second assertion is the one that would rot silently: the corpus and the refusal both
    name the secret and neither may carry its value, or the record built to govern a secret
    becomes the place it leaks.
    """

    monkeypatch.setenv("GITHUB_TOKEN", "ghp-not-a-real-token")
    corpus = tmp_path / "decisions.jsonl"
    box = sandbox(tmp_path, "ai-report", "issue", confirm=yes, corpus=corpus)

    assert box.secret("github.token") == "ghp-not-a-real-token"

    ungoverned = sandbox(tmp_path, confirm=yes, corpus=corpus)
    with pytest.raises(executor.Refused) as refusal:
        ungoverned.secret("github.token")
    assert refusal.value.result.code == "CAPABILITY_ACTION_UNDECLARED"
    assert "ghp-not-a-real-token" not in str(refusal.value)
    assert "ghp-not-a-real-token" not in corpus.read_text(encoding="utf-8")

    monkeypatch.delenv("GITHUB_TOKEN")
    with pytest.raises(executor.Refused) as refusal:
        box.secret("github.token")
    assert refusal.value.result.code == "CAPABILITY_SECRET_ABSENT"


def test_a_declared_host_comes_back_and_an_undeclared_one_is_refused(tmp_path):
    """`ai-research cited-web` declares two hosts and a purpose per host, and the purpose is
    part of the tuple: the same host for a different reason is a different action."""

    box = sandbox(tmp_path, "ai-research", "cited-web", confirm=yes)

    assert box.connect("https", "api.exa.ai", "cited.research") == "https://api.exa.ai"

    for attempt in (
        ("https", "evil.example", "cited.research"),
        ("https", "api.exa.ai", "exfiltrate"),
        ("http", "api.exa.ai", "cited.research"),
    ):
        with pytest.raises(executor.Refused) as refusal:
            box.connect(*attempt)
        assert refusal.value.result.code == "CAPABILITY_ACTION_UNDECLARED", attempt


def test_one_sandbox_cannot_launder_another_capabilitys_action(tmp_path):
    """The identity check inside `owns`, and it is not a formality.

    `preflight` reads the declaration from the ids it is handed. A sandbox that answered
    `owns` without comparing them would let an `ai-note` sandbox present itself as `ai-ship`
    and get a PASS for a write it is then the one to perform.
    """

    box = sandbox(tmp_path, confirm=yes)

    assert (
        capability.preflight(
            "ai-build", "default", capability.Action.write("src/anything.py"), executor=box
        ).code
        == "CAPABILITY_ENFORCEMENT_UNAVAILABLE"
    )
    assert (
        capability.preflight(
            "ai-note", "default", capability.Action.write("docs/notes/a.md"), executor=box
        ).outcome
        == "PASS"
    )


def test_an_executor_that_crashes_is_a_refusal_and_not_a_pass(tmp_path):
    """Fail-closed, including when the thing that fails is the enforcement itself. An
    executor raising out of `owns` or `confirmed` has proved nothing, and the branch that
    would read naturally — letting the exception escape to the caller — is a control whose
    crash looks like an unrelated bug at the call site."""

    class Broken:
        def confirmed(self, action):
            raise RuntimeError("no")

        def owns(self, *_):
            raise RuntimeError("no")

    result = capability.preflight(
        "ai-note", "default", capability.Action.write("docs/notes/a.md"), executor=Broken()
    )
    assert result.outcome == "INCOMPLETE"
    assert result.code == "CAPABILITY_ENFORCEMENT_UNAVAILABLE"


def test_every_decision_lands_in_the_corpus_under_the_proof_id_it_was_declared_with(tmp_path):
    """`EP-162`: deny-proof ids were declared per mode and backed by nothing.

    `proof_requirements.allow` and `.deny` are strings in a manifest. This is what makes one
    of them evidence: a decision taken, in the corpus, under the id the manifest named for
    exactly that kind of decision. Counted per outcome, because a corpus with allows in it
    and no denials would satisfy a check that only asked whether the file had lines.
    """

    corpus = tmp_path / "runtime" / "capability-decisions.jsonl"
    box = sandbox(tmp_path, confirm=yes, corpus=corpus)

    box.write("docs/notes/kept.md", b"x")
    with pytest.raises(executor.Refused):
        box.write("src/pwn.py", b"x")

    lines = [json.loads(one) for one in corpus.read_text(encoding="utf-8").splitlines()]
    allowed = [one for one in lines if one["allowed"]]
    denied = [one for one in lines if not one["allowed"]]

    assert [one["proof_id"] for one in allowed] == ["ai-note.default.allow"]
    assert [one["proof_id"] for one in denied] == ["ai-note.default.deny"]
    assert denied[0]["code"] == "CAPABILITY_ACTION_UNDECLARED"
    assert all(one["capability"] == "ai-note" and one["mode"] == "default" for one in lines)
    assert all(one["ts"].endswith("Z") for one in lines)


def test_a_corpus_that_cannot_be_written_never_turns_a_refusal_into_a_pass(tmp_path):
    """The one fail-open in the module, bounded and asserted.

    The record is written after the decision, so a full disk must not make a governed action
    unavailable — but the direction of that trade has to be checked, because the same code
    written slightly differently would swallow the refusal along with the record.
    """

    box = sandbox(tmp_path, confirm=yes, corpus=tmp_path / "repo" / "docs" / "notes")
    (box.root / "docs" / "notes").mkdir(parents=True)

    assert box.write("docs/notes/still-written.md", b"x").exists()
    with pytest.raises(executor.Refused):
        box.write("src/pwn.py", b"x")


def test_a_gate_word_nobody_recognises_gates_everything(tmp_path):
    """The fallback in `preflight`, which the shipped manifest cannot reach because the
    schema constrains the word. It is asserted anyway: the branch that reads naturally there
    is an empty tuple, and an unrecognised gate word silently meaning "ask nobody" is the
    exact defect class this repository keeps finding."""

    assert executor.GATES["never"] == ()
    assert set(executor.GATES) == {
        "never",
        "before_write",
        "before_exec",
        "before_network",
        "before_publish",
    }

    box = sandbox(tmp_path, "ai-review", "default")
    unknown = {**box._declared_mode(), "human_gate": "before_the_heat_death"}

    def one_mode(_source):
        return {
            "capabilities": [{"id": "ai-review", "phase": "deliver", "modes": [unknown]}],
        }

    original = capability._validated
    capability._validated = one_mode
    try:
        result = capability.preflight(
            "ai-review", "default", capability.Action.execute("git", "status"), executor=box
        )
    finally:
        capability._validated = original
    assert result.code == "CAPABILITY_HUMAN_GATE_UNCONFIRMED"


def test_a_read_of_something_that_is_not_a_regular_file_is_refused(tmp_path):
    """A directory, a device and an absent file are three ways a read can be a read of
    something that is not a file. `ai-explore` declares the whole tree, so nothing about the
    path is what refuses these — the operation is."""

    box = sandbox(tmp_path, "ai-explore", "default")
    (box.root / "docs").mkdir()

    for attempt in ("docs", "docs/absent.md"):
        with pytest.raises(executor.Refused) as refusal:
            box.read(attempt)
        assert refusal.value.result.code == "CAPABILITY_ENFORCEMENT_UNAVAILABLE", attempt

    if os.path.exists("/dev/zero"):
        assert box._resolved("/dev/zero", writing=False) is None


def test_the_report_verbs_draft_is_the_executors_first_real_caller(tmp_path):
    """An executor with no caller is a control nobody meets.

    `EP-184` was exactly that shape — a deterministic DAG nothing called — and closing it
    taught this repository to check for the second half. So `issue.draft`, which writes
    `.ai/issue/draft.json` and is the one shipped verb whose write root the manifest already
    declared, goes through the sandbox rather than to disk.

    The refusal is real and this is what makes it visible: `.ai/issue` replaced by a link to
    somewhere else stops the draft, where the previous `write_bytes` would have followed the
    link and written the payload into whatever it pointed at.
    """

    from ai_engineering import issue

    root = tmp_path / "repo"
    root.mkdir()
    payload = issue.build(
        "bug",
        "the gate is green over nothing",
        "the lane reported PASS with no inputs",
        "a run over zero inputs is INCOMPLETE",
        ["run the lane with no inputs"],
    )

    written = issue.draft(root, payload)
    assert written.read_bytes() == issue.exact_bytes(payload)

    # And the decision was recorded under the id the manifest declares for it.
    corpus = root / ".ai" / "runtime" / executor.CORPUS
    recorded = [json.loads(one) for one in corpus.read_text(encoding="utf-8").splitlines()]
    assert recorded[-1]["proof_id"] == "ai-report.issue.allow"
    assert recorded[-1]["allowed"] is True

    # The refusal: the declared root is a link out of the tree.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    written.unlink()
    (root / ".ai" / "issue").rmdir()
    (root / ".ai" / "issue").symlink_to(elsewhere)

    with pytest.raises(executor.Refused):
        issue.draft(root, payload)
    assert not (elsewhere / "draft.json").exists(), "the draft was written through a link"
