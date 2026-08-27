"""specs/NNN-slug/spec.md — the record, in the user's repository, in their diff.

Specs live at the root and not inside a hidden directory, deliberately: a governance
record hidden in a dot-directory is a record nobody reviews, because reviewers read the
file tree and do not expand hidden folders. There is no drafts/ either — a draft is a
spec with status: draft from the first keystroke, on a branch. That is not tidiness, it
is data loss: `git clean -ndx` eats a draft that sits inside a committed directory.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import shlex
import stat
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from ai_engineering import intent, outcome, paths, spec_transaction

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#-]*$")
_NON_AUTHORITY = re.compile(r"(^|[^A-Za-z0-9])(agent|model|reviewer)([^A-Za-z0-9]|$)", re.I)
_CANONICAL_SPEC = re.compile(r"^([0-9]{3})-[a-z0-9]+(?:-[a-z0-9]+)*$")
_PENDING_SPEC = re.compile(r"^pending-([0-9]{3})-[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_FILE_BYTES = 100_000
_MAX_GRAPH_FILES = 128
_MAX_SLUG = 80
_MAX_REF = 256
_document_relations = intent._document_relations
_MISSING_AUTHORITY = intent.Validation(
    "INCOMPLETE",
    "INTENT_AUTHORITY_MISSING",
    "canonical Solution Intent is not actively approved by an accountable role",
)


def _why_not_authority(status: str, role: str, owner: str, transition: dict, approval: dict) -> str:
    """Which of the five conditions failed, in the values that failed it.

    The one message covered four different situations and named none of them. Measured on
    this repository: the Intent was active and approved, and the verb refused because
    `authority_role` read `repository owner` while `accountable_role` read
    `repository maintainer` — two names for one person, and the check compares strings. The
    refusal was correct and unreadable, so it cost an afternoon and would have cost a
    stranger more. A control that is right and illegible gets worked around rather than
    fixed.

    Four branches for five conditions is the same defect one turn later, and an independent
    reviewer proved it: an Intent differing only in `approval_ref` fell through every branch
    and was told the role was one this framework refuses to read as an authority, about the
    role it does accept. A wrong reason is worse than the one reason it replaced, because
    the reader now has somewhere confident to go and it is the wrong place. The fall-through
    is the last condition in the guard and nothing else may reach it."""

    if status != "active":
        return f"the Intent's lifecycle status is {status!r} and only 'active' grants this"
    if role != owner:
        return (
            f"the Intent was approved by {role!r} and names {owner!r} as accountable. "
            f"Whoever approves has to be whoever answers for it — if those are one person, "
            f"the two fields have to say the same words"
        )
    if transition.get("authority_role") != role:
        return (
            f"the last transition was made by {transition.get('authority_role')!r} and the "
            f"approval is held by {role!r}"
        )
    if transition.get("approval_ref") != approval.get("approval_ref"):
        return (
            f"the last transition cites approval {transition.get('approval_ref')!r} and the "
            f"approval on record is {approval.get('approval_ref')!r}. The Intent moved "
            f"without the approval moving with it"
        )
    return f"the role {role!r} is one this framework refuses to read as an authority"


BOXES = [
    "CI/CD — build, lint, test and security analysis on every push; deploy from the default branch",
    "Logs — structured JSON, one line per event, with level and service, to stdout",
    "Traces — only if this is our code and has more than one hop; no hop, no trace",
    "Errors — every uncaught exception leaves as a log with severity 17 and marks its span",
    "Health and data age — alive, age of the newest datum, and an independent recomputation",
    "External check — something outside the service verifies it and says what it could not check",
    "Second path — every published number recomputed by an independent route and compared",
    "Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI",
]

TEMPLATE = """---
id: "{number}"
slug: {slug}
status: draft
date: {today}
ref: {ref}
supersedes: ""
---

# {title}

## Who this is for, and what it is worth to them

TODO: who has this problem, what it costs them today, and what changes for them when this
is done. Named people or a named role — "the user" is a way of not deciding. A spec that
cannot say whose day gets better is a spec about the tree rather than about the work.

## Context and problem

TODO: what is true today, and what about it is a problem. Written so somebody who does
not code can follow.

## Options considered

1. TODO: the first real option, and what it costs.
2. TODO: the second. At least two, and the losers are killed in writing here.

## Decision

TODO: the one chosen, and why the others were not. If this decision constrains specs

that do not exist yet, mark it `[X]` under ## Decisions and give it a record of its own:
`ai-eng decide "<title>"`.


## Challenged once

TODO: the strongest realistic case that the decision above is wrong. Then either revise
it or keep it and say why the case fails. A challenge nobody could lose to is not one.

## Assumptions and unresolved risks

TODO: what this decision takes as true without proving it, and what is still open. Kept
apart from each other and from accepted risk: an assumption written as a fact is how a
spec stops being checkable, and `ai-eng accept` is the only thing that accepts a risk.

## Examples somebody can check

TODO: Given / When / Then for the important success, the denial and the case nobody can
decide. Observable outcomes, not intentions — an example whose Then is "it works" is a
sentence, and the undecidable path is the one that gets forgotten. At least one Then
names the command in backticks and the exact output beside it, because that is the half
of an example a script can re-run and the half a vague one cannot fake.

## Decisions

<!-- One `**D-NNN-NN — <the decision>**` per line, each with a `**Rationale:**` under it.
     Prefix a line with `- [X]` to claim the decision earns promotion: it constrains
     specs that do not exist yet, and `ai-eng decide` promotes only marked lines.
     `ai-eng decide` does not write here: it writes a record under docs/adr/. -->


## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

{boxes}
"""


def specs_dir(root: Path) -> Path:
    return root / "specs"


def _render(number: str, slug: str, ref: str) -> bytes:
    return TEMPLATE.format(
        number=number,
        slug=slug,
        today=date.today().isoformat(),
        ref=f'"{ref}"' if ref else '""',
        title=slug.replace("-", " ").capitalize(),
        boxes="\n".join(f"- [ ] {box}" for box in BOXES),
    ).encode()


def _number(inventory: spec_transaction.Inventory) -> str:
    used: set[int] = set()
    for name in inventory.names:
        if name == ".gitkeep":
            continue
        matched = _CANONICAL_SPEC.fullmatch(name) or _PENDING_SPEC.fullmatch(name)
        if matched is None:
            if name[:1].isdecimal() or name.lower().startswith("pending-"):
                raise spec_transaction.Unsafe("spec namespace contains an ambiguous identifier")
            continue
        identifier = int(matched.group(1))
        if identifier in used:
            raise spec_transaction.Unsafe("spec namespace contains a duplicate identifier")
        used.add(identifier)
    next_identifier = max(used, default=0) + 1
    if next_identifier > 999:
        raise spec_transaction.Unsafe("spec identifier range is exhausted")
    return f"{next_identifier:03d}"


def _canonical_specs(root: Path) -> list[Path]:
    home = specs_dir(root)
    try:
        home_value = home.lstat()
    except FileNotFoundError:
        return []
    if not stat.S_ISDIR(home_value.st_mode) or stat.S_ISLNK(home_value.st_mode):
        raise OSError("specs home is not one regular repository directory")
    found: list[Path] = []
    for folder in home.iterdir():
        if _CANONICAL_SPEC.fullmatch(folder.name) is None:
            continue
        folder_value = folder.lstat()
        if not stat.S_ISDIR(folder_value.st_mode) or stat.S_ISLNK(folder_value.st_mode):
            raise OSError("canonical spec entry is not one regular directory")
        candidate = folder / SPEC_FILE
        try:
            candidate_value = candidate.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(candidate_value.st_mode) or stat.S_ISLNK(candidate_value.st_mode):
            raise OSError("canonical spec file is not one regular file")
        found.append(candidate)
    return sorted(found)


EXAMPLES = "## Examples somebody can check"

# Closed on purpose. A Then that names something nobody in this repository can run is prose
# wearing a command, and the whole point of the clause is that it cannot be satisfied by
# writing three words. `git` is here because specification 019's own success example uses it
# and 019 is the only specification the gate's executable rule does not freeze.
# ponytail: closed verb list, widen it when a specification legitimately names a tool that
# is not on it — and widen it in the commit that needs it, so the reason is beside the word.
RUNNABLE = ("ai-eng", "just", "uv", "pytest", "python3", "python", "git", "gh", "npm", "node")

_SPAN = re.compile(r"`([^`]+)`")
PLAN_FILE = "plan.md"
SPEC_FILE = "spec.md"
INTENT_FILE = ".ai/intent.md"
CLAIMS_LABEL = "The claims that could start together"


TASK_FIELDS = ("file", "check", "rollback", "done when")

# The tick column: what a command may write between a task's number and its bold title, and
# the only part of a plan `approval_bytes` masks before it is signed. Written once because
# three readers have to agree on it exactly — the parser below, the canonical digest, and the
# writer that fills it. When they disagreed for one commit, every plan in the tree parsed as
# having no tasks at all.
_COLUMN = r"(?:\[[ xX]\] )?(?:<!--t:[0-9a-f]{12}--> )?"

_TASK = re.compile(r"^\s*(\d+[a-z]*)\. " + _COLUMN + r"\*\*(.+?)\*\*", re.M)
_HEADING = re.compile(r"^#{1,6} ", re.M)
_FIELD = re.compile(
    r"\*\*(file|check|rollback|done when)\*\*:?(.*?)"
    r"(?=\*\*(?:file|check|rollback|done when)\*\*|\n\n|\Z)",
    re.S,
)


def plan_tasks(text: str) -> list[dict[str, str]]:
    """Every numbered task of a plan, with the four fields the plan skill demands.

    A plan is the one document in this repository nothing could read. Across thirteen of
    them the task shape is three different things and sometimes absent, so an executor could
    not be handed a task — only the whole file, which for the governing plan is 74,216 bytes
    beside a 53,831-byte specification, re-read once per task. That is the second problem
    the specification names and the one none of the first nine repairs touched.

    A task is a numbered item whose title is bold — and the number may carry a letter, because
    twenty-six of the tasks in this tree do: `39a` through `39u` and `52a` through `52c` in
    spec 010, `6a` and `6b` in 011. Reading integers only found 90 of 116 and reported the
    other twenty-six as absent rather than as unchecked, which is a gate describing its own
    enumeration.

    Its fields run to the next task or to the next heading, whichever comes first. Returned
    as read, with no field invented: a task missing one comes back missing it, because a
    parser that fills in blanks is a parser that hides them."""

    found: list[dict[str, str]] = []
    marks = list(_TASK.finditer(text))
    for at, mark in enumerate(marks):
        end = marks[at + 1].start() if at + 1 < len(marks) else len(text)
        block = text[mark.start() : end]
        # And it stops at a heading too. A task's block ran to the next numbered item, so an
        # amendment section or a block heading between two tasks sat inside the first one —
        # and a `**file**` written in that prose was read as the task's file. No plan donates
        # a field today; 011 carries four amendment sections and is one authoring pass away.
        heading = _HEADING.search(block)
        if heading:
            block = block[: heading.start()]
        task: dict[str, str] = {"task": mark.group(1), "title": " ".join(mark.group(2).split())}
        for name, value in _FIELD.findall(block):
            task.setdefault(name, " ".join(value.split()).lstrip(": ").rstrip("."))
        found.append(task)
    return found


def runs_something(value: str) -> bool:
    """Whether a check field names a command this repository can run.

    The plan skill has asked for this since it was written — "a check is a command, never a
    judgement, and 'looks right' is not a check" — and nothing read it. The same closed list
    the examples clause uses, for the same reason: a backticked phrase that starts with a
    word nobody can type at a prompt is prose wearing a command."""

    return any((one.split() or [""])[0] in RUNNABLE for one in _SPAN.findall(value))


# The gap between a task's number and its bold title, which is the only part of a plan a
# command is allowed to write. Everything else in the file is signed as it stands.
_TASK_GAP = re.compile(r"^([ \t]*\d+[a-z]*\.) " + _COLUMN + r"(?=\*\*)", re.M)


def approval_bytes(path: Path) -> bytes:
    r"""What an approval is a signature on, which is not always the file's bytes.

    Approving a plan is signing a digest of it. Ticking a box changes bytes, so it would
    void the signature — and the answer is not a looser signature but a different subject:
    the digest is taken over the file with the tick column removed, the way a document is
    photocopied with one column masked before it is sealed. The seal then certifies what the
    plan *says*. Change a word, or a task's check command, and it moves exactly as before.

    Two anchors keep this from becoming a hole, and both are load-bearing. The `(?=\*\*)`
    lookahead means only a line that is genuinely a task — a number, then a bold title — has
    an invisible column at all; without it any numbered line of prose or of a code block
    could carry a flipped `[ ]` the signature could not see. And `spec.md` is never touched:
    its bytes are signed raw, because the eight production-ready boxes in every specification
    are a live control `readiness.py` reads. A box in a specification is a person's claim. A
    box in a plan is going to be a command's result, and the two cannot share a rule.

    Measured on this tree the day it was written: over all 16 plans and 22 specifications the
    canonical digest equals the raw digest, so this function is the identity today and no
    approval on record changes value. `specs/010/plan.md` canonicalises to 7bc96b09ed43,
    which is the number `docs/adr/0009` signs. With a box inserted on all 141 tasks and every
    one of them ticked, it is still 7bc96b09ed43."""

    raw = path.read_bytes()
    if path.name != PLAN_FILE:
        return raw
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError:
        # A plan that is not text is not a plan this can canonicalise, and guessing at its
        # bytes would change what was signed. Sign what is there and let the reader fail.
        return raw
    return _TASK_GAP.sub(r"\1 ", body).encode("utf-8")


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(approval_bytes(path)).hexdigest()


def _envelope(home: Path, wanted: str, named: dict[str, str], tick: bool = False) -> outcome.Result:
    """One task, the two digests it was read under, and nothing else.

    This is the answer to the second problem specification 019 names. An executor could not
    be handed a task, only the document holding it: 74,216 bytes of plan beside a
    53,831-byte specification, re-read once per task, because no plan had a shape a script
    could enumerate. Task 15 gave plans that shape; this hands one task over.

    Every unknown refuses rather than printing part of an envelope. A half-written one is
    worse than none — it names a file and a check that may belong to a different task, and
    the reader has no way to tell.
    """

    plan = home / PLAN_FILE
    if not plan.is_file():
        print(f"  no plan beside {home.name}, so there is no task to hand over")
        return outcome.result("INCOMPLETE")
    for what, path in (("spec", home / SPEC_FILE), ("plan", plan)):
        asked = named.get(what)
        if asked and asked != _digest(path):
            # The caller said which bytes this is about and it is not these. Refusing is the
            # whole reason an envelope can carry authority: a task extracted from a plan
            # nobody approved is a task nobody approved.
            print(f"  the {what} digest you named does not match {path.name} on disk")
            return outcome.result("INCOMPLETE")
    tasks = plan_tasks(plan.read_text(encoding="utf-8", errors="replace"))
    if not tasks:
        print(f"  {home.name} has a plan with no numbered tasks a script can enumerate")
        return outcome.result("INCOMPLETE")
    # A written task wins a collision. A plan whose "Options considered" list is numbered
    # 1. and 2. parses those as tasks with no fields, and taking the first match returned
    # the prose item and refused a task that exists and is whole. No plan in the tree has a
    # duplicate id today; the refusal it produced was the wrong answer to the right question.
    matching = [one for one in tasks if one["task"] == wanted]
    found = next(
        (one for one in matching if any(one.get(field) for field in TASK_FIELDS)),
        matching[0] if matching else None,
    )
    if found is None:
        print(
            f"  no task {wanted} in {home.name}: it has {', '.join(one['task'] for one in tasks)}"
        )
        return outcome.result("INCOMPLETE")
    # `.get`, not `in`. A bolded field marker with no value after it parses to an empty
    # string, and testing for the key printed an envelope with blank lines where the file
    # and the rollback should be — a partial envelope, which the paragraph above forbids.
    missing = [field for field in TASK_FIELDS if not found.get(field)]
    if missing:
        print(f"  task {wanted} of {home.name} carries no {', '.join(missing)}")
        return outcome.result("INCOMPLETE")

    # Verified only when the caller named the digest. With no digest named this check
    # proves nothing, and an envelope silent about the difference is one nobody can audit —
    # so it says which of the two happened rather than refusing the ordinary case, where a
    # person reading their own plan has no digest to hand.
    print(f"  task: {found['task']}  {found['title']}")
    for what, path in (("spec", home / SPEC_FILE), ("plan", plan)):
        seal = " (verified)" if named.get(what) else ""
        print(f"  {what}: {_digest(path)}{seal}")
    for field in TASK_FIELDS:
        print(f"  {field}: {found[field]}")
    if tick:
        return _tick(home, plan, found, named)
    return outcome.result("PASS")


def seal(task: str, check: str) -> str:
    """Twelve characters that say a command decided this box, and which command it was.

    The canonical digest is blind to the tick column by construction, so it would never
    notice an `[x]` somebody typed. This is what notices. It is not a secret and it is not
    meant to be one — anybody can run sha256 over two strings, which is the same standard
    `docs/adr/0009` already lives under. What it removes is the case that actually happens:
    a box ticked because somebody believed the work was done.

    Copying another task's seal changes the identifier and fails. Editing the check text
    expires the seal, and that is right rather than unfortunate: the evidence was for a
    different command."""

    return hashlib.sha256(f"{task}\n{check}".encode()).hexdigest()[:12]


def _one_command(check: str) -> tuple[list[str], str]:
    """The single runnable command a check declares, and why there is not one when there is not.

    A check field is prose with backticked spans in it. Only the spans whose first word is on
    `RUNNABLE` are commands; the rest are file names and phrases. Two of them is a refusal
    rather than a choice — picking the first would tick a box on evidence from half the
    check, and picking both would hide which one failed."""

    runnable = [one for one in _SPAN.findall(check) if (one.split() or [""])[0] in RUNNABLE]
    if not runnable:
        return [], "its check names no command this tool can run"
    if len(runnable) > 1:
        return (
            [],
            f"its check names {len(runnable)} commands and choosing one is not this tool's call",
        )
    try:
        argv = shlex.split(runnable[0])
    except ValueError as unbalanced:
        return [], f"its check does not parse as a command line: {unbalanced}"
    if not argv or argv[0] not in RUNNABLE:
        return [], "its check starts with a word that is not on the runnable list"
    return argv, ""


def _write_tick(plan: Path, task: str, mark: str) -> bool:
    """Put one task's box in the state a command just measured. True when the file moved."""

    body = plan.read_text(encoding="utf-8")
    # Concatenated rather than formatted: `_COLUMN` contains a `{12}` repeat, and `.format`
    # reads that as a field to substitute and raises on the twelfth positional argument
    # nobody passed.
    line = re.compile(r"^([ \t]*" + re.escape(task) + r"\.) " + _COLUMN + r"(?=\*\*)", re.M)
    written = line.sub(lambda hit: f"{hit.group(1)} {mark}", body, count=1)
    if written == body:
        return False
    plan.write_text(written, encoding="utf-8")
    return True


def _tick(home: Path, plan: Path, found: dict[str, str], named: dict[str, str]) -> outcome.Result:
    """Run the check a task declares and write down what happened. Nothing else writes a box.

    Three things in this order, and the order is the control. The approval is checked before
    anything executes, because running a command out of a plan nobody approved is the risk
    this whole verb exists inside. Then the command runs, without a shell, with its first
    word on the closed list. Then the result is written: exit 0 ticks the box and seals it,
    anything else leaves the box empty, removes any seal and prints the command with its
    code.

    There is no ratchet and no separate command to untick. A check that passed yesterday and
    fails today empties its own box on the next run, which is the only behaviour that keeps
    a ticked box worth reading.

    Said plainly, because it is the sharp edge here: **this executes a command taken out of a
    markdown file**. Measured over the 141 checks in this tree, 134 begin with `uv`, and
    `uv run --with ...` resolves and runs third-party code from PyPI. Saying "only two of
    them reach the network" would be false. What bounds it is the approval — the caller must
    name the digest of the plan being executed, and it must be the plan on disk."""

    if not named.get("plan"):
        print("  --tick needs --plan-digest: executing a command out of a plan nobody named")
        print("  as approved is the one thing this must not do quietly")
        return outcome.result("INCOMPLETE")
    argv, why_not = _one_command(found["check"])
    if not argv:
        print(f"  task {found['task']} was not ticked: {why_not}")
        return outcome.result("INCOMPLETE")
    try:
        done = subprocess.run(argv, cwd=plan.parent.parents[1], timeout=1800, check=False)
    except (OSError, subprocess.SubprocessError) as unrunnable:
        print(f"  task {found['task']} was not ticked: {argv[0]} did not run ({unrunnable})")
        _write_tick(plan, found["task"], "[ ] ")
        return outcome.result("INCOMPLETE")
    if done.returncode:
        _write_tick(plan, found["task"], "[ ] ")
        print(f"  task {found['task']} is open: {' '.join(argv)} exited {done.returncode}")
        return outcome.result("INCOMPLETE")
    stamp = seal(found["task"], found["check"])
    if not _write_tick(plan, found["task"], f"[x] <!--t:{stamp}--> "):
        print(f"  {' '.join(argv)} passed and task {found['task']} has no line to tick")
        return outcome.result("INCOMPLETE")
    print(f"  task {found['task']} is ticked: {' '.join(argv)} exited 0, sealed {stamp}")
    return outcome.result("PASS")


_SEALED = re.compile(r"^[ \t]*(\d+[a-z]*)\. (\[[ xX]\] )?(?:<!--t:([0-9a-f]{12})--> )?", re.M)


def _receipts(root: Path, spec_id: str) -> set[str]:
    """Which tasks of this specification a commit says something was run over.

    The store is the git history and there is nothing to maintain. `commit-msg` writes
    `Ai-Eng-Ran:` from a receipt keyed to the bytes being committed, so the trailer cannot
    be moved to a commit it did not measure — edit a file after running the suite and
    before committing, and the digest moves and no trailer is written. The absence is the
    signal, which is the property that makes this worth reading at all.

    `separator=` matters here for the same reason it does in the harness that writes them:
    without it a present trailer carries a newline, every commit that has one splits into
    two lines, and the commits that ran read as malformed while the ones that did not read
    as fine. The inversion is the whole risk."""

    try:
        listed = subprocess.run(
            ["git", "log", "--format=%(trailers:key=Ai-Eng-Ran,valueonly,separator=%x00)"],
            capture_output=True,
            text=True,
            cwd=str(root),
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    wanted = re.compile(rf"\btask:{re.escape(spec_id)}#(\d+[a-z]*)\b")
    return {hit.group(1) for hit in wanted.finditer(listed.stdout)}


def _progress(home: Path) -> outcome.Result:
    """Each task of one plan, and which of the three things is true of it.

    **sealed** — `--tick` ran this task's own check here and it exited zero. Nobody writes
    this by hand; the seal is what says so.

    **receipt** — a commit carries `Ai-Eng-Ran: task:<id>#<n>`, so a suite ran over exactly
    those bytes. This survives the box being emptied later and answers a different question:
    not "does the check pass now" but "did anything ever run for this task".

    **open** — neither. The absence is the valuable half and it is printed, not skipped: a
    report that lists what happened and stays quiet about what did not is the shape of every
    green nobody earned."""

    plan = home / PLAN_FILE
    if not plan.is_file():
        print(f"  no plan beside {home.name}, so there is no task to report on")
        return outcome.result("INCOMPLETE")
    body = plan.read_text(encoding="utf-8", errors="replace")
    tasks = plan_tasks(body)
    if not tasks:
        print(f"  {home.name} has a plan with no numbered tasks a script can enumerate")
        return outcome.result("INCOMPLETE")
    boxes = {hit.group(1): (hit.group(2) or "", hit.group(3)) for hit in _SEALED.finditer(body)}
    ran = _receipts(home.parents[1], home.name[:3])
    counted = {"sealed": 0, "receipt": 0, "open": 0}
    for task in tasks:
        box, stamp = boxes.get(task["task"], ("", None))
        ticked = box.strip() in ("[x]", "[X]") and stamp == seal(
            task["task"], task.get("check", "")
        )
        state = "sealed" if ticked else "receipt" if task["task"] in ran else "open"
        counted[state] += 1
        print(f"  {task['task']:>4}  {state:<8}  {task['title'][:64]}")
    print(
        f"  {counted['sealed']} sealed, {counted['receipt']} with a receipt and no seal, "
        f"{counted['open']} open, of {len(tasks)}"
    )
    return outcome.result("PASS")


ONE_WRITER = "one writer owns repository changes"


def _declared_width(offered: str) -> int:
    """A positive integer, or one. Absent, unparseable, zero and negative are all the same
    answer, because a scheduler that guesses wide on a number it could not read is the
    fail-open direction and this one has no other direction."""

    try:
        asked = int(offered)
    except (TypeError, ValueError):
        return 1
    return asked if asked > 0 else 1


def _width(
    declared: int, ready: list[str], root: Path, facts: list[outcome.Fact]
) -> outcome.Execution:
    """The smallest of what was offered, what is ready, and one.

    Its own function because every refusal above reaches it: a remote that did not
    answer, a claim set with a cycle, a wave read cleanly. Each of those has a different
    fact to add and the same arithmetic to run, and the first version reached the shared
    half by raising an exception four lines up from the handler that caught it."""

    widths = [declared, len(ready)]
    # The test is whether the file parses as an Intent, not whether it is non-blank. Two
    # earlier versions guarded a narrower shape each time — first the deleted file, then the
    # emptied one — and each left a way through: a byte-order mark, undecodable bytes and a
    # file of NUL bytes are all untouched by `str.strip()` and none of them is an Intent.
    # `solution_intent` already reads this file with `json.loads`, so parsing is the shape
    # the repository has rather than a new one. Specification 013's stated exit is that the
    # sentence "has been swapped for another sentence"; anything that does not parse is
    # neither the sentence nor another one, so the state is unknown, and unknown here is one.
    try:
        held = (root / ".ai" / "intent.md").read_text(encoding="utf-8")
        json.loads(held)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        held = ""
    if ONE_WRITER in held:
        widths.append(1)
        facts.append(
            outcome.fact(
                "one-writer",
                "OBSERVED",
                "The constraint the Intent holds",
                f".ai/intent.md still says {ONE_WRITER!r}, so the width is one",
            )
        )
    elif not held:
        # A separate fact because the width is the same and the reason is not. Reporting
        # "still says" over a deleted or unparseable file is a true number with a false
        # reason, which is the defect the `claim.base` probe four commits ago exists to
        # remove; it should not be reintroduced here to save a branch.
        widths.append(1)
        facts.append(
            outcome.fact(
                "one-writer",
                "INCOMPLETE",
                "The constraint the Intent holds",
                ".ai/intent.md could not be read as an Intent, so the constraint's state "
                "is unknown and the width is one",
                cure="restore .ai/intent.md, or say in it what replaced the one-writer sentence",
            )
        )
    width = max(1, min(widths))
    facts.append(
        outcome.fact(
            "width",
            "OBSERVED",
            "How many writers this build could carry",
            f"width: {width}",
        )
    )
    return outcome.execution(
        outcome.result("PASS"),
        summary=f"width: {width}",
        checks=facts,
        remaining=[],
    )


def _wave(root: Path, offered: str, remote: str) -> outcome.Execution:
    """How many writers this build could carry, computed and never spent.

    The Intent says one writer owns repository changes until a separately approved
    coordination plan proves otherwise, and specification 013 records that nothing
    executable ever read that sentence — "whatever replaces the one-writer sentence arrives
    with a check that fails, or the sentence has been swapped for another sentence". This is
    the check. While the sentence is there the answer is one whatever anybody offers, and the
    file that decided it is named, because a clamp nobody can trace is just a number.

    The width is the smallest of three: what the surface says it can run, how many claims
    have nothing in front of them, and one for every unknown. It grants nothing — the
    writers still claim through the compare-and-swap on the remote, are still confined by
    `claim_scope_guard`, and are still re-checked from the remote at the merge gate.
    """

    from ai_engineering import claim, dag

    declared = _declared_width(offered)
    ready: list[str] = []
    facts = [
        outcome.fact(
            "declared-width",
            "OBSERVED",
            "What the surface said it can run",
            f"{declared} from {offered or 'nothing offered'}",
        )
    ]
    # Asked before the claims are read, because `claim.every` skips a ref it cannot read
    # rather than failing — so an unreachable remote comes back as an empty list and reads
    # as "nobody has claimed anything". The width would be right and the reason would be a
    # lie: nothing was measured. `base` is the one call that says whether the remote answered.
    if not claim.base(root, remote):
        facts.append(
            outcome.fact(
                "wave",
                "INCOMPLETE",
                CLAIMS_LABEL,
                f"no claim was read from {remote}, so nothing there is coordinated against",
                cure="check the remote is reachable, then ask again",
            )
        )
        return _width(declared, ready, root, facts)

    try:
        ready = dag.wave(root, claim.every(root, remote))
    except (OSError, ValueError, subprocess.SubprocessError) as refused:
        facts.append(
            outcome.fact(
                "wave",
                "INCOMPLETE",
                CLAIMS_LABEL,
                f"{remote} could not be read: {refused}",
                cure="check the remote is reachable, then ask again",
            )
        )
    except dag.Unreadable as refused:
        facts.append(
            outcome.fact(
                "wave",
                "INCOMPLETE",
                CLAIMS_LABEL,
                str(refused),
                cure="split or merge the claims, or fix the file nobody can parse",
            )
        )
    else:
        facts.append(
            outcome.fact(
                "wave",
                "OBSERVED",
                CLAIMS_LABEL,
                ", ".join(ready) or "none are claimed on the remote",
            )
        )
    return _width(declared, ready, root, facts)


def examples_section(text: str) -> str:
    """The body under the examples heading, or nothing.

    One definition, because there were two and they disagreed. The gate over authored
    specifications sliced the section itself while this module partitioned it, and after a
    repair changed only one of them the two answered differently on a document that quotes
    the heading in prose — which 019, a specification about this section, is one editing pass
    from being.

    The leading newline is prepended rather than tested for. A conditional fallback here
    returned the whole document when the heading sat at position 0, so a specification with
    no section at all — quoting the heading in prose beside an example — read as having one.
    That is the fail-open direction, and it was introduced by the repair that added it.
    """

    return ("\n" + text).partition("\n" + EXAMPLES)[2].split("\n## ", 1)[0].replace("\r\n", "\n")


# Conversation leaks that make a spec unreadable by a builder who receives only the file.
# A spec is the whole interface to its builder (spec 031 / B-031-3): "as we discussed"
# cannot be resolved from the bytes alone, so the record is not governed.
_LEAKS = (
    "as we discussed",
    "as discussed",
    "the remaining work",
    "per our conversation",
    "like we said",
)


def self_contained(text: str) -> list[str]:
    """Every conversation leak the spec carries, or an empty list when self-contained."""
    folded = text.casefold()
    return [leak for leak in _LEAKS if leak in folded]


_DECISIONS_HEADING = re.compile(r"^## Decisions[ \t]*$", re.M)
# One marked decision entry under ## Decisions: `- [X] **D-NNN-NN — the decision**`.
# The marker is the author's claim that the decision earns promotion; the dash may be
# written as — – - or :, and any amount of space around the identifier is accepted.
_MARKED_DECISION = re.compile(
    r"^\s*[-*]\s+\[[xX]\]\s+\*\*(D-\d{3}-\d{2}(?:-\d+)?)[ \t]*[—–:-][ \t]*(.+?)\*\*",
    re.M,
)
_HEADING_ANY = re.compile(r"^#{1,6} ", re.M)


def _decisions_body(text: str) -> str:
    """The lines under the first `## Decisions` heading, or empty when there is none.

    The section ends at the next heading of any depth; a second `## Decisions` later in
    the document is not the decision record and is not part of it."""
    start = _DECISIONS_HEADING.search(text)
    if not start:
        return ""
    next_heading = _HEADING_ANY.search(text, start.end())
    return text[start.end() : next_heading.start() if next_heading else len(text)]


def marked_decisions(text: str) -> list[tuple[str, str]]:
    """Every decision the author marked `[X]` under ## Decisions, as `(id, title)`.

    The marker is the author's claim that the decision constrains specs that do not
    exist yet — the promotion condition `ai-eng decide` asks. The parser returns only
    marked lines, so the filter a verb applies is the record's own claim, never an
    inference about the author's intent."""
    return [
        (match.group(1), match.group(2).strip())
        for match in _MARKED_DECISION.finditer(_decisions_body(text))
    ]


def section(text: str, number: int) -> str:
    """The Nth ## heading's body, resolved by position, or empty when out of range.

    Position-based: the first `## ` heading is section 1. Duplicating a spec's content to
    reference a part is how two copies drift; this resolves the part deterministically.
    """
    heads = [m for m in re.finditer(r"^## (.+)$", text, re.M)]
    if number < 1 or number > len(heads):
        return ""
    start = heads[number - 1].start()
    end = heads[number].start() if number < len(heads) else len(text)
    return text[start:end]


def examples_facts(text: str) -> tuple[int, int, int, int]:
    """(given, when, then, thens that name a command and the output beside it).

    Counts, never a verdict: a caller decides what the numbers mean. The fourth is the one
    that cannot be faked — spec 002 refused a rule that only asked for the three words,
    because it goes green on "Given a user, When they click, Then it works".

    A Then is executable when its paragraph carries a code span whose first word is on the
    closed list above and at least one further span after it. Both halves are required: a
    command with no expected output is an instruction, and an output with the command left
    in prose is what the two specifications that have this section already carry."""

    body = examples_section(text)
    if not body:
        return (0, 0, 0, 0)

    given = when = then = executable = 0
    for chunk in body.split("\n\n"):
        flat = " ".join(chunk.split())
        given += flat.count("Given ")
        when += flat.count("When ")
        then += flat.count("Then ")
        if "Then " not in flat:
            continue
        # The whole paragraph, not the tail after `Then`. The canonical division of labour
        # puts the action in When and the observation in Then — "When `just check` runs, Then
        # it prints `2101 passed`" — and reading only the tail refused it. What is required is
        # a runnable command with at least one span after it, wherever the two sit.
        spans = _SPAN.findall(flat)
        heads = [(one.split() or [""])[0] for one in spans]
        if any(head in RUNNABLE for head in heads[:-1]):
            executable += 1
    return (given, when, then, executable)


def status_of(path: Path) -> str:
    head = path.read_text(errors="replace")[:600]
    found = re.search(r"^status:\s*(\S+)", head, re.M)
    return found.group(1) if found else "?"


def target(root: Path, named: str = "") -> Path:
    """The spec a record verb writes to. It used to be whichever directory sorted last,
    and that is not a guess anybody can check: writing spec 003, two decisions landed in
    another session's spec because a fourth directory appeared between two commands.
    Named, it is the one you named. Unnamed, it is the only candidate there is — the
    drafts if there are any, everything otherwise — and where there is more than one
    there is no answer to guess at, so it refuses and says which ones it saw."""
    if named:
        matches = [path for path in _canonical_specs(root) if path.parent.name.startswith(named)]
        if not matches:
            raise LookupError(f"no spec matches {named!r}")
        if len(matches) > 1:
            raise LookupError(
                f"{named!r} matches {', '.join(m.parent.name for m in matches)}. Name one of them."
            )
        return matches[0]
    every = _canonical_specs(root)
    candidates = [path for path in every if status_of(path) == "draft"] or every
    if not candidates:
        raise LookupError("no spec to record this against. `ai-eng spec new <slug>` first")
    if len(candidates) > 1:
        raise LookupError(
            f"{len(candidates)} specs are open — {', '.join(p.parent.name for p in candidates)}. "
            f"Name the one this belongs to with --spec."
        )
    return candidates[0]


def listing(root: Path, everything: bool) -> list[str]:
    """Derived, never hand-maintained: a hand-maintained index rots, and ours did — 198
    rows whose own third line said the details were in the git history."""
    rows = []
    for spec in _canonical_specs(root):
        head = spec.read_text(errors="replace")[:600]
        status = (re.search(r"^status:\s*(\S+)", head, re.M) or [None, "?"])[1]
        if status == "superseded" and not everything:
            continue
        title = (re.search(r"^# (.+)$", head, re.M) or [None, spec.parent.name])[1]
        rows.append(f"  {spec.parent.name:<28} {status:<12} {title}")
    return rows


def _argument(
    pattern: re.Pattern[str],
    label: str,
    *,
    allow_empty: bool = False,
    maximum: int | None = None,
):
    def parse(value: str) -> str:
        if (maximum is not None and len(value) > maximum) or (
            not (allow_empty and value == "") and pattern.fullmatch(value) is None
        ):
            raise argparse.ArgumentTypeError(f"{label} is not canonical")
        return value

    return parse


@dataclass(frozen=True, slots=True)
class _Snapshot:
    record: Mapping[str, Any] | None
    validation: intent.Validation
    observations: tuple[spec_transaction.Observation, ...]


def _schema_invalid() -> intent.Validation:
    return intent.Validation("INCOMPLETE", *intent.SCHEMA_INVALID)


def _materialize(writer: Any) -> _Snapshot:
    observations: dict[str, spec_transaction.Observation] = {}
    try:
        authority = writer.read(INTENT_FILE, maximum=_MAX_FILE_BYTES)
        observations[authority.path] = authority
        record = intent._json(authority.body)
        if not isinstance(record, dict) or not isinstance(record.get("relations"), list):
            return _Snapshot(None, _schema_invalid(), tuple(observations.values()))
        pending: list[str] = []
        for relation in record["relations"]:
            if not isinstance(relation, dict) or not isinstance(relation.get("path"), str):
                return _Snapshot(record, _schema_invalid(), tuple(observations.values()))
            pending.append(relation["path"])
        while pending:
            relative = pending.pop()
            if relative == INTENT_FILE or relative in observations:
                continue
            if len(observations) >= _MAX_GRAPH_FILES:
                validation = intent.Validation(
                    "INCOMPLETE", "INTENT_RELATION_BROKEN", "relation graph exceeds its bound"
                )
                return _Snapshot(record, validation, tuple(observations.values()))
            observed = writer.read(relative, maximum=_MAX_FILE_BYTES)
            observations[relative] = observed
            try:
                linked = _document_relations(observed.body)
            except (RecursionError, TypeError, ValueError):
                break
            pending.extend(linked)
        materialized = {path: observed.body for path, observed in observations.items()}
        validation = intent.validate(record, materialized)
        return _Snapshot(record, validation, tuple(observations.values()))
    except (RecursionError, TypeError, ValueError):
        return _Snapshot(None, _schema_invalid(), tuple(observations.values()))


def _authority(snapshot: _Snapshot) -> intent.Validation:
    """Only an exact materialized Intent snapshot may grant this bounded mutation."""
    if snapshot.validation.outcome != "PASS" or snapshot.record is None:
        return snapshot.validation
    try:
        lifecycle = snapshot.record["lifecycle"]
        approval = lifecycle["approval"]
        transition = lifecycle["transitions"][-1]
        role = approval["authority_role"]
        owner = snapshot.record["ownership"]["accountable_role"]
    except (IndexError, KeyError, RecursionError, TypeError, ValueError):
        return _schema_invalid()
    if (
        lifecycle["status"] != "active"
        or role != owner
        or transition["authority_role"] != role
        or transition["approval_ref"] != approval["approval_ref"]
        or _NON_AUTHORITY.search(role)
    ):
        return intent.Validation(
            _MISSING_AUTHORITY.outcome,
            _MISSING_AUTHORITY.code,
            _why_not_authority(lifecycle["status"], role, owner, transition, approval),
        )
    return intent.PASS


def _same_snapshot(
    before: _Snapshot,
    after: _Snapshot,
    pending: spec_transaction.Pending,
) -> bool:
    if before.validation != intent.PASS or after.validation != intent.PASS:
        return False
    left = {item.path: item for item in before.observations}
    right = {item.path: item for item in after.observations}
    if left.keys() != right.keys():
        return False
    for path, earlier in left.items():
        later = right[path]
        if (
            earlier.path != later.path
            or earlier.body != later.body
            or earlier.generation != later.generation
            or earlier.maximum != later.maximum
            or len(earlier.parents) != len(later.parents)
        ):
            return False
        for old_parent, new_parent in zip(earlier.parents, later.parents, strict=True):
            if old_parent.path != new_parent.path:
                return False
            if old_parent.path == "specs":
                if (
                    old_parent.identity != new_parent.identity
                    or new_parent != pending.home_generation
                ):
                    return False
            elif old_parent != new_parent:
                return False
    return True


@dataclass(frozen=True, slots=True)
class _Report:
    execution: outcome.Execution
    lines: tuple[str, ...]


def _incomplete_report(
    code: str,
    message: str,
    *,
    proven_pending: str | None = None,
    possible_pending: str | None = None,
    retryable: bool = True,
) -> _Report:
    if proven_pending is not None and possible_pending is not None:
        raise ValueError("pending state cannot be both proven and possible")
    changes = []
    checks = []
    remaining = ["No canonical spec was published"]
    next_actions = ["restore one stable approved Intent snapshot and run spec new again"]
    lines = [f"  INCOMPLETE  {message}"]
    if proven_pending is not None:
        relative = f"specs/{proven_pending}/spec.md"
        changes.append(
            outcome.fact(
                "spec-pending",
                "INCOMPLETE",
                "A noncanonical pending spec state requires inspection",
                relative,
            )
        )
        remaining.append(f"Inspect or remove {relative} before retrying")
        next_actions = [f"inspect {relative}; remove it only after proving it is this attempt"]
        lines.append(f"    pending: {relative}")
    elif possible_pending is not None:
        relative = f"specs/{possible_pending}/spec.md"
        remaining.append(f"If {relative} exists, inspect it before retrying")
        next_actions = [f"if {relative} exists, inspect it without assuming ownership"]
        checks.append(
            outcome.fact(
                "spec-pending-possible",
                "INCOMPLETE",
                "A stage failure left the pending path existence or ownership unproven",
                relative,
            )
        )
        lines.append(f"    possible pending: {relative}; inspect only if it exists")
    checks.append(outcome.fact("spec-publication", "INCOMPLETE", message))
    execution = outcome.execution(
        outcome.result("INCOMPLETE"),
        summary=message,
        changes=changes,
        checks=checks,
        remaining=remaining,
        next_actions=next_actions,
        execution_error=outcome.error(code, message, retryable, next_actions[0]),
    )
    return _Report(execution, tuple(lines))


def _finish(report: _Report) -> outcome.Execution:
    with contextlib.suppress(OSError, UnicodeError):
        for line in report.lines:
            print(line)
    return report.execution


def _transaction_kind(problem: spec_transaction.TransactionError) -> str:
    if isinstance(problem, spec_transaction.Busy):
        return "busy"
    if isinstance(problem, spec_transaction.Unsupported):
        return "unsupported"
    if isinstance(problem, spec_transaction.Collision):
        return "collision"
    return "unsafe"


def _transaction_incomplete(
    problem: spec_transaction.TransactionError,
    *,
    proven_pending: str | None = None,
    possible_pending: str | None = None,
) -> _Report:
    kind = _transaction_kind(problem)
    if kind == "busy":
        return _incomplete_report(
            "SPEC_TRANSACTION_BUSY",
            "another spec transaction holds the canonical Intent lock",
            proven_pending=proven_pending,
            possible_pending=possible_pending,
        )
    if kind == "unsupported":
        return _incomplete_report(
            "SPEC_TRANSACTION_UNSUPPORTED",
            "this filesystem cannot prove a safe spec publication",
            proven_pending=proven_pending,
            possible_pending=possible_pending,
            retryable=False,
        )
    if kind == "collision":
        return _incomplete_report(
            "SPEC_PUBLICATION_COLLISION",
            "the reserved spec destination is no longer exclusive",
            proven_pending=proven_pending,
            possible_pending=possible_pending,
        )
    return _incomplete_report(
        "SPEC_TRANSACTION_UNSAFE",
        "the spec transaction could not prove an unchanged safe filesystem state",
        proven_pending=proven_pending,
        possible_pending=possible_pending,
    )


def _new(root: Path, slug: str, ref: str) -> outcome.Execution:
    # The Intent is this transaction's anchor, and a repository that has never had one is
    # the ordinary state of every repository on its first day. Without this the writer
    # refused with "filesystem resolved a missing or differently spelled entry" — true about
    # a path and useless about a decision, in the command `init` closes by recommending.
    if not (root / ".ai" / "intent.md").is_file():
        return _finish(
            _incomplete_report(
                "INTENT_MISSING",
                "there is no Solution Intent here yet, and a spec is a decision inside one. "
                "Write `.ai/intent.md` first — `/ai-spec` walks through it — and run this again",
                retryable=False,
            )
        )

    candidate_name: str | None = None
    pending: spec_transaction.Pending | None = None
    try:
        with spec_transaction.writer(root, INTENT_FILE, "specs") as transaction:
            inventory = transaction.inventory()
            number = _number(inventory)
            first = _materialize(transaction)
            authority = _authority(first)
            if authority.outcome != "PASS":
                return _finish(
                    _incomplete_report(
                        authority.code or "INTENT_AUTHORITY_MISSING",
                        f"Solution Intent authority is incomplete: {authority.reason}",
                    )
                )

            final_name = f"{number}-{slug}"
            candidate_name = f"pending-{final_name}"
            body = _render(number, slug, ref)
            pending = transaction.stage(inventory, candidate_name, "spec.md", body)

            relative = f"specs/{final_name}/spec.md"
            success_line = f"  ✓ {relative}"
            completed = outcome.execution(
                outcome.result("PASS"),
                summary=f"Created governed spec {final_name}",
                changes=[
                    outcome.fact("spec-created", "APPLIED", "Created governed spec", relative)
                ],
                checks=[
                    outcome.fact(
                        "intent-authority",
                        "PASS",
                        "Solution Intent is actively approved by its accountable role",
                    ),
                    outcome.fact(
                        "authority-snapshot",
                        "PASS",
                        "Authority files and parent generations remained unchanged",
                    ),
                    outcome.fact(
                        "spec-publication",
                        "PASS",
                        "Published the spec with native no-replace semantics",
                        relative,
                    ),
                ],
                remaining=[],
                next_actions=[f"edit and review {relative}"],
            )
            changed_report = _incomplete_report(
                "INTENT_SNAPSHOT_CHANGED",
                "Solution Intent authority changed before publication",
                proven_pending=pending.name,
            )
            second = _materialize(transaction)
            second_authority = _authority(second)
            same = _same_snapshot(first, second, pending)
            if second_authority.outcome != "PASS" or not same:
                return _finish(changed_report)
            transaction.publish(pending, final_name)
            with contextlib.suppress(OSError, UnicodeError):
                print(success_line)
            return completed
    except spec_transaction.TransactionError as problem:
        if pending is not None:
            report = _transaction_incomplete(problem, proven_pending=pending.name)
        else:
            report = _transaction_incomplete(problem, possible_pending=candidate_name)
        return _finish(report)


def main(argv: list[str]) -> outcome.Result | outcome.Execution:
    parser = argparse.ArgumentParser("ai-eng spec")
    sub = parser.add_subparsers(dest="action", required=True)
    made = sub.add_parser("new")
    made.add_argument("slug", type=_argument(_SLUG, "slug", maximum=_MAX_SLUG))
    made.add_argument(
        "--ref",
        default="",
        type=_argument(_REF, "work item", allow_empty=True, maximum=_MAX_REF),
        help='a work item, e.g. "owner/repo#45"',
    )
    shown = sub.add_parser("show")
    shown.add_argument("id", type=_argument(re.compile(r"^[0-9]+$"), "spec id"))
    # Options on `show` rather than a sixth subcommand: the verb's closed list of five is
    # pinned in four places and the ten verbs are the product's shape, not a convenience.
    shown.add_argument("--task", type=_argument(re.compile(r"^[0-9]+[a-z]*$"), "task number"))
    shown.add_argument("--spec-digest", default="")
    shown.add_argument("--plan-digest", default="")
    shown.add_argument(
        "--tick",
        action="store_true",
        help="run this task's check and write what it measured into the plan",
    )
    shown.add_argument(
        "--progress",
        action="store_true",
        help="every task of this plan, and whether anything has been run for it",
    )
    listed = sub.add_parser("list")
    listed.add_argument("--all", action="store_true", help="include superseded specs")
    # The one subcommand here that reaches a remote, and the reason `spec`'s declared scope
    # names one. A claim is a decision recorded where the other machine can also read it —
    # which is what this verb is for — and it is the only shape of that decision two agents
    # who cannot talk to each other can both act on.
    taken = sub.add_parser("claim")
    taken.add_argument("item", type=_argument(_REF, "work item", maximum=_MAX_REF))
    taken.add_argument("--base", required=True, help="the exact SHA this claim is taken against")
    taken.add_argument("--path", action="append", default=[], required=True)
    taken.add_argument("--role", required=True)
    taken.add_argument("--remote", default="origin")
    width = sub.add_parser("wave")
    width.add_argument("--surface-width", dest="surface_width", default="")
    width.add_argument("--remote", default="origin")
    checked = sub.add_parser("checkpoint")
    checked.add_argument("--base", default="", help="verify this branch against that SHA or ref")
    checked.add_argument("--item", default="", help="read the claim from the remote, not here")
    checked.add_argument("--remote", default="origin")
    args = parser.parse_args(argv)

    root = paths.repo_root()
    if root is None:
        print("not inside a repository")
        return outcome.result("INCOMPLETE")
    if args.action == "wave":
        return _wave(root, args.surface_width, args.remote)
    if args.action == "checkpoint":
        from ai_engineering import checkpoint

        return checkpoint.verify(root, base=args.base, item=args.item, remote=args.remote)
    if args.action == "claim":
        from ai_engineering import claim

        return claim.take(root, args.item, args.base, args.path, args.role, args.remote)
    if args.action == "new":
        return _new(root, args.slug, args.ref)
    if args.action == "list":
        try:
            rows = listing(root, args.all)
        except OSError as why:
            print(f"  INCOMPLETE  specs could not be listed: {why}")
            return outcome.result("INCOMPLETE")
        print("\n".join(rows) if rows else "  no specs yet — `ai-eng spec new <slug>`")
        return outcome.result("PASS")
    try:
        matches = [path for path in _canonical_specs(root) if path.parent.name.startswith(args.id)]
    except OSError:
        print("  INCOMPLETE  specs could not be read safely")
        return outcome.result("INCOMPLETE")
    if not matches:
        print(f"  no spec matches {args.id!r}")
        return outcome.result("INCOMPLETE")
    if getattr(args, "progress", False):
        if len(matches) > 1:
            print(f"  {args.id!r} matches {len(matches)} specs; name one of them exactly")
            return outcome.result("INCOMPLETE")
        return _progress(matches[0].parent)
    if getattr(args, "task", None):
        if len(matches) > 1:
            print(f"  {args.id!r} matches {len(matches)} specs; name one of them exactly")
            return outcome.result("INCOMPLETE")
        return _envelope(
            matches[0].parent,
            args.task,
            {"spec": args.spec_digest, "plan": args.plan_digest},
            tick=getattr(args, "tick", False),
        )
    # All of them, named. Printing the first and saying nothing about the rest is how
    # somebody reads one spec and acts as though it were the only one that matched.
    for match in matches:
        if len(matches) > 1:
            print(f"── {match.parent.name} ── {matches.index(match) + 1} of {len(matches)}")
        try:
            body = match.read_text()
        except OSError as why:
            print(f"  INCOMPLETE  {match.parent.name} could not be read: {why}")
            return outcome.result("INCOMPLETE")
        print(body)
        # What the examples section holds, for the specifications that have one. An
        # observation and not a verdict — no status word, no exit code — because the
        # examples were written into every specification by the template and read by nothing,
        # and the honest first reader is the verb that already opens the file. Silent when
        # there is no section: sixteen of the nineteen have none, and a row of zeroes under
        # each of them is noise standing where a fact should be.
        given, when, then, executable = examples_facts(body)
        if given or when or then:
            # "N of them" would put `1 of` in this line, and `tests/test_mut_spec.py`
            # asserts that substring is absent from `show` output — it is the prefix of the
            # `1 of 2` multi-match heading. It passes today only because the template's
            # worked shape deliberately scores zero, so the guard would have been protected
            # by another task's word choice rather than by anything structural.
            print(
                f"  examples: {given} given, {when} when, {then} then, "
                f"{executable} naming a command and its output"
            )
    return outcome.result("PASS")
