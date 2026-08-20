"""How many writers a build could carry, and why the answer here is one.

The Intent says one writer owns repository changes until a separately approved coordination
plan proves otherwise, and specification 013 records that nothing executable ever read that
sentence — "whatever replaces the one-writer sentence arrives with a check that fails, or
the sentence has been swapped for another sentence". This is that check.

It computes a width and never spends it. Every unknown resolves to one, and the sentence
being present is itself an unknown resolved to one.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ai_engineering import spec


def git(where: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(where), *args], capture_output=True, text=True, check=False
    )


@pytest.fixture
def coordinated(tmp_path, monkeypatch):
    """A bare remote, one clone, two claims over paths that do not overlap."""

    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], capture_output=True)
    work = tmp_path / "work"
    subprocess.run(["git", "init", "-b", "main", str(work)], capture_output=True)
    git(work, "config", "user.email", "suite@example.com")
    git(work, "config", "user.name", "suite")
    git(work, "remote", "add", "origin", str(bare))
    (work / "src").mkdir()
    for name in ("alpha.py", "beta.py"):
        (work / "src" / name).write_text("VALUE = 1\n", encoding="utf-8")
    (work / ".ai").mkdir()
    (work / ".ai" / "intent.md").write_text(
        json.dumps(
            {
                "solution_intent": {
                    "fixed_constraints": [
                        "Until a separately approved P3 plan proves safe coordination, "
                        "one writer owns repository changes."
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    git(work, "add", "-A")
    git(work, "commit", "-m", "chore: seed")
    git(work, "push", "origin", "main")

    from ai_engineering import claim

    base = claim.base(work)
    for item, path in (("work-alpha", "src/alpha.py"), ("work-beta", "src/beta.py")):
        (work / ".ai" / "claim.json").unlink(missing_ok=True)
        taken = claim.take(work, item, base, [path], "writer")
        assert taken.outcome == "PASS", taken.summary
    (work / ".ai" / "claim.json").unlink(missing_ok=True)

    monkeypatch.setattr(spec.paths, "repo_root", lambda start=None: work)
    return work


def _facts(result) -> dict[str, str]:
    """The facts, by id. Asserted rather than stdout: this subcommand returns an execution
    and the CLI renders it, so a test reading the terminal would be testing the renderer."""

    return {fact.id: (fact.detail or "") for fact in result.checks}


def test_the_width_is_one_while_the_intent_says_one_writer(coordinated):
    """Two claims that could start together, four writers offered, and the answer is one —
    with the file that decided it named, because a clamp nobody can trace is a number."""

    result = spec.main(["wave", "--surface-width", "4"])
    facts = _facts(result)

    assert result.outcome == "PASS"
    assert result.summary == "width: 1"
    assert ".ai/intent.md" in facts["one-writer"]
    assert "work-alpha" in facts["wave"] and "work-beta" in facts["wave"]
    assert "4" in facts["declared-width"]
    # Observations, never a verdict about the branch.
    assert {fact.status for fact in result.checks} == {"OBSERVED"}


def test_the_width_is_the_wave_once_the_sentence_is_gone(coordinated):
    """The other half of specification 013's resolution: the sentence has been swapped for
    another sentence, and the check that read it stops clamping. Nothing else changes."""

    (coordinated / ".ai" / "intent.md").write_text(
        json.dumps({"solution_intent": {"fixed_constraints": ["Guards fail closed."]}}),
        encoding="utf-8",
    )

    result = spec.main(["wave", "--surface-width", "4"])

    assert result.summary == "width: 2"
    assert "one-writer" not in _facts(result)


def test_every_unknown_width_resolves_to_one(coordinated):
    """Absent, unparseable, zero, negative. A scheduler that guesses wide on a number it
    could not read is the fail-open direction, and this one has no other direction."""

    (coordinated / ".ai" / "intent.md").write_text(
        json.dumps({"solution_intent": {"fixed_constraints": []}}), encoding="utf-8"
    )

    for offered in ("banana", "0", "-3", "1.5", ""):
        assert spec.main(["wave", "--surface-width", offered]).summary == "width: 1", offered

    # And absent entirely is one, not the size of the wave.
    assert spec.main(["wave"]).summary == "width: 1"


def test_a_remote_that_cannot_be_read_is_one_and_says_so(coordinated):
    """Not in the task's three cases and it is the one that matters most: the wave is
    derived from what the remote holds, so a remote nobody can reach is a wave nobody
    measured — and a width taken from that is a number about nothing."""

    (coordinated / ".ai" / "intent.md").write_text(
        json.dumps({"solution_intent": {"fixed_constraints": []}}), encoding="utf-8"
    )

    result = spec.main(["wave", "--surface-width", "4", "--remote", "nowhere"])
    facts = _facts(result)

    assert result.summary == "width: 1"
    assert "nowhere" in facts["wave"]
    assert next(one.status for one in result.checks if one.id == "wave") == "INCOMPLETE"


def test_an_intent_that_does_not_parse_is_unknown_and_unknown_is_one(coordinated):
    """Three versions of this guard, each one shape narrower than the accident.

    First a deleted Intent, then an emptied one — `>` beats `rm`. Neither caught a
    byte-order mark, undecodable bytes, or a file of NUL bytes, and none of those is
    whitespace to `str.strip()`. Specification 013's stated exit is that the sentence "has
    been swapped for another sentence"; anything that does not parse as an Intent is neither
    the sentence nor another one, so the state is unknown, and every unknown here is one.

    The reason is asserted as well as the number. A clamp that reports the sentence is still
    there, over a file that was deleted, is a true width with a false reason — the same
    defect the `claim.base` probe exists to remove.
    """

    where = coordinated / ".ai" / "intent.md"

    corrupt = {
        "empty": b"",
        "whitespace": b"   \n\n  ",
        "byte order mark": b"\xef\xbb\xbf",
        "undecodable": b"\xff\xfe\x00garbage",
        "nul bytes": b"\x00\x00\x00",
        "not json": b"one writer, probably",
    }
    for name, contents in corrupt.items():
        where.write_bytes(contents)
        ran = spec.main(["wave", "--surface-width", "4"])
        assert ran.summary == "width: 1", name
        said = next(f for f in ran.checks if f.id == "one-writer")
        assert "could not be read" in said.detail, (name, said.detail)
        assert "still says" not in said.detail, (name, said.detail)

    where.unlink()
    ran = spec.main(["wave", "--surface-width", "4"])
    assert ran.summary == "width: 1"
    assert "could not be read" in next(f for f in ran.checks if f.id == "one-writer").detail

    # And a sentence that genuinely replaced it does lift the clamp, which is the exit
    # specification 013 names. The authority lives in an approved plan, not in this string;
    # what this does is stop being the thing that says no.
    where.write_text(
        json.dumps({"solution_intent": {"fixed_constraints": ["Guards fail closed."]}}),
        encoding="utf-8",
    )
    assert spec.main(["wave", "--surface-width", "4"]).summary == "width: 2"


# The eight boxes every wave specification carries, and the statuses that claim a wave is
# finished. `draft` and `proposed` claim nothing; the rest do.
BOXES = 8
CLAIMS_DONE = ("shipped", "accepted", "active", "done")


def _waves():
    """Every wave specification with its status and how many boxes it has ticked."""

    import re

    root = Path(__file__).resolve().parents[1]
    for folder in sorted((root / "specs").glob("0*/")):
        spec = folder / "spec.md"
        if not spec.is_file():
            continue
        body = spec.read_text(encoding="utf-8")
        if "## Production-ready" not in body:
            continue
        status = re.search(r"(?m)^status:\s*(\S+)", body)
        block = body.split("## Production-ready", 1)[1].split("\n## ", 1)[0]
        ticked = len(re.findall(r"(?m)^- \[x\]", block))
        total = len(re.findall(r"(?m)^- \[[ x]\]", block))
        yield folder.name, (status.group(1) if status else "?"), ticked, total


def test_every_wave_carries_the_same_eight_boxes():
    """`EP-297` asks that every wave get its own admission gate, read mechanically rather
    than asserted. The boxes are that gate in data form, and until now nothing read them —
    the P5 register was the only wave with a claim anything could refuse.

    Read here rather than declared, so a wave that quietly ships seven boxes instead of eight
    is a wave whose gate got smaller without anybody deciding it should."""

    found = list(_waves())

    assert found, "no specification carries a production-ready block, so this read nothing"
    thin = [(name, total) for name, _, _, total in found if total != BOXES]
    assert not thin, f"these waves carry a different number of boxes: {thin}"


def test_no_wave_claims_to_be_finished_over_an_unticked_box():
    """The refusal, and the reason it looks vacuous today: every wave is `draft`, so every
    one of them claims nothing and passes. That is the honest state and it is exactly when
    this is worth writing — the case fires on the first wave somebody marks shipped, which is
    the moment nobody is looking for an unticked box.

    `Nothing gets a URL until every box is ticked by observed evidence` is the sentence each
    specification opens that block with. This is that sentence, executed."""

    claimed = [
        f"{name} is {status} with {ticked} of {total} boxes ticked"
        for name, status, ticked, total in _waves()
        if status in CLAIMS_DONE and ticked < total
    ]

    assert not claimed, (
        "; ".join(claimed) + ". Every specification says nothing gets a URL until every box "
        "is ticked by observed evidence. Tick them, or say the wave is not finished."
    )
