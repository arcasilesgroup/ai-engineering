"""Twenty assertions and one line.

These are not document sections: they are checks that fail. `--ci` runs the ones that
make sense on a runner and says in its output which it skipped, because a doctor that
comes out red by construction is a doctor somebody silences forever.

Three states, and the third is the honest one. OK and FAIL are obvious. COULD NOT
EVALUATE is never green and here it is not red either: it is named, with the reason,
because a green nobody earned is the failure this whole product exists to cure.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from ai_engineering import __version__, audit, paths, ui, wiring

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
    """Raised when a check could not be evaluated. Never counted as a pass."""


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
def pin_matches(root: Path | None) -> str | None:
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
def wiring_present(root: Path | None) -> str | None:
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
def git_hook_fires(root: Path | None) -> str | None:
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
    return None


@check(13, "The wiring", "Every symlink resolves and the doctrine is loaded")
def links_resolve(root: Path | None) -> str | None:
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
def surfaces_alive(root: Path | None) -> str | None:
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
    tracked = set(git(root, "ls-files", ".ai").splitlines())
    allowed = {".ai/.gitignore", ".ai/config.toml"}
    extra = tracked - allowed
    if extra:
        return f"state slipped into git: {sorted(extra)[:3]}"
    return None


@check(18, "The record", "Your data is yours: every framework file has a declared home")
def data_is_yours(root: Path | None) -> str | None:
    if root is None:
        raise Undecidable("not inside a repository")
    homes = (".ai/", "specs/", "docs/adr/")
    strays = [
        name
        for name in git(root, "ls-files").splitlines()
        if name.startswith(".ai-engineering/") or name.endswith(".ai-eng.json")
    ]
    if strays:
        return (
            f"{len(strays)} framework files are committed outside {', '.join(homes)} — "
            f"the first is {strays[0]}. That is the first step back toward 528 of them."
        )
    return None


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
    if not stamp or (time.time() - float(stamp)) / 86400 > 7:
        return "the real-model half has no dated green result in the last 7 days"
    return None


# ---------------------------------------------------------------- the context


@check(1, "The context", "Every SKILL.md meets the contract")
def skills_contract(root: Path | None) -> str | None:
    from ai_engineering import contract

    problems = contract.audit(paths.skills())
    return None if not problems else f"{len(problems)} problems, first: {problems[0]}"


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


# Assertion 5 was here: the product repository is under its line ceiling. It computed the
# same number from the same function and compared it to the same constant as
# `tests/test_contracts.test_the_line_ceiling_holds`, and CI ran both in the same job
# eleven lines apart. It also refused to evaluate anywhere outside this repository, so it
# has never told a user anything. The test is the right one to keep of the two: it fails
# the build, where the check only printed a line.


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
    command. The ceiling is recorded as an accepted risk: a backtick proves something was
    named, never that it passed."""
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


def standing(surface: dict, installed: set[str], inert: str, guarded: set[str]) -> tuple[str, str]:
    """One surface's word, and the sentence that says what to do about it. The word carried
    the whole message before and the message did not fit in one word: `documented, unrun
    UNPROVEN` and `not installed UNPROVEN` are the same verdict for opposite reasons, and
    only one of them is any of your business.

    `guarded` is the fourth argument and the reason this whole task exists. The word came
    from whether the vendor's own directory exists plus a static `proven` flag in
    policy/surfaces.toml, and never from the settings file — so on a machine `ai-eng
    uninstall` had just stripped, the block whose entire job is *where a call can actually
    be stopped* printed `claude-code BLOCKS a denial has executed here` and
    `copilot-cli UNPROVEN installed and wired`, over zero entries. `proven` says a denial has
    executed on this kind of surface at some point in this product's life; it can never say
    there is anything here to execute one now."""
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
    if surface["proven"]:
        return "BLOCKS", "a denial has executed here"
    return "UNPROVEN", "installed and wired, but no denial has ever run here"


def coverage(root: Path | None) -> list[str]:
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
        inert = surfaces_alive(root) or ""
    except Undecidable:
        inert = ""  # nothing installed, so every row below already reads UNPROVEN
    for surface in wiring.table()["surface"]:
        word, why = standing(surface, installed, inert, guarded)
        lines.append(f"  {surface['tier']:<4} {surface['id']:<16} {word:<9} {why}")
    return [*lines, *OPEN]


def main(argv: list[str]) -> int:
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
        return 0

    failed: list[int] = []
    unanswered: list[tuple[int, str, str]] = []
    cures: dict[int, str] = {}
    for family in families():
        ui.section(family, data=True)
        for number, group, title, in_ci, fn in sorted(CHECKS):
            if group != family:
                continue
            if args.ci and not in_ci:
                ui.verdict(number, "skipped", f"{title} — needs a real working copy")
                unanswered.append((number, title, "needs a real working copy"))
                continue
            try:
                problem = fn(root)
            except (Undecidable, wiring.Unreadable) as why:
                # A file we cannot parse is the same answer as a question we cannot ask, and
                # this is the only reader of it that must not stop: a diagnosis that dies on
                # one broken file tells you nothing about the other nineteen assertions.
                ui.verdict(number, "unknown", title, f"could not evaluate: {why}")
                unanswered.append((number, title, str(why)))
                continue
            if not problem:
                ui.verdict(number, "ok", title)
                continue
            problem, cure = resolve(number, problem)
            ui.verdict(number, "fail", title, problem)
            ui.cure(cure)
            failed.append(number)
            if unattended(cure):
                cures[number] = cure

    ui.write("\nCoverage — where a call can actually be stopped, and where it cannot", data=True)
    for line in LEGEND:
        ui.write(line, style="muted", data=True)
    ui.write(data=True)
    for line in coverage(root):
        # The words themselves are vocabulary — BLOCKS, INERT, UNPROVEN, ADVISES mean
        # something and do not move. Only the colour is added, and it is chosen by the word
        # rather than recomputed here, so this can never disagree with what the line says.
        ui.write(line, style=tint(line), data=True)

    if unanswered:
        ui.section(
            f"Not evaluated — {len(unanswered)} of {len(CHECKS)} could not be answered here",
            data=True,
        )
        for number, title, why in unanswered:
            ui.write(f"  {number:>2}  {title}", data=True)
            ui.write(f"      {why}", style="muted", data=True)
        ui.write(
            "  None of these is a pass. Not evaluated is never green.", style="warn", data=True
        )

    verdict_panel(failed, len(unanswered), cures)
    if args.fix and cures:
        return repair(cures, argv)
    if args.fix:
        ui.write("\n  Nothing that failed here has a command --fix runs for you.", data=True)
    return 1 if failed else 0


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


def verdict_panel(failed: list[int], unanswered: int, cures: dict[int, str]) -> None:
    """Whether it passed, and if not, how much of it a command can put right. This was one
    unframed line under the coverage block, in the same weight as the rows above it, and it
    was read as more of the table.

    The failures arrive as their numbers and not as a count beside a list of them: two
    arguments that have to agree are two arguments that can stop agreeing."""
    rows = [
        (
            "",
            f"{len(CHECKS) - len(failed) - unanswered} passed · "
            f"{len(failed)} failed · {unanswered} not evaluated",
        )
    ]
    if cures:
        rows.append(("fixable now", f"{len(cures)}   ai-eng doctor --fix"))
    people = sorted(number for number in failed if number not in cures)
    if people:
        listed = ", ".join(str(number) for number in people)
        word = "assertion" if len(people) == 1 else "assertions"
        rows.append(("needs a person", f"{len(people)}   {word} {listed}"))
    ui.summary("FAILED" if failed else "OK", rows, "red" if failed else ui.BRAND)


def repair(cures: dict[int, str], argv: list[str]) -> int:
    """Runs what the failures themselves named, each command once, and then asks the whole
    question again. In this process rather than through a shell: `ai-eng` is on the PATH of
    the person who typed it and not necessarily of whatever would run it here, and a repair
    that fails because it could not find itself is worse than no repair.

    What it writes is what `init` writes: the guard entries, the skill links, and any of the
    instruction files that are missing. It overwrites none of yours — `-y` leaves the picker
    with nothing ticked — and it does not touch the pin, because `init` only writes that
    when it is absent and `ai-eng update` is the verb that changes it.

    The second pass has no --fix in it, so this recurses exactly once, and its exit code is
    the answer: two of the cures cannot reach every shape of their failure — a Codex entry
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
            return code
    code = main([flag for flag in argv if flag != "--fix"])
    if code:
        ui.write(
            "\n  Still failing. What is left above is not something these commands reach, "
            "and running --fix again will run the same ones.",
            style="warn",
            data=True,
        )
    return code
