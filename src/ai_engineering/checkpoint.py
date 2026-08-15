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

from ai_engineering import acceptance_privacy, claim, outcome

RECEIPTS = Path(".ai") / "receipts"
MAX_STAGED_BYTES = 400_000


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60, check=False
    )
    return done.stdout


def staged(root: Path) -> list[str]:
    """The paths this checkpoint would publish, in git's own words."""

    return [name for name in _git(root, "diff", "--cached", "--name-only").splitlines() if name]


def _privacy(root: Path) -> outcome.Fact:
    """The staged content, not the working directory. A file that is lying around and was
    never added is not what a checkpoint publishes, and reading it instead is how a scan
    reports on something nobody was about to send."""

    # The added lines only, with git's own metadata dropped. A unified diff's header
    # carries `--- /dev/null` for every new file, and the machine-path scanner is right to
    # call that an absolute path — so scanning the whole diff reported on git's punctuation
    # rather than on anything a person wrote. Removals are not scanned either: a line being
    # deleted was already in history, and this receipt is about what is being published.
    added = [
        line[1:]
        for line in _git(root, "diff", "--cached", "--unified=0").splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    body = "\n".join(added)[:MAX_STAGED_BYTES]
    if not body.strip():
        return outcome.fact(
            "staged-privacy", "SKIPPED", "The staged content", "nothing is staged to scan"
        )
    for verdict in (
        acceptance_privacy.acceptance_machine_path_v1(body),
        acceptance_privacy.acceptance_pii_v1(body),
    ):
        if verdict.outcome != "PASS":
            return outcome.fact(
                "staged-privacy",
                "FAIL" if verdict.outcome == "FAIL" else "INCOMPLETE",
                "The staged content",
                f"{verdict.code}: {verdict.reason}",
                cure="unstage it and say the same thing without the value it carried",
            )
    return outcome.fact(
        "staged-privacy",
        "PASS",
        "The staged content",
        "no machine path and no personal datum in the staged diff",
    )


def _inside(root: Path) -> outcome.Fact:
    """The same rule the guard enforces on the write, enforced again on the diff — because
    a write that never went through the guard is exactly what this catches."""

    where = root / claim.IN_FORCE
    if not where.is_file():
        return outcome.fact(
            "claimed-paths",
            "SKIPPED",
            "The claim in force",
            "no claim is held here, so there is no scope to stay inside",
        )
    try:
        held = json.loads(where.read_text(encoding="utf-8"))
        claimed = [str(one).rstrip("/") for one in held["paths"]]
    except (OSError, ValueError, KeyError, TypeError):
        return outcome.fact(
            "claimed-paths",
            "INCOMPLETE",
            "The claim in force",
            f"{claim.IN_FORCE} exists and could not be read",
            cure="fix or remove the claim file, then check again",
        )

    outside = [
        name
        for name in staged(root)
        if not any(name == one or name.startswith(f"{one}/") for one in claimed)
    ]
    if outside:
        return outcome.fact(
            "claimed-paths",
            "FAIL",
            "The claim in force",
            f"{held.get('item', 'this claim')} does not cover: {', '.join(sorted(outside))}",
            cure="unstage them, or widen the claim and take it again",
        )
    return outcome.fact(
        "claimed-paths", "PASS", "The claim in force", f"every staged path is inside {claimed}"
    )


def _executed(root: Path, now: datetime | None = None) -> outcome.Fact:
    """Read, never assumed. A gate that ran last week over different code proves nothing
    about this checkpoint, so an expired receipt is the same answer as no receipt."""

    folder = root / RECEIPTS
    moment = now or datetime.now(UTC)
    freshest: tuple[str, str] | None = None
    for found in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            record = json.loads(found.read_text(encoding="utf-8"))
            finished = datetime.strptime(record["finished_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=UTC
            )
            age = (moment - finished).total_seconds()
            if age <= float(record.get("max_age_seconds", 0)):
                freshest = (str(record.get("outcome", "")), str(record.get("id", found.stem)))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    if freshest is None:
        return outcome.fact(
            "checks-executed",
            "INCOMPLETE",
            "The checks this diff affects",
            "no receipt from a check that ran recently enough to be about this code",
            cure="run the gate, and check again",
        )
    said, name = freshest
    if said != "PASS":
        return outcome.fact(
            "checks-executed",
            "FAIL",
            "The checks this diff affects",
            f"{name} ran and reported {said}",
            cure="fix what it found and run it again",
        )
    return outcome.fact(
        "checks-executed", "PASS", "The checks this diff affects", f"{name} ran and reported PASS"
    )


def verify(root: Path, now: datetime | None = None) -> outcome.Execution:
    """The three receipts, and the worst of them as the answer.

    FAIL outranks INCOMPLETE, and both outrank a pass: a checkpoint is published or it is
    not, and "two of three" is not a state anything downstream can act on.
    """

    facts = [_privacy(root), _inside(root), _executed(root, now)]
    said = {fact.status for fact in facts}
    word = "FAIL" if "FAIL" in said else "INCOMPLETE" if "INCOMPLETE" in said else "PASS"
    return outcome.execution(
        outcome.result(word),
        summary=f"{sum(fact.status == 'PASS' for fact in facts)} of 3 checkpoint receipts pass",
        checks=facts,
        remaining=[fact.detail for fact in facts if fact.status not in ("PASS", "SKIPPED")],
    )
