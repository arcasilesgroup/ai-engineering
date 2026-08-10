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
import subprocess
import sys
from pathlib import Path

from ai_engineering import init as installer
from ai_engineering import paths, wiring

KEEPS = ("specs/", "CONSTITUTION.md", "AGENTS.md", "docs/adr/")


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
    subprocess.run(["git", "-C", str(root), *key], timeout=10, capture_output=True)


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
    for skill in sorted(paths.skills().glob("ai-*")):
        target = root / skill.name
        if target.is_symlink():
            landing = Path(os.readlink(target))
            if landing == mine / skill.name or landing.is_relative_to(mine):
                target.unlink()
                removed += 1
        elif how == "copy" and target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            removed += 1
    return removed


def strip_skills(path: Path) -> bool:
    """The store this install copied the skills into. It is ours, nothing else reads it, and
    it was listed under "Remove them?" with no branch to remove it — so eight skills survived
    every uninstall and `init` counted them off the disk and called the machine ready."""
    if not path.is_dir():
        return False
    for skill in path.glob("ai-*"):
        shutil.rmtree(skill, ignore_errors=True)
    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser("ai-eng uninstall")
    parser.add_argument("--project", action="store_true", help="also unwire this repository")
    parser.add_argument("-y", "--yes", action="store_true")
    args = parser.parse_args(argv)

    rows = wiring.receipt().get("wrote", [])
    root = paths.repo_root() if args.project else None
    plan = [(row, fate(row, root), canonical(row, root)) for row in rows]
    going = [safe for _, kept, safe in plan if not kept and safe]

    print(f"  {len(rows)} things are recorded here, and {len(going)} of them will be removed:")
    for row, kept, _ in plan:
        print(f"    {row['kind']:<8} {row['path']}{'  ·  ' + kept if kept else ''}")
    print(f"  Kept, always: {', '.join(KEEPS)}")
    elsewhere = sorted({row["path"] for row, kept, _ in plan if kept and row["kind"] == "repo"})
    for other in elsewhere:
        print(f"  Not entered: {other} — `cd {other} && ai-eng uninstall --project`")
    if not going:
        print("  Nothing to remove.")
        return 0
    if not (
        args.yes
        or (sys.stdin.isatty() and input("\n◆ Remove them? (y/N) › ").lower().startswith("y"))
    ):
        print("  nothing removed.")
        return 1

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

    if root is not None:
        unwire(root, going)
        print(f"  ✓ {root} unwired. specs/, CONSTITUTION.md and AGENTS.md are untouched.")
        gone += [row for row in going if row["kind"] in ("project", "repo")]
    # Our own cache, and the OpenCode plugin's only proof that it ever loaded. It is fresh
    # for a day, so left behind it kept the coverage block reading BLOCKS for twenty-four
    # hours after the file it attests to was deleted. Cleared whenever the machine half runs
    # at all: after this, no plugin of ours is loaded anywhere, whatever the rows said.
    (paths.home() / "cache" / "opencode-heartbeat").unlink(missing_ok=True)
    # The record stops claiming what is no longer here. Without this the next `init` reads
    # the log, counts four guards and four links that were removed a second ago, prints
    # "Global ready", and refuses to rewire the machine it has just been asked to install.
    wiring.forget(gone)
    print(
        f"\n  The record is still at {paths.home() / 'state'}. Delete that folder yourself "
        f"if you want it gone: it is proof of what happened, and not ours to throw away."
    )
    if stuck:
        print(
            f"  {len(stuck)} of them are still wired and are still in the record. "
            f"Fix the files named above and run this again."
        )
        return 1
    return 0
