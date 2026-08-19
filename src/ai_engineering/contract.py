"""The contract every SKILL.md meets, checked by a script rather than by taste.

The open standard defines six portable fields and treats anything else as a hard error
on the packaged-distribution path. This allows those six plus exactly three Claude Code
extensions and nothing else. The portability cost is paid deliberately and named in the
README: these files are not uploadable to claude.ai as-is, and the alternative is a
per-surface rewrite layer, which is the machinery this product exists to delete.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ai_engineering import text

SPEC_FIELDS = {"name", "description", "license", "compatibility", "allowed-tools", "version"}
EXTENSIONS = {"disable-model-invocation", "context", "background"}
JARGON = (
    "leverage",
    "utilise",
    "utilize",
    "synergy",
    "robust",
    "seamless",
    "delve",
    "holistic",
    "best-in-class",
    "cutting-edge",
)
CEILING = 80
DESCRIPTION_MAX = 1000
# The line ceiling, in one place so raising it is a single reviewable edit. Every move it
# has made is in `git log -S REPO_CEILING -- src/ai_engineering/contract.py`, and the
# arithmetic behind each one is in the specification that spent it. Both were true while a
# hand-written prose changelog of this one integer also sat here, 3,330 lines of it, charged
# against the very number it documented — eighteen of them for a paragraph about itself. A
# governance file that quotes a count goes stale silently; a governance file that quotes
# three hundred of them goes stale in three hundred places. Raise it in a commit whose
# message says why, and let git be the record of that, because git already is.
REPO_CEILING = 81_959

# The shape of that total, not just its size. This began as a sentence in the comment above
# saying the test plane was three times the product; it was written from no measurement and
# it was wrong. An unmeasured number in a governance file is the defect this product is
# about, so the sentence is deleted and the measurement is a gate instead.
#
# Code, not lines, and both sides measured the same way. Counting raw lines, this read 1.97
# against a bound of 2.0 — and 3,362 of the lines on the product side of that fraction were
# comment in this one file, most of them the ceiling's own changelog. Deleting them moved the
# ratio to 2.28 without one line of test being written, which is the gate firing at exactly
# the work it should reward. Measured over lines that are neither blank nor comment, the
# ratio was 2.23 before that deletion and 2.23 after: the suite is genuinely more than twice
# the product, it always was, and the raw count was being flattered by the mass of prose the
# repository had accumulated about itself.
#
# 2.3 and not 2.0, therefore, because 2.0 was never the measurement — it was a bound set
# against a number that could not see comments. What this still catches is the shape the
# ceiling cannot: a suite that grows while the product does not.
TEST_RATIO_MAX = 2.3
PRODUCT = ("src/", "hooks/")
TESTS = ("tests/",)


def audit(root: Path) -> list[str]:
    skills = sorted(root.glob("ai-*/SKILL.md"))
    if not skills:
        return [f"no skills found under {root}"]
    return [problem for skill in skills for problem in audit_one(skill)]


def audit_one(path: Path) -> list[str]:
    name = path.parent.name
    found: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > CEILING:
        found.append(
            f"{name}: {len(lines)} lines. Over {CEILING} means it is a procedure "
            f"that should be a script."
        )
    try:
        header = text.frontmatter(path)
    except ValueError as why:
        return [*found, f"{name}: {why}"]

    unknown = set(header) - SPEC_FIELDS - EXTENSIONS
    if unknown:
        found.append(
            f"{name}: {sorted(unknown)} are not in the contract. Every extra field "
            f"is hidden behaviour in a file nobody re-reads."
        )
    if header.get("name") != name:
        found.append(f"{name}: the name field says {header.get('name')!r}")
    description = header.get("description", "")
    if not description:
        found.append(f"{name}: no description. That field is the routing decision.")
    if len(description) > DESCRIPTION_MAX:
        found.append(
            f"{name}: the description is {len(description)} characters, over {DESCRIPTION_MAX}"
        )
    if "Not for" not in description:
        found.append(
            f"{name}: the description has no 'Not for X — use /ai-Y' clause, which is "
            f"the line that stops the wrong skill from firing."
        )
    if header.get("context") == "fork" and header.get("background") != "false":
        found.append(
            f"{name}: context: fork without background: false. A forked skill runs in "
            f"the background by default, so its verdict lands out of order and /rewind "
            f"will not undo its edits."
        )
    if "when_to_use" in header:
        found.append(f"{name}: when_to_use shares the description's character budget")
    body = "\n".join(lines).lower()
    for word in JARGON:
        if word in body:
            found.append(f"{name}: {word!r} — write it so somebody who does not code can follow")
    found.extend(_corpus_problems(path.parent, name))
    return found


ROUTES = "## Routes here"
REFUSES = "## Refuses"


def _corpus_problems(folder: Path, name: str) -> list[str]:
    """The two lists a skill is judged by, in the skill's own directory.

    Everything above this checks the file's *shape* — its fields, its length, its
    vocabulary. None of it can tell a skill that routes correctly from one that fires on
    everything, so a skill whose description overlapped its neighbour's passed every gate
    this repository had. Spec 012 D-012-01: no skill file lands before a case it must take
    and a case it must refuse.

    Plain markdown beside the skill, not a registry: one more home is one more thing to
    keep in sync, and the audit has already found four copies of a list this week. The
    refusal half is the one that matters — "what it does" is in every description ever
    written, and "what it must not do" is the half that stops the wrong skill firing."""

    corpus = folder / "corpus.md"
    if not corpus.exists():
        return [
            f"{name}: no corpus.md. A skill needs a case it must take and a case it must "
            f"refuse, or nothing can tell it apart from the skill beside it."
        ]
    text_ = corpus.read_text(encoding="utf-8")
    problems = []
    for heading in (ROUTES, REFUSES):
        section = text_.partition(heading)[2].partition("\n## ")[0]
        if heading not in text_ or not [
            line for line in section.splitlines() if line.strip().startswith("- ")
        ]:
            problems.append(f"{name}: corpus.md has no cases under {heading!r}")
    return problems


# Not the product, so not counted, and these two reasons are the only ones that qualify:
# the record grows by design every time a decision is written down, and nobody here wrote
# the licence or can shorten it. Everything we chose to write, documentation included, counts.
# What the ceiling does not count, and the rule is one sentence: this is the record and the
# inputs, not the thing that ships. `.ai/reports/` joins them because those two documents are
# what the whole of spec 010 is judged against — 4,293 lines of research nobody wrote here and
# nobody may edit to fit. Counting them would put the tree over its bound for having brought
# its own source of truth into view, and raising the bound by their size would say the ceiling
# is negotiable by adding files. Neither is the answer; they are simply not the product.
NOT_THE_PRODUCT = ("specs/", "docs/adr/", ".ai/reports/", "LICENSE", "NOTICE")


def tracked(root: Path) -> list[str]:
    names = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, timeout=30
    ).stdout.split()
    if not names:
        raise ValueError(f"git listed no files under {root}, so this counted zero lines")
    return names


def count(root: Path, names: list[str]) -> int:
    total = 0
    for name in names:
        try:
            total += len((root / name).read_bytes().decode("utf-8", "replace").splitlines())
        except OSError:
            continue
    return total


def repo_lines(root: Path) -> int:
    """Every committed line of the product. The ceiling is the mechanism that prevents a
    second 436,091: not discipline, an exit code."""
    names = [n for n in tracked(root) if not n.startswith(NOT_THE_PRODUCT)]
    return count(root, names)


def test_ratio(root: Path) -> tuple[int, int]:
    """Lines of test against lines of product, counting neither blanks nor comment.

    Raw lines flattered this for as long as one file carried a 3,330-line prose changelog:
    comment counted as product, so writing prose about the repository bought room for tests.
    Both sides are measured the same way here, which is the only property that makes a ratio
    mean anything."""

    names = tracked(root)

    def code(prefixes: tuple[str, ...]) -> int:
        total = 0
        for name in names:
            if not name.startswith(prefixes) or not name.endswith(".py"):
                continue
            try:
                body = (root / name).read_bytes().decode("utf-8", "replace")
            except OSError:
                continue
            total += sum(
                1 for line in body.splitlines() if line.strip() and not line.strip().startswith("#")
            )
        return total

    tests, product = code(TESTS), code(PRODUCT)
    if not product:
        raise ValueError(f"no product lines under {PRODUCT} in {root}")
    return tests, product


def prose(body: str) -> str:
    """A skill's sentences, with everything that is not a sentence taken out.

    Code, tables and block quotes are not prose and score like nonsense in either
    direction — a fenced shell command is one enormous word, a table row is a sentence with
    no verb. Inline code becomes the word `code` rather than vanishing, because the
    sentence around it still has to parse without it.
    """

    stripped = body.split("---", 2)[2] if body.startswith("---") else body
    kept, fenced = [], False
    for line in stripped.splitlines():
        if re.match(r"^(```|~~~)", line.strip()):
            fenced = not fenced
            continue
        if fenced or line.strip().startswith(("|", ">")):
            continue
        kept.append(re.sub(r"`[^`]*`", "code", line))
    return "\n".join(kept)


def _syllables(word: str) -> int:

    groups = re.findall(r"[aeiouy]+", word.lower())
    count_of = len(groups)
    if word.lower().endswith("e") and count_of > 1:
        count_of -= 1
    return max(count_of, 1)


def fog(body: str) -> float:
    """Gunning fog over a skill's prose: how many years of schooling it assumes.

    Two things make a sentence hard and this counts both — its length, and how much of it
    is long words. Either alone is gameable in the direction that does not help anybody:
    short words in a sixty-word sentence, or six words of jargon in a row.

    Common inflections are not counted as long words. `governed` and `receipts` are three
    syllables by the rule and one idea by any reader, and counting them would push every
    document in this repository over the line for using the plural.
    """

    sentences = [one for one in re.split(r"[.!?]+(?:\s|$)", body) if one.strip()]
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", body)
    if not sentences or not words:
        raise ValueError("nothing here reads as prose, so no score can be taken from it")
    hard = [
        word for word in words if _syllables(word) >= 3 and not word.endswith(("es", "ed", "ing"))
    ]
    return 0.4 * (len(words) / len(sentences) + 100 * len(hard) / len(words))


SKILL_FOG_CEILING = 11.03
