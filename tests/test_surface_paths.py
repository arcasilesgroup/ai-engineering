"""A path named where no test can execute it, checked as a string.

Three times now this repository has deleted a file and left something naming it. Twice the
namer was a GitHub workflow, which no local suite can run: `install-matrix.yml` needs a built
wheel on three operating systems, so the only thing a machine here can do with it is read it.
The third time it shipped — the commit that deleted `change_scope_guard.py` for blocking three
times against 670 bypasses left `install-matrix.yml` asserting that same file was present in
the wheel, on all three runners, with a green local gate and no `|| true` to soften it.

That is `docs/adr/0014`'s defect class, in the one place the suite is structurally blind: a
claim one file makes about another with no comparator that executes. And it is rule 12 at the
third occurrence, so it stops being a thing to remember and becomes an exit code.

The comparator cannot read intent, and it does not try. A surface may name a deleted file for
exactly one honest reason — to assert it is gone — and both real instances here do. So the
rule is not "never name a missing path"; it is "a missing path is named on purpose, and the
purpose is written down". Deleting a file reds this until somebody either repairs the
reference or says in one line why the name outlives the file. That sentence is the
conversation the guard cut never had.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Everything that names a path and that `pytest` cannot execute: CI, the task runner, the git
# hooks. `src/` and `tests/` are deliberately absent — a bad path there is an ImportError or a
# failing test, which is a comparator that already runs.
SURFACES = (
    "justfile",
    ".github/workflows/check.yml",
    ".github/workflows/install-matrix.yml",
    ".github/workflows/release.yml",
    "git-hooks/pre-commit",
    "git-hooks/commit-msg",
    "git-hooks/pre-push",
)

# Anything shaped like a path into one of this repository's own homes. Deliberately not a
# general URL or filename matcher: a token that does not start at a directory we own is
# somebody else's, and guessing about it is how a check earns a reputation for noise.
NAMED = re.compile(
    r"(?<![\w/.-])((?:hooks|src|tests|policy|surfaces|git-hooks|migrations|docs|specs|\.agents)"
    r"/[\w./-]+\.\w{2,4})"
)

# A name that outlives its file, and the reason. Every row is a sentence somebody had to write,
# which is the entire mechanism: the cost of keeping a dead name is one line of justification,
# and the cost of forgetting one is a red gate. The list is not pinned to a length — a carve-out
# that cannot shrink is the shape this repository already regrets in `PLANS_WITHOUT_NUMBERED_TASKS`.
TOMBSTONES = {
    "hooks/design_gate.py": "release.yml refuses a wheel that still carries the pre-rename name",
    "hooks/change_scope_guard.py": "install-matrix refuses a wheel that still carries it; deleted "
    "for 3 blocks against 670 bypasses",
    "hooks/claim_scope_guard.py": "install-matrix refuses a wheel that still carries it; deleted "
    "for denying on an unreadable claim with an impossible remedy printed beside it",
    "specs/010/plan.md": "a comment in pre-commit citing where a commitment was recorded, in the "
    "shorthand a person writes rather than the directory's real name",
}


def _tracked() -> set[str]:
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, timeout=30
    ).stdout.split()
    if not listed:
        raise ValueError("git listed no files, so this compared nothing")
    return set(listed)


def test_every_path_a_surface_names_exists_or_says_why_it_does_not():
    tracked = _tracked()
    missing: list[str] = []

    for surface in SURFACES:
        body = (ROOT / surface).read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(body.splitlines(), 1):
            for found in NAMED.findall(line):
                named = found.rstrip(".,;:)\"'")
                if named in tracked or (ROOT / named).exists() or named in TOMBSTONES:
                    continue
                missing.append(f"{surface}:{number} names {named}, which is not in the tree")

    assert not missing, (
        "\n".join(missing) + "\n\nEither repair the reference, or add the path to TOMBSTONES "
        "with the reason its name outlives it. No local test runs these files, so a name left "
        "behind here fails on a runner and nowhere else."
    )


def test_a_tombstone_stops_being_one_when_its_file_comes_back():
    """The other direction, which is the half a carve-out list always forgets.

    A row here is a licence to name something absent. If the file returns and the row stays,
    the licence outlives the reason for it, and the next deletion of that path is waved through
    by a sentence written about a different deletion."""

    tracked = _tracked()
    revived = sorted(name for name in TOMBSTONES if name in tracked or (ROOT / name).exists())

    assert not revived, (
        f"{revived} is in the tree and still in TOMBSTONES. Remove the row: the name no longer "
        "outlives the file, so nothing needs excusing."
    )
