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

MARK = "ai-engineering"
EVENTS = ("PreToolUse", "PostToolUse", "SessionStart", "SessionEnd")


def table() -> dict:
    return tomllib.loads(paths.policy("surfaces.toml").read_text(encoding="utf-8"))


def expand(entry: str) -> Path:
    return Path(entry).expanduser()


def command(event: str) -> str:
    """Absolute, expanded, and pointing inside the wheel."""
    return f'"{sys.executable}" "{paths.hooks() / "chain.py"}" {event}'


def detect(only: list[str] | None = None) -> list[dict]:
    found = []
    for surface in table()["surface"]:
        if only and surface["id"] not in only:
            continue
        if surface["detect"] and expand(surface["detect"]).exists():
            found.append(surface)
    return found


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ours(entry) -> bool:
    return MARK in json.dumps(entry)


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
    The receipt turns "do not step on a file you did not create" into a lookup."""
    data = receipt()
    data.setdefault("machine_id", paths.load("_emit").machine_id())
    data["version"] = __version__
    data["python"] = sys.executable
    data["hooks"] = str(paths.hooks())
    known = {(row["path"], row["kind"]) for row in entries}
    kept = [row for row in data.get("wrote", []) if (row["path"], row["kind"]) not in known]
    data["wrote"] = kept + entries
    write_json(receipt_path(), data)


def install_skills() -> list[dict]:
    real = paths.home() / "skills"
    real.mkdir(parents=True, exist_ok=True)
    for skill in sorted(paths.skills().glob("ai-*")):
        shutil.copytree(skill, real / skill.name, dirs_exist_ok=True)
    written = [{"path": str(real), "kind": "skills", "how": "wheel"}]
    for root in sorted({s["skills"] for s in table()["surface"] if s.get("skills")}):
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


def hooks_path_for(root: Path) -> str:
    return str(paths.git_hooks())


def wire_git(root: Path) -> str:
    """Repository-scoped, absolute, expanded. A global core.hooksPath would impose our
    commit convention on every foreign clone on the machine, forks included.

    ai.eng records which CLI wrote these hooks. `command -v ai-eng` proves a binary exists
    and never that it is this one: an older install on the PATH has no `accept` verb, so
    pre-push refused every push in the repository it had just been installed into."""
    rows = (
        ("core.hooksPath", hooks_path_for(root)),
        ("ai.managed", "true"),
        ("ai.eng", f"{sys.executable} -m ai_engineering.cli"),
    )
    for key, value in rows:
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True, timeout=10)
    return hooks_path_for(root)
