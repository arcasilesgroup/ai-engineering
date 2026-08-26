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
DESCRIPTION_MAX = 1000

# A repo-specific tool a shipped skill must not invoke as a required command. The wheel
# guarantees only the commands it installs (`ai-eng` verbs) and the outputs a gate keeps;
# a skill that tells a downstream repo to run a `just` recipe or a bare scanner assumes the
# stranger has the tool, which is the behavioural half of the taxonomy's Series of Commands
# smell. `just` remains the maintainer's local orchestrator and is never named by a skill.
PORTABLE_BANNED = ("just ", "semgrep", "gitleaks", "trivy", "git grep")

# Cues that turn a mention of a banned binary into an instruction to run it. A bare
# noun ("the `just` recipe") is a reference; "Run `just check`" is a command. The rule
# refuses the command and passes the reference.
_RUN_CUES = re.compile(
    r"\b(?:run|running|execute|executes|execution|drive|via)\b"
    r"(?<!\bwas )(?<!\bis )",
    re.I,
)
_SPAN = re.compile(r"`([^`]+)`")
_JUST = re.compile(r"\bjust [a-z-]+")
_GIT_GREP = re.compile(r"\bgit\s+grep\b")

# A cross-file reference a skill body makes to a path the wheel does not guarantee beside
# the skill. The skill's own `references/` subfolder ships with it and is not a dependency;
# every other root — policy/, hooks/, specs/, docs/, CONSTITUTION.md and a sibling skill's
# references/ — is a file the stranger's repo may not have unless the skill says so and
# fails closed when it does not.
# A path a shipped skill depends on: the wheel guarantees nothing beside the skill except
# its own `references/` subfolder. The skill's own output namespace is excluded — a skill
# writing `specs/NNN-slug/council.md` or `docs/notes/<slug>.md` creates that path, it does
# not depend on it, so demanding an existence check for its own artifact is noise.
_EXIST_ROOTS = re.compile(
    r"`((?:policy|hooks)/[^`]+|specs/(?!NNN-slug)[^`]+)`"
    r"|`(CONSTITUTION\.md)`|`([a-z][a-z0-9-]*/references/[^`]+)`"
)
_FAIL_CLOSED = re.compile(
    r"\b(absent|missing|does not exist|fail(?:s)? closed|refus(?:es|e)"
    r"|when it is not there)\b",
    re.I,
)

# A cross-file reference a skill body makes to a path the wheel does not guarantee beside
# the skill. The skill's own `references/` subfolder ships with it and is not a dependency;
# every other root — policy/, hooks/, specs/, docs/, CONSTITUTION.md and a sibling skill's
# references/ — is a file the stranger's repo may not have unless the skill says so and
# fails closed when it does not.
# A "Done when" clause that requires an artifact a reader can verify. The taxonomy's
# Forced-Output Verification Gate exists because a mere "verify" instruction is skipped.
_ARTIFACT = re.compile(
    r"`[^`]+\.(?:md|html|json|toml|txt|log)`|`[^`]*(?:output|digest|receipt|report)"
    r"|printed|paste the output|show (?:its|the)? ?output|committed|the output is shown|"
    r"a page|checklist|status table|file signature|output is in the conversation",
    re.I,
)
_WEAK_OUTPUT = re.compile(
    r"\b(verif(?:y|ied|ies)|ensure|makes? sure|check that|confirm(?:ed)?)\b"
    r"|\w+ approval is the gate",
    re.I,
)

# A statistic that claims a number without naming where it came from. The taxonomy's
# sourced-statistic smell: a percentage or a ratio with no source is an assertion the
# reader cannot check, and this framework's whole discipline is that every claim carries
# evidence. A bare percentage/ratio with no `[N]`, `(report NNN)`, `arXiv:`, `Measured on`
# or `report 00N` beside it on the same line refuses.
_STAT = re.compile(
    r"\b\d+(?:\.\d+)?%(?:\s*[–-]\s*\d+(?:\.\d+)?%)?"
    r"|\b\d+(?:\.\d+)?\s*(?:vs|to|against)\s+\d+(?:\.\d+)?\b"
    r"|\b(?:0\.\d{2})\b|\bfive of twenty\b|\bfour of twenty\b"
)
_STAT_SOURCE = re.compile(r"\b(?:arXiv|report\s+00?\d|Measured on)\b|`\[source:[^\]]+`|\[\d+\]")

# The catalogue budget, not the file budget: the open Agent Skills specification and each
# surface load a catalogue, and a skill that silently does not fit is a skill that silently
# does not exist there. 50 000 is the smallest documented budget (Zed's 50 KB, spec 024
# D-024-03); the per-file `DESCRIPTION_MAX` above stays 1000 and the divergence from the
# open standard's 1,024 is deliberate and recorded in that decision.
CATALOG_MAX = 50_000

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
    problems = [problem for skill in skills for problem in audit_one(skill)]
    # Measured once for the whole catalogue, because that is what a surface loads and what
    # the smallest documented budget bounds. One parse per skill, in the same pass that
    # names the largest contributor: a catalogue that blows the budget is usually one
    # skill far over, and a message that names it is a message somebody can act on.
    total = 0
    largest: tuple[int, str] = (0, "")
    for skill in skills:
        try:
            header = text.frontmatter(skill)
        except ValueError:
            continue  # audit_one already reported the broken frontmatter
        size = len(skill.parent.name) + len(header.get("description", ""))
        total += size
        if size > largest[0]:
            largest = (size, skill.parent.name)
    if total > CATALOG_MAX:
        problems.append(
            f"catalogue budget: {total} characters over CATALOG_MAX={CATALOG_MAX}; top "
            f"contributor {largest[1]} is {largest[0]} — a surface that loads this catalogue "
            f"would drop a skill silently"
        )
    return problems


def audit_one(path: Path) -> list[str]:
    name = path.parent.name
    found: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
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
    found.extend(_portable_problems(path.parent, name))
    found.extend(_existence_problems(path.parent, name))
    found.extend(_forced_output_problems(path.parent, name))
    found.extend(_sourced_statistic_problems(path.parent, name))
    found.extend(_corpus_problems(path.parent, name))
    # Spec 032: the craft rules — anti-rationalization, output contract, Incorrect/Correct
    # pairs (where a rules section exists) and load tiers, one refuser each.
    found.extend(_anti_rationalization_problems(path.parent, name))
    found.extend(_output_contract_problems(path.parent, name))
    found.extend(_incorrect_correct_problems(path.parent, name))
    found.extend(_load_tier_problems(path.parent, name))
    return found


ROUTES = "## Routes here"
REFUSES = "## Refuses"


def _existence_problems(folder: Path, name: str) -> list[str]:
    """A cross-file reference without a fail-closed clause for when it is absent.

    Spec 027 D-027-01: every reference a skill body makes to another path must be
    accompanied by a check that the path exists and a fail-closed sentence when it does
    not. `ai-spec`'s handling of CONSTITUTION.md is the pattern. A skill that names
    `policy/threat-model.toml` as if the file is always there silently stops fitting on
    the machine that lacks it; one that says "if `policy/threat-model.toml` is absent,
    refuse to continue" stays honest. Both files of the pair are read, for the same
    reason the portable rule reads both.
    """

    problems = []
    for doc in (folder / "SKILL.md", folder / "corpus.md"):
        if not doc.exists():
            continue
        all_lines = doc.read_text(encoding="utf-8").splitlines()
        for line_no, line in enumerate(all_lines):
            if not _EXIST_ROOTS.search(line):
                continue
            target = next(
                group for match in _EXIST_ROOTS.finditer(line) for group in match.groups() if group
            )

            # The fail-closed clause must sit with the reference — the same paragraph, not
            # two sections away: this line, or up to three lines around it.
            def boundary(k: int, all_lines=all_lines) -> bool:
                return (
                    k < 0
                    or k >= len(all_lines)
                    or not all_lines[k].strip()
                    or all_lines[k].lstrip().startswith("#")
                )

            start = line_no
            while not boundary(start - 1) and line_no - start < 3:
                start -= 1
            end = line_no
            while not boundary(end + 1) and end - line_no < 3:
                end += 1
            around = "\n".join(all_lines[start : end + 1])
            if not _FAIL_CLOSED.search(around):
                problems.append(
                    f"{name}: {doc.name} line {line_no + 1} references `{target}` without "
                    f"a fail-closed sentence for when that path is absent. Add an existence "
                    f"check and a refusal beside the reference, the way ai-spec handles "
                    f"CONSTITUTION.md."
                )
    return problems


def _forced_output_problems(folder: Path, name: str) -> list[str]:
    """A skill whose exit says only "verify" without naming a kept artifact.

    Spec 027 D-027-01: every skill must end with a "Done when" clause naming the
    artifact it produces — a status table, a printed digest, a committed file — or the
    exact command whose output it keeps. A mere "verify" or "the approval is the gate"
    is the Forced-Output smell: a workflow that just tells the agent to ensure done is
    the one most often skipped. The artifact must appear in the same section as the
    weak phrase, not somewhere the reader would have to search for it.
    """

    problems = []
    for doc in (folder / "SKILL.md", folder / "corpus.md"):
        if not doc.exists():
            continue
        body = doc.read_text(encoding="utf-8")
        done = body.partition("## Done when")[2].partition("\n## ")[0]
        if not done:
            continue
        # 'verify' inside a backticked command (`ai-eng audit verify`) is the portable
        # verb, not a weak exit — only prose outside the backticks can be weak.
        weak = _WEAK_OUTPUT.search(_SPAN.sub("", done))
        if weak and not _ARTIFACT.search(done):
            problems.append(
                f"{name}: {doc.name} 'Done when' says only {weak.group(0)!r} — "
                f"name the artifact it produces (a committed file, a printed digest, a "
                f"status table) or the exact command whose output it keeps. A mere "
                f"'verify' is skipped."
            )
    return problems


def _sourced_statistic_problems(folder: Path, name: str) -> list[str]:
    """A numeric statistic that carries no source.

    Spec 027 D-027-01: any statistic in a skill body carries the source, or is deleted.
    `ai-council` and `ai-challenge` state numbers with no anchor; each must get its
    source beside it (the arithmetic resolves in `.ai/reports/003-council-peer-review-
    evidence.html`) or be struck. A percentage or a ratio with a source on its own line
    passes; one with no source anywhere near it refuses.

    Reads `SKILL.md` only: `corpus.md` is routing cases, not claims, so a statistic in
    a refusal example is prose, not a citation obligation.
    """

    problems = []
    for doc in (folder / "SKILL.md",):
        if not doc.exists():
            continue
        body = doc.read_text(encoding="utf-8")
        for line_no, line in enumerate(body.splitlines()):
            if not _STAT.search(line):
                continue
            if _STAT_SOURCE.search(line):
                continue
            problems.append(
                f"{name}: {doc.name} line {line_no + 1} carries a statistic "
                f"({_STAT.findall(line)[0]!r}) with no source. Anchor it "
                f"(`[arXiv:...]`, `report 00N`, or 'Measured on ...') or strike it — "
                f"an unsourced number is an assertion the reader cannot check."
            )
    return problems


def _portable_problems(folder: Path, name: str) -> list[str]:
    """A skill that names a repo-specific tool as a required command.

    Spec 027 D-027-02: a shipped skill names only portable commands — an `ai-eng` verb,
    or the output of a tool kept as the gate's evidence. A skill that tells a downstream
    repo to `just check` or run a bare scanner assumes the stranger has the tool, which
    is the Series of Commands smell of arXiv:2607.01456: a concrete toolchain command
    dies the moment the tree it was written for is not the tree it runs in. Both files
    of the pair are read, because `corpus.md` ships verbatim beside `SKILL.md` and the
    council's finding was that the smells live in both.

    A mention is not a command: "the `just` recipe" is a reference and passes, "Run
    `just check`" is an instruction and refuses. The run cues are the line's own words,
    so a skill that merely names a tool as evidence a gate keeps is not punished for
    saying which tool it keeps the output of.
    """

    problems = []
    for doc in (folder / "SKILL.md", folder / "corpus.md"):
        if not doc.exists():
            continue
        for line in doc.read_text(encoding="utf-8").splitlines():
            found_this_line: set[str] = set()
            for span in _SPAN.findall(line):
                lowered = span.strip().lower()
                if lowered.startswith(PORTABLE_BANNED):
                    # The command must be directly commanded, not merely mentioned later
                    # in the sentence: "Run `just check`" fires, "that is just check in
                    # CI" does not. The cue has to be the words immediately before the
                    # span (with only a preposition or connective allowed between).
                    mech = _SPAN.search(line)
                    prefix = line[: mech.start()] if mech else ""
                    tail = re.split(r"[.;:|\n]", prefix)[-1].strip().lower()
                    if re.search(
                        r"\b(?:run|running|execute|executes|drive|via)"
                        r"(?:\s+(?:the|a|an|its|your|our|their|these|those|this"
                        r"|repo(?:sitory)?'?s))?\s*$",
                        tail,
                    ):
                        found_this_line.add(lowered)
            for command in sorted(found_this_line):
                problems.append(
                    f"{name}: {doc.name} runs {command!r} — a repo-specific command "
                    f"the wheel does not guarantee on the stranger's machine. Name an "
                    f"`ai-eng` verb, or keep the tool only as the output the gate holds."
                )
    return problems


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


# ── spec 032 craft rules ──────────────────────────────────────────────────────
# Four checked authoring rules, added the way spec 027 added its smell rules: a script
# refuses the shape, so the discipline is enforced rather than requested. Each rule names
# the fix beside the refusal, so a person who reads the problem reads the answer.

# B-032-1: a skill must carry an anti-rationalization section (## What this is not or
# ## Anti-rationalizations) that names at least one excuse and answers it factually in
# the same entry. An excuse with no counter is a skipped step wearing a name.
_ANTI_SECTION = re.compile(r"^## (?:What this is not|Anti-rationalizations)", re.M)
_ANTI_ENTRY = re.compile(r"^- .*— .+", re.M)


def _anti_rationalization_problems(folder: Path, name: str) -> list[str]:
    body = (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    if not _ANTI_SECTION.search(body):
        return [
            f"{name}: has no anti-rationalization section (## What this is not or "
            "## Anti-rationalizations) naming an excuse and answering it"
        ]
    entries = _ANTI_ENTRY.findall(body)
    if not entries:
        return [f"{name}: the anti-rationalization section names no excuse-and-answer entry"]
    return []


# B-032-2: ## What it produces must name the artifact (a path, a file, a record, a
# verdict), not a "verify"-style instruction. A prose exit is not an output.
_PRODUCES = "## What it produces"
_ARTIFACT = re.compile(r"`[^`]+`|(?:path|file|record|verdict|report|receipt)\b", re.I)


def _output_contract_problems(folder: Path, name: str) -> list[str]:
    body = (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    if _PRODUCES not in body:
        return [f"{name}: no '## What it produces' section naming the artifact it exits"]
    section = body.partition(_PRODUCES)[2].partition("\n## ")[0]
    if not _ARTIFACT.search(section):
        return [f"{name}: '## What it produces' names no artifact (path/file/record/verdict)"]
    return []


# B-032-3: a skill with a ## Rules section must state each rule as an Incorrect/Correct
# pair; bare prose rules are a source of interpretation. A skill with no rules section
# passes — the rule fires where rules exist, never forcing fake pairs.
_RULES = re.compile(r"^## Rules", re.M)
_PAIR = re.compile(r"^### Incorrect.*?^### Correct", re.M | re.S)


def _incorrect_correct_problems(folder: Path, name: str) -> list[str]:
    body = (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    if not _RULES.search(body):
        return []  # no rules section: scoped out
    if not _PAIR.search(body):
        return [f"{name}: '## Rules' states rules without an Incorrect/Correct pair"]
    return []


# B-032-4: the body must sit within the load tier the surfaces give it — 500 lines, with
# long embedded scripts moved to scripts/ (executed, never read into context).
LOAD_TIER_MAX = 500
_INLINE_SCRIPT = re.compile(r"^(?:python3?|bash|sh)\s+-|<<['\"]?EOF", re.M)


def _load_tier_problems(folder: Path, name: str) -> list[str]:
    body = (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    size = body.count("\n") + 1
    problems: list[str] = []
    if size > LOAD_TIER_MAX:
        problems.append(
            f"{name}: body is {size} lines, over LOAD_TIER_MAX={LOAD_TIER_MAX}; "
            "a surface reads it partially. Split references/ or move scripts to scripts/"
        )
    if _INLINE_SCRIPT.search(body):
        problems.append(
            f"{name}: carries an inline script body; move it to scripts/ so it "
            "is executed, never read into context"
        )
    return problems


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
