"""Three receipts before a checkpoint is published, and none of them optional.

Specification 013: staged content scanned for secrets, personal data and machine paths;
proof the diff stays inside `claimed_paths`; the checks the diff affects, executed. A
checkpoint missing any of them cannot be claimed or published.

The audit measured what existed: `git-hooks/pre-push` covered secrets only, and
`acceptance_privacy.py` had never seen a staged diff. These are the other two, and the
third receipt is read rather than assumed — a check nobody ran is INCOMPLETE and INCOMPLETE
is not a pass.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest


def git(where, *args) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(where), *args], capture_output=True, text=True, check=False
    )


@pytest.fixture
def working(tmp_path):
    """A repository with one claim in force over `src/`, and one commit behind it."""
    root = tmp_path / "repository"
    subprocess.run(["git", "init", "-b", "main", str(root)], capture_output=True)
    git(root, "config", "user.email", "suite@example.com")
    git(root, "config", "user.name", "suite")
    (root / "src").mkdir(parents=True)
    (root / ".ai").mkdir()
    (root / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-m", "chore: seed")
    (root / ".ai" / "claim.json").write_text(
        json.dumps({"item": "work-42", "paths": ["src/"]}), encoding="utf-8"
    )
    return root


def stage(root: Path, relative: str, body: str) -> None:
    where = root / relative
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(body, encoding="utf-8")
    git(root, "add", relative)


def test_a_clean_checkpoint_reports_two_receipts_and_says_the_third_was_not_run(working):
    """The honest shape of today. Two receipts are produced here; the third is a check
    somebody has to have executed, and this reads for it rather than assuming it."""

    from ai_engineering import checkpoint

    stage(working, "src/added.py", "VALUE = 2\n")
    result = checkpoint.verify(working)

    kinds = {fact.id: fact.status for fact in result.checks}
    assert kinds["staged-privacy"] == "PASS"
    assert kinds["claimed-paths"] == "PASS"
    assert kinds["checks-executed"] == "INCOMPLETE"
    assert result.outcome == "INCOMPLETE", "a missing receipt is not a pass"


def test_a_machine_path_in_the_staged_content_fails_the_first_receipt(working):
    """`acceptance_privacy.py` had never seen a staged diff. It does now, over the content
    that is about to become history rather than over the files that happen to be lying
    around the working directory."""

    from ai_engineering import checkpoint

    stage(working, "src/added.py", "HOME = '/Users/somebody/repos/thing'\n")
    result = checkpoint.verify(working)

    failed = {fact.id: fact.status for fact in result.checks}
    assert failed["staged-privacy"] == "FAIL"
    assert result.outcome == "FAIL"


def test_a_staged_file_outside_the_claim_fails_the_second_receipt(working):
    """The same rule the guard enforces on the write, enforced again on the diff — because
    a write that never went through the guard is exactly the write this catches."""

    from ai_engineering import checkpoint

    stage(working, "docs/notes.md", "notes\n")
    result = checkpoint.verify(working)

    failed = {fact.id: fact.status for fact in result.checks}
    assert failed["claimed-paths"] == "FAIL"
    assert "docs/notes.md" in next(
        fact.detail for fact in result.checks if fact.id == "claimed-paths"
    )


def test_with_no_claim_in_force_the_second_receipt_is_not_applicable_and_not_a_pass(working):
    """Most repositories have never coordinated. The receipt says so — a check that did not
    apply is `SKIPPED`, and the vocabulary already has a word for it, so it does not need to
    borrow `PASS`."""

    from ai_engineering import checkpoint

    (working / ".ai" / "claim.json").unlink()
    stage(working, "docs/notes.md", "notes\n")
    result = checkpoint.verify(working)

    assert {fact.id: fact.status for fact in result.checks}["claimed-paths"] == "SKIPPED"


def test_a_fresh_check_receipt_satisfies_the_third_and_a_stale_one_does_not(working):
    """The receipt has an age for a reason: a gate that ran last week over different code
    proves nothing about this checkpoint."""

    from datetime import UTC, datetime, timedelta

    from ai_engineering import checkpoint

    stage(working, "src/added.py", "VALUE = 2\n")
    receipts = working / ".ai" / "receipts"
    receipts.mkdir(parents=True)

    def write(when: datetime) -> None:
        (receipts / "gate.json").write_text(
            json.dumps(
                {
                    "schema": "urn:ai-engineering:check-evidence:1",
                    "schema_version": "1",
                    "kind": "automated",
                    "id": "gate",
                    "applicability": "applicable",
                    "command": "just check",
                    "tool_version": "just 1.58.0",
                    "input_digest": "sha256:" + "0" * 64,
                    "artifact_digest": "",
                    "started_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "finished_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "max_age_seconds": 86400,
                    "outcome": "PASS",
                }
            ),
            encoding="utf-8",
        )

    write(datetime.now(UTC))
    fresh = checkpoint.verify(working)
    assert {fact.id: fact.status for fact in fresh.checks}["checks-executed"] == "PASS"
    assert fresh.outcome == "PASS"

    write(datetime.now(UTC) - timedelta(days=3))
    stale = checkpoint.verify(working)
    assert {fact.id: fact.status for fact in stale.checks}["checks-executed"] == "INCOMPLETE"
    assert stale.outcome == "INCOMPLETE"


def test_a_failed_check_receipt_is_a_failure_and_not_an_absence(working):
    """A gate that ran and said no is the strongest evidence here, and reading it as
    "no receipt" would turn the clearest failure into the vaguest one."""

    from datetime import UTC, datetime

    from ai_engineering import checkpoint

    stage(working, "src/added.py", "VALUE = 2\n")
    receipts = working / ".ai" / "receipts"
    receipts.mkdir(parents=True)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    (receipts / "gate.json").write_text(
        json.dumps(
            {
                "schema": "urn:ai-engineering:check-evidence:1",
                "schema_version": "1",
                "kind": "automated",
                "id": "gate",
                "applicability": "applicable",
                "command": "just check",
                "tool_version": "just 1.58.0",
                "input_digest": "sha256:" + "0" * 64,
                "artifact_digest": "",
                "started_at": now,
                "finished_at": now,
                "max_age_seconds": 86400,
                "outcome": "FAIL",
            }
        ),
        encoding="utf-8",
    )

    result = checkpoint.verify(working)
    assert {fact.id: fact.status for fact in result.checks}["checks-executed"] == "FAIL"
    assert result.outcome == "FAIL"


def test_the_commit_hook_asks_for_the_receipts_only_while_a_claim_is_held():
    """Wired where a checkpoint is made, and gated on the claim.

    Every repository that has never coordinated commits as it always did: the third
    receipt is a gate somebody has to have run, and demanding it on every commit everywhere
    would put a wall between a person and their own working tree. The gate is the claim."""

    hook = (Path(__file__).resolve().parents[1] / "git-hooks" / "pre-commit").read_text(
        encoding="utf-8"
    )
    assert "spec checkpoint" in hook
    guarded = hook.split('if [ -f ".ai/claim.json" ]; then', 1)
    assert len(guarded) == 2, "the checkpoint runs unconditionally"
    assert "spec checkpoint" in guarded[1]


def test_a_failing_receipt_is_not_masked_by_a_passing_one_that_sorts_later(working):
    """The defect this fixture exists for, found by reading the loop rather than the name.

    `_executed` kept one receipt, assigned inside a loop over `sorted(...)`, so the winner
    was the alphabetically last fresh receipt while the variable holding it was called
    `freshest`. A FAIL from `adversarial-attacks.json` was therefore overwritten by a PASS
    from `local-command-python.json`, and the checkpoint reported that the checks had run and
    passed. Nothing in the output said otherwise, which is what makes it a false green rather
    than an ordering preference.

    Both names are real ones this repository writes, and the order is the real order: `a`
    before `l`. The worst fresh receipt decides now.
    """

    from ai_engineering import checkpoint

    folder = working / ".ai" / "receipts"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for name, said in (("adversarial-attacks", "FAIL"), ("local-command-python", "PASS")):
        (folder / f"{name}.json").write_text(
            json.dumps(
                {
                    "id": name,
                    "outcome": said,
                    "finished_at": stamp,
                    "max_age_seconds": 86400,
                }
            ),
            encoding="utf-8",
        )

    fact = checkpoint._executed(working)

    assert fact.status == "FAIL", fact
    assert fact.detail and "adversarial-attacks" in fact.detail


def test_the_snapshot_the_checkpoint_is_taken_against_changes_what_it_sees(working):
    """`EP-179` asks for the snapshot, freshness and final-combination correctness to be
    three separately checkable things. This is the first of the three, and it was the one
    nobody had checked.

    It is called `base` here rather than snapshot, which is why an audit grepping for the
    word found nothing: the parameter is threaded through `staged`, `_diff_args`, `_privacy`
    and `_inside`, so every receipt is computed relative to it. What none of the eight
    fixtures beside this one did was pass it. A parameter that decides which diff gets
    scanned and that nothing exercises is a parameter that can stop working silently — and
    the failure is the worst shape available: a checkpoint that scanned the wrong range and
    reported clean.

    So it is exercised both ways round. Committed work is invisible to a checkpoint taken
    against HEAD and visible to one taken against the commit before it, over the same tree.
    """
    from ai_engineering import checkpoint

    stage(working, "src/committed.py", "SECRET = 'not really'\n")
    git(working, "commit", "-m", "feat: a commit this branch made")
    behind = git(working, "rev-parse", "HEAD~1").stdout.strip()
    head = git(working, "rev-parse", "HEAD").stdout.strip()
    assert behind and head and behind != head

    # No snapshot: only what is staged right now, and nothing is.
    assert checkpoint.staged(working) == []

    # Against HEAD: the commit is behind the snapshot, so it is not this checkpoint's to
    # answer for. An empty answer here is correct and is exactly why the other direction
    # has to be asserted too — on its own this line would pass with `base` ignored.
    assert checkpoint.staged(working, head) == []

    # Against the commit before it: the file appears, by name.
    assert checkpoint.staged(working, behind) == ["src/committed.py"]


def test_a_snapshot_that_names_nothing_is_not_read_as_a_clean_range(working):
    """The fail-closed half. A base that no longer resolves — a rebased branch, a deleted
    ref, a truncated SHA pasted by hand — must not answer "nothing changed", because that is
    indistinguishable from a checkpoint over a branch that really changed nothing.

    What this holds is that the answer is empty *and* the receipts do not claim a pass on
    the strength of it. `git diff` against an unknown revision fails rather than returning
    a diff, so the range is unreadable and the checkpoint has no evidence either way.
    """
    from ai_engineering import checkpoint

    stage(working, "src/thing.py", "VALUE = 2\n")

    unresolvable = "0" * 40
    with pytest.raises(checkpoint.Unreadable) as refused:
        checkpoint.staged(working, unresolvable)
    assert "diff" in str(refused.value)

    # And the staged file is still there to be found, which is the proof that the refusal
    # above came from the unreadable range and not from an empty tree.
    assert checkpoint.staged(working) == ["src/thing.py"]


def test_a_checkpoint_over_a_base_that_does_not_exist_is_not_a_pass(working):
    """The receipts a git failure used to produce, and what they said.

    `_git` returned standard output and dropped the exit code, so an unreadable range gave
    an empty file list: claimed-paths reported PASS over zero files, staged-privacy reported
    SKIPPED because there was nothing to scan, and the aggregate treated SKIPPED as neither
    a failure nor an incompletion. A checkpoint whose git call broke published green.

    One command away from reachable: `ai-eng spec verify --base <ref that is not there>`.
    """
    from ai_engineering import checkpoint

    stage(working, "src/thing.py", "VALUE = 2\n")
    (working / ".ai").mkdir(exist_ok=True)
    (working / ".ai" / "claim.json").write_text(
        json.dumps({"item": "work-1", "paths": ["src"]}), encoding="utf-8"
    )

    answered = checkpoint.verify(working, base="0" * 40)

    assert answered.outcome != "PASS", answered.summary
    by_name = {fact.id: fact for fact in answered.checks}
    assert by_name["claimed-paths"].status == "INCOMPLETE", by_name["claimed-paths"]
    assert by_name["staged-privacy"].status == "INCOMPLETE", by_name["staged-privacy"]
    # The message names the call that failed, because "something went wrong" sends a reader
    # to the wrong file.
    assert "diff" in by_name["claimed-paths"].detail


def test_a_receipt_taken_before_the_staged_change_is_incomplete(working):
    """The one receipt in the tree bound to content, and what reading it changes.

    `ran.json` carries a digest over every tracked or about-to-be-tracked file, and the
    commit-msg hook already refuses to write a trailer when it does not match. `_executed`
    globbed the same directory and dropped it: no `finished_at`, `KeyError`, swallowed by the
    handler that skips a malformed receipt. So the one receipt that could say "this ran over
    exactly these bytes" was the one the checkpoint threw away, and what it kept instead was
    chosen by age — up to a week, in the receipts on disk today.
    """

    from ai_engineering import checkpoint, evidence

    receipts = working / ".ai" / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    stage(working, "src/thing.py", "VALUE = 2\n")

    matched = evidence.content_digest(working)
    (receipts / "ran.json").write_text(
        json.dumps({"suite": "quick:thing", "content": matched, "at": 0}), encoding="utf-8"
    )
    assert checkpoint._executed(working).status == "PASS"

    # One edit after the run, and the receipt is about other bytes.
    stage(working, "src/thing.py", "VALUE = 3\n")
    stale = checkpoint._executed(working)
    assert stale.status == "INCOMPLETE", stale
    assert stale.cure and "quick" in stale.cure

    # A digest receipt that is present and wrong outranks a fresh aged one that says PASS:
    # the aged one proves a run happened somewhere, and this one proves it was not here.
    (receipts / "local-command-python.json").write_text(
        json.dumps(
            {
                "id": "local-command-python",
                "outcome": "PASS",
                "finished_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "max_age_seconds": 604800,
            }
        ),
        encoding="utf-8",
    )
    assert checkpoint._executed(working).status == "INCOMPLETE"
