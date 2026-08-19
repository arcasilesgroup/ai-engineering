"""The measurement `PO-16` never had, and the one way it could flatter.

The rule is one primary home per commit. The audit graded it CONTRADICTED from a single
observation — the widest commit touched twenty-one files across six homes — and nothing has
measured it since, so the sentence was one commit's worth of evidence about a hundred and
ninety.

What this file holds is the classification, because that is where a generous answer would
come from. A path whose top-level name is not a known home must become its own home and never
join an existing one: fold `justfile` or a new top-level area into "src" and every commit
that touched it reads as narrower than it was.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import one_home  # noqa: E402 — the reader under test, beside this file


def test_a_path_outside_the_known_homes_becomes_its_own():
    """The generous answer this must not give. `justfile` and `pyproject.toml` are not under
    any declared home, and folding them into one would make every commit that touched them
    read as narrower than it was."""

    assert one_home.home("src/ai_engineering/cli.py") == "src"
    assert one_home.home(".github/workflows/check.yml") == ".github"
    assert one_home.home("justfile") == "justfile"
    assert one_home.home("pyproject.toml") == "pyproject.toml"


def test_the_homes_are_the_ones_the_doctrine_names():
    """A home this file invented would be a rule this file wrote, and `PO-16` is about the
    rule `AGENTS.md` and the plan already carry."""

    doctrine = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    # `AGENTS.md` names each home under "The shape of the tree", some by their full path —
    # `src/ai_engineering/`, `.agents/skills/` — so the top-level name is what is looked for.
    # A home this file invented and the doctrine does not carry would be a rule this file
    # wrote, and `PO-16` is about the rule the doctrine and the plan already carry.
    for name in ("src", "hooks", "policy", "specs", "surfaces", ".agents"):
        assert name in one_home.HOMES
        assert f"`{name}/" in doctrine, f"{name} is not a home AGENTS.md names"


def test_this_branch_is_measured_rather_than_described():
    """The point of the file: a number that moves with the tree instead of a sentence about
    one commit somebody looked at once."""

    commits = one_home.git("rev-list", "main..HEAD").split()
    if not commits:  # pragma: no cover - only on a branch with nothing on it
        return

    spread = [one_home.homes(one) for one in commits[:20]]

    assert all(seen for seen in spread), "a commit touching no file at all is not a commit"
    assert any(len(seen) > 1 for seen in spread), (
        "no commit in the last twenty touches more than one home, which would make PO-16 "
        "PROVEN rather than CONTRADICTED — regrade it rather than leaving this assertion"
    )
