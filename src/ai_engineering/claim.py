"""One task, one work item, one writer — decided by the remote and not by us.

Two agents on two machines cannot agree about who owns a task by asking each other. The
only thing both can see is the remote, so the claim is a ref that must not already exist,
and the loser is refused by git's own fast-forward rule rather than by a check either side
could skip.

A stale base is a refusal. It is never repaired by a rebase and never retried in a loop:
a claim names the exact commit it was reasoning about, and if that commit is no longer what
the branch is, the reasoning is out of date and so is the claim.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

from ai_engineering import acceptance_privacy, outcome

REF = "refs/ai-eng/claims/{item}"
# Where the guard on this machine reads what is claimed. Under `.ai/`, which is disposable
# and gitignored: a claim is state about one worktree and belongs in nobody's diff.
IN_FORCE = Path(".ai") / "claim.json"
TIMEOUT_SECONDS = 60

# A commit takes its author from whoever is sitting at the machine. A coordination record
# that carries a person's name and address has published a person to everyone who can
# fetch, so the claim object is written with an identity that belongs to this framework and
# to nobody. `.invalid` is reserved by RFC 2606 and can never be delivered to.
IDENTITY = {
    "GIT_AUTHOR_NAME": "ai-engineering",
    "GIT_AUTHOR_EMAIL": "claims@ai-engineering.invalid",
    "GIT_COMMITTER_NAME": "ai-engineering",
    "GIT_COMMITTER_EMAIL": "claims@ai-engineering.invalid",
}


def _git(root: Path, *args: str, identity: bool = False) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, **(IDENTITY if identity else {})}
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
        env=environment,
    )


def base(root: Path, remote: str = "origin", branch: str = "main") -> str:
    """Fetch, then the exact SHA a claim will name. Fetch first, always: a base read out of
    a stale clone is a base that was true this morning."""

    _git(root, "fetch", remote, branch)
    found = _git(root, "rev-parse", f"{remote}/{branch}")
    return found.stdout.strip() if found.returncode == 0 else ""


def record(item: str, base_sha: str, paths: list[str], role: str, claimant: str) -> str:
    """The claim, as the message of the object the ref points at.

    Closed on purpose: a work item, the base it was taken against, the paths it may write,
    the role, and one opaque claimant. No prompt, no reasoning, no client, no user, no
    hostname, no absolute path, no provider payload — and the two scanners below are what
    stops the last three arriving inside one of these fields anyway.
    """

    lines = [
        f"claim {item}",
        "",
        f"base {base_sha}",
        f"role {role}",
        f"claimant {claimant}",
        *(f"path {one}" for one in paths),
    ]
    return "\n".join(lines) + "\n"


def held(root: Path, item: str, remote: str = "origin") -> list[str] | None:
    """The paths a claim holds, read from the remote rather than from this machine.

    The merge gate is the one reader that cannot be told what was claimed by the writer it
    is judging. `ls-remote` for the ref, `fetch` for the object, and the message is the
    record — which is why the record is the message and not a file in the branch.
    """

    reference = REF.format(item=item)
    listed = _git(root, "ls-remote", remote, reference).stdout.split()
    if not listed:
        return None
    _git(root, "fetch", remote, f"{reference}:{reference}")
    body = _git(root, "show", "-s", "--format=%B", listed[0]).stdout
    if not body.strip():
        return None
    return [line[len("path ") :] for line in body.splitlines() if line.startswith("path ")]


def every(root: Path, remote: str = "origin") -> list[dict]:
    """Every claim the remote holds, as the shape `dag.order` reads.

    `held` answers about one work item because the merge gate judges one branch. An order is
    a fact about all of them at once, and there was no way to ask for all of them — which is
    why `dag` had no caller anywhere in the product and its determinism was proven against
    fixtures only. One `ls-remote` over the whole namespace, then the record of each.

    A claim whose object cannot be read is skipped rather than fatal: a reader that dies on
    one unreadable ref reports nothing about the others, and the order it would have derived
    is the one thing worth having here.
    """

    prefix = REF.format(item="")
    listed = _git(root, "ls-remote", remote, f"{prefix}*").stdout.splitlines()
    tasks: list[dict] = []
    for line in listed:
        parts = line.split()
        if len(parts) != 2 or not parts[1].startswith(prefix):
            continue
        item = parts[1][len(prefix) :]
        paths = held(root, item, remote)
        if paths:
            tasks.append({"item": item, "paths": paths})
    return sorted(tasks, key=lambda one: one["item"])


def _refused(code: str, message: str, cure: str) -> outcome.Execution:
    return outcome.execution(
        outcome.result("INCOMPLETE"),
        summary=message,
        execution_error=outcome.error(code, message, False, cure),
    )


def take(
    root: Path,
    item: str,
    expected_base: str,
    paths: list[str],
    role: str,
    remote: str = "origin",
) -> outcome.Execution:
    """Claim one work item against one exact base, or be refused.

    Three refusals, in this order, and each one leaves the remote untouched: the record
    carries something no coordination record may carry; the base has moved; another writer
    already holds the ref. The third is git's answer rather than ours, which is the only
    version of it that holds when the two writers are on different machines.
    """

    claimant = uuid.uuid4().hex
    body = record(item, expected_base, paths, role, claimant)
    for verdict in (
        acceptance_privacy.acceptance_machine_path_v1(body),
        acceptance_privacy.acceptance_pii_v1(body),
    ):
        if verdict.outcome != "PASS":
            return _refused(
                "CLAIM_RECORD_REFUSED",
                f"the claim record was refused before it was published: {verdict.reason}",
                "say the same thing with repository-relative paths and no personal data",
            )

    current = base(root, remote)
    if not current:
        return _refused(
            "CLAIM_BASE_UNAVAILABLE",
            f"{remote} could not be read, so there is no base to claim against",
            "check the remote is reachable and rerun",
        )
    if current != expected_base:
        return _refused(
            "CLAIM_BASE_STALE",
            f"the claim names {expected_base[:12]} and the branch is at {current[:12]}",
            "read the new base, decide again against it, and claim once",
        )

    tree = _git(root, "rev-parse", f"{expected_base}^{{tree}}").stdout.strip()
    built = _git(root, "commit-tree", tree, "-p", expected_base, "-m", body, identity=True)
    if built.returncode != 0 or not built.stdout.strip():
        return _refused(
            "CLAIM_OBJECT_UNAVAILABLE",
            "the claim object could not be written locally",
            "check the repository is not read-only and rerun",
        )
    object_id = built.stdout.strip()

    reference = REF.format(item=item)
    pushed = _git(root, "push", remote, f"{object_id}:{reference}")
    if pushed.returncode != 0:
        return _refused(
            "CLAIM_LOST",
            f"another writer holds {item}; the remote refused this claim",
            "read who holds it, and take a different task",
        )

    # The guard reads this, and it is written only after the remote agreed. A claim file
    # that appeared before the push would let a writer who lost the race carry on believing
    # it holds the work — which is the disagreement the remote exists to settle.
    local = root / IN_FORCE
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(
        json.dumps({"item": item, "base": expected_base, "role": role, "paths": list(paths)}),
        encoding="utf-8",
    )

    return outcome.execution(
        outcome.result("PASS"),
        summary=f"{item} is claimed at {expected_base[:12]} for {len(paths)} path(s)",
        changes=[
            outcome.fact("claim-ref", "APPLIED", "Claimed on the remote", reference),
            outcome.fact("claim-local", "APPLIED", "The claim the guard reads", str(IN_FORCE)),
        ],
        checks=[
            outcome.fact("claim-object", "OBSERVED", "The claim object", object_id),
            outcome.fact("claim-base", "OBSERVED", "The base it was taken against", expected_base),
            outcome.fact("claim-role", "OBSERVED", "The writer role", role),
        ],
        remaining=["One writer holds this item. Nothing outside its paths may be written."],
    )
