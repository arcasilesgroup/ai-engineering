#!/usr/bin/env python3
"""Green now requires proof of work, not absence of failure.

The previous system's flagship gate came back green for ten days in a row without
running. Teaching this framework each tool's output format is exactly the router that
`just` exists to delete, so the contract moves to the interface: each repository prints
`RAN <name>=<n>` lines that it owns, and all this verifies is that they exist and are at
least one.

Usage: just check | tee check.log && python tests/anti_theatre.py check.log
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

RAN = re.compile(r"^RAN\s+([\w.-]+)=(\d+)\s*$", re.M)
PARTIAL = re.compile(r"^PARTIAL\s+([\w.-]+)=(\d+)\s*$", re.M)
# How stale the whole-tree run may be before a scoped one stops standing for it. Four days,
# not one: a nightly that fails to start on a Saturday must not block Monday's pull request,
# and a gap longer than a weekend is a gap somebody should be told about.
WHOLE_TREE_MAX_AGE_HOURS = 96
# Reading only the lines that are present cannot tell a gate that ran from a gate that
# was deleted: both print nothing about the missing one. Naming them is what closes it.
# The default is what `just check` owes. A job that runs a different gate passes its own
# names as the third argument — the mutation job runs in its own CI job, so its RAN line
# never reaches this log, and without a second call that whole gate could stop running
# with nothing to notice. One reader, one contract, called once per gate.
REQUIRED = ("lint", "tests", "suite")
# This check only ever runs on this repository — it is not in the wheel and does not reach
# a user's. So it covers the two manifests that can appear here, and no more.
MANIFESTS = {
    "pyproject.toml": ("uv.lock", "poetry.lock", "requirements.txt"),
    "package.json": ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb"),
}


def dependency_free(manifest: Path) -> bool:
    """A project that declares no dependencies has nothing to lock, and demanding a
    lockfile from it would teach people to commit an empty one."""
    text = manifest.read_text(errors="replace")
    if manifest.name == "pyproject.toml":
        import tomllib

        parsed = tomllib.loads(text)
        project = parsed.get("project", {})
        # dependency-groups is top level, not under project, and it is where uv puts dev
        # tools by default — missing it waives the modern layout while checking the old one.
        return not (
            project.get("dependencies")
            or project.get("optional-dependencies")
            or parsed.get("dependency-groups")
        )
    return False


def die(message: str) -> None:
    sys.stderr.write(f"anti-theatre: {message}\n")
    raise SystemExit(1)


def whole_tree_receipt(receipt: Path) -> str:
    """When a scoped run may stand for the whole tree, and for how long.

    A scoped mutation run prints `PARTIAL`, and this reader has always refused it, because
    one mutated file standing in for all of them is the theatre with extra steps. That rule
    was right and it made the gate impossible: measured on 2026-08-16, a whole-tree run is
    20,816 mutants and 121 minutes, against a job capped at 30. So it never finished, never
    printed a score, and died reported as `cancelled` on every commit for weeks.

    The split: the whole tree runs on a schedule and this receipt is what it leaves behind;
    the pull request runs over its own diff. `PARTIAL` is accepted only against a receipt
    naming a whole-tree run that actually completed inside the window — read from the
    server, not from the branch, because the branch is the thing being judged.

    It is deliberately not "and passed". The scheduled run reports the standing score and
    blocks nothing; requiring green here would mean requiring the whole backlog cleared
    before any pull request could merge, which is a different decision and not this one's
    to take. What this proves is that the whole tree is still being measured.
    """

    try:
        record = json.loads(receipt.read_text(errors="replace"))
    except (OSError, ValueError) as why:
        die(f"the whole-tree receipt is unreadable ({type(why).__name__}): PARTIAL proves nothing")
    # Status before timestamp, and the order is the finding. A run killed at its cap is what
    # this receipt will most often describe — the real lane did it on every commit for weeks —
    # and such a record carries a status and no completion time. Parsing first turned that
    # into "unreadable receipt", which is true about the bytes and wrong about the run.
    if record.get("status") != "completed":
        state = record.get("status")
        die(f"the whole-tree run is {state!r}: it never finished, so PARTIAL stands for nothing")
    try:
        finished = datetime.fromisoformat(str(record["completed_at"]).replace("Z", "+00:00"))
    except (ValueError, KeyError, TypeError) as why:
        die(f"the receipt names no time it finished ({type(why).__name__}): PARTIAL proves nothing")
    age = (datetime.now(UTC) - finished).total_seconds() / 3600
    if age > WHOLE_TREE_MAX_AGE_HOURS:
        die(
            f"the last whole-tree run finished {age:.0f}h ago, over the "
            f"{WHOLE_TREE_MAX_AGE_HOURS}h bound: a scoped run no longer stands for it"
        )
    return f"whole tree measured {age:.0f}h ago by {record.get('name', 'a scheduled run')}"


def main(
    log: Path, root: Path, required: tuple[str, ...] = REQUIRED, receipt: Path | None = None
) -> int:
    body = log.read_text(errors="replace")
    counts = {name: int(number) for name, number in RAN.findall(body)}
    if receipt is not None:
        note = whole_tree_receipt(receipt)
        for name, number in PARTIAL.findall(body):
            counts.setdefault(name, int(number))
        print(f"anti-theatre: PARTIAL accepted — {note}")
    if not counts:
        die("check printed no RAN lines. It did not prove it ran. The green is a lie.")
    for name, number in counts.items():
        if number < 1:
            die(f"RAN {name}={number}: it ran over zero items, which is not a pass.")
    absent = [name for name in required if name not in counts]
    if absent:
        die(f"nothing reported {', '.join(absent)}. A deleted gate prints no line at all.")

    shipped = (root / "src" / "ai_engineering" / "skeletons.py").read_text(errors="replace")
    for lie in ("RAN tests=0", "git ls-files | wc -l"):
        if lie in shipped:
            die(f"the justfile we hand a stranger prints {lie!r}: the theatre, as a template.")

    for manifest, lockfiles in MANIFESTS.items():
        for found in root.rglob(manifest):
            if any(part in {".git", "node_modules", ".venv"} for part in found.parts):
                continue
            if any((found.parent / lock).exists() for lock in lockfiles):
                continue
            if dependency_free(found):
                continue  # nothing to pin is not the same as nothing pinned
            die(
                f"{found}: there are dependencies and no lockfile, so the vulnerability "
                f"scan over it is silently empty."
            )

    print(
        f"anti-theatre: {len(counts)} RAN lines, all over at least one item — "
        f"{', '.join(f'{k}={v}' for k, v in sorted(counts.items()))}"
    )
    return 0


if __name__ == "__main__":
    names = tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 else REQUIRED
    proof = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else "."), names, proof))
