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
# 12,686 to 13,671 for spec 006, which is the screen rather than the truth on it: the
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
#
# 13,671 to 14,590 for spec 007, and 31 of those are not spec 007's: the tree carried spec
# 003's uncommitted work when this branch started, and a ceiling that quietly absorbs
# somebody else's lines has stopped meaning anything. 879 is this spec, measured, and 9 is
# this paragraph. 006 drew the screens and this one makes them answerable: the operator ran
# the two verbs again and asked, of six screens in turn, what he was supposed to do about
# what they said. A cure stops being a sentence at the end of a message and becomes a field,
# which is what lets `--fix` invoke the verb that already carries the consent — ADR 0003,
# superseding 0002 three days after it.
#
# 552 of the 879 are tests against 327 of product, and where they came from is the part
# worth keeping. 106 were planned. The mutation floor found 358 more, nearly all of one
# shape: a style name and a stream flag are invisible to a suite that reads undecorated
# stdout, so every line of new screen could be emptied of its colour or written to stderr
# with the whole thing green. An adversarial review of the finished branch found the last
# 88, and two of those were defects rather than gaps — a last screen promising the guards
# were loaded over its own row reading `0 guard entries`, and `--fix` reaching `init`'s
# unconditional rewrite of `.ai/config.toml`, which is `update` with its three consent
# gates removed and is the exact objection ADR 0002 raised. The pin is written once now
# and never rewritten, which reverses a decision spec 005 made in the other direction.
#
# 14,590 to 15,100 for specs 002 and 003 together, and this is the fourth move. 68 of it
# has already landed: the work-item paste deleted with its four tests, a changelog this
# repository has owed rule 4 since rule 4 was written, the renewal that retires what it
# renews, three lines in the hooks that never ran, the session the dispatcher now adopts
# and the loop guard's two arms. 205 more is predicted for what is left — the false green
# on a malformed record block, the install signature that is an accident of how the tool
# was installed, uninstall's crash on any machine with OpenCode, self-protection derived
# from the wiring table, a denial that does not end the agent's turn, a mutation run that
# cannot reach the operator's home, a packaged guard exercised in CI, and the three numbers
# this repository states as prose. 237 is slack, and it is deliberate rather than sloppy:
# the one prior estimate on file in this project overran by ninety per cent, and a ceiling
# that goes red two thirds of the way through a branch blocks every commit after it with
# this project's own gate. The closing commit of that branch sets this constant to the
# count that actually landed, so none of the slack survives it. 15 of the 68 are this
# paragraph.
#
# 15,100 to 15,700, four commits later, and the honest note is that the estimate above was
# short. 457 of the 205 predicted had landed by the time the record verbs were reached —
# the guards' own tests are most of it, and they are the half of that work nothing else
# would have caught. What is left is the denial protocol, the mutation worker's disposable
# home, uninstall restoring what init overwrote, the record verbs, the packaged guard in
# CI and the three numbers this repository states as prose. This raise is measured against
# the same overrun rather than against the same optimism: 250 predicted, and the rest is
# slack the closing commit takes back.
#
# Closed at the count that landed: 15,615 against the 14,590 those two specs started from,
# so 1,025 for work priced at 273 across two raises. No slack survives the branch, which is
# the only thing that keeps a ceiling meaning anything, and this repository has the
# 436,091-line receipt for the alternative. Where the other 750 went is one sentence, and it
# is the same sentence both times: the five guards had almost no tests of their own — they
# were attacked by the adversarial suite and asserted nowhere else — so eighteen measured
# shell commands against self-protection, ten hooks-path spellings, three loop arms and two
# denial protocols are most of the overrun. The honest reading is that the estimate priced
# the fixes and not the evidence for them.
#
# 15,615 to 15,663, and this one is a correction rather than a spec: closing 003 at the
# measured count did not mean 003 was finished. An audit of every spec in the tree found
# two things it had left — the adversarial harness's docstring still said twelve attacks
# over a registry of fourteen, which was a named task in its own plan; and `just mutate`
# was red at 13 of 14 because moving the repeat arm off `signature()` left that function's
# only rule, truncating a path from its tail, with nothing behind it. A rule with no test
# is the shape this whole spec was about, so the test is the payer's opposite: 48 lines,
# nine of them this paragraph, and the ceiling says so rather than absorbing them.
#
# 15,663 to 15,689, and the payer is spec 006's one unmet check finally being met. That
# spec added the first runtime dependencies this wheel has ever had, and its plan said the
# lane that scans them had to be seen to fail on a planted advisory or the mitigation in
# its accepted risk was itself an unproven claim. It never was: the workflow still carried
# "zero declared dependencies today, so this finds nothing today" over seven packages, and
# the Snyk job still explained its SAST-only shape by an empty requirements file. Both
# comments are now what is true, and the audit step gained the assertion the observation
# argued for — `pip-audit --strict` over an empty export exits 0, so the export is checked
# against the declared dependencies before the audit is allowed to report anything. Fifteen
# lines of workflow, eleven of this paragraph, and no slack.
#
# 15,689 to 15,712, and this one is rule 4 being paid rather than a feature. Spec 007 removed
# two behaviours a person could have been relying on — `init --project` rewriting the pin on
# every run, and the CI workflow being printed at the reader to paste — and neither was ever
# written down in CHANGELOG.md, whose own first paragraph says every hard delete goes in it in
# the words somebody upgrading would search for. Fifteen lines of changelog, eight of this
# paragraph. The dependencies spec 006 added are not in there, and that is deliberate: adding
# one is neither a rename nor a delete, and that file says what it covers.
REPO_CEILING = 15712

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
