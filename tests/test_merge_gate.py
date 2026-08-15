"""What the merge gate can see, and where it has to read it from.

Specification 013: two disjoint claims integrate through the queue with no conflict, and
overlapping claims are blocked and visible at the merge gate rather than merged.

The gate cannot take the writer's word for what was claimed — the writer holds that file and
could have written anything in it. So it reads the claim from the remote, which is the one
copy both sides can see, and every case here runs against a real bare repository under the
test's own tmp_path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def git(where, *args) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(where), *args], capture_output=True, text=True, check=False
    )


@pytest.fixture
def shared(tmp_path):
    """One bare repository, two clones, one seeded main."""
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], capture_output=True)
    for name in ("one", "two"):
        work = tmp_path / name
        subprocess.run(["git", "init", "-b", "main", str(work)], capture_output=True)
        git(work, "config", "user.email", "suite@example.com")
        git(work, "config", "user.name", "suite")
        git(work, "remote", "add", "origin", str(bare))
    first = tmp_path / "one"
    # What `ai-eng init` writes, and the reason the claim file never reaches a branch: `.ai/`
    # is ignored except for the four files it names. Without this the fixture committed
    # `.ai/claim.json` and the gate was right to call it a path outside the claim.
    (first / ".ai").mkdir()
    (first / ".ai" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    for folder in ("alpha", "beta"):
        (first / folder).mkdir()
        (first / folder / "seed.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(first, "add", "-A")
    git(first, "commit", "-m", "chore: seed")
    git(first, "push", "origin", "main")
    second = tmp_path / "two"
    git(second, "fetch", "origin")
    git(second, "reset", "--hard", "origin/main")
    return bare


def branch(work: Path, name: str, relative: str, body: str) -> None:
    git(work, "checkout", "-b", name)
    where = work / relative
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(body, encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-m", f"feat: {name}")


def test_two_disjoint_claims_both_pass_the_gate(tmp_path, shared):
    """EP-038. Two writers, two work items, two sets of paths that do not touch — and
    nothing in the gate has an opinion about either of them."""

    from ai_engineering import checkpoint, claim

    one, two = tmp_path / "one", tmp_path / "two"
    base = claim.base(one)
    assert claim.take(one, "work-alpha", base, ["alpha/"], "writer-one").outcome == "PASS"
    assert claim.take(two, "work-beta", base, ["beta/"], "writer-two").outcome == "PASS"

    branch(one, "alpha-work", "alpha/added.py", "VALUE = 2\n")
    branch(two, "beta-work", "beta/added.py", "VALUE = 3\n")

    for work, item in ((one, "work-alpha"), (two, "work-beta")):
        result = checkpoint.verify(work, base=base, item=item)
        said = {fact.id: (fact.status, fact.detail) for fact in result.checks}
        assert said["claimed-paths"][0] == "PASS", (work.name, item, said["claimed-paths"])
        assert said["staged-privacy"][0] == "PASS", said["staged-privacy"]


def test_a_branch_that_wanders_outside_its_claim_is_blocked_at_the_gate(tmp_path, shared):
    """EP-039. The overlap is visible before the merge and named: the file that is outside,
    and the claim that does not cover it."""

    from ai_engineering import checkpoint, claim

    one, two = tmp_path / "one", tmp_path / "two"
    base = claim.base(one)
    assert claim.take(one, "work-alpha", base, ["alpha/"], "writer-one").outcome == "PASS"
    assert claim.take(two, "work-beta", base, ["beta/"], "writer-two").outcome == "PASS"

    # The second writer edits a file the first writer's claim holds.
    branch(two, "beta-work", "alpha/seed.py", "VALUE = 99\n")

    result = checkpoint.verify(two, base=base, item="work-beta")
    said = {fact.id: fact.detail for fact in result.checks}

    assert {fact.id: fact.status for fact in result.checks}["claimed-paths"] == "FAIL"
    assert "alpha/seed.py" in said["claimed-paths"]
    assert result.outcome == "FAIL"


def test_the_gate_reads_the_claim_from_the_remote_and_not_from_the_writer(tmp_path, shared):
    """The writer's own claim file is not evidence at the gate: it is a file on the machine
    being judged. Rewriting it to cover everything has to change nothing."""

    from ai_engineering import checkpoint, claim

    one, two = tmp_path / "one", tmp_path / "two"
    base = claim.base(one)
    assert claim.take(two, "work-beta", base, ["beta/"], "writer-two").outcome == "PASS"
    branch(two, "beta-work", "alpha/seed.py", "VALUE = 99\n")

    # The writer widens its own copy. The remote still holds what was actually claimed.
    (two / claim.IN_FORCE).write_text('{"item": "work-beta", "paths": ["."]}', encoding="utf-8")

    result = checkpoint.verify(two, base=base, item="work-beta")
    assert {fact.id: fact.status for fact in result.checks}["claimed-paths"] == "FAIL"


def test_a_branch_with_no_claim_on_the_remote_is_incomplete_and_not_a_pass(tmp_path, shared):
    """A work item nobody claimed has nothing to be checked against, and INCOMPLETE is the
    honest answer — reading it as "no violation found" would let an unclaimed branch through
    the one gate that exists to notice it."""

    from ai_engineering import checkpoint, claim

    two = tmp_path / "two"
    base = claim.base(two)
    branch(two, "beta-work", "beta/added.py", "VALUE = 3\n")

    result = checkpoint.verify(two, base=base, item="work-nobody-claimed")

    assert result.outcome == "INCOMPLETE"
    assert {fact.id: fact.status for fact in result.checks}["claimed-paths"] == "INCOMPLETE"
