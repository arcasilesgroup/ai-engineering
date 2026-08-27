"""What has to be true before a checkpoint is published, and which of it is not.

Three receipts, and a checkpoint missing any of them cannot be claimed or published: the
staged content scanned, the diff proved to stay inside the claim, and the checks the diff
affects executed. The first two are produced here. The third is read: a check nobody ran is
INCOMPLETE, and this module has no way to make that a pass.

Secrets are the one scan not repeated here. `git-hooks/pre-commit` runs gitleaks over the
staged hunks before this is reached, at its pinned version, and a second opinion from the
same scanner would be a second place for it to be missing from.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from ai_engineering import acceptance_privacy, claim, dag, evidence, outcome

STAGED_ROW = "The staged content"
CLAIM_ROW = "The claim in force"
CHECKS_ROW = "The checks this diff affects"
ORDER_ROW = "The order the claims run in"

RECEIPTS = Path(".ai") / "receipts"
MAX_STAGED_BYTES = 400_000


class Unreadable(outcome.Unreadable):
    """Git was asked something and did not answer it."""


def _git(root: Path, *args: str) -> str:
    """Standard output, or a refusal. Never an empty string standing in for both.

    It used to drop the exit code and return `done.stdout`, which for a failed call is the
    empty string — so `staged` answered "nothing changed", `_compare` found nothing outside
    the claim and reported PASS over zero files, `_privacy` had nothing to scan and reported
    SKIPPED, and `verify` treats SKIPPED as neither a failure nor an incompletion. A
    checkpoint published green because git broke. `ai-eng spec verify --base <ref that is
    not there>` is the whole reproduction."""

    done = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60, check=False
    )
    if done.returncode:
        said = done.stderr.strip().splitlines()
        raise Unreadable(
            f"git {' '.join(args)} exited {done.returncode}" + (f": {said[0]}" if said else "")
        )
    return done.stdout


def staged(root: Path, base: str = "") -> list[str]:
    """The paths this checkpoint would publish, in git's own words.

    Staged, or — at the merge gate, where nothing is staged and the commits already exist —
    everything this branch changed since it left `base`."""

    args = ["diff", "--cached", "--name-only"]
    if base:
        args = ["diff", "--name-only", f"{base}...HEAD"]
    return [name for name in _git(root, *args).splitlines() if name]


def _privacy(root: Path, base: str = "") -> outcome.Fact:
    """The staged content, not the working directory. A file that is lying around and was
    never added is not what a checkpoint publishes, and reading it instead is how a scan
    reports on something nobody was about to send."""

    # The added lines only, with git's own metadata dropped. A unified diff's header
    # carries `--- /dev/null` for every new file, and the machine-path scanner is right to
    # call that an absolute path — so scanning the whole diff reported on git's punctuation
    # rather than on anything a person wrote. Removals are not scanned either: a line being
    # deleted was already in history, and this receipt is about what is being published.
    try:
        diff = _git(root, *_diff_args(base))
    except Unreadable as refused:
        return outcome.fact(
            "staged-privacy",
            "INCOMPLETE",
            STAGED_ROW,
            str(refused),
            cure="give a base this repository has, then check again",
        )
    added = [
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    body = "\n".join(added)[:MAX_STAGED_BYTES]
    if not body.strip():
        return outcome.fact("staged-privacy", "SKIPPED", STAGED_ROW, "nothing is staged to scan")
    for verdict in (
        acceptance_privacy.acceptance_machine_path_v1(body),
        acceptance_privacy.acceptance_pii_v1(body),
    ):
        if verdict.outcome != "PASS":
            return outcome.fact(
                "staged-privacy",
                "FAIL" if verdict.outcome == "FAIL" else "INCOMPLETE",
                STAGED_ROW,
                f"{verdict.code}: {verdict.reason}",
                cure="unstage it and say the same thing without the value it carried",
            )
    return outcome.fact(
        "staged-privacy",
        "PASS",
        STAGED_ROW,
        "no machine path and no personal datum in the staged diff",
    )


def _diff_args(base: str) -> list[str]:
    if base:
        return ["diff", "--unified=0", f"{base}...HEAD"]
    return ["diff", "--cached", "--unified=0"]


def _inside(root: Path, base: str = "", claimed: list[str] | None = None) -> outcome.Fact:
    """The same rule the guard enforces on the write, enforced again on the diff — because
    a write that never went through the guard is exactly what this catches."""

    if claimed is not None:
        return _compare(root, base, claimed, "the claim held on the remote")

    where = root / claim.IN_FORCE
    if not where.is_file():
        return outcome.fact(
            "claimed-paths",
            "SKIPPED",
            CLAIM_ROW,
            "no claim is held here, so there is no scope to stay inside",
        )
    try:
        held = json.loads(where.read_text(encoding="utf-8"))
        claimed = [str(one) for one in held["paths"]]
    except (OSError, ValueError, KeyError, TypeError):
        return outcome.fact(
            "claimed-paths",
            "INCOMPLETE",
            CLAIM_ROW,
            f"{claim.IN_FORCE} exists and could not be read",
            cure="fix or remove the claim file, then check again",
        )

    return _compare(root, base, claimed, str(held.get("item", "this claim")))


def _compare(root: Path, base: str, claimed: list[str], named: str) -> outcome.Fact:
    # Normalised here and not at each caller. The local claim file was stripped of its
    # trailing slash and the one read from the remote was not, so `alpha/` became `alpha//`
    # and every path inside the claim read as outside it — a gate that failed the writer who
    # had done exactly what they claimed.
    claimed = [str(one).rstrip("/") for one in claimed]
    try:
        changed = staged(root, base)
    except Unreadable as refused:
        return outcome.fact(
            "claimed-paths",
            "INCOMPLETE",
            CLAIM_ROW,
            str(refused),
            cure="give a base this repository has, then check again",
        )
    outside = [
        name
        for name in changed
        if not any(name == one or name.startswith(f"{one}/") for one in claimed)
    ]
    if outside:
        return outcome.fact(
            "claimed-paths",
            "FAIL",
            CLAIM_ROW,
            f"{named} does not cover: {', '.join(sorted(outside))}",
            cure="unstage them, or widen the claim and take it again",
        )
    return outcome.fact(
        "claimed-paths", "PASS", CLAIM_ROW, f"every changed path is inside {claimed}"
    )


def _bound_to_this_tree(root: Path, folder: Path) -> outcome.Fact | None:
    """The receipt that names the bytes it ran over, when there is one.

    Everything else in this directory is chosen by age, and age is the weakest possible
    reading: the windows on disk go up to a week, so a passing gate over entirely different
    code publishes today's checkpoint. `ran.json` is the exception — `evidence.content_digest`
    hashes every tracked and about-to-be-tracked file, and the commit-msg hook already refuses
    a trailer when it does not match. `_executed` used to drop it, because it has no
    `finished_at` and the handler that skips a malformed receipt swallowed the `KeyError`.

    Preferred when present, and only then: a rule that refused every aged receipt would leave
    a fresh clone permanently incomplete, because `.ai/receipts/` is not committed. And
    preferred only over the aged receipts that PASSED — the first version of this returned
    before the caller's failure scan, so a matching digest answered PASS over a fresh receipt
    reporting FAIL, which is the shape the paragraph below was written to deny.

    It carries no outcome field, so presence means the suite passed — the writer records it
    after a green run and nowhere else. That is why this returns PASS or INCOMPLETE and never
    FAIL: a failure leaves no receipt at all, and the aged reading is what catches that.
    """

    found = folder / "ran.json"
    try:
        record = json.loads(found.read_text(encoding="utf-8"))
        recorded, suite = str(record["content"]), str(record.get("suite", "a suite"))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    try:
        measured = evidence.content_digest(root)
    except (OSError, ValueError, subprocess.SubprocessError) as refused:
        # Not None. Dropping through to the aged reading is how a repository whose git is
        # broken reads PASS off a week-old receipt, which is the fail-open this lane exists
        # to replace and the one `_git` above already refuses twice.
        return outcome.fact(
            "checks-executed",
            "INCOMPLETE",
            CHECKS_ROW,
            f"the receipt names bytes and this tree could not be read: {refused}",
            cure="check the repository is readable, then check again",
        )
    if recorded == measured:
        return outcome.fact(
            "checks-executed",
            "PASS",
            CHECKS_ROW,
            f"{suite} ran over exactly these bytes",
        )
    return outcome.fact(
        "checks-executed",
        "INCOMPLETE",
        CHECKS_ROW,
        f"{suite} ran over {recorded[:12]} and this tree is {measured[:12]}",
        cure=f"run `just {suite.replace(':', ' ')}` again, then check again",
    )


def _executed(root: Path, now: datetime | None = None) -> outcome.Fact:
    """Read, never assumed. A gate that ran last week over different code proves nothing
    about this checkpoint, so an expired receipt is the same answer as no receipt."""

    folder = root / RECEIPTS
    moment = now or datetime.now(UTC)
    # Every fresh receipt, and the worst of them decides. It used to keep one — assigned in a
    # loop over `sorted(...)`, so the winner was the alphabetically last fresh receipt while
    # the variable holding it was called `freshest`. With `adversarial-attacks.json` reporting
    # FAIL and `local-command-python.json` reporting PASS, this returned PASS: a failing check
    # masked by a passing one whose filename sorts later. Nothing about that is visible in the
    # output, which is what makes it the shape this product exists to refuse rather than an
    # ordering preference.
    fresh: list[tuple[str, str]] = []
    for found in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            record = json.loads(found.read_text(encoding="utf-8"))
            finished = datetime.strptime(record["finished_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=UTC
            )
            age = (moment - finished).total_seconds()
            if age <= float(record.get("max_age_seconds", 0)):
                fresh.append((str(record.get("outcome", "")), str(record.get("id", found.stem))))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    failed = [row for row in fresh if row[0] != "PASS"]
    # After the failure scan and not before it. A receipt bound to these bytes is the better
    # evidence that something ran over this code; it is not evidence that nothing else
    # reported a failure over the same code, and the first version of this returned above the
    # scan and published PASS across a fresh FAIL.
    bound = _bound_to_this_tree(root, folder)
    if bound is not None and not failed:
        return bound
    freshest = failed[0] if failed else (fresh[0] if fresh else None)
    if freshest is None:
        return outcome.fact(
            "checks-executed",
            "INCOMPLETE",
            CHECKS_ROW,
            "no receipt from a check that ran recently enough to be about this code",
            cure="run the gate, and check again",
        )
    said, name = freshest
    if said != "PASS":
        return outcome.fact(
            "checks-executed",
            "FAIL",
            CHECKS_ROW,
            f"{name} ran and reported {said}",
            cure="fix what it found and run it again",
        )
    return outcome.fact("checks-executed", "PASS", CHECKS_ROW, f"{name} ran and reported PASS")


def _ordered(root: Path, remote: str) -> outcome.Fact:
    """The order every claim on the remote runs in, derived where somebody reads it.

    `dag` was written for P3, proven deterministic against fixtures, and imported by nothing
    outside its own test file — so the module was correct and no gate had ever run it. A
    contract nothing executes is the shape this repository exists to refuse, and it had
    grown one of its own.

    It is OBSERVED and never a pass: an order is a fact about what can run beside what, not
    a verdict on this branch. What it can be is INCOMPLETE — a cycle, or a file whose
    imports cannot be read — and that is a real refusal, because an order nobody can derive
    is one two writers would each invent differently.
    """

    try:
        tasks = claim.every(root, remote)
    except (OSError, ValueError, subprocess.SubprocessError):
        return outcome.fact(
            "claim-order",
            "INCOMPLETE",
            ORDER_ROW,
            f"the claims on {remote} could not be listed",
            cure="check the remote is reachable, then derive the order again",
        )
    if not tasks:
        return outcome.fact(
            "claim-order",
            "SKIPPED",
            ORDER_ROW,
            f"no claim is held on {remote}, so there is no order to derive",
        )
    derived = dag.order(root, tasks)
    if derived.outcome != "PASS":
        return outcome.fact(
            "claim-order",
            "INCOMPLETE",
            ORDER_ROW,
            derived.summary,
            cure="break the cycle, or exclude the file whose imports cannot be read",
        )
    return outcome.fact(
        "claim-order",
        "OBSERVED",
        ORDER_ROW,
        ", ".join(dag.sequence(derived)),
    )


def verify(
    root: Path,
    now: datetime | None = None,
    base: str = "",
    item: str = "",
    remote: str = "origin",
) -> outcome.Execution:
    """The three receipts, and the worst of them as the answer.

    FAIL outranks INCOMPLETE, and both outrank a pass: a checkpoint is published or it is
    not, and "two of three" is not a state anything downstream can act on.
    """

    # At the merge gate the claim cannot come from the machine being judged: the writer
    # holds that file and could have written anything in it. `item` says to read the claim
    # from the remote instead, which is the one copy both sides can see.
    claimed = claim.held(root, item, remote) if item else None
    if item and claimed is None:
        return outcome.execution(
            outcome.result("INCOMPLETE"),
            summary=f"no claim for {item} is held on {remote}; there is nothing to check against",
            checks=[
                outcome.fact(
                    "claimed-paths",
                    "INCOMPLETE",
                    "The claim on the remote",
                    f"{item} is not claimed on {remote}",
                    cure="claim it before pushing, or check without --item",
                )
            ],
        )
    facts = [
        _privacy(root, base),
        _inside(root, base, claimed),
        _executed(root, now),
        _ordered(root, remote),
    ]
    said = {fact.status for fact in facts}
    word = "FAIL" if "FAIL" in said else "INCOMPLETE" if "INCOMPLETE" in said else "PASS"
    passed = sum(fact.status == "PASS" for fact in facts)
    return outcome.execution(
        outcome.result(word),
        summary=f"{passed} of {len(facts)} checkpoint receipts pass",
        checks=facts,
        remaining=[
            fact.detail for fact in facts if fact.detail and fact.status not in ("PASS", "SKIPPED")
        ],
    )
