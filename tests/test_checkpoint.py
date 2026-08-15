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
