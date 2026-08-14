"""Undoes everything the receipt lists. The no-lock-in promise, as a command.

It never touches specs/, your CONSTITUTION.md or your AGENTS.md. Those were yours from
the second they were written, and deleting somebody's record to uninstall a tool is the
behaviour this product was built to argue against.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from ai_engineering import __version__, outcome, paths, wiring
from ai_engineering import init as installer

KEEPS = ("specs/", "CONSTITUTION.md", "AGENTS.md", "docs/adr/")
GLOBAL_KINDS = ("guard", "link", "skills")


def receipt_state() -> tuple[dict, list[dict]] | None:
    """One current, complete receipt whose rows cannot expand uninstall's authority."""
    target = wiring.receipt_path()
    try:
        parent = target.parent.lstat()
        if not stat.S_ISDIR(parent.st_mode):
            return None
        info = target.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            return None
        data = wiring.receipt()
    except (OSError, wiring.Unreadable):
        return None
    if (
        not isinstance(data, dict)
        or data.get("version") != __version__
        or not all(
            isinstance(data.get(key), str) and data[key]
            for key in ("machine_id", "python", "hooks")
        )
        or not isinstance(data.get("wrote"), list)
    ):
        return None
    rows = data["wrote"]
    if any(
        not isinstance(row, dict)
        or set(row) != {"path", "kind", "how"}
        or not all(isinstance(row.get(key), str) for key in ("path", "kind", "how"))
        for row in rows
    ):
        return None
    identities = [(row["path"], row["kind"]) for row in rows]
    if len(identities) != len(set(identities)):
        return None

    repository_roots = [
        Path(row["path"])
        for row in rows
        if row["kind"] == "repo"
        and Path(row["path"]).is_absolute()
        and canonical(row, Path(row["path"])) is not None
    ]
    safe: list[dict] = []
    for row in rows:
        if row["kind"] in GLOBAL_KINDS:
            normalized = canonical(row, None)
        elif row["kind"] == "repo":
            root = Path(row["path"])
            normalized = canonical(row, root) if root in repository_roots else None
        elif row["kind"] == "project":
            candidates = [root for root in repository_roots if canonical(row, root) is not None]
            normalized = canonical(row, candidates[0]) if len(candidates) == 1 else None
        else:
            normalized = None
        if normalized is None:
            return None
        safe.append(normalized)
    return data, safe


def _tree(path: Path) -> dict[str, bytes] | None:
    """Regular bytes below one directory, or None when aliases/special files make it blind."""
    try:
        if path.is_symlink() or not path.is_dir():
            return None
        files: dict[str, bytes] = {}
        for item in path.rglob("*"):
            if item.is_symlink():
                return None
            if item.is_file():
                files[item.relative_to(path).as_posix()] = item.read_bytes()
            elif not item.is_dir():
                return None
        return files
    except OSError:
        return None


def _expected_skill_names() -> tuple[str, ...] | None:
    source = paths.skills()
    try:
        info = source.lstat()
        if not stat.S_ISDIR(info.st_mode):
            return None
        skills = [path for path in source.glob("ai-*")]
        if not skills or any(path.is_symlink() or not path.is_dir() for path in skills):
            return None
    except OSError:
        return None
    return tuple(sorted(path.name for path in skills))


def _skills_owned(root: Path, how: str) -> bool:
    """Every canonical skill still present is byte-identical to the installed source."""
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        return False
    names = _expected_skill_names()
    if names is None:
        return False
    store = paths.home() / "skills"
    for name in names:
        target = root / name
        if not os.path.lexists(target):
            continue
        if how == "symlink":
            if not target.is_symlink():
                return False
            landing = Path(os.readlink(target))
            landing = landing if landing.is_absolute() else target.parent / landing
            if landing.resolve(strict=False) != (store / name).resolve(strict=False):
                return False
        elif how in ("copy", "wheel"):
            if _tree(target) != _tree(paths.skills() / name):
                return False
        else:
            return False
    return True


def _opencode_source() -> str:
    source = (paths.surfaces() / "opencode.ts").read_text(encoding="utf-8")
    for token, value in (
        ("__PYTHON__", sys.executable),
        ("__CHAIN__", str(paths.hooks() / "chain.py")),
        ("__BEAT__", str(paths.home() / "cache" / "opencode-heartbeat")),
    ):
        source = source.replace(token, value)
    return source


def _json_guard_owned(data: dict, how: str) -> bool:
    own = []

    def collect(node) -> None:
        if isinstance(node, list):
            own.extend(item for item in node if wiring.ours(item))
            for item in node:
                collect(item)
        elif isinstance(node, dict):
            for value in node.values():
                collect(value)

    collect(data)

    def same(expected: list[dict]) -> bool:
        def render(item: dict) -> str:
            return json.dumps(item, sort_keys=True, separators=(",", ":"))

        return sorted(map(render, own)) == sorted(map(render, expected))

    if how == "json_claude":
        expected = []
        for event in wiring.EVENTS:
            hook = {"type": "command", "command": wiring.command(event)}
            expected.extend(({"matcher": "*", "hooks": [hook]}, hook))
        return same(expected)
    if how == "json_cursor":
        expected = [
            {"command": wiring.command("PreToolUse")},
            {"command": wiring.command("PreToolUse")},
        ]
        return data.get("failClosed") is True and same(expected)
    if how == "json_codex":
        expected = {
            "handlers": [
                {
                    "type": "command",
                    "command": wiring.command("PreToolUse"),
                    "timeout_ms": 5000,
                    "status_message": f"{wiring.MARK} guards",
                    "async": False,
                }
            ]
        }
        return same([expected, expected["handlers"][0]])
    if how == "json_copilot":
        return data == {
            "hooks": {"preToolUse": [{"type": "command", "command": wiring.command("PreToolUse")}]}
        }
    return False


def _guard_owned(row: dict) -> bool:
    target = wiring.expand(row["path"])
    if not os.path.lexists(target):
        return True
    try:
        info = target.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            return False
        if row["how"] == "ts_opencode":
            return target.read_text(encoding="utf-8") == _opencode_source()
        data = json.loads(target.read_text(encoding="utf-8"))
        return isinstance(data, dict) and _json_guard_owned(data, row["how"])
    except (OSError, UnicodeError, ValueError):
        return False


def _project_body(path: Path, root: Path) -> str | None:
    name = path.relative_to(root).as_posix()
    if name in installer.OFFERS and name not in installer.PROTECTED:
        return installer.OFFERS[name][1](root)
    return {
        ".ai/config.toml": installer.skeletons.CONFIG_TOML.format(version=__version__),
        ".ai/.gitignore": installer.skeletons.AI_GITIGNORE,
        "specs/.gitkeep": "",
    }.get(name)


def _git_value(root: Path, key: str) -> str | None:
    try:
        read = subprocess.run(
            ["git", "-C", str(root), "config", "--local", "--get", key],
            timeout=10,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if read.returncode not in (0, 1):
        return None
    return read.stdout.strip() if read.returncode == 0 else ""


def _owned(row: dict, root: Path | None) -> bool:
    kind = row["kind"]
    if kind == "guard":
        return _guard_owned(row)
    if kind == "link":
        return _skills_owned(Path(row["path"]), row["how"])
    if kind == "skills":
        return _skills_owned(Path(row["path"]), "wheel")
    if root is None:
        return False
    if kind == "project":
        target = Path(row["path"])
        if not os.path.lexists(target):
            return True
        expected = _project_body(target, root)
        try:
            info = target.lstat()
            return (
                expected is not None
                and stat.S_ISREG(info.st_mode)
                and info.st_nlink == 1
                and target.read_text(encoding="utf-8") == expected
            )
        except (OSError, UnicodeError):
            return False
    if kind == "repo":
        return (
            _git_value(root, "core.hooksPath") == str(paths.git_hooks())
            and _git_value(root, "ai.managed") == "true"
            and _git_value(root, "ai.eng") == f"{sys.executable} -m ai_engineering.cli"
        )
    return False


def remove_plugin(path: Path) -> bool:
    """The OpenCode plugin is a file this installer wrote whole, so it is removed rather
    than edited. It used to be sent to the JSON stripper below, which found the signature
    inside the TypeScript, handed the TypeScript to a JSON parser and raised — uncaught,
    and mid-loop, so every surface after it stayed wired by the one verb whose whole pitch
    is that governance comes out cleanly."""
    if not path.exists():
        return False
    path.unlink()
    return True


def strip_entries(path: Path) -> bool:
    """True when our entries were taken out, False when there were none to take. Anything
    else — a file we cannot read, cannot parse, or cannot write — raises, because those are
    three ways of leaving a guard wired and all three used to answer "had no entry of ours".

    The write is inside the guard now. It was outside every `try` in a function whose read
    and parse were both guarded, so one settings file with the wrong permissions raised
    mid-loop and left every surface after it in the receipt's order still wired — which is
    the shape spec 003 closed for the OpenCode parse crash, in the one line that fix did not
    reach."""
    try:
        blob = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    except OSError as why:
        raise wiring.Unreadable(f"{path} could not be read: {why.strerror}") from why
    if wiring.SIGNATURE not in blob:
        return False
    try:
        data = json.loads(blob)
    except ValueError as why:
        # It holds our entry and this routine only knows how to edit JSON. Reporting "no
        # entry of ours" about a file that has just proved it has one is the false green
        # this whole spec is about, one function down.
        raise wiring.Unreadable(
            f"{path} holds our entry and is not readable as JSON: {why}"
        ) from why

    def clean(node):
        if isinstance(node, list):
            return [clean(item) for item in node if wiring.SIGNATURE not in json.dumps(item)]
        if isinstance(node, dict):
            return {key: clean(value) for key, value in node.items()}
        return node

    try:
        wiring.write_json(path, clean(data))
    except OSError as why:
        raise wiring.Unreadable(f"{path} could not be written: {why.strerror}") from why
    return True


def inside(path: str, root: Path) -> bool:
    """Whether a recorded path is in this repository, by path parts and never by string
    prefix. `"/repos/tests-backup/justfile".startswith("/repos/tests")` is True, and the
    line that asked it went straight on to `unlink`, so standing in one repository deleted
    recorded files out of every sibling whose name began with the same letters. Nothing on
    the operator's machine happened to pair that way, which is luck and not a control."""
    return Path(path) == root or root in Path(path).parents


def canonical(row: dict, root: Path | None) -> dict | None:
    """Return the trusted form of a destination this installer is capable of owning.

    `machine.json` records what happened; it is not an instruction language. Without this
    closed set, changing `kind` and `path` in one row turns uninstall into arbitrary unlink
    or rmtree. The table and init's managed set are the sources that wrote the rows, so they
    also supply the path used on the way out; receipt text is only compared with it."""
    kind, path, how = row.get("kind"), row.get("path"), row.get("how", "")
    if not isinstance(path, str):
        return None
    if kind == "guard":
        for surface in wiring.table()["surface"]:
            if path == surface["settings"] and how == surface["writer"] != "none":
                return {"path": surface["settings"], "kind": "guard", "how": surface["writer"]}
    if kind == "link":
        for surface in wiring.table()["surface"]:
            target = wiring.expand(surface["skills"]) if surface.get("skills") else None
            if target is not None and path == str(target) and how in ("copy", "symlink"):
                safe_how = "copy" if how == "copy" else "symlink"
                return {"path": str(target), "kind": "link", "how": safe_how}
    if kind == "skills":
        target = paths.home() / "skills"
        if path == str(target) and how == "wheel":
            return {"path": str(target), "kind": "skills", "how": "wheel"}
    if root is None:
        return None
    if kind == "project":
        for target in installer.managed_paths(root):
            if path == str(target) and how == "written":
                return {"path": str(target), "kind": "project", "how": "written"}
    if kind == "repo":
        safe = isinstance(how, str) and len(how) <= 4096 and (not how or how.isprintable())
        if path == str(root) and safe:
            return {"path": str(root), "kind": "repo", "how": how}
    return None


def owned(row: dict, root: Path | None) -> bool:
    return canonical(row, root) is not None


def unwire(root: Path, rows: list[dict]) -> None:
    """The repository half, from the receipt and never from a hardcoded list. Two things
    it fixes: the hooks path is restored to whatever was configured before us rather than
    unset, so a repository that had its own does not lose it to a verb that promises no
    lock-in; and only files this install actually wrote are removed, so a CLAUDE.md or a
    justfile somebody wrote by hand survives. Anything the constitution protects was never
    in the receipt, because init writes those two once and never touches them again."""
    mine = [row for row in rows if row.get("kind") == "project" and owned(row, root)]
    for row in mine:
        Path(row["path"]).unlink(missing_ok=True)
    before = next(
        (row["how"] for row in rows if row["kind"] == "repo" and row["path"] == str(root)), ""
    )
    restore = (
        ["config", "--local", "--", "core.hooksPath", before]
        if before
        else ["config", "--local", "--unset", "--", "core.hooksPath"]
    )
    for key in (
        restore,
        ["config", "--local", "--unset", "--", "ai.managed"],
        ["config", "--local", "--unset", "--", "ai.eng"],
    ):
        git(root, key)


def git(root: Path, key: list[str]) -> None:
    """One place for the three arguments every call here shares, and that is the whole
    reason it exists: `timeout=10` and `capture_output=True` written at three call sites are
    six mutants no honest test can kill, because a repository that answers in eleven seconds
    instead of ten is not a behaviour anybody can assert. Spec 006 met the same thing in
    `soft_wrap=True` and took the same way out — the argument stops being repeated, so the
    mutants stop existing rather than being waived."""
    subprocess.run(["git", "-C", str(root), *key], timeout=10, capture_output=True, check=True)


def unredirected(path: Path, anchor: Path) -> bool:
    """Whether every component below `anchor` is exactly what it says it is.

    A global destination is reached by name, and a name is not a place: one symlink,
    junction or reparse point on the way and this verb removes entries from, or writes over,
    a file somewhere else entirely. Ownership is checked by content elsewhere in this module,
    which answers "is this ours" — it cannot answer "is this here".

    The anchor itself is trusted and nothing above it is inspected. On a real machine the
    path to a home directory crosses links nobody controls (`/var` is a link on macOS), so
    claiming to have proved that part would be the false green this file is full of comments
    about. What is claimed is the part that is ours: from the home down.
    """

    try:
        relative = path.relative_to(anchor)
    except ValueError:
        return False
    walked = anchor
    for part in relative.parts:
        walked = walked / part
        try:
            value = walked.lstat()
        except FileNotFoundError:
            return True
        except OSError:
            return False
        if stat.S_ISLNK(value.st_mode) or getattr(value, "st_reparse_tag", 0):
            return False
    return True


def fate(row: dict, root: Path | None) -> str:
    """What this run will do with this row, decided before anything is printed and used
    again to decide what is done. Two answers derived separately are two answers that can
    disagree, and this verb's whole defect was a list that promised more than the loop
    underneath it had branches for: it printed thirty-two rows under "every one is listed
    here", asked "Remove them?", and had no branch at all for twenty-four of them.

    An empty string means remove it. Anything else is the reason it is kept, printed on the
    row's own line so that nothing is silently spared."""
    kind, path = row.get("kind"), row.get("path")
    if kind in ("project", "repo") and root is None:
        return "kept — repository files; re-run with --project inside that repository"
    if not isinstance(path, str):
        return "kept — receipt target is not one this installer can own"
    if kind == "project" and root is not None and not inside(path, root):
        return "kept — belongs to another repository"
    if kind == "repo" and root is not None and path != str(root):
        return f"kept — not this repository ({root})"
    if not owned(row, root):
        return "kept — receipt target is not one this installer can own"
    anchor = root if kind in ("project", "repo") else Path.home()
    if anchor is not None and not unredirected(wiring.expand(path), anchor):
        return "kept — a link on the way means this name is not that place"
    return ""


def strip_links(root: Path, how: str) -> int:
    """The skills this install put in that root, and nothing else that happens to be named
    like them. It used to glob `ai-*` and unlink whatever came back, so a skill somebody
    else installed under that prefix was collateral — and every skill on Windows survived,
    because `wiring.link` copies where symlinks are unavailable and records `how: "copy"`
    while this branch only ever unlinked symlinks. That second half was a strict xfail in
    this repository, which is a defect with an alarm on it rather than an unknown one.

    The names come from the wheel's own skills directory rather than from the store, because
    the store row is removed earlier in the same run and a list read from it would be empty
    by the time this is reached. A symlink counts as ours when it resolves into our store."""
    mine = paths.home() / "skills"
    removed = 0
    names = _expected_skill_names()
    if names is None:
        raise wiring.Unreadable("the installed skill catalogue could not be read")
    for name in names:
        target = root / name
        if target.is_symlink():
            landing = Path(os.readlink(target))
            landing = landing if landing.is_absolute() else target.parent / landing
            if landing.resolve(strict=False) == (mine / name).resolve(strict=False):
                target.unlink()
                removed += 1
        elif how == "copy" and target.is_dir():
            shutil.rmtree(target)
            removed += 1
    return removed


def strip_skills(path: Path) -> bool:
    """The store this install copied the skills into. It is ours, nothing else reads it, and
    it was listed under "Remove them?" with no branch to remove it — so eight skills survived
    every uninstall and `init` counted them off the disk and called the machine ready."""
    if not path.is_dir():
        return False
    removed = False
    names = _expected_skill_names()
    if names is None:
        raise wiring.Unreadable("the installed skill catalogue could not be read")
    for name in names:
        skill = path / name
        if skill.is_dir() and not skill.is_symlink():
            shutil.rmtree(skill)
            removed = True
    return removed


def _removed(row: dict, root: Path | None) -> bool:
    kind, target = row["kind"], Path(row["path"])
    if kind == "guard":
        actual = wiring.expand(row["path"])
        if not os.path.lexists(actual):
            return True
        if row["how"] == "ts_opencode":
            return False
        try:
            return wiring.SIGNATURE not in actual.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return False
    if kind in ("link", "skills"):
        names = _expected_skill_names()
        return names is not None and not any(os.path.lexists(target / name) for name in names)
    if kind == "project":
        return not os.path.lexists(target)
    if kind == "repo" and root is not None:
        return (
            _git_value(root, "core.hooksPath") == row["how"]
            and _git_value(root, "ai.managed") == ""
            and _git_value(root, "ai.eng") == ""
        )
    return False


def main(argv: list[str]) -> outcome.Result:
    parser = argparse.ArgumentParser(prog="ai-eng uninstall")
    parser.add_argument("--project", action="store_true", help="also unwire this repository")
    parser.add_argument("-y", "--yes", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not sys.stdin.isatty():
        print("  INCOMPLETE: uninstall requires a person at a keyboard. Nothing removed.")
        return outcome.result("INCOMPLETE")
    installed = receipt_state()
    if installed is None:
        print("  INCOMPLETE: the install receipt is missing, partial, corrupt or ambiguous.")
        print("  Nothing removed. Repair or migrate the receipt, then run uninstall again.")
        return outcome.result("INCOMPLETE")
    receipt, rows = installed
    root = paths.repo_root() if args.project else None
    if args.project and root is None:
        print("  INCOMPLETE: --project requires the repository that will be unwired.")
        print("  Nothing removed. Run this from inside the intended repository.")
        return outcome.result("INCOMPLETE")
    plan = [(row, fate(row, root), canonical(row, root)) for row in rows]
    going = [safe for _, kept, safe in plan if not kept and safe is not None]

    if any(not _owned(row, root if row["kind"] in ("project", "repo") else None) for row in going):
        print(
            "  INCOMPLETE: a receipted target no longer matches the exact bytes or entries owned."
        )
        print("  Nothing removed. Restore the owned target or remove the ambiguous receipt row.")
        return outcome.result("INCOMPLETE")

    print(f"  {len(rows)} things are recorded here, and {len(going)} of them will be removed:")
    for row, kept, _ in plan:
        print(f"    {row['kind']:<8} {row['path']}{'  ·  ' + kept if kept else ''}")
    print(f"  Kept, always: {', '.join(KEEPS)}")
    elsewhere = sorted({row["path"] for row, kept, _ in plan if kept and row["kind"] == "repo"})
    for other in elsewhere:
        print(f"  Not entered: {other} — `cd {other} && ai-eng uninstall --project`")
    if not going:
        print("  Nothing to remove.")
        return outcome.result("READY")
    if args.dry_run:
        print("  Dry run: the exact receipted removals above were derived; nothing was removed.")
        return outcome.dry_run(exact_changes=True)
    if not (
        args.yes
        or (sys.stdin.isatty() and input("\n◆ Remove them? (y/N) › ").lower().startswith("y"))
    ):
        print("  nothing removed.")
        return outcome.result("CANCELLED")
    current = receipt_state()
    if current is None or current[0] != receipt or current[1] != rows:
        print("  INCOMPLETE: the receipt changed while consent was being requested.")
        print("  Nothing removed. Review the current receipt, then run uninstall again.")
        return outcome.result("INCOMPLETE")
    if any(not _owned(row, root if row["kind"] in ("project", "repo") else None) for row in going):
        print("  INCOMPLETE: ownership changed while consent was being requested. Nothing removed.")
        return outcome.result("INCOMPLETE")

    gone, stuck = [], []
    for row in going:
        path = Path(row["path"])
        try:
            if row["kind"] == "guard" and row.get("how") == "ts_opencode":
                done = remove_plugin(wiring.expand(row["path"]))
                print(f"  ✓ plugin removed: {path}" if done else f"  → {path} was already gone")
            elif row["kind"] == "guard":
                done = strip_entries(wiring.expand(row["path"]))
                print(
                    f"  ✓ entries removed from {path}"
                    if done
                    else f"  → {path} had no entry of ours"
                )
            elif row["kind"] == "link":
                count = strip_links(path, row.get("how", ""))
                print(
                    f"  ✓ {count} skills removed from {path}"
                    if count
                    else f"  → {path} had none of ours left"
                )
            elif row["kind"] == "skills":
                done = strip_skills(path)
                print(f"  ✓ skills removed from {path}" if done else f"  → {path} was already gone")
            else:
                continue  # project and repo rows are the repository half, undone below
        except (wiring.Unreadable, OSError) as why:
            # This file, and not the loop. One settings file with the wrong permissions used
            # to raise here and leave every surface after it wired, silently, from the verb
            # whose whole pitch is that governance comes out cleanly. The row stays in the
            # receipt because the entry is still in the file, which is the truth.
            print(f"  ✗ {why}")
            stuck.append(row)
            continue
        gone.append(row)

    project_rows = [row for row in going if row["kind"] in ("project", "repo")]
    if root is not None and project_rows:
        try:
            unwire(root, project_rows)
        except (OSError, subprocess.SubprocessError) as why:
            print(f"  ✗ repository could not be unwired: {why}")
            stuck += project_rows
        else:
            print(f"  ✓ {root} unwired. specs/, CONSTITUTION.md and AGENTS.md are untouched.")
            gone += project_rows
    if any(row["kind"] == "guard" and row["how"] == "ts_opencode" for row in gone):
        (paths.home() / "cache" / "opencode-heartbeat").unlink(missing_ok=True)
    # The record stops claiming what is no longer here. Without this the next `init` reads
    # the log, counts four guards and four links that were removed a second ago, prints
    # "Global ready", and refuses to rewire the machine it has just been asked to install.
    try:
        wiring.forget(gone)
    except (OSError, wiring.Unreadable) as why:
        print(f"  INCOMPLETE: the receipt could not be updated after removal: {why}")
        return outcome.result("INCOMPLETE")
    print(
        f"\n  The record is still at {paths.home() / 'state'}. Delete that folder yourself "
        f"if you want it gone: it is proof of what happened, and not ours to throw away."
    )
    if stuck:
        print(
            f"  {len(stuck)} of them are still wired and are still in the record. "
            f"Fix the files named above and run this again."
        )
        return outcome.result("INCOMPLETE")
    after = receipt_state()
    removed = {(row["path"], row["kind"]) for row in gone}
    expected = [row for row in receipt["wrote"] if (row["path"], row["kind"]) not in removed]
    if (
        after is None
        or after[0]["wrote"] != expected
        or any(
            not _removed(row, root if row["kind"] in ("project", "repo") else None) for row in gone
        )
    ):
        print("  INCOMPLETE: uninstall could not prove its removal and receipt postconditions.")
        return outcome.result("INCOMPLETE")
    return outcome.result("PASS")
