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

import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from ai_engineering import __version__, paths

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


class Unreadable(Exception):
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
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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
    own source about replacing that positional key."""
    data = read_json(path)
    groups = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
    for group in groups:
        if ours(group):
            return f"already present at position {groups.index(group) + 1} of {len(groups)}"
    groups.append(
        {
            "handlers": [
                {
                    "type": "command",
                    "command": command("PreToolUse"),
                    "timeout_ms": 5000,
                    "status_message": f"{MARK} guards",
                    "async": False,
                }
            ]
        }
    )
    write_json(path, data)
    return f"appended, position {len(groups)} of {len(groups)}"


def ts_opencode(path: Path) -> str:
    """One TypeScript file that shells out to the same dispatcher every other surface
    calls. Not weightless: the moment any local plugin exists OpenCode creates a
    lockfile and a ~61 MB node_modules, and the first run pays an install."""
    path.parent.mkdir(parents=True, exist_ok=True)
    source = (paths.surfaces() / "opencode.ts").read_text(encoding="utf-8")
    for token, value in (
        ("__PYTHON__", sys.executable),
        ("__CHAIN__", str(paths.hooks() / "chain.py")),
        ("__BEAT__", str(paths.home() / "cache" / "opencode-heartbeat")),
    ):
        source = source.replace(token, value)
    path.write_text(source, encoding="utf-8")
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
        how = "none"
        for skill in sorted(real.glob("ai-*")):
            how = link(skill, expand(root) / skill.name)
        written.append({"path": str(expand(root)), "kind": "link", "how": how})
    return written


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


def wire_git(root: Path) -> str:
    """Repository-scoped, absolute, expanded. A global core.hooksPath would impose our
    commit convention on every foreign clone on the machine, forks included.

    ai.eng records which CLI wrote these hooks. `command -v ai-eng` proves a binary exists
    and never that it is this one: an older install on the PATH has no `accept` verb, so
    pre-push refused every push in the repository it had just been installed into."""
    rows = (
        ("core.hooksPath", str(paths.git_hooks())),
        ("ai.managed", "true"),
        ("ai.eng", f"{sys.executable} -m ai_engineering.cli"),
    )
    for key, value in rows:
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True, timeout=10)
    return str(paths.git_hooks())
