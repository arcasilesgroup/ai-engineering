"""Undoes everything the receipt lists. The no-lock-in promise, as a command.

It never touches specs/, your CONSTITUTION.md or your AGENTS.md. Those were yours from
the second they were written, and deleting somebody's record to uninstall a tool is the
behaviour this product was built to argue against.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

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
    try:
        blob = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if wiring.SIGNATURE not in blob:
        return False
    try:
        data = json.loads(blob)
    except ValueError:
        return False  # not ours to edit: this routine only knows how to edit JSON

    def clean(node):
        if isinstance(node, list):
            return [clean(item) for item in node if wiring.SIGNATURE not in json.dumps(item)]
        if isinstance(node, dict):
            return {key: clean(value) for key, value in node.items()}
        return node

    wiring.write_json(path, clean(data))
    return True


def unwire(root: Path, rows: list[dict]) -> None:
    """The repository half, from the receipt and never from a hardcoded list. Two things
    it fixes: the hooks path is restored to whatever was configured before us rather than
    unset, so a repository that had its own does not lose it to a verb that promises no
    lock-in; and only files this install actually wrote are removed, so a CLAUDE.md or a
    justfile somebody wrote by hand survives. Anything the constitution protects was never
    in the receipt, because init writes those two once and never touches them again."""
    mine = [row for row in rows if row["kind"] == "project" and row["path"].startswith(str(root))]
    for row in mine:
        Path(row["path"]).unlink(missing_ok=True)
    before = next(
        (row["how"] for row in rows if row["kind"] == "repo" and row["path"] == str(root)), ""
    )
    restore = (
        ["config", "core.hooksPath", before] if before else ["config", "--unset", "core.hooksPath"]
    )
    for key in (restore, ["config", "--unset", "ai.managed"], ["config", "--unset", "ai.eng"]):
        subprocess.run(["git", "-C", str(root), *key], timeout=10, capture_output=True)


def fate(row: dict, root: Path | None) -> str:
    """What this run will do with this row, decided before anything is printed and used
    again to decide what is done. Two answers derived separately are two answers that can
    disagree, and this verb's whole defect was a list that promised more than the loop
    underneath it had branches for: it printed thirty-two rows under "every one is listed
    here", asked "Remove them?", and had no branch at all for twenty-four of them.

    An empty string means remove it. Anything else is the reason it is kept, printed on the
    row's own line so that nothing is silently spared."""
    if row["kind"] in ("guard", "link", "skills"):
        return ""
    if root is None:
        return "kept — repository files; re-run with --project inside that repository"
    if row["kind"] == "repo":
        return "" if row["path"] == str(root) else f"kept — not this repository ({root})"
    return "" if row["path"].startswith(str(root)) else "kept — belongs to another repository"


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
    plan = [(row, fate(row, root)) for row in rows]
    going = [row for row, kept in plan if not kept]

    print(f"  {len(rows)} things are recorded here, and {len(going)} of them will be removed:")
    for row, kept in plan:
        print(f"    {row['kind']:<8} {row['path']}{'  ·  ' + kept if kept else ''}")
    print(f"  Kept, always: {', '.join(KEEPS)}")
    elsewhere = sorted({row["path"] for row, kept in plan if kept and row["kind"] == "repo"})
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

    gone = []
    for row in going:
        path = Path(row["path"])
        if row["kind"] == "guard" and row.get("how") == "ts_opencode":
            done = remove_plugin(wiring.expand(row["path"]))
            print(f"  ✓ plugin removed: {path}" if done else f"  → {path} was already gone")
        elif row["kind"] == "guard":
            done = strip_entries(wiring.expand(row["path"]))
            print(
                f"  ✓ entries removed from {path}" if done else f"  → {path} had no entry of ours"
            )
        elif row["kind"] == "link":
            for link in path.glob("ai-*"):
                link.unlink() if link.is_symlink() else None
            print(f"  ✓ symlinks removed from {path}")
        elif row["kind"] == "skills":
            done = strip_skills(path)
            print(f"  ✓ skills removed from {path}" if done else f"  → {path} was already gone")
        else:
            continue  # project and repo rows are the repository half, undone below
        gone.append(row)

    if root is not None:
        unwire(root, rows)
        print(f"  ✓ {root} unwired. specs/, CONSTITUTION.md and AGENTS.md are untouched.")
        gone += [row for row in going if row["kind"] in ("project", "repo")]
    # The record stops claiming what is no longer here. Without this the next `init` reads
    # the log, counts four guards and four links that were removed a second ago, prints
    # "Global ready", and refuses to rewire the machine it has just been asked to install.
    wiring.forget(gone)
    print(
        f"\n  The record is still at {paths.home() / 'state'}. Delete that folder yourself "
        f"if you want it gone: it is proof of what happened, and not ours to throw away."
    )
    return 0
