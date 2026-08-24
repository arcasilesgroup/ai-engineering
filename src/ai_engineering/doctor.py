"""Twenty-seven assertions and one line.

These are not document sections: they are checks that fail. `--ci` runs the ones that
make sense on a runner and says in its output which it skipped, because a doctor that
comes out red by construction is a doctor somebody silences forever.

Three states, and the third is the honest one. OK and FAIL are obvious. COULD NOT
EVALUATE is never green and here it is not red either: it is named, with the reason,
because a green nobody earned is the failure this whole product exists to cure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from ai_engineering import __version__, audit, outcome, paths, readiness, ui, wiring

# Aliased: three loops in this file already bind `surface` to a row of the wiring table,
# and a module that shadows a local is a module somebody silently reads the wrong one of.
from ai_engineering import surface as surfaces

# A problem, or a problem and the cure that is not the one FIXES holds for this number.
# One check needs the second form: a pin can be wrong two ways and they are two commands.
Assertion = Callable[[Path | None], "str | tuple[str, str] | None"]
CHECKS: list[tuple[int, str, str, bool, Assertion]] = []


# The order the six families are read in, which is a sentence: what this repository is,
# how it is wired, whether the controls have fired, what got written down, whether what
# runs is what was pinned, and what the world outside this machine says. The registry is
# sorted by assertion number — those are cited in prose all over this repository and do not
# move — so without this the families interleave and the printer opens a new section every
# time the number's family differs from the last one. Six families, nine headings, `The
# wiring` four times. A report that looks like it lost its place is a report nobody trusts.
FAMILIES = (
    "The context",
    "The wiring",
    "The controls",
    "The record",
    "The pin",
    "The outside",
)


# The vocabulary of a coverage row, as a colour. UNPROVEN is not a failure and it is not a
# pass either, which is the entire point of the line, so it reads as the same warning as
# INERT rather than as red. Looked up by the word appearing anywhere in the row and no
# longer by the row's last token: the word is what means something, and a column that moves
# must not be able to take the colour with it.
COLOURS = {
    "BLOCKS": "ok",
    "INERT": "warn",
    "UNPROVEN": "warn",
    "ADVISES": "muted",
    "MISMATCH": "fail",
    "OPEN": "warn",
    "OK": "ok",
}

# The two sentences the block never had. Every word in it was already vocabulary — BLOCKS,
# INERT, UNPROVEN, ADVISES and the four tiers all mean something exact — and none of it was
# defined anywhere a person running `doctor` would see, so eight rows of it read as noise.
# Three lines and not two, because the block's own widest row is 95 columns and a legend
# that wraps in an eighty-column terminal is a legend that arrives as four ragged ones.
LEGEND = (
    "  BLOCKS a denial has executed here · INERT installed but asleep",
    "  UNPROVEN never denied here · ADVISES instructions only, it cannot deny",
    "  T2 can deny a call · T3 can only advise · T1 your git hooks · T0 the server's own check",
)

# What none of the rows above covers, and it closes the block rather than opening it: read
# first it is an excuse, read last it is the boundary of everything just claimed. It was
# one line reading `Bypasses that work today: --no-verify from your own shell. T1 is not
# T0`, which is true and is four pieces of vocabulary deep.
OPEN = (
    "  OPEN  --no-verify from your own shell walks past every row above, and so does",
    "        anything that never asks a surface. Only a required check on the server",
    "        (T0) stops those, and nothing on this machine can give you one.",
    "  OPEN  self_protect matches shell commands as text: `cd hooks && rm x`,",
    "        `xargs rm`, `env rm`, `patch` and a relative path all get through.",
)

# The cure for a failure, where a command is the cure. Sixteen of the twenty have none,
# and that is the honest answer for them: a TODO: marker in your own constitution, a
# hook Codex will only run once a person has approved it, and a branch protected on a
# server this machine cannot reach are not things a wheel gets to do for you.
FIXES = {
    2: "ai-eng init --global --no-project",
    11: "ai-eng init --project",
    12: "ai-eng init --global --no-project",
    13: "ai-eng init --global --no-project",
}

# The verbs `--fix` may run itself, and what it appends so each runs with nobody in front of
# it. An allow-list and not a lookup with a default: `ai-eng update` asks for a typed `y`
# before it migrates and ADR 0003 keeps that gate, so running it here waited for a keystroke
# in the middle of a repair. Assertion 12 still prints it as the cure a person types.
UNATTENDED = {"init": ["-y"]}


def families() -> list[str]:
    """Every family that has a check, in the declared order, with anything unlisted last
    rather than dropped. A printer that silently omits a section is worse than one that
    prints it in the wrong place."""
    rank = {name: index for index, name in enumerate(FAMILIES)}
    return sorted({row[1] for row in CHECKS}, key=lambda name: rank.get(name, len(rank)))


class Undecidable(Exception):
    """Raised when a check could not be evaluated. Never counted as a pass.

    It may carry a cure. Without one, "could not decide" and "could not decide, and here is
    the command that would settle it" were the same state, so a check whose answer is one
    command away had to be reported as a failure to say so — which is a red nobody earned.
    """

    def __init__(self, message: str, cure: str = "") -> None:
        super().__init__(message)
        self.cure = cure


class Noted(str):
    """A pass that has something to report, which until now had nowhere to report it.

    `EP-290` asks that the framework write only into the homes it declares *and that the
    count be published*. The refusal half executes — assertion 18 fails by name on a stray —
    and the count half could not exist, because a check returns `None` for a pass and a
    string for the problem. There was no channel at all for a passing observation, so a check
    that had looked at nineteen files and found them all correctly homed could say only the
    same nothing as a check that had looked at none.

    That is this repository's own defect one level up: a green nobody can distinguish from a
    green nobody earned. A `str` subclass is the whole of the fix. Every existing check keeps
    working untouched — `None` is still a silent pass and a plain string is still a problem —
    and a check with something to show returns it wrapped, which the runner reads as a pass
    carrying a detail rather than as a failure.
    """


def check(number: int, family: str, title: str, in_ci: bool = True):
    def decorate(fn):
        CHECKS.append((number, family, title, in_ci, fn))
        return fn

    return decorate


def git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def tracked_files(root: Path) -> list[str]:
    """The tracked repository inventory, or no answer rather than an empty inventory."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "-z"],
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise Undecidable("git could not inventory tracked files") from error
    if result.returncode:
        raise Undecidable("git could not inventory tracked files")
    try:
        rendered = result.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Undecidable("git could not inventory tracked files") from error
    if not rendered:
        return []
    if not rendered.endswith("\0"):
        raise Undecidable("git could not inventory tracked files")
    files = rendered.removesuffix("\0").split("\0")
    if any(not name for name in files):
        raise Undecidable("git could not inventory tracked files")
    return files


def intent_homes(files: list[str]) -> list[str]:
    """Tracked paths classified as Intent homes by the canonical repository contract."""
    homes = []
    for raw in files:
        path = PurePosixPath(raw)
        if not path.parts or path.parts[0].casefold() == "tests":
            continue
        if path.name.casefold().endswith("intent.md"):
            homes.append(raw)
    return homes


def events(root: Path | None) -> list[dict]:
    emit = paths.load("_emit")
    try:
        lines = emit.chain_path(root).read_text().splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def suite_result() -> dict:
    try:
        return json.loads((paths.home() / "cache" / "suite.json").read_text())
    except (OSError, ValueError) as err:
        raise Undecidable("the adversarial suite has never written a result here") from err


# ---------------------------------------------------------------- the pin


@check(12, "The pin", "What runs is what is pinned")
def pin_matches(root: Path | None) -> str | tuple[str, str] | None:
    if root is None:
        raise Undecidable("not inside a repository")
    emit = paths.load("_emit")
    pinned = emit.config(root).get("framework", {}).get("version")
    if not pinned:
        raise Undecidable("this repository has no .ai/config.toml, so nothing is pinned here")
    if pinned != __version__:
        return (
            f"the wheel running is {__version__} and this repository pins {pinned}",
            "ai-eng update",
        )
    installed = str(paths.hooks())
    for surface in wiring.detect():
        path = wiring.expand(surface["settings"]) if surface["settings"] else None
        if path is None or not path.exists():
            continue
        blob = path.read_text(errors="replace")
        if wiring.SIGNATURE in blob and installed not in blob:
            return f"{surface['name']}'s guard entry points at another install, not {installed}"
    return None


@check(15, "The pin", "No guard decides the same call twice")
def no_double_decision(root: Path | None) -> str | None:
    """Only calls the surface gave an identifier can be judged this way. Without one,
    two decisions on identical arguments are two different calls — a retry loop looks
    exactly like a double delivery, and treating them as the same is what blinds
    loop_guard. Guards record the fingerprint only when there was an identifier."""
    seen: dict[str, set[str]] = {}
    for event in events(root):
        fp = (event.get("data") or {}).get("fp")
        if event.get("cls") in ("blocked", "bypassed") and fp:
            seen.setdefault(f"{event['name']}:{fp}", set()).add(event["hash"])
    twice = [key for key, hashes in seen.items() if len(hashes) > 1]
    return (
        None
        if not twice
        else (f"{len(twice)} calls were decided twice by the same guard, e.g. {twice[0]}")
    )


# ---------------------------------------------------------------- the wiring


@check(2, "The wiring", "Every guard is registered, and points at a file that exists")
def wiring_present(root: Path | None) -> str | tuple[str, str] | None:
    dispatcher = paths.hooks() / "chain.py"
    if not dispatcher.exists():
        # An empty cure and not the one this number carries, because there is no `ai-eng`
        # command that puts it back: the dispatcher lives inside the wheel, so its absence
        # is a broken install and `--fix` must not offer to rewire around it.
        return f"the dispatcher is missing at {dispatcher}", ""
    # The same call `init.global_ready` makes, so the installer and the diagnosis cannot
    # hold two opinions about whether this machine is wired.
    on, off = wiring.wired()
    if not on and not off:
        raise Undecidable(
            "no surface that takes a guard entry is installed here, so this looked at "
            "nothing. Declining the machine half of `ai-eng init` still wires the "
            "repository, which is how a governed repository ends up on a machine with "
            "no guards at all."
        )
    return None if not off else "; ".join(f"{surface['name']} has no entry" for surface in off)


@check(3, "The wiring", "Every hook that can block is a guard, and all are classified")
def classes_are_honest(root: Path | None) -> str | None:
    chain = paths.load("chain")
    blocking = {"PreToolUse", "PostToolUse"}
    wrong = []
    for event, rows in chain.TABLE.items():
        for name, _ in rows:
            module = paths.load(name)
            kind = getattr(module.run, "hook_class", None)
            if kind is None:
                wrong.append(f"{name} is not classified")
            elif event in blocking and kind != "guard" and name != "autoformat":
                wrong.append(f"{name} is telemetry on {event}, which can block")
    return None if not wrong else "; ".join(wrong)


@check(11, "The wiring", "A git hook actually fires", in_ci=False)
def git_hook_fires(root: Path | None) -> str | tuple[str, str] | None:
    if root is None:
        raise Undecidable("not inside a repository")
    configured = git(root, "config", "--get", "core.hooksPath")
    if not configured:
        raise Undecidable("core.hooksPath is not set here: this repository has no floor")
    if configured.startswith("~"):
        return "core.hooksPath holds a tilde. Git never expands it: the hooks never fire."
    # Resolved against the repository and never against the directory the command was run
    # from. git reads a relative core.hooksPath from the root, this read it from wherever
    # you were standing, and the relative form is what this repository's own bootstrap
    # writes — so the answer depended on your shell's working directory.
    where = (root / Path(configured)).resolve()
    if not (where / "pre-commit").exists():
        return f"core.hooksPath points at {configured}, which has no pre-commit in it"
    # A pre-commit at that path proves something lives there, never that it is ours. Any
    # other tool that manages git hooks — and several do — left this check green over a
    # repository where none of our floor runs, which is the shape of green this product
    # exists to refuse.
    if where != paths.git_hooks().resolve():
        return (
            f"core.hooksPath points at {configured}, which is not the directory this "
            f"install wires. Something lives there; none of it is ours.",
            "ai-eng init --project",
        )
    return _cli_answers(root)


# The only argument lists this check will run. Not a shell, and not whatever `ai.eng` happens
# to hold: a configured value that is executed is a configured value that can be anything, on
# a machine that may already be doing what an injected instruction told it to.
_CLI_TAIL = ["-m", "ai_engineering.cli"]
_CLI_CURE = "ai-eng init --project"


def _interpreter_of(configured: str) -> str:
    """The interpreter an `ai.eng` value names, or an empty string when it names none.

    The value is always one interpreter followed by `-m ai_engineering.cli`, so the tail is
    matched exactly and whatever precedes it is the interpreter — quoted or not, with spaces
    or without. A tokeniser cannot do this: `shlex` in POSIX mode eats backslashes and in
    Windows mode keeps the quotes, and either way a path with a space becomes two arguments.
    """

    suffix = " " + " ".join(_CLI_TAIL)
    if not configured.endswith(suffix):
        return ""
    return configured[: -len(suffix)].strip().strip('"')


def _run_cli(root: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """Run this interpreter's own CLI, in the repository being diagnosed, safely.

    `PYTHONSAFEPATH` is the whole reason this helper exists. `-m` prepends the child's
    working directory to `sys.path`, and the working directory here is somebody's
    repository — so a repository holding a top-level `ai_engineering/` package had its own
    `cli.py` executed by `ai-eng doctor`, and could print a well-formed footer to make this
    assertion pass. A review planted exactly that and watched it work. The flag stops the
    implicit path entry, so the module that answers is the installed one.
    """

    return subprocess.run(
        [sys.executable, *_CLI_TAIL, *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={**os.environ, "PYTHONSAFEPATH": "1"},
    )


def _cli_answers(root: Path) -> str | tuple[str, str] | None:
    """Whether the CLI this repository names can actually answer.

    The hooks resolve the CLI through `ai.eng`, and a configured value proves only that
    somebody wrote a string. This machine was found with a live interpreter and a dead
    `ai_engineering.cli` — an editable install pointing at a deleted worktree — so the value
    read as configured, `git config --get` returned it, and every hook that used it failed.

    It asked a fourth question until specification 022: whether that CLI could sign a commit
    footer. That footer is deleted, and the three questions left are the ones with a cure —
    is a CLI named, is it this install's, and does it run.
    """

    configured = git(root, "config", "--get", "ai.eng")
    if not configured:
        raise Undecidable("ai.eng is not set here, so the hooks have no CLI to resolve", _CLI_CURE)
    # Compared by shape rather than by tokenising. POSIX quoting eats a Windows path's
    # backslashes and every splitter cuts `C:\Program Files\...` in two, so both spellings
    # were permanently red — with a cure that rewrites the same unsplittable value, which
    # is a loop and not a repair. The value has one exact shape, so it is read as one.
    if _interpreter_of(configured) != sys.executable:
        return (
            "ai.eng does not name this interpreter and this module, so what the hooks run "
            "is not what this install would run",
            _CLI_CURE,
        )
    try:
        alive = _run_cli(root, ["--version"])
    except (OSError, subprocess.SubprocessError) as why:
        raise Undecidable(
            f"the CLI `ai.eng` names could not be executed: {why.__class__.__name__}",
            _CLI_CURE,
        ) from why
    if alive.returncode != 0 or "ai-engineering" not in alive.stdout:
        return (
            "the CLI `ai.eng` names is installed and does not run: the hooks resolve a "
            "module that answers nothing",
            _CLI_CURE,
        )
    return None


@check(13, "The wiring", "Every symlink resolves and the doctrine is loaded")
def links_resolve(root: Path | None) -> str | tuple[str, str] | None:
    """The doctrine half is answered first, because it can be answered without a receipt
    and dropping a real failure to report could-not-evaluate would be the same trade in
    the other direction."""
    claude = (root / "CLAUDE.md") if root is not None else None
    if claude and claude.exists() and "@./AGENTS.md" not in claude.read_text(errors="replace"):
        # No cure, and this is the half of the check that has none: CLAUDE.md is the user's
        # file from the moment it is written and no verb here edits it again.
        return (
            "CLAUDE.md does not import AGENTS.md, so the doctrine never reaches the model",
            "",
        )
    roots = {wiring.expand(s["skills"]) for s in wiring.detect() if s.get("skills")}
    if not roots:
        raise Undecidable(
            "no surface with a skills root is installed here, so there is nothing to "
            "resolve. An empty loop is not a passing check."
        )
    # Inside the directory, and not the directory. This asked whether the recorded root
    # exists — and a skills root exists because the surface made it, and keeps existing
    # because it holds skills that belong to the user. So on a machine where every link of
    # ours had just been deleted, the check titled "Every symlink resolves" reported ok.
    # Its own Undecidable branch above says an empty loop is not a passing check, and it was
    # keyed on the receipt having no link rows, which a receipt that never shrank could not
    # reach. This is the same sentence, applied one level down where the emptiness is.
    empty = sorted(str(root) for root in roots if root not in set(wiring.linked()))
    if not empty:
        return None
    return f"{len(empty)} skills roots hold none of ours: {empty[0]}"


@check(21, "The wiring", "Per-surface liveness: installed is not the same as running")
def surfaces_alive(root: Path | None) -> str | tuple[str, str] | None:
    found = wiring.detect()
    if not found:
        raise Undecidable("no surface is installed here, so none of them can be running")
    # A surface with no entry of ours is not inert, it is unwired, and the two have
    # different cures. This told you to type /hooks in Codex to approve a guard that was not
    # there to approve — ADR 0003's rule failing on a shape spec 007 wrote it before seeing.
    _, off = wiring.wired()
    missing = {s["id"] for s in off}
    problems, unwired = [], []
    for surface in found:
        if surface["id"] in missing:
            unwired.append(f"{surface['name']}: no entry of ours, so nothing can run")
            continue
        if surface.get("trust_required"):
            trusted = any(
                (wiring.expand("~/.codex") / name).exists()
                for name in ("trust.json", "hooks-trust.json")
            )
            if not trusted:
                problems.append(f"{surface['name']}: installed but INERT — run /hooks in Codex")
        if surface.get("heartbeat"):
            beat = paths.home() / "cache" / "opencode-heartbeat"
            fresh = beat.exists() and (time.time() - beat.stat().st_mtime) < 86400
            if not fresh:
                problems.append(
                    f"{surface['name']}: the plugin has not reported loading. "
                    f"A malformed plugin is dropped with no error and no log."
                )
    if unwired:
        # First, and with its own cure: approving an entry nobody has written is not a
        # thing a person can do, so naming the command that writes it comes before naming
        # the one that approves it.
        return "; ".join(unwired + problems), FIXES[2]
    return None if not problems else "; ".join(problems)


# ---------------------------------------------------------------- the record


@check(6, "The record", "The hash chain is intact and writable")
def chain_intact(root: Path | None) -> str | None:
    emit = paths.load("_emit")
    path = emit.chain_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # It used to return ok here, having proved that a directory can be created. There
        # was nothing to be intact and nothing had been written, so the one assertion in
        # the set that measured nothing was the one that called it clean.
        raise Undecidable("nothing has been written to this chain yet")
    prev = ""
    # audit.read and not events(): events() drops a line it cannot parse, which is how this
    # assertion used to walk a chain cut mid-write and call it intact. The two readers of
    # this file now agree about what a cut looks like.
    for index, event in enumerate(audit.read(root), 1):
        if event.get("cls") == "unreadable":
            return f"link {index} is not JSON — a write was cut here"
        if event.get("prev") != prev:
            return f"link {index} does not extend the one before it"
        prev = event.get("hash", "")
    # And the seal, asked of the verifier rather than re-implemented. This walked `prev`
    # and `hash` only, so a link sealed as `outcome: "edited"` — the literal tamper marker,
    # whose hashes all match precisely because it was sealed truthfully — passed here while
    # `ai-eng audit verify` refused the same file. Measured on the operator's machine:
    # the verifier exits 1 on 22 broken links while this printed "the hash chain is intact
    # and writable". Two readers of one file, two verdicts, and the greener one is the one
    # on the summary screen. That direction is what makes it a defect.
    broken = [why for kind, why in audit._chain_findings(audit.read(root)) if kind == "BROKEN"]
    return broken[0] if broken else None


# A session is minutes; a day is two orders of magnitude more. Anything older than this
# waiting in the buffer is not a session in progress, it is a seal that stopped.
SEAL_MAX_AGE = 86_400


@check(22, "The record", "The buffer is being sealed into the chain")
def buffer_sealed(root: Path | None) -> str | None:
    """Half of "survives losing the laptop" is the seal, and nothing measured whether it
    still runs. `flush()` has exactly one caller outside the suite, on `SessionEnd`/`Stop`;
    if that path stops firing, every event since sits in a file inside the clone, outside
    the hash chain, and no assertion says a word. Measured on this repository's own machine:
    987 sealed links stopping on 2026-08-12 beside a buffer past 4,500 lines and growing.

    A buffer is not a failure — it is where events live between seals. A buffer whose
    oldest line has been waiting longer than any session lasts is a different statement."""

    emit = paths.load("_emit")
    buffer = emit.buffer_path(root)
    if buffer is None or not buffer.exists():
        return None
    lines = [line for line in buffer.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None
    oldest = ""
    for line in lines:
        try:
            stamp = json.loads(line).get("ts", "")
        except ValueError:
            continue
        if isinstance(stamp, str) and stamp and (not oldest or stamp < oldest):
            oldest = stamp
    if not oldest:
        return None
    try:
        waited = datetime.now(UTC) - datetime.fromisoformat(oldest)
    except (TypeError, ValueError):
        return None
    if waited.total_seconds() <= SEAL_MAX_AGE:
        return None
    return (
        f"{len(lines)} events unsealed, the oldest waiting since {oldest[:19]}: "
        f"the session hook that seals the buffer has not run"
    )


@check(23, "The record", "Declared capabilities say whether anything enforces them")
def capabilities_enforced(root: Path | None) -> str | None:
    """`policy/capabilities.toml` declares fifteen capabilities with read roots, write
    roots, exec allowlists, network hosts, secrets and human gates. Until `executor.py`
    existed, `capability.preflight` validated all of it and then returned
    `CAPABILITY_ENFORCEMENT_UNAVAILABLE` on every path — the honest answer, pinned by a
    test, and a declaration nobody enforces and nobody flags is the shape of a false green.

    Half of that is now closed and the half that is not is what this line is for. An action
    performed through a `Sandbox` is enforced: the path is resolved at the moment of the
    operation, the executable comes off the allowlist, the human gate is asked, and the
    decision lands in a corpus under the proof id the manifest declared. An action performed
    by a *surface* is not, and cannot be from here — nothing reads a running capability's
    identity out of somebody else's payload, and no receipt has ever shown one being sent.

    So this stays undecidable rather than becoming a pass. "Some actions are enforced" is
    not an answer a person can act on unless it also says which, and the sentence below
    says which.

    Reported as undecidable and not as a failure, which is a correction. FAIL is what an
    executed check says when it conclusively finds a violation; nothing executed here,
    because the executor is what does not exist. The message is unchanged and still prints,
    now under "Not evaluated", where the line beneath it reads "None of these is a pass."
    That is the same warning without the wrong word on it — and the wrong word was load
    bearing: it made `doctor` FAIL on every machine, forever, which is a red nobody can
    clear and therefore a red everybody learns to ignore."""

    from ai_engineering import capability

    try:
        declared = capability._validated(None)["capabilities"]
    except Exception:  # the manifest has its own assertion; this one is about enforcement
        return None
    if not declared:
        return None
    # What is missing, named, because "no executor exists yet" is true and tells a reader
    # nothing about whether the gap is ours or the surface's. Two things are absent and only
    # one of them is in our hands: nothing here reads a running capability's identity out of
    # a payload, and no receipt has ever shown a surface putting one there. Those are
    # different claims — the first is a gap in this tree, the second is a measurement about
    # somebody else's software that has never been taken. Saying "no surface sends it" would
    # be asserting the second from the first.
    raise Undecidable(
        f"{len(declared)} capabilities are declared and only this framework's own actions "
        f"are enforced: an action taken through `executor.Sandbox` is decided at the "
        f"operation, and one taken by a surface is not. An executor needs the running "
        f"capability's identity to arrive with the action, and nothing here reads one — nor "
        f"has any receipt yet shown a surface sending one"
    )


@check(24, "The wiring", "Every generated router is still the one we generated")
def routers_intact(root: Path | None) -> str | tuple[str, str] | None:
    """A router is a file this installer wrote into somebody's home, so it owes the same
    answer as every other file it wrote: is it there, and is it ours.

    The digest travels in the receipt beside the path. A router that is gone was removed by
    somebody and that is their business — it is reported, not repaired, because `--fix`
    rewriting a file a person deleted is the installer overruling them. A router that is
    there and different is the more interesting state: somebody wanted something else, and
    `uninstall` will now leave it alone rather than deleting their work.
    """

    recorded = [row for row in wiring.receipt().get("wrote", []) if row.get("kind") == "router"]
    if not recorded:
        raise Undecidable("no router has been written here, so there is none to check")

    # The path that gets opened is built here, from the surface table and a file name — the
    # string recorded in the receipt is never used as a path at all. That is the difference
    # between bounding a risk and removing it, and it took two attempts to see.
    #
    # The receipt is a file on disk, so a path inside it is only as trustworthy as that file,
    # and this loop opens whatever it names. Checking the recorded string and then opening it
    # left the shape intact: an entry redirected to any readable file would still be hashed,
    # and the check would report whether the digest matched, which is an oracle. Somebody who
    # can rewrite the receipt is already inside the framework's own home — and that is the
    # argument that ends with a control nobody bounded.
    #
    # So the recorded row contributes a name and nothing else. A router lives in a directory
    # the surface table declares, it is called `ai-<something>.md`, and it is a regular file
    # rather than a link to one. A row that does not resolve to exactly that is reported and
    # never opened, which is also the more useful answer for whoever is reading the report.
    #
    # "A link to one" covers both kinds, and the second was missed. `is_symlink()` is False
    # for a hard link, so `os.link(secret, root/"ai-oracle.md")` put the oracle back: guess
    # the digest right and the row is silent, guess it wrong and the report says
    # `1 edited (ai-oracle.md)`. Narrower than what it replaced — it needs a write into a
    # declared command root — but a bound that names links and reads only one of the two
    # kinds is the defect this file exists to find, so `st_nlink` is asked as well. A
    # legitimate router has one name.
    def _hard_linked(path: Path) -> bool:
        """More than one name for these bytes. A router has one; an oracle needs two."""

        try:
            return path.stat().st_nlink > 1
        except OSError:
            return False

    roots = [
        wiring.expand(row["commands"]) for row in wiring.table()["surface"] if row.get("commands")
    ]
    missing, edited, astray = [], [], []
    for row in recorded:
        name = Path(str(row.get("path", ""))).name
        rebuilt = [root / name for root in roots if (root / name).parent in roots]
        if not (name.startswith("ai-") and name.endswith(".md")) or not rebuilt:
            astray.append(name or "<unnamed>")
            continue
        target = next((one for one in rebuilt if one.exists()), rebuilt[0])
        if target.is_symlink() or _hard_linked(target):
            astray.append(name)
            continue
        _, _, digest = str(row.get("how", "")).partition(" ")
        if not target.is_file():
            missing.append(name)
        elif hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            edited.append(name)
    if not missing and not edited and not astray:
        return None
    said = []
    if missing:
        said.append(f"{len(missing)} removed ({', '.join(sorted(missing)[:3])})")
    if edited:
        said.append(f"{len(edited)} edited ({', '.join(sorted(edited)[:3])})")
    if astray:
        said.append(
            f"{len(astray)} recorded outside any command root and not read "
            f"({', '.join(sorted(astray)[:3])})"
        )
    return (
        f"of {len(recorded)} routers, {' and '.join(said)}",
        "`ai-eng init` writes them again; an edited one is left alone by `uninstall`",
    )


@check(27, "The wiring", "The opt-in hooks template is present, ours, and removable")
def hooks_template_owned(root: Path | None) -> str | tuple[str, str] | None:
    """D-024-01's observability half. The machine's hooks template and its global key are a
    state doctor can see: a template the receipt says we wrote, a directory still holding the
    shipped bytes, and a global key still pointing at it are all consistent and all fine; a
    receipt row with no template is a removable gap; a template with no row is not ours to
    explain. It is a machine-state check, so it answers outside a repository too."""

    template = paths.home() / "hooks-template"
    recorded = [
        row for row in wiring.receipt().get("wrote", []) if row.get("kind") == "hooks-template"
    ]
    try:
        read = subprocess.run(
            ["git", "config", "--global", "--get", "init.templateDir"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        pointed = read.stdout.strip() if read.returncode in (0,) else ""
    except (OSError, subprocess.SubprocessError):
        raise Undecidable("git config could not be read to inspect the hooks template")

    if not recorded and not template.exists():
        return None  # the feature is opt-in; a machine that never opted in is fine
    if not recorded or not template.is_dir():
        return (
            "the hooks template and its receipt disagree on what is installed here",
            "`ai-eng uninstall` removes the key, or `ai-eng init --hooks-template` rewrites it",
        )
    names = ("pre-commit", "commit-msg", "pre-push")
    try:
        owned = all((template / name).is_file() for name in names) and pointed == str(template)
    except OSError:
        owned = False
    if not owned:
        return (
            "the hooks template is recorded but no longer the bytes we wrote, or the global "
            "key no longer points at it",
            "`ai-eng uninstall` to remove it cleanly, then `ai-eng init --hooks-template`",
        )
    return None


@check(10, "The record", "Continuity: this head extends the last archived one")
def continuity(root: Path | None) -> str | None:
    emit = paths.load("_emit")
    seq, _ = emit.head(emit.chain_path(root))
    archived = paths.home() / "state" / emit.repo_id(root) / "archived.json"
    if not archived.exists():
        return None
    last = json.loads(archived.read_text()).get("seq", 0)
    return (
        None
        if seq >= last
        else (
            f"the chain is at {seq} and the archive already recorded {last}: "
            f"it was reset or truncated"
        )
    )


@check(16, "The record", "No risk acceptance is past its expiry")
def acceptances_current(root: Path | None) -> str | None:
    from ai_engineering import accept

    if root is None:
        raise Undecidable("not inside a repository")
    try:
        stale = accept.expired(root)
    except ValueError as why:
        raise Undecidable(str(why)) from why
    return (
        None
        if not stale
        else "; ".join(f"{row['id']} expired {row['expires']}" for row in stale[:3])
    )


@check(17, "The record", "The record is committed and the state is not")
def polarity(root: Path | None) -> str | None:
    if root is None:
        raise Undecidable("not inside a repository")
    intent_home = ".ai/intent.md"
    tracked = {name for name in tracked_files(root) if name.startswith(".ai/")}
    # The pin, plus the research documents this repository's work is judged against. Those
    # are inputs and not state: nobody's machine produced them, editing one to fit would be
    # the defect, and until they were committed the requirement ledger was the only in-tree
    # record of what they asked. The rule is written twice on purpose — here and in
    # `.ai/.gitignore` — and CI caught this reader still holding the old list while the other
    # had moved, which is the check working rather than duplication nobody wanted.
    #
    # A shape rather than a list, on both sides. Naming each report meant every report after
    # the second was state by default, and three of them were: they lived only on the machine
    # that made them, ordered by a file date a `git checkout` rewrites. Three digits, a
    # hyphen, a name, `.html`, directly under `reports/`.
    allowed = {
        ".ai/.gitignore",
        ".ai/config.toml",
        intent_home,
        readiness.DECLARATION,
    }
    report = re.compile(r"^\.ai/reports/[0-9]{3}-[^/]+\.html$")
    problems = []
    if intent_home not in tracked:
        problems.append(f"Solution Intent is not tracked at {intent_home}")
    # A receipt for one of the boxes, and not merely the folder they live in. That folder
    # holds every check-evidence receipt this machine writes — the adversarial suite puts
    # four of its own there — and keying on its existence made running that suite red this
    # assertion in a class nothing can repair.
    if (
        any((root / readiness.RECEIPTS / f"{box.id}.json").exists() for box in readiness.BOXES)
        and readiness.DECLARATION not in tracked
    ):
        # Receipts are this machine's, and are ignored. The requirement they are measured
        # against is everybody's, and is reviewed — so a repository holding receipts whose
        # declaration nobody has committed is one where the same hand wrote the question
        # and the answer, which is the one thing the readiness verifier exists to prevent.
        # With the remedy in it, because there is no verb that performs it: `.ai/.gitignore`
        # is written once and never rewritten, so a repository set up by an earlier release
        # has an ignore file that drops this declaration silently on `git add -A`.
        problems.append(
            f"receipts are here and {readiness.DECLARATION} is not committed — add "
            f"!{PurePosixPath(readiness.DECLARATION).name} to .ai/.gitignore, then commit it"
        )
    extra = {name for name in tracked - allowed if not report.fullmatch(name)}
    if extra:
        problems.append(f"state slipped into git: {sorted(extra)[:3]}")
    return None if not problems else "; ".join(problems)


@check(18, "The record", "Your data is yours: every framework file has a declared home")
def data_is_yours(root: Path | None) -> str | None:
    from ai_engineering import intent

    if root is None:
        raise Undecidable("not inside a repository")
    homes = (".ai/", "specs/", "docs/adr/")
    problems = []
    tracked = tracked_files(root)
    strays = [
        name
        for name in tracked
        if name.startswith(".ai-engineering/") or name.endswith(".ai-eng.json")
    ]
    if strays:
        problems.append(
            f"{len(strays)} framework files are committed outside {', '.join(homes)} — "
            f"the first is {strays[0]}. That is the first step back toward 528 of them."
        )
    intent_home = ".ai/intent.md"
    mirrors = [candidate for candidate in intent_homes(tracked) if candidate != intent_home]
    if mirrors:
        problems.append(f"Solution Intent is also tracked outside {intent_home}: {mirrors[0]}")
    source = root / intent_home
    if not source.is_file():
        problems.append(f"Solution Intent is missing at {intent_home}")
    else:
        result = intent.validate(source, root)
        if result.outcome != "PASS":
            problems.append(
                f"Solution Intent at {intent_home} is {result.outcome}: "
                f"{result.code} — {result.reason}"
            )
    if problems:
        return "; ".join(problems)
    # The published count. Not a decoration: `EP-290` asks for it by name, and the reason it
    # is worth publishing is that "no strays" and "nothing was inventoried" print the same
    # word. A number beside the pass is the difference between the two.
    return Noted(
        f"{len(tracked)} tracked files inventoried, {len(intent_homes(tracked))} Intent home"
        f"{'' if len(intent_homes(tracked)) == 1 else 's'}, none outside {', '.join(homes)}"
    )


@check(25, "The record", "No declared capability has a second handler in this repository")
def one_handler_each(root: Path | None) -> str | None:
    """`EP-164` asks that `ai-spec` be pinned to one mode and that nothing be able to stand
    up a second handler elsewhere. The first half was pinned by a test reading the manifest's
    own content, which proves the manifest says what it says and nothing about elsewhere.

    Elsewhere is where it matters. A capability is a name a surface routes on, so a second
    `SKILL.md` calling itself `ai-spec` — in `.claude/skills/`, in a vendored copy, anywhere
    a surface reads — is a second answer to the same request, and which one runs depends on
    the surface's own search order rather than on anything declared here. That is the exact
    shape of an ungoverned handler: it looks installed, it answers, and no record of this
    framework mentions it.

    Only tracked files are considered. An untracked scratch copy is somebody's working
    directory and not this check's business, and reading the whole tree would also mean
    reading `node_modules`.

    The framework's own tree is the one legitimate home and is excluded by path, not by
    name. Excluding by name would mean any file that declared itself canonical was.
    """

    if root is None:
        raise Undecidable("not inside a repository")
    from ai_engineering import capability

    try:
        declared = {entry["id"] for entry in capability._validated(None)["capabilities"]}
    except Exception as broken:  # the manifest has its own assertion; this one is about homes
        raise Undecidable("the capability manifest could not be read here") from broken

    canonical = paths.skills().resolve()
    found: dict[str, list[str]] = {}
    for name in tracked_files(root):
        if not name.endswith("SKILL.md"):
            continue
        where = (root / name).resolve()
        if where == canonical or canonical in where.parents:
            continue
        # The declared name, from the frontmatter, and not from the directory. A handler is
        # found by what it calls itself: a surface reads the name, so a directory renamed to
        # hide a duplicate would still route.
        try:
            head = (root / name).read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        for line in head.splitlines():
            if line.startswith("name:"):
                claimed = line.split(":", 1)[1].strip()
                if claimed in declared:
                    found.setdefault(claimed, []).append(name)
                break

    if not found:
        return None
    detail = "; ".join(f"{one}: {', '.join(sorted(where))}" for one, where in sorted(found.items()))
    return (
        f"{len(found)} declared capabilities have a second handler committed here — {detail}. "
        "Which one answers is the surface's search order, not a decision anything recorded."
    )


# ---------------------------------------------------------------- the controls


@check(7, "The controls", "Liveness: the suite exercised every guard in the last 7 days")
def guards_alive(root: Path | None) -> str | None:
    result = suite_result()
    age = (time.time() - float(result.get("at", 0))) / 86400
    if age > 7:
        return f"the adversarial suite last ran {age:.0f} days ago"
    missed = [name for name, ok in result.get("guards", {}).items() if not ok]
    return None if not missed else f"the suite could not fire {', '.join(missed)}"


@check(8, "The controls", "Signal ratio: what is recorded is what was decided")
def signal_ratio(root: Path | None) -> str | None:
    rows = events(root)
    if len(rows) < 50:
        raise Undecidable(f"only {len(rows)} events recorded so far; too few to judge")
    real = sum(1 for e in rows if e.get("cls") in ("blocked", "bypassed", "command"))
    ratio = real / len(rows)
    return (
        None
        if ratio >= 0.10
        else (
            f"{ratio:.2%} of the record says something was decided. Below 10% you are "
            f"recording noise."
        )
    )


@check(9, "The controls", "The acceptance suite has not rotted")
def suite_fresh(root: Path | None) -> str | None:
    result = suite_result()
    if not result.get("deterministic_green"):
        return "the deterministic half of the suite is not green"
    stamp = result.get("real_model_at")
    if not stamp:
        # Never run and gone stale are different answers, and this returned the second for
        # both. The real-model half needs a key and somebody's spend — that is R-001-02,
        # accepted and dated — so nothing on a runner or on a fresh machine can ever write
        # this field, and a failure here made `ai-eng doctor --ci` impossible to pass
        # anywhere. Undecidable is what this file already has for a question it cannot ask,
        # and it is never counted as a pass.
        raise Undecidable("the real-model half has never run here; it needs a key and spend")
    if (time.time() - float(stamp)) / 86400 > 7:
        return "the real-model half's last green result is more than 7 days old"
    return None


# ---------------------------------------------------------------- the context


@check(1, "The context", "Every SKILL.md meets the contract")
def skills_contract(root: Path | None) -> str | None:
    from ai_engineering import contract

    problems = contract.audit(paths.skills())
    return None if not problems else f"{len(problems)} problems, first: {problems[0]}"


# A year. An argued criterion is held by a sentence rather than by a test, and a sentence
# about a product that ships every few weeks goes stale without anybody noticing — which is
# the whole reason `EP-293` asked for the age of one. Long enough that re-reading five
# paragraphs is not a chore, short enough that nobody inherits an argument nobody made.
ACCESSIBILITY_MAX_AGE = 365


@check(26, "The context", "Every accessibility criterion is checked or argued, never neither")
def accessibility_floor(root: Path | None) -> str | None:
    """`policy/accessibility.toml` names the release floor, and this is what stops it being
    a level named in a document.

    The file is deliberately smaller than WCAG, because WCAG is written for pages and this is
    a command-line tool — so each criterion says either how it is checked or why it cannot
    be. What it must never say is neither. A criterion with no check and no reason is a claim
    about accessibility nobody made and nobody can refuse, which is the shape of every false
    green this repository exists to remove.

    Read here rather than only in the suite, and that is the whole reason this function
    exists. A policy file only a test reads is a file that governs the tests — the repository
    has its own check for exactly that, and it caught this one on the commit that added it.
    The floor ships in the wheel, so the machine it was installed on is where it is asked.
    """

    from ai_engineering import paths as _paths

    try:
        policy = tomllib.loads(_paths.policy("accessibility.toml").read_text(encoding="utf-8"))
        criteria = policy["criterion"]
        journeys = policy["journey"]
        level = policy["floor"]["level"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as broken:
        raise Undecidable("the accessibility floor cannot be read here") from broken

    silent = [
        row.get("id", "?")
        for row in criteria
        if not row.get("checked") and len(str(row.get("reason", "")).strip()) < 30
    ]
    if silent:
        return (
            f"{len(silent)} criteria are neither checked nor argued for: {', '.join(silent)}. "
            "A criterion with no check and no reason is a claim nobody made"
        )
    executed = [row for row in criteria if row.get("checked")]
    if not executed:
        return f"the floor claims {level} and nothing in it executes"
    if not journeys:
        return "no critical journey is enumerated, so coverage over them is a share of nothing"

    # `EP-293` asked for the age of an accessibility exception, and the answer used to be
    # that none had ever been recorded, so there was nothing to age. There are five now, and
    # this is what makes the date mean something: a criterion that executes is re-read by its
    # test on every run, and one held by a sentence is re-read only when somebody decides to.
    # A year without is not a failure — nothing broke — but it is worth a person's attention,
    # so it says so and does not block.
    stale = []
    for row in criteria:
        if row.get("checked"):
            continue
        try:
            when = datetime.strptime(str(row.get("reviewed", "")), "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            return f"criterion {row.get('id', '?')} is argued and carries no date it was read"
        if (datetime.now(UTC) - when).days > ACCESSIBILITY_MAX_AGE:
            stale.append(f"{row.get('id', '?')} ({when.date()})")
    if stale:
        raise Undecidable(
            f"{len(stale)} accessibility exceptions have gone a year without being re-read: "
            f"{', '.join(stale)}. Nothing broke; a sentence held them and nobody has looked"
        )
    return None


@check(4, "The context", "The doctrine is short, present and filled in")
def doctrine(root: Path | None) -> str | None:
    if root is None:
        raise Undecidable("not inside a repository")
    problems = []
    agents = root / "AGENTS.md"
    if not agents.exists():
        problems.append("AGENTS.md is missing")
    elif len(agents.read_text(errors="replace").splitlines()) > 150:
        problems.append("AGENTS.md is over 150 lines: the always-loaded budget has escaped")
    identity = root / "CONSTITUTION.md"
    if not identity.exists():
        problems.append("CONSTITUTION.md is missing: this project's identity was never written")
    elif "TODO:" in identity.read_text(errors="replace"):
        problems.append("CONSTITUTION.md still has TODO: markers. A person fills those in.")
    return None if not problems else "; ".join(problems)


# Assertion 5 was here: the product repository is under its line ceiling. It duplicated a
# test that ran in the same CI job eleven lines apart, and it refused to evaluate anywhere
# outside this repository, so it never told a user anything. Both it and the ceiling itself
# are gone now — the number was obliged to follow the tree it bounded.


# ---------------------------------------------------------------- the outside


@check(14, "The outside", "T0: the default branch is protected on the server")
def branch_protection(root: Path | None) -> str | None:
    if root is None:
        raise Undecidable("not inside a repository")
    if shutil.which("gh") is None:
        raise Undecidable("gh is not installed, so the server could not be asked")
    branch = git(root, "rev-parse", "--abbrev-ref", "origin/HEAD").rsplit("/", 1)[-1] or "main"
    out = subprocess.run(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/branches/{branch}/protection"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        raise Undecidable("the API call did not succeed — a fork, or a token without permissions")
    body = json.loads(out.stdout or "{}")
    if not body.get("required_status_checks", {}).get("contexts"):
        return (
            "the default branch has no required check. Nothing a person types locally "
            "skips T0, and nothing else offers that."
        )
    return None


# A marker the template ships and nobody replaced. Anchored to the start of a line, with a
# list marker allowed before it, and never assertion 4's unanchored `"TODO:" in text`: that
# form has exactly one red across every spec in this tree, and it is the document that
# proposed the rule, which quotes the literal strings three times as evidence. A gate whose
# only red in the whole repository is the spec arguing for it is a trap. Anchored, it has
# four reds on the template `ai-eng spec new` writes — which is the entire target — and
# none on any spec anybody has written.
MARKER = re.compile(r"^\s*(?:[-*]|\d+\.)?\s*TODO:", re.M)


@check(19, "The outside", "Nothing shipped with a box ticked and no command beside it")
def production_ready(root: Path | None) -> str | None:
    """The old title said the work was finished, which this cannot see. What it can see is
    the tick and what is written beside it, and it used to read neither: it searched a
    shipped spec for an unticked box and never once looked at a ticked one, so the gate
    enforced that the question was answered and never that the answer said anything. Three
    of the eight boxes in this repository's own shipped spec claimed a control and named no
    command. A backtick proves something was named, never that it passed."""
    if root is None:
        raise Undecidable("not inside a repository")
    bad = []
    for spec in sorted((root / "specs").glob("*/spec.md")) if (root / "specs").exists() else []:
        text = spec.read_text(errors="replace")
        if not re.search(r"^status:\s*shipped", text, re.M):
            continue
        boxes = [line.strip() for line in text.partition("## Production-ready")[2].splitlines()]
        unproven = [
            box
            for box in boxes
            if box.startswith("- [x]") and "`" not in box and "not applicable" not in box.lower()
        ]
        if unproven or any(box.startswith("- [ ]") for box in boxes) or MARKER.search(text):
            bad.append(spec.parent.name)
    return None if not bad else f"shipped with a box nothing proves: {', '.join(bad[:3])}"


@check(20, "The outside", "The observability destination is real")
def destination_real(root: Path | None) -> str | None:
    emit = paths.load("_emit")
    if not emit.config(root).get("observability", {}).get("endpoint"):
        raise Undecidable("no destination is configured, so there is nothing to prove")
    ok, detail = paths.load("_otlp").probe()
    return None if ok else f"the destination answered {detail}. A 200 is not a delivery."


# ---------------------------------------------------------------- coverage


def standing(
    surface: dict,
    installed: set[str],
    inert: str,
    guarded: set[str],
    *,
    proved: frozenset[str] = frozenset(),
) -> tuple[str, str]:
    """One surface's word, and the sentence that says what to do about it. The word carried
    the whole message before and the message did not fit in one word: `documented, unrun
    UNPROVEN` and `not installed UNPROVEN` are the same verdict for opposite reasons, and
    only one of them is any of your business.

    `guarded` is the fourth argument and the reason this whole task exists. The word came
    from whether the vendor's own directory exists plus a static `proven` flag in
    policy/surfaces.toml, and never from the settings file — so on a machine `ai-eng
    uninstall` had just stripped, the block whose entire job is *where a call can actually
    be stopped* printed `claude-code BLOCKS a denial has executed here` and
    `copilot-cli UNPROVEN installed and wired`, over zero entries. A receipt says a denial
    executed on this surface, on this machine; nothing here says there is one able to
    execute another now, which is what the installed and wired branches above are for."""
    if surface["id"] not in installed:
        return "UNPROVEN", "not installed here, so nothing about it is proven"
    if surface["tier"] == "T3":
        return "ADVISES", "reads the skills; it cannot deny a call"
    if surface["id"] not in guarded:
        return "UNPROVEN", "installed, and carries no entry of ours: nothing here can deny"
    if surface["name"] in inert:
        # Installed, and not running. Both surfaces that can reach this state fail silently
        # by design, so it is the one that must never be reported as covered.
        if surface.get("trust_required"):
            return "INERT", "installed and unapproved — type /hooks in Codex to approve it"
        return "INERT", "the plugin never reported loading; a malformed one is dropped in silence"
    if surface["id"] in proved:
        return "BLOCKS", "a denial has executed here"
    return "UNPROVEN", "installed and wired, but no denial has ever run here"


def enforced(root: Path | None, *, now: datetime) -> frozenset[str]:
    """The surfaces whose enforcement receipt proved, and no others.

    This is the whole of the change: the coverage word used to come from a field in a
    table, and OpenCode's row read BLOCKS on the strength of it with no denial ever
    executed there. A flag we set cannot contradict us, so it could never turn the screen
    red — and a report that cannot go red is a report nobody needs to read."""

    if root is None:
        return frozenset()
    return frozenset(
        row.surface
        for row in surfaces.read(root, now=now).rows
        if row.state == "enforcement" and row.outcome == "PASS" and row.code == surfaces.PROVEN
    )


def coverage(root: Path | None, *, now: datetime | None = None) -> list[str]:
    """The honesty layer, and it is derived: from the pin, the settings files on disk and
    the recorded trust state. No probes, no billed sessions. A surface that is not installed
    here reads UNPROVEN, not "covered".

    That sentence named the receipt and the settings files for a version in which it read
    neither, and the two it did not read were the two that decide the word. It reads them
    now, and the receipt is gone from the list rather than added to it: what a log says was
    written is not evidence that anything is wired today, which is the whole subject of the
    spec this paragraph was corrected by.

    Four columns and not three: the verdict is its own column now, so the eye can run down
    it, and the reason is the column after it rather than a prefix squeezed in front of the
    word. The words did not change — they are the vocabulary and they are asserted."""
    emit = paths.load("_emit")
    pinned = emit.config(root).get("framework", {}).get("version", "—")
    lines = [
        f"  PIN  wheel {__version__} = pinned {pinned}"
        f"{'  OK' if pinned == __version__ else '  MISMATCH'}"
    ]
    installed = {s["id"] for s in wiring.detect()}
    # The same call assertion 2 and `init.global_ready` make. A surface with no entry of
    # ours in its settings file cannot deny anything, whatever the table says about it.
    on, _ = wiring.wired()
    guarded = {s["id"] for s in on} | {
        s["id"] for s in wiring.table()["surface"] if s["writer"] == "none"
    }
    try:
        # The message only. `surfaces_alive` returns `(message, cure)` as soon as any
        # surface has no entry of ours, and a tuple is not a string: `surface["name"] in
        # inert` silently stops being a substring test and becomes an exact-element test
        # that is never true. So the coverage block could not print INERT whenever any one
        # surface was unwired, and the two surfaces that fail *silently* — Codex without
        # its trust ceremony, OpenCode whose plugin was dropped with no error and no log —
        # printed as `installed and wired` on a machine where assertion 21 was telling the
        # person they were dead. That is the case the comment beside `INERT` says must
        # never be reported as covered.
        said = surfaces_alive(root)
        inert = (said[0] if isinstance(said, tuple) else said) or ""
    except Undecidable:
        inert = ""  # nothing installed, so every row below already reads UNPROVEN
    proved = enforced(root, now=now or datetime.now(UTC))
    for surface in wiring.table()["surface"]:
        word, why = standing(surface, installed, inert, guarded, proved=proved)
        lines.append(f"  {surface['tier']:<4} {surface['id']:<16} {word:<9} {why}")
    return [*lines, *OPEN]


def _terminal_result(
    failed: list[int],
    unanswered: list[tuple[int, str, str]],
    coverage_lines: list[str],
    coverage_unknown: bool,
    readiness_failed: bool = False,
    surface_failed: bool = False,
    surface_warned: bool = False,
) -> outcome.Result:
    words = {word for line in coverage_lines for word in re.findall(r"[A-Z]+", line)}
    if failed or readiness_failed or surface_failed or "MISMATCH" in words:
        return outcome.result("FAIL")
    if unanswered or coverage_unknown:
        return outcome.result("INCOMPLETE")
    if surface_warned or words & {"INERT", "UNPROVEN", "OPEN"}:
        return outcome.result("WARN")
    return outcome.result("PASS")


# The three questions the coverage word used to answer at once, defined where somebody
# running `doctor` will meet them. Each is read from its own receipt and speaks for nothing
# else: a surface can list the skills and be unable to run them, and it can run them and
# never be able to stop anything.
STATE_LEGEND = (
    "  discovery   the surface can see the skills · invocation somebody can run one",
    "  enforcement a denial has executed here · not applicable a T3 surface cannot deny",
)


def surface_states(root: Path | None, *, now: datetime) -> list[outcome.Fact]:
    """Discovery, invocation and enforcement for every surface, one fact each.

    Every row is printed even when nothing has been receipted, because an omitted row
    reads, to anything counting, like a question that was not worth asking. Unproven is the
    honest answer and it is never a pass."""

    if root is None:
        return []
    said = {
        surfaces.PROVEN: "a denial has executed here",
        surfaces.NOT_APPLICABLE: "a T3 surface cannot deny, so there is nothing to prove",
        surfaces.RECEIPT_MISSING: "no receipt: unproven, which is not a pass",
        surfaces.RECEIPT_STALE: "the receipt is older than a proof is allowed to be",
        surfaces.RECEIPT_MISMATCH: "the receipt names another surface or another state",
        surfaces.CANNOT_ENFORCE: "a denial receipt for a surface that cannot deny",
        surfaces.WARNED: "it ran, it passed, and it had something to say",
        surfaces.REFUSED_EXCUSE: "the receipt says the check did not apply, and here it does",
    }
    facts = []
    for row in surfaces.read(root, now=now).rows:
        detail = said.get(row.code, row.code)
        aged = "" if row.age_seconds is None else f" · {row.age_seconds}s old"
        facts.append(
            outcome.fact(
                f"surface-{row.surface}-{row.state}",
                row.outcome,
                f"{row.surface} · {row.state}",
                detail + aged,
            )
        )
    return facts


def readiness_facts(root: Path | None, *, now: datetime) -> list[outcome.Fact]:
    """What the production-ready boxes are proven to be, and how old the proof is.

    Age is reported next to every verdict because a receipt has two ways of not meaning
    anything, and only one of them shows up as a failure: it can say the wrong thing, or it
    can say the right thing about a run from six months ago. The second is the one that
    reads green in every summary that only counts outcomes.

    No box is claimed here that a receipt did not carry, and a repository with nothing to
    read reports that it has nothing to read."""

    if root is None:
        return [
            outcome.fact(
                "readiness",
                "INCOMPLETE",
                "Production-ready boxes",
                "there is no repository here to read receipts from",
            )
        ]
    report = readiness.read(root, now=now)
    facts = [
        outcome.fact("readiness", report.result.outcome, "Production-ready boxes", report.code)
    ]
    for box in report.boxes:
        aged = "no receipt to age" if box.age_seconds is None else f"{box.age_seconds}s old"
        facts.append(
            outcome.fact(f"readiness-{box.id}", box.outcome, box.label, f"{box.code} · {aged}")
        )
    return facts


def main(argv: list[str]) -> outcome.Result | outcome.Execution:
    parser = argparse.ArgumentParser("ai-eng doctor")
    parser.add_argument("--ci", action="store_true", help="only the checks a runner can answer")
    parser.add_argument("--paths", action="store_true", help="print where every file class lives")
    parser.add_argument("--fix", action="store_true", help="run the cures the failures name")
    args = parser.parse_args(argv)

    root = paths.repo_root()
    if args.paths:
        # Five paths and nothing else, so this is the half a person pipes into a script.
        for label, where in (
            ("guards", paths.hooks()),
            ("git hooks", paths.git_hooks()),
            ("skills", paths.home() / "skills"),
            ("record", paths.load("_emit").chain_path(root)),
            ("receipt", wiring.receipt_path()),
        ):
            ui.write(f"  {label:<14}{where}", data=True)
        return outcome.result("PASS")

    # One clock for the whole run. Two `datetime.now()` calls read the receipts at two
    # different instants, and a receipt expiring between them makes the one-word block
    # and the state block disagree about the same file.
    observed = datetime.now(UTC)
    failed: list[int] = []
    unanswered: list[tuple[int, str, str]] = []
    cures: dict[int, str] = {}
    check_facts: list[outcome.Fact] = []
    for family in families():
        ui.section(family, data=True)
        for number, group, title, in_ci, fn in sorted(CHECKS):
            if group != family:
                continue
            if args.ci and not in_ci:
                ui.verdict(number, "skipped", f"{title} — needs a real working copy")
                unanswered.append((number, title, "needs a real working copy"))
                check_facts.append(
                    outcome.fact(
                        f"assertion-{number}",
                        "SKIPPED",
                        title,
                        "needs a real working copy",
                    )
                )
                continue
            try:
                problem = fn(root)
            except (Undecidable, wiring.Unreadable) as why:
                # A file we cannot parse is the same answer as a question we cannot ask, and
                # this is the only reader of it that must not stop: a diagnosis that dies on
                # one broken file tells you nothing about the other nineteen assertions.
                ui.verdict(number, "unknown", title, f"could not evaluate: {why}")
                offered = getattr(why, "cure", "")
                if offered:
                    ui.cure("INCOMPLETE", offered)
                unanswered.append((number, title, str(why)))
                check_facts.append(
                    outcome.fact(f"assertion-{number}", "INCOMPLETE", title, str(why))
                )
                continue
            # Before the falsy test, because a `Noted` is a non-empty string and would
            # otherwise be read as the problem it is the opposite of.
            if isinstance(problem, Noted):
                ui.verdict(number, "ok", title, str(problem))
                check_facts.append(outcome.fact(f"assertion-{number}", "PASS", title, str(problem)))
                continue
            if not problem:
                ui.verdict(number, "ok", title)
                check_facts.append(outcome.fact(f"assertion-{number}", "PASS", title))
                continue
            problem, cure = resolve(number, problem)
            ui.verdict(number, "fail", title, problem)
            ui.cure("FAIL", cure)
            failed.append(number)
            check_facts.append(
                outcome.fact(f"assertion-{number}", "FAIL", title, problem, cure=cure)
            )
            if unattended(cure):
                cures[number] = cure

    ui.write("\nCoverage — where a call can actually be stopped, and where it cannot", data=True)
    for line in LEGEND:
        ui.write(line, style="muted", data=True)
    ui.write(data=True)
    coverage_unknown = False
    try:
        coverage_lines = coverage(root, now=observed)
    except (Undecidable, wiring.Unreadable) as why:
        coverage_unknown = True
        coverage_lines = []
        ui.write(f"  INCOMPLETE  could not evaluate coverage: {why}", style="warn", data=True)
        check_facts.append(outcome.fact("coverage", "INCOMPLETE", "Surface coverage", str(why)))
    for index, line in enumerate(coverage_lines, 1):
        # The words themselves are vocabulary — BLOCKS, INERT, UNPROVEN, ADVISES mean
        # something and do not move. Only the colour is added, and it is chosen by the word
        # rather than recomputed here, so this can never disagree with what the line says.
        ui.write(line, style=tint(line), data=True)
        coverage_status = (
            "FAIL"
            if "MISMATCH" in line
            else "WARN"
            if any(word in line for word in ("INERT", "UNPROVEN", "OPEN"))
            else "PASS"
            if any(word in line for word in ("BLOCKS", "OK"))
            else "OBSERVED"
        )
        check_facts.append(
            outcome.fact(f"coverage-{index}", coverage_status, "Surface coverage", line)
        )

    ui.section("Surfaces — three questions, and one receipt for each of them", data=True)
    for line in STATE_LEGEND:
        ui.write(line, style="muted", data=True)
    states = surface_states(root, now=observed)
    for entry in states:
        ui.write(f"  {entry.status:<11} {entry.summary} — {entry.detail}", data=True)
        check_facts.append(entry)
    # A state whose own check ran and failed is decided, so it counts — the same argument
    # the production-ready block already makes, wired the same way. It printed FAIL into
    # the JSON envelope and returned PASS with exit 0, which is a gate result this code
    # did not observe.
    surface_failed = any(entry.status == "FAIL" for entry in states)
    # A warning is not a failure and it is not nothing. It joins the same branch the
    # coverage vocabulary already routes INERT and UNPROVEN to, rather than being invented
    # as a status that appears in the envelope and changes no verdict — which is blocker
    # two's shape one severity down.
    surface_warned = any(entry.status == "WARN" for entry in states)

    ui.section("Production-ready — a box is ticked by a receipt that ran, or not at all", data=True)
    boxes = readiness_facts(root, now=observed)
    for entry in boxes:
        ui.write(f"  {entry.status:<11} {entry.summary} — {entry.detail}", data=True)
        check_facts.append(entry)
    # Unproven is reported and not folded into the verdict: whether anything is allowed a
    # URL is a decision this verb observes and does not make, and a doctor that went red on
    # every repository with no receipts yet would be turned off by everybody who has one.
    # A box whose own check ran and failed is a different answer, and it is decided, so it
    # counts — reporting a decided fault as something to look at later is the same lie as a
    # green nobody earned, told slowly.
    # The aggregate fact restates the worst box, so it is not counted beside it: one
    # fault named twice reads as two.
    failed_boxes = [entry for entry in boxes if entry.status == "FAIL" and entry.id != "readiness"]
    readiness_failed = bool(failed_boxes)

    if unanswered:
        ui.section(
            f"Not evaluated — {len(unanswered)} of {len(CHECKS)} could not be answered here",
            data=True,
        )
        # `reason` and not `why`: the same function binds `why` in an `except ... as why`
        # above, and Python deletes that name when the block ends, so reusing it here is a
        # read of a deleted variable that happens to work only because this loop rebinds it.
        for number, title, reason in unanswered:
            ui.write(f"  {number:>2}  {title}", data=True)
            ui.write(f"      {reason}", style="muted", data=True)
        ui.write(
            "  None of these is a pass. Not evaluated is never green.", style="warn", data=True
        )

    result = _terminal_result(
        failed,
        unanswered,
        coverage_lines,
        coverage_unknown,
        readiness_failed,
        surface_failed,
        surface_warned,
    )
    verdict_panel(result, failed, len(unanswered), cures, len(failed_boxes))
    if args.fix and cures:
        return repair(cures, argv)
    if args.fix:
        ui.write("\n  Nothing that failed here has a command --fix runs for you.", data=True)
    remaining = [
        *(f"assertion {number} failed" for number in failed),
        *(f"{entry.summary} failed its own check" for entry in failed_boxes),
        *(f"{entry.summary} failed" for entry in states if entry.status == "FAIL"),
        *(f"assertion {number} could not be evaluated" for number, _, _ in unanswered),
        *(["surface coverage could not be evaluated"] if coverage_unknown else []),
    ]
    actions = sorted(set(cures.values())) or [result.next_action]
    return outcome.execution(
        result,
        checks=check_facts,
        remaining=remaining,
        next_actions=actions,
    )


def resolve(number: int, problem: str | tuple[str, str]) -> tuple[str, str]:
    """A failure's message and its cure, however the check chose to say them. A cure the
    check named for itself beats the one this number usually carries, because a pin can be
    wrong two ways and they are two different commands."""
    return problem if isinstance(problem, tuple) else (problem, FIXES.get(number, ""))


def unattended(cure: str) -> bool:
    """Whether `--fix` may run this cure itself. It invokes the verb through `cli.main` with
    nobody in front of it, and `ai-eng update` asks for a typed `y` before it migrates — ADR
    0003 keeps that gate — so that cure is printed for a person and never run from here."""
    words = cure.split()
    return len(words) > 1 and words[1] in UNATTENDED


def tint(line: str) -> str:
    """The colour of a coverage row, taken from the vocabulary word in it. By position
    before, which meant the colour was one column-width edit away from being wrong about
    what the line said."""
    return next((style for word, style in COLOURS.items() if word in line), "")


def verdict_panel(
    result: outcome.Result,
    failed: list[int],
    unanswered: int,
    cures: dict[int, str],
    boxes_failed: int,
) -> None:
    """Whether it passed, and if not, how much of it a command can put right. This was one
    unframed line under the coverage block, in the same weight as the rows above it, and it
    was read as more of the table.

    The failures arrive as their numbers and not as a count beside a list of them: two
    arguments that have to agree are two arguments that can stop agreeing. The title comes
    from the same terminal result the caller returns, so a warning or an unknown answer can
    never acquire a green label from an empty failures list."""
    rows = [
        (
            "",
            f"{len(CHECKS) - len(failed) - unanswered} passed · "
            f"{len(failed)} failed · {unanswered} not evaluated",
        )
    ]
    if cures:
        rows.append(("fixable now", f"{len(cures)}   ai-eng doctor --fix"))
    if boxes_failed:
        # Counted on its own line rather than folded into the failures above, which are
        # numbered assertions. Without it the banner read FAILED over "0 failed", and a
        # verdict whose own counters contradict it is a verdict nobody reads twice.
        #
        # The label is short because the column that holds it is sixteen wide and pads to
        # exactly that: `production-ready` filled it and printed hard against its own
        # count, in the one row this exists to make legible.
        word = "box" if boxes_failed == 1 else "boxes"
        rows.append(
            ("not ready", f"{boxes_failed}   production-ready {word} failed a check that ran")
        )
    people = sorted(number for number in failed if number not in cures)
    if people:
        listed = ", ".join(str(number) for number in people)
        word = "assertion" if len(people) == 1 else "assertions"
        rows.append(("needs a person", f"{len(people)}   {word} {listed}"))
    title, style = {
        "PASS": ("OK", ui.BRAND),
        "WARN": ("WARN", "yellow"),
        "FAIL": ("FAILED", "red"),
        "INCOMPLETE": ("INCOMPLETE", "yellow"),
    }[result.outcome]
    ui.summary(title, rows, style)


def repair(cures: dict[int, str], argv: list[str]) -> outcome.Result | outcome.Execution:
    """Runs what the failures themselves named, each command once, and then asks the whole
    question again. In this process rather than through a shell: `ai-eng` is on the PATH of
    the person who typed it and not necessarily of whatever would run it here, and a repair
    that fails because it could not find itself is worse than no repair.

    What it writes is what `init` writes: the guard entries, the skill links, and any of the
    instruction files that are missing. It overwrites none of yours — `-y` leaves the picker
    with nothing ticked — and it does not touch the pin, because `init` only writes that
    when it is absent and `ai-eng update` is the verb that changes it.

    The second pass has no --fix in it, so this recurses exactly once, and its terminal
    result is the answer: two of the cures cannot reach every shape of their failure — a Codex entry
    is appended and never rewritten, and a skill root belonging to a surface that is gone is
    linked by nothing — so a repair that changed nothing has to say so rather than invite a
    second run of the same command."""
    from ai_engineering import cli

    for command in sorted(set(cures.values())):
        verb, *rest = command.split()[1:]
        run = [verb, *rest, *UNATTENDED.get(verb, [])]
        # The blank line is its own write and not a \n inside the styled one: a newline
        # carried inside a styled Text puts the escape sequence before the line break, so
        # the colour of the command is asserted through a leading blank line or not at all.
        ui.write(data=True)
        ui.write(f"  running ai-eng {' '.join(run)}", style="cmd", data=True)
        code = cli.main(run)
        if code:
            ui.write(f"  it exited {code}. The rest is not attempted.", style="fail", data=True)
            return outcome.result("INCOMPLETE")
    result = main([flag for flag in argv if flag != "--fix"])
    if result.exit_code:
        ui.write(
            "\n  Still failing. What is left above is not something these commands reach, "
            "and running --fix again will run the same ones.",
            style="warn",
            data=True,
        )
    return result
