"""The writers: one entry per surface, in the file that surface already reads.

No guard file is ever copied. The guards live inside the installed wheel and stay
there; what gets written outside is always a pointer to that path — which is why
`update` can rewrite the entries from the receipt when the interpreter's directory
changes underneath them, and why assertion 12 can tell a live entry from a stale one.

Nothing here ever writes a tilde into a config file. None of the three main surfaces
documents expanding ~ inside a setting value, and a tilde in core.hooksPath saves fine,
fires nothing, and lets the commit through without a complaint. It is measured.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from ai_engineering import __version__, outcome, paths

MARK = "ai-engineering"  # rendered into Codex's status message, and hashed there

# What makes an entry ours, and the only string here we control. It used to be MARK, and
# MARK can only reach an entry through the interpreter path, which spells this package
# with an underscore under a wheel: it worked because uv tool and pipx happen to put the
# hyphenated project name in the path of the interpreter they create, and was false
# everywhere at once for anyone installing with pip into a venv named anything else.
# The basename and never the absolute path: assertion 12 catches an entry pointing at
# another install by asking whether the signature is present while the install path is
# not, and a signature containing the install path makes that check unable to fire.
SIGNATURE = "chain.py"
EVENTS = ("PreToolUse", "PostToolUse", "SessionStart", "SessionEnd")


def table() -> dict:
    return tomllib.loads(paths.policy("surfaces.toml").read_text(encoding="utf-8"))


def expand(entry: str) -> Path:
    return Path(entry).expanduser()


def command(event: str) -> str:
    """Absolute, expanded, and pointing inside the wheel."""
    return f'"{sys.executable}" "{paths.hooks() / "chain.py"}" {event}'


def detect(only: list[str] | None = None) -> list[dict]:
    """A surface is found when the path it created itself exists. Naming it with
    `--harness` says it is here on your word instead — which is the only way to wire a
    surface this table cannot detect, and some cannot be detected without our creating
    the very evidence the detector reads."""
    found = []
    for surface in table()["surface"]:
        if only and surface["id"] not in only:
            continue
        if only or (surface["detect"] and expand(surface["detect"]).exists()):
            found.append(surface)
    return found


def wired(only: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    """The surfaces that take a guard and are here, split by whether our entry is actually
    in the file. Read from the settings files themselves and never from the receipt.

    It lived inside doctor's assertion 2, and `init` had a second opinion — a log of what
    was once written — so the two disagreed the moment anything changed the machine without
    going through this tool. `uninstall` was only the loudest way to do that; a settings file
    edited by hand, a surface removed by its own installer and a home restored from a backup
    all get the same wrong answer out of a receipt. One question, asked in one place."""
    on: list[dict] = []
    off: list[dict] = []
    for surface in detect(only):
        if surface["writer"] == "none" or not surface.get("settings"):
            continue
        path = expand(surface["settings"])
        body = path.read_text(errors="replace") if path.exists() else ""
        (on if SIGNATURE in body else off).append(surface)
    return on, off


def linked() -> list[Path]:
    """The skills roots that hold at least one of ours, by the same rule and for the same
    reason: `already()` printed `links 4` off a receipt while all four roots were empty.

    Deduplicated, because five of the eight surfaces share `~/.agents/skills` and a count
    that walks the table row by row reports five links over one directory — which is the
    same class of wrong number this whole task is removing, arriving from the other side."""
    store = paths.home() / "skills"
    copied = {row["path"] for row in receipt().get("wrote", []) if row.get("how") == "copy"}
    roots = {expand(s["skills"]) for s in table()["surface"] if s.get("skills")}
    return sorted(root for root in roots if root.is_dir() and holds_ours(root, store, copied))


def holds_ours(root: Path, store: Path, copied: set[str]) -> bool:
    """A symlink into our store is ours by what it points at. A directory is ours only when
    the receipt says we copied it there, which is what a receipt is for and the one question
    the disk genuinely cannot answer — and it is the Windows case, where `link` copies."""
    for item in root.iterdir():
        if item.is_symlink() and str(store) in str(item.readlink()):
            return True
        if str(root) in copied and item.is_dir() and item.name.startswith("ai-"):
            return True
    return False


def foreign(root: Path, names: list[str]) -> list[Path]:
    """The directories in a shared skills root that carry one of our names and are not ours.

    A skills root belongs to the person, not to us: eighteen `ai-*` skills from other
    publishers sat in one of these while this framework claimed the whole prefix. A real
    directory with something in it, at a name we ship, that the receipt does not record us
    copying there, is theirs. It is named and skipped now. It used to refuse the machine:
    one folder called `ai-design`, owned four weeks before we shipped a skill of that name,
    left eight surfaces uninstalled and named nothing in the message."""
    copied = {row["path"] for row in receipt().get("wrote", []) if row.get("how") == "copy"}
    if str(root) in copied:
        return []
    theirs = []
    for name in names:
        target = root / name
        if target.is_symlink() or not target.is_dir():
            continue
        if any(target.iterdir()):
            theirs.append(target)
    return sorted(theirs)


class Unreadable(outcome.Unreadable):
    """A file that is there and cannot be read. Absent is an answer; unreadable is not."""


def read_json(path: Path) -> dict:
    """Missing is empty. Present-and-unparseable raises, and that is the whole of this fix.

    It used to answer `{}` to both, and every caller inherited it. Two of them lose data on
    that answer. `record` reads the receipt, appends and writes, so one interrupted write
    made the machine's whole install record — including the project rows that are the only
    thing telling `uninstall` which justfile is ours — vanish on the next `init`, silently.
    And the three settings writers read, mutate and write back, so a `~/.claude/settings.json`
    carrying a JSONC comment was replaced by our hooks block alone, under a line of output
    reading `(merged)` and a docstring promising foreign entries are preserved.

    This repository already made this ruling for `text.yaml_blocks`: silence on a parse
    failure is the exact shape of a false green, and undecidable is an answer while invisible
    is not. The record verbs got that rule; the files this one reads did not."""
    try:
        body = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as why:
        raise Unreadable(f"{path} could not be read: {why.strerror}") from why
    try:
        return json.loads(body)
    except ValueError as why:
        raise Unreadable(f"{path} is not readable as JSON: {why}") from why


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(data, indent=2) + "\n")


def ours(entry) -> bool:
    """Ours by what it runs, not by where it happens to live. Where this answers no, init
    stops recognising its own entry and writes a second one — a blocking guard firing twice
    — uninstall reports there was nothing of ours and leaves every guard wired, and doctor
    reports no entry against a live install."""
    body = json.dumps(entry)
    return SIGNATURE in body


def json_claude(path: Path) -> str:
    """Claude Code, and VS Code Copilot, which reads this same file and needs no wiring
    of its own. Foreign entries are preserved: this merges, it never replaces."""
    data = read_json(path)
    hooks = data.setdefault("hooks", {})
    for event in EVENTS:
        rows = [row for row in hooks.get(event, []) if not ours(row)]
        rows.append({"matcher": "*", "hooks": [{"type": "command", "command": command(event)}]})
        hooks[event] = rows
    write_json(path, data)
    return "merged"


def json_cursor(path: Path) -> str:
    """Cursor fails OPEN unless failClosed is set, which would make our guard advisory —
    a guard that advises is a guard that is off."""
    data = read_json(path)
    data["version"] = data.get("version", 1)
    data["failClosed"] = True
    hooks = data.setdefault("hooks", {})
    for name, event in (("beforeShellExecution", "PreToolUse"), ("beforeReadFile", "PreToolUse")):
        rows = [row for row in hooks.get(name, []) if not ours(row)]
        rows.append({"command": command(event)})
        hooks[name] = rows
    write_json(path, data)
    return "failClosed: true"


def json_copilot(path: Path) -> str:
    """Its own file, merged with five other sources rather than replacing them."""
    write_json(
        path, {"hooks": {"preToolUse": [{"type": "command", "command": command("PreToolUse")}]}}
    )
    return "own file"


def json_codex(path: Path) -> str:
    """Trust is a sha256 over the normalised handler — command, timeout, status message,
    matcher, async flag — keyed by source path, group index and handler index. So the
    handler is frozen whole and appended, never reordered: inserting above somebody
    else's entry silently invalidates their trust, and there is a TODO in the vendor's
    own source about replacing that positional key.

    The keys are `hooks`, `timeout` and `statusMessage`, and they were `handlers`,
    `timeout_ms` and `status_message` until this was read off the shipped binary rather
    than off a document. Codex CLI 0.147.0 declares `ConfiguredHookMatcherGroup` with two
    fields, `matcher` and `hooks`, and an `internally tagged enum HookHandlerConfig` whose
    fields are `type`, `command`, `commandWindows`, `timeout`, `async`, `statusMessage` and
    `additionalContextLimit`. The word `handlers` appears in that binary only as Rust
    module paths. On a machine with Codex installed, every hook another tool had written
    used the vendor spelling and only ours did not.

    So this entry could not deserialise, and a guard that cannot deserialise is a guard
    that never ran. It is still unproven: no denial has receipted on this surface, and
    nothing here claims one has. What changed is that it can now be attempted."""
    data = read_json(path)
    groups = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
    for group in groups:
        if ours(group):
            return f"already present at position {groups.index(group) + 1} of {len(groups)}"
    groups.append(
        {
            "hooks": [
                {
                    "type": "command",
                    "command": command("PreToolUse"),
                    "timeout": 5,
                    "statusMessage": f"{MARK} guards",
                    "async": False,
                }
            ]
        }
    )
    write_json(path, data)
    return f"appended, position {len(groups)} of {len(groups)}"


def opencode_source() -> str:
    """The plugin exactly as it is installed, from one definition.

    There were three: this writer, `uninstall`'s reconstruction, and a test's copy. They
    agreed only by accident of platform, and the moment one was corrected the other two
    disagreed — `uninstall` compares the installed bytes to its own reconstruction and
    refuses the *whole* run when they differ, so a fix here removed nothing anywhere.

    One caller now: `uninstall._guard_owned` compares the installed bytes to this output
    directly. The test still reconstructs independently, which is
    what a test is for — it would agree with any defect it shared a definition with."""

    source = (paths.surfaces() / "opencode.ts").read_text(encoding="utf-8")
    for token, value in (
        ('"__PYTHON__"', sys.executable),
        ('"__CHAIN__"', str(paths.hooks() / "chain.py")),
        ('"__BEAT__"', str(paths.home() / "cache" / "opencode-heartbeat")),
    ):
        # The quotes go too, and the value is written as a JSON string. Dropping a raw
        # Windows path inside existing quotes made `C:\Users\me\...` into `C:Usersme...`
        # — every backslash a TypeScript escape — so the plugin pointed at a path that never
        # existed. It used to allow silently; once the plugin failed closed it denied
        # everything instead.
        source = source.replace(token, json.dumps(value))
    return source


def ts_opencode(path: Path) -> str:
    """One TypeScript file that shells out to the same dispatcher every other surface
    calls. Not weightless: the moment any local plugin exists OpenCode creates a
    lockfile and a ~61 MB node_modules, and the first run pays an install."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(opencode_source(), encoding="utf-8")
    return "plugin written"


WRITERS = {
    "json_claude": json_claude,
    "json_cursor": json_cursor,
    "json_copilot": json_copilot,
    "json_codex": json_codex,
    "ts_opencode": ts_opencode,
}


def link(source: Path, target: Path) -> str:
    """Symlink where symlinks work, copy where they do not. On Windows creating one
    needs developer mode or an elevated console and it fails silently when it cannot,
    which is how a competing product leaves its skills directory empty. So copying is
    the default there, not an embarrassed plan B — and the receipt records which it was
    so doctor can warn when a copy goes stale."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or target.exists():
        if target.is_symlink() and target.resolve() == source.resolve():
            return "symlink"
        if target.is_dir() and not target.is_symlink():
            shutil.copytree(source, target, dirs_exist_ok=True)
            return "copy"
        target.unlink()
    try:
        target.symlink_to(source, target_is_directory=source.is_dir())
        return "symlink"
    except (OSError, NotImplementedError):
        shutil.copytree(source, target, dirs_exist_ok=True)
        return "copy"


def receipt_path() -> Path:
    return paths.home() / "machine.json"


def receipt() -> dict:
    return read_json(receipt_path())


def record(entries: list[dict]) -> None:
    """Probing the disk can prove a file exists; it can never prove that we wrote it.
    The receipt turns "do not step on a file you did not create" into a lookup.

    It reads before it writes, which is why `read_json` raising matters here more than
    anywhere: while an unreadable receipt answered `{}`, this appended to that nothing and
    stored it, so a single interrupted write destroyed every row — including the project
    rows that are the only record of which files here are ours. It now refuses, and the
    file stays exactly as it is for a person to look at."""
    data = receipt()
    data.setdefault("machine_id", paths.load("_emit").machine_id())
    data["version"] = __version__
    data["python"] = sys.executable
    data["hooks"] = str(paths.hooks())
    known = {(row["path"], row["kind"]) for row in entries}
    kept = [row for row in data.get("wrote", []) if (row["path"], row["kind"]) not in known]
    data["wrote"] = kept + entries
    write_json(receipt_path(), data)


def forget(entries: list[dict]) -> None:
    """The way out this record never had, and the reason spec 005 refused per-surface
    uninstall in writing: without it, removing something left it recorded forever and the
    receipt became a file that misstates the present. It did — `uninstall` removed four
    guards and four link sets and the next `init` read the log, called the machine ready,
    and declined to rewire it.

    Keyed on `(path, kind)`, which is what `record` already deduplicates by. A retraction
    that matched on anything else would be a second identity for one row. The head fields —
    machine_id, version, python, hooks — describe the install and not what it wrote, so they
    survive an uninstall the same way the chain under state/ does. Forgetting a row that was
    never there is not an error: the caller is saying "this is gone", and it is."""
    data = receipt()
    known = {(row["path"], row["kind"]) for row in entries}
    data["wrote"] = [
        row for row in data.get("wrote", []) if (row["path"], row["kind"]) not in known
    ]
    write_json(receipt_path(), data)


def install_skills(surfaces: list[dict] | None = None) -> list[dict]:
    """Into the roots of the surfaces that were found, and no others. Linking creates the
    parent of a skills root, so linking into every root in the table put a directory on
    the machine for each of the eight — and four of those directories are what the next
    run's detector looks for. The no-argument form still means every root, because
    `uninstall` and the wiring tests ask about the table rather than about a machine."""
    real = paths.home() / "skills"
    real.mkdir(parents=True, exist_ok=True)
    for skill in sorted(paths.skills().glob("ai-*")):
        shutil.copytree(skill, real / skill.name, dirs_exist_ok=True)
    written = [{"path": str(real), "kind": "skills", "how": "wheel"}]
    rows = table()["surface"] if surfaces is None else surfaces
    for root in sorted({s["skills"] for s in rows if s.get("skills")}):
        where = expand(root)
        ours = sorted(real.glob("ai-*"))
        # Skipped rather than merged. `link` copies into a directory that is already there,
        # so without this line one shared name puts our SKILL.md on top of somebody else's.
        theirs = {path.name for path in foreign(where, [skill.name for skill in ours])}
        how = "none"
        for skill in ours:
            if skill.name in theirs:
                continue
            how = link(skill, where / skill.name)
        written.append({"path": str(where), "kind": "link", "how": how})
    return written


ROUTER = """---
description: {description}
---

# {name} · {phase}

{example}

{follows}
Use the `{name}` skill to handle this request. The canonical skill body lives in the shared
skills root this framework installed; load it and follow it. Everything after the command
name is the request, forwarded verbatim.

$ARGUMENTS
"""


def phases() -> dict[str, str]:
    """Which of the five phases each capability serves, read from the one file that lists
    all eighteen. A second copy here would be a second answer within a week."""

    try:
        declared = tomllib.loads(paths.policy("capabilities.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return {str(row["id"]): str(row.get("phase", "")) for row in declared.get("capabilities", [])}


def example(skill: Path) -> str:
    """One case the skill must take, in the words somebody would actually type.

    Taken from the labelled corpus beside it rather than written here, so the example a
    person reads on their surface is one the routing evaluation runs every time the gate
    does. An example nothing checks is the sentence that goes stale first.
    """

    corpus = skill / "corpus.md"
    if not corpus.is_file():
        return ""
    section = corpus.read_text(encoding="utf-8").partition("## Routes here")[2]
    for line in section.partition("\n## ")[0].splitlines():
        quoted = re.match(r'-\s+"([^"]+)"', line.strip())
        if quoted:
            return quoted.group(1)
    return ""


# The order the five phases run in, which is the only reason to order them at all: a map
# sorted alphabetically would put `build` before `decide` and read as a claim about sequence
# that is false. Named here rather than derived, because there is no field in the manifest
# that says which comes first and inventing one to sort by would be a second answer.
PHASE_ORDER = ("discover", "decide", "plan", "build", "verify")


def phase_map() -> list[tuple[str, list[str]]]:
    """The catalogue grouped the way it is meant to be read, in the order the work happens.

    `EP-135` asks that the surfaces show the skills by the five phases, and until this
    function the map existed in exactly one place: `tests/skill_eval.py`, a gate runner. So
    the field was declared for a person meeting the catalogue with no idea what any of it is
    for, and the only person who ever saw it was a developer watching CI — which is the
    complaint the row was reopened with.

    It lives here so the product can show it and the gate can call the same one. Two copies
    of a map is two maps within a week.

    A phase with nothing in it is returned empty rather than dropped: the five are a claim
    about how the work is arranged, and a map that quietly showed four would be the claim
    changing without anybody deciding to.
    """

    placed = phases()
    grouped: dict[str, list[str]] = {phase: [] for phase in PHASE_ORDER}
    for name, phase in sorted(placed.items()):
        grouped.setdefault(phase, []).append(name)
    ordered = [(phase, grouped.get(phase, [])) for phase in PHASE_ORDER]
    # Anything declared under a phase nobody named comes last and is visible. Dropping it
    # would hide a manifest that had grown a sixth phase, which is exactly the change
    # somebody would want to see.
    ordered += [
        (phase, names) for phase, names in sorted(grouped.items()) if phase not in PHASE_ORDER
    ]
    return ordered


def skill_sequence() -> dict:
    """The governed cycle's order, read from the one data file that owns it.

    Bare prose in `ai-cycle/SKILL.md` was the only declaration of which stage follows
    which, and nothing in the gate read it — a renamed stage would fail the corpus
    refusals that name it while the cycle's own sequence rotted in silence. It is data
    now, `policy/skill-sequence.toml`, so a rename, a backwards phase or a fork flag the
    frontmatter does not carry fails a test instead of rotting. A second copy here would
    be a second answer within a week.
    """

    try:
        declared = tomllib.loads(paths.policy("skill-sequence.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return declared


def next_stage(name: str) -> str:
    """The stage that follows `name` in the cycle, in words a person reads.

    The gate is a line, not a stage: the last stage of the first half hands over to the
    human approval the map's `[gate]` section declares, and the last stage of the cycle
    hands over to the end. A skill that is not in the cycle returns the empty string, and
    the absence of a "Sigue" line on its router says it is standalone — which is how a
    router tells a person the map rather than a second copy of it.
    """

    declared = skill_sequence()
    first = declared.get("first_half", [])
    order = first + declared.get("second_half", [])
    if name not in order:
        return ""
    position = order.index(name)
    if position == len(order) - 1:
        return "fin del ciclo"
    if position == len(first) - 1:
        return "la aprobación humana del brief"
    return order[position + 1]


def router_body(name: str, description: str, phase: str = "", case: str = "") -> str:
    """One router, generated from the skill it routes to.

    A router is a convenience and not a second copy: it names the skill and forwards the
    request, and every instruction still lives in one `SKILL.md`. A router that restated any
    of it would be the second normative layer `EP-071` forbids, kept up to date by hand.

    The phase and the example are not a restatement for the same reason the description is
    not: every one of them is read from a file that already holds it — the manifest and the
    labelled corpus — and written with a digest beside it. Without them a person meeting the
    catalogue on their own surface got a wall of commands with no map, which is the thing
    `EP-135` names, and the map was being printed only where the gate runs.
    """

    follows = next_stage(name)
    if follows in ("la aprobación humana del brief", "fin del ciclo"):
        line = f"Sigue: {follows}"
    elif follows:
        line = f"Sigue en el ciclo: {follows}"
    else:
        line = ""
    return ROUTER.format(
        name=name,
        description=description.strip().replace("\n", " "),
        phase=phase or "phase not declared",
        example=f"Say something like: “{case}”" if case else "",
        follows=line,
    )


def install_routers(surfaces: list[dict] | None = None) -> list[dict]:
    """A `/ai-*` command per skill, into the surfaces that declare where those live.

    Generated, hashed and recorded — those three together are what makes this an install
    rather than a file drop. `how` carries the digest of exactly what was written, so
    `doctor` can tell a router nobody touched from one somebody edited, and `uninstall` can
    refuse to remove a file that is no longer the one we wrote.

    Only surfaces with a `commands` root get one, and today that is one of eight. Writing a
    router into a directory whose convention was guessed at is worse than not writing it:
    the file lands somewhere a person did not expect, does nothing, and has to be found by
    hand. The absence is reported by `doctor` rather than filled in by the installer.
    """

    rows = table()["surface"] if surfaces is None else surfaces
    written: list[dict] = []
    placed = phases()
    # A commands root is the person's directory too. `write_text` below is unconditional,
    # so without this set a personal `~/.claude/commands/ai-note.md` was destroyed by the
    # generated router — no prompt, no backup, and a repository file in the same run gets
    # both. A path this framework has not recorded writing is not this framework's to
    # replace, and a router for a skill we skipped points at a body that never landed.
    mine = {row["path"] for row in receipt().get("wrote", []) if row.get("kind") == "router"}
    for surface in rows:
        root = surface.get("commands")
        if not root:
            continue
        where = expand(root)
        where.mkdir(parents=True, exist_ok=True)
        names = [skill.name for skill in sorted(paths.skills().glob("ai-*"))]
        theirs = (
            {path.name for path in foreign(expand(surface["skills"]), names)}
            if surface.get("skills")
            else set()
        )
        for skill in sorted(paths.skills().glob("ai-*")):
            if skill.name in theirs:
                continue
            if (where / f"{skill.name}.md").exists() and str(
                where / f"{skill.name}.md"
            ) not in mine:
                continue
            body = router_body(
                skill.name, _described(skill), placed.get(skill.name, ""), example(skill)
            )
            target = where / f"{skill.name}.md"
            target.write_text(body, encoding="utf-8")
            # The bytes on disk, never the string we meant to put there. `write_text`
            # translates `\n` to `\r\n` on Windows, so hashing `body` recorded a digest of
            # something that was never written — and `uninstall` reads the file back with
            # `read_bytes`, so every generated router looked edited by a stranger from the
            # first second and refused to be removed. Hashing the file cannot desync from
            # the file, on any platform, for any reason anybody thinks of later.
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            written.append({"path": str(target), "kind": "router", "how": f"generated {digest}"})
    return written


def _described(skill: Path) -> str:
    """The skill's own description, so the router and the skill cannot disagree.

    Folded, because every one of these is written `description: >-` with the text on the
    lines below it. Reading only the first line answered with the fold marker and produced a
    router describing itself by its own name — which is a description that tells a person
    nothing they did not already have from the command they typed.
    """

    lines = (skill / "SKILL.md").read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        inline = line.removeprefix("description:").strip()
        if inline and inline not in (">-", ">", "|", "|-"):
            return inline
        folded = []
        for following in lines[index + 1 :]:
            if not following.startswith("  "):
                break
            folded.append(following.strip())
        return " ".join(folded) or skill.name
    return skill.name


def install_guards(surfaces: list[dict]) -> list[tuple[str, str, str]]:
    results = []
    for surface in surfaces:
        writer = WRITERS.get(surface["writer"])
        if writer is None:
            results.append((surface["name"], "", "no wiring needed"))
            continue
        detail = writer(expand(surface["settings"]))
        results.append((surface["name"], surface["settings"], detail))
    return results


def prior_hooks_path(root: Path) -> str:
    """What core.hooksPath was before we wrote ours. The wiring overwrote it without ever
    reading it and uninstall then unset it, so a repository that had its own hooks path
    before us did not get it back: the no-lock-in promise was a command that left the
    repository different from how it found it."""
    return subprocess.run(
        ["git", "-C", str(root), "config", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


def cli_answers(*arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Ask this interpreter's own CLI a question, and hand back what it said.

    It was called `anchor_answers` and never checked an anchor: it ran `--version`.
    Specification 022 deleted the anchor and the name went with it, in one pass, because
    `tests/conftest.py` captures this function at import — so a half-done rename reds the
    whole suite during collection rather than in one test.

    Its own function because it is the one part of wiring that depends on the environment
    rather than on the repository, and a test about where files land should not turn on
    whether the interpreter running it happens to have the package importable. It did:
    inside the mutation harness's sandbox this probe fails, and it took a shipped test on
    canonical homes down with it, so the mutation gate could not collect a baseline at all.

    `-m` puts the working directory on `sys.path`, so without `PYTHONSAFEPATH` the module
    that answers is whichever `ai_engineering/` the caller happened to be standing in.
    A review planted one and watched it satisfy this check. Spec 044: `doctor` shares the
    probe, passing its own arguments, so the two cannot drift."""

    return subprocess.run(
        [sys.executable, "-m", "ai_engineering.cli", *arguments],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        cwd=str(cwd) if cwd is not None else None,
        env={**os.environ, "PYTHONSAFEPATH": "1"},
    )


def wire_git(root: Path) -> str:
    """Repository-scoped, absolute, expanded. A global core.hooksPath would impose our
    commit convention on every foreign clone on the machine, forks included.

    ai.eng records which CLI wrote these hooks. `command -v ai-eng` proves a binary exists
    and never that it is this one: an older install on the PATH has no `accept` verb, so
    pre-push refused every push in the repository it had just been installed into.

    And the anchor is executed before it is written down. A live interpreter with a dead
    `ai_engineering.cli` — an editable install whose `.pth` points at a deleted worktree,
    which is the state this machine was actually found in — persists an anchor that looks
    configured and answers nothing. Every hook that resolves the CLI through it then fails
    on a repository somebody just installed into. So the command runs first, and none of
    the three keys is written unless it did."""

    try:
        proved = cli_answers()
    except (OSError, subprocess.SubprocessError) as why:
        raise Unreadable(
            f"the CLI this install would record could not be executed: {why.__class__.__name__}"
        ) from why
    if proved.returncode != 0 or "ai-engineering" not in proved.stdout:
        raise Unreadable(
            "the CLI this install would record did not answer `--version`, so the git anchor "
            "would name an interpreter that cannot run it"
        )

    rows = (
        ("core.hooksPath", str(paths.git_hooks())),
        ("ai.managed", "true"),
        ("ai.eng", f"{sys.executable} -m ai_engineering.cli"),
    )
    for key, value in rows:
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True, timeout=10)
    return str(paths.git_hooks())
