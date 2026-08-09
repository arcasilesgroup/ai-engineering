"""The contract every SKILL.md meets, checked by a script rather than by taste.

The open standard defines six portable fields and treats anything else as a hard error
on the packaged-distribution path. This allows those six plus exactly three Claude Code
extensions and nothing else. The portability cost is paid deliberately and named in the
README: these files are not uploadable to claude.ai as-is, and the alternative is a
per-surface rewrite layer, which is the machinery this product exists to delete.
"""

from __future__ import annotations

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

# The line ceiling, in one place so raising it is a single reviewable edit. 5,000 to 5,600 in
# specs/001; 5,600 to 5,610 for the test plane named in that commit, while the product itself
# lost nine lines; 5,610 to 5,764 for four controls that reported green while doing nothing —
# a plan gate any plan ever written satisfied, a repeat rule counting an identifier that is
# unique per call, two dispatcher rows naming a payload key no guard read, and a git hook that
# refused every push when an older CLI answered on the PATH — plus the measurement plane that
# stops the next one hiding; and 5,764 to 8,441 for the test plane the operator asked for, at
# his own decision and after being shown the counter-argument. That last move is 2,660 lines,
# nearly half this repository, and the honest accounting is that it bought 95% branch coverage
# rather than the 80% asked for, and nine defects nothing else had found — one of which put a
# broken CI workflow in front of every user this tool has ever initialised. The test plane is
# now larger than the product. That is a fact about this ceiling, not a defence of it: the next
# commit that needs lines deletes a test that kills no mutant — and there is now a command that
# says which those are. 8,441 to 8,661 for it: mutmut over the package, a hand-written runner
# over the guards mutmut cannot import, and a floor that fails the build. It bought the number
# the coverage percentage was hiding — 95% of lines run, 59% of deliberate defects caught.
# 8,661 to 11,587 to answer that number: five suites, 2,549 lines, which took the mutation
# score from 59% to 89% and found four more defects on the way, including a mutation gate
# configured by a list of four filenames that silently excluded every test file written
# after it. Two of the fifteen modules have no suite yet, and their 197 survivors are the
# six points between 89 and the 95 that was asked for. The test fails the build on the
# line after.
#
# 11,587 to 12,017 happened with no line here: the last figure this comment named and the
# constant under it disagreed by 430, which is this comment's own failure mode, one level up.
# 12,017 to 12,686 for spec 005 — thirteen defects in `init` and `doctor`, every one of them a
# statement the software made about itself that was not true, or a green nobody had earned.
# 466 of those lines are test against 154 of product, three to one inside a branch on a tree
# the ratio gate caps at two to one, and that shape is the work: four of the seven reported
# defects had a test sitting beside them asserting the wrong half, and one carried a strict
# xfail this branch deleted. 116 of the 466 were not planned at all — the mutation floor went
# red at 88%, and what it had caught was two new screens asserted by fragment, where every line
# the fragment did not name could be emptied with the suite still green. The other 35 lines are
# package.json and tsconfig.json, an in-flight lane of the operator's that this branch's first
# commit swept up out of an index that already held them — named here rather than absorbed,
# because a ceiling quietly carrying somebody else's lines has already stopped meaning anything.
#
# 12,686 to 13,664 for spec 006, which is the screen rather than the truth on it: the
# operator installed 005, ran the two verbs in a terminal and said it was still just as
# ugly, and he was right — 005 changed what the software claimed and nothing about how any
# of it is drawn. Measured against the version he prefers, the gap was 1,368 lines of
# presentation layer that version has and this one did not, so this buys the two
# dependencies it used and one module that owns the ticks, the widths, the theme and the
# two streams. 139 of the total is uv.lock, which the first runtime dependencies this wheel
# has ever had brought with them, and 409 is that module and its suite. What it also bought
# is a defect: doctor was printing nine section headings for six families, which is not
# taste and was most of what "ugly" meant. 176 of the total are the tests the mutation
# floor asked for after going red at 86%: a renderer's mutants are style names, and the
# suite drives the undecorated path where a style name is invisible.
REPO_CEILING = 13664

# The shape of that total, not just its size. This began as a sentence in the comment above
# saying the test plane was three times the product; it was written from no measurement and
# it was wrong — the ratio is 1.68. An unmeasured number in a governance file is the defect
# this product is about, so the sentence is deleted and the measurement is a gate instead.
#
# 2.0 and not 1.7: there is no industry law here, the working heuristic is one to two lines
# of test per line of product, and the ceiling above already caps the total. This one catches
# the shape the ceiling cannot see — tests padded to chase a mutation number, or a product
# that shrank while its tests did not.
TEST_RATIO_MAX = 2.0
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
    return found


# Not the product, so not counted, and these two reasons are the only ones that qualify:
# the record grows by design every time a decision is written down, and nobody here wrote
# the licence or can shorten it. Everything we chose to write, documentation included, counts.
NOT_THE_PRODUCT = ("specs/", "docs/adr/", "LICENSE", "NOTICE")


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
    """Test lines against product lines. Both halves are counted the same way and from the
    same index, so the answer cannot drift the way a hand-written number does."""
    names = tracked(root)
    tests = count(root, [n for n in names if n.startswith(TESTS)])
    product = count(root, [n for n in names if n.startswith(PRODUCT)])
    if not product:
        raise ValueError(f"no product files under {root}, so this ratio measured nothing")
    return tests, product
