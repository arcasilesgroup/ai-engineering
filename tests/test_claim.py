"""The claim, and the two ways it is refused.

Specification 013's first obligations: fetch before claim, one task and one work item, and
a compare-and-swap against an exact base SHA where a stale SHA is a refusal that is never
repaired by a rebase and never retried in a loop.

Every case here runs against a real bare repository under the test's own tmp_path — git's
file transport, the same push and refusal semantics as any other remote, and nothing that
leaves this machine. What it cannot prove is the network transport, and the fixtures say so
rather than implying otherwise.
"""

from __future__ import annotations

import subprocess

import pytest


def git(where, *args) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(where), *args], capture_output=True, text=True, check=False
    )


@pytest.fixture
def remote(tmp_path):
    """One bare repository and two clones of it, each with a seeded main branch."""
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], capture_output=True)
    for name in ("one", "two"):
        work = tmp_path / name
        subprocess.run(["git", "init", "-b", "main", str(work)], capture_output=True)
        git(work, "config", "user.email", "suite@example.com")
        git(work, "config", "user.name", "suite")
        git(work, "remote", "add", "origin", str(bare))
    first = tmp_path / "one"
    (first / "seed.txt").write_text("seed\n", encoding="utf-8")
    git(first, "add", "-A")
    git(first, "commit", "-m", "chore: seed")
    git(first, "push", "origin", "main")
    git(tmp_path / "two", "fetch", "origin")
    git(tmp_path / "two", "reset", "--hard", "origin/main")
    return bare


def test_exactly_one_of_two_writers_wins_the_same_work_item(tmp_path, remote):
    """EP-036. Two writers, one work item, one winner and one refusal receipt.

    The losing writer is refused by the remote and not by a check on our side, which is the
    only version of this that holds when the two are on different machines. It is not
    retried and it is not rebased: the refusal is the answer."""

    from ai_engineering import claim

    one, two = tmp_path / "one", tmp_path / "two"
    base = claim.base(one)
    assert base and base == claim.base(two)

    outcomes = [
        claim.take(where, "work-42", base, ["src/thing.py"], role)
        for where, role in ((one, "writer-one"), (two, "writer-two"))
    ]
    words = sorted(result.outcome for result in outcomes)

    assert words == ["INCOMPLETE", "PASS"], words
    lost = next(result for result in outcomes if result.outcome == "INCOMPLETE")
    assert lost.error is not None and lost.error.code == "CLAIM_LOST"
    assert "retry" not in (lost.error.cure or ""), "a lost race must not be retried"

    listed = git(one, "ls-remote", "origin", claim.REF.format(item="work-42")).stdout
    won = next(result for result in outcomes if result.outcome == "PASS")
    held = next(fact.detail for fact in won.checks if fact.id == "claim-object")
    assert listed.startswith(held), "the remote holds an object the winner does not name"


def test_a_stale_base_is_refused_and_never_rebased(tmp_path, remote):
    """EP-031's compare-and-swap half. The claim carries the exact base it fetched, and a
    base that has moved is a refusal — not a rebase, not a retry, not a warning."""

    from ai_engineering import claim

    one, two = tmp_path / "one", tmp_path / "two"
    stale = claim.base(two)

    (one / "moved.txt").write_text("moved\n", encoding="utf-8")
    git(one, "add", "-A")
    git(one, "commit", "-m", "feat: move main on")
    git(one, "push", "origin", "main")

    result = claim.take(two, "work-43", stale, ["src/thing.py"], "writer-two")

    assert result.outcome == "INCOMPLETE"
    assert result.error is not None and result.error.code == "CLAIM_BASE_STALE"
    assert not git(two, "ls-remote", "origin", claim.REF.format(item="work-43")).stdout.strip()
    # The refusal is the answer, so the working tree is where it was: no rebase happened.
    assert git(two, "rev-parse", "HEAD").stdout.strip() == stale


def test_a_claim_record_carrying_a_machine_path_never_reaches_the_remote(tmp_path, remote):
    """EP-193. No coordination record carries an absolute path, a hostname or a person.

    The scanners are the ones `accept` and `report issue` already use, and the refusal
    happens before the push rather than after it — a record that reached the remote and was
    then judged has already been published to everyone who can fetch."""

    from ai_engineering import claim

    two = tmp_path / "two"
    base = claim.base(two)

    result = claim.take(two, "work-44", base, ["/Users/somebody/repo/src/thing.py"], "writer-two")

    assert result.outcome == "INCOMPLETE"
    assert result.error is not None and result.error.code == "CLAIM_RECORD_REFUSED"
    assert not git(two, "ls-remote", "origin", claim.REF.format(item="work-44")).stdout.strip()


def test_a_winning_claim_leaves_the_file_the_guard_reads_and_a_losing_one_does_not(
    tmp_path, remote
):
    """The two halves have to agree. `claim_scope_guard` denies a write outside the claim
    in force, and it reads that from `.ai/claim.json` — so the writer who lost the race must
    not be left holding a file that says it owns the work."""

    from ai_engineering import claim

    one, two = tmp_path / "one", tmp_path / "two"
    base = claim.base(one)
    first = claim.take(one, "work-46", base, ["src/thing.py"], "writer-one")
    second = claim.take(two, "work-46", base, ["src/thing.py"], "writer-two")

    assert first.outcome == "PASS" and second.outcome == "INCOMPLETE"
    assert (one / claim.IN_FORCE).is_file()
    assert not (two / claim.IN_FORCE).exists(), "the loser was left believing it holds the work"

    import json

    held = json.loads((one / claim.IN_FORCE).read_text(encoding="utf-8"))
    assert held["paths"] == ["src/thing.py"] and held["item"] == "work-46"


def test_the_claim_object_carries_our_identity_and_not_the_machine_s(tmp_path, remote):
    """A commit takes its author from whoever is sitting there. A coordination record that
    carries a person's name and address has published a person, so the claim object is
    written with an identity that belongs to this framework."""

    from ai_engineering import claim

    two = tmp_path / "two"
    base = claim.base(two)
    result = claim.take(two, "work-45", base, ["src/thing.py"], "writer-two")
    assert result.outcome == "PASS"

    held = git(two, "ls-remote", "origin", claim.REF.format(item="work-45")).stdout.split()[0]
    author = git(two, "show", "-s", "--format=%an <%ae>%n%B", held).stdout
    assert "suite@example.com" not in author
    assert "ai-engineering" in author
    assert "work-45" in author and base in author


def test_every_refusal_a_claim_can_give_says_its_own_code_sentence_and_cure(tmp_path, remote):
    """Eighty-four mutants lived in the function that decides who holds a work item.

    Five refusals, in a fixed order, and the order is the design: the record is scanned before
    anything is built, the base is read before anything is pushed, and the race is settled by
    the remote rather than by us. Each leaves the remote untouched, and each tells a different
    person to do a different thing — read the new base, take a different task, check the
    remote is reachable. The fixtures had asserted the codes and never the sentences or the
    cures, so a writer who lost a race could have been told to check their disk.
    """
    from ai_engineering import claim

    one, two = tmp_path / "one", tmp_path / "two"
    good = claim.base(one)
    assert good

    # A record carrying a machine path never reaches the remote, and the cure says how to say
    # the same thing without it.
    refused = claim.take(one, "work-90", good, [str(tmp_path / "somewhere" / "thing.py")], "one")
    assert refused.result.outcome == "INCOMPLETE"
    assert refused.error.code == "CLAIM_RECORD_REFUSED"
    assert refused.error.message.startswith("the claim record was refused before it was published")
    assert refused.error.cure == (
        "say the same thing with repository-relative paths and no personal data"
    )
    assert refused.error.retryable is False

    # A base that has moved names both, shortened, so the reader can see which is which.
    (one / "moved.txt").write_text("moved\n", encoding="utf-8")
    git(one, "add", "-A")
    git(one, "commit", "-m", "feat: move the base on")
    git(one, "push", "origin", "main")
    stale = claim.take(two, "work-91", good, ["src/thing.py"], "two")
    assert stale.error.code == "CLAIM_BASE_STALE"
    assert good[:12] in stale.error.message
    assert stale.error.cure == "read the new base, decide again against it, and claim once"

    # And the race, which git answers rather than we do. The loser is told to take another
    # task, not to retry — a retry here is two writers taking turns at the same work.
    fresh = claim.base(one)
    assert fresh and fresh != good
    won = claim.take(one, "work-92", fresh, ["src/thing.py"], "one")
    assert won.result.outcome == "PASS"
    lost = claim.take(two, "work-92", fresh, ["src/other.py"], "two")
    assert lost.error.code == "CLAIM_LOST"
    assert "another writer holds work-92" in lost.error.message
    assert lost.error.cure == "read who holds it, and take a different task"
    assert "retry" not in lost.error.cure


def test_an_unreachable_remote_is_its_own_refusal_and_not_a_stale_base(tmp_path, remote):
    """Two failures that look alike from a distance and are not: a base that moved is somebody
    else's work landing, and a remote that cannot be read is a network or a permission. Telling
    the second person to "read the new base" sends them looking for a change that is not
    there."""
    from ai_engineering import claim

    one = tmp_path / "one"
    good = claim.base(one)
    git(one, "remote", "set-url", "origin", str(tmp_path / "no-such-remote.git"))

    refused = claim.take(one, "work-93", good, ["src/thing.py"], "one")
    assert refused.error.code == "CLAIM_BASE_UNAVAILABLE"
    assert "could not be read, so there is no base to claim against" in refused.error.message
    assert refused.error.cure == "check the remote is reachable and rerun"


def test_the_claim_the_guard_reads_appears_only_after_the_remote_agreed(tmp_path, remote):
    """The order that settles a race, asserted from the loser's side.

    A local claim file written before the push would let a writer who lost carry on believing
    it holds the work — which is exactly the disagreement the remote exists to settle. So the
    winner has the file and the loser has none, and the winner's summary counts the paths it
    actually claimed rather than saying "some".
    """
    from ai_engineering import claim

    one, two = tmp_path / "one", tmp_path / "two"
    shared = claim.base(one)

    won = claim.take(one, "work-94", shared, ["src/a.py", "src/b.py"], "one")
    lost = claim.take(two, "work-94", shared, ["src/c.py"], "two")

    assert won.result.outcome == "PASS"
    assert won.summary == f"work-94 is claimed at {shared[:12]} for 2 path(s)"
    assert (one / claim.IN_FORCE).is_file()

    assert lost.result.outcome == "INCOMPLETE"
    assert not (two / claim.IN_FORCE).exists(), "the writer that lost the race kept a claim file"
