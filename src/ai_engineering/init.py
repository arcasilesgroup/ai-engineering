"""The only install verb: this machine, and then this repository if you say yes.

It is stateful and it is safe to run a thousand times. Every question has a default
that destroys nothing, so pressing Enter without reading never breaks a file — and
every file that already exists and is not ours lands on one checklist, on one screen,
with nothing selected, because a queue of yes/no prompts shows you the blast radius one
file at a time and prompt fatigue does the rest.

What it never does: render a template tree, copy a guard, install a binary, commit
anything, or own any file after it exits.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

from ai_engineering import __version__, paths, skeletons, wiring

OFFERS = {
    "CLAUDE.md": ("one line: @./AGENTS.md", lambda: skeletons.CLAUDE_MD),
    "AGENTS.md": ("skeleton, ~48 lines, TODO marker per section", lambda: skeletons.AGENTS_MD),
    "CONSTITUTION.md": ("skeleton, ~40 lines, MANDATORY", lambda: skeletons.CONSTITUTION_MD),
    "justfile": ("5 recipes + the RAN lines", lambda: skeletons.JUSTFILE),
}


def out(text: str = "") -> None:
    sys.stdout.write(text + "\n")


def banner() -> None:
    """It costs four lines and it is the only moment the product has a face. To stderr,
    on a TTY only, so it never lands in a log or a CI transcript."""
    if not sys.stderr.isatty():
        return
    sys.stderr.write(
        f"\n  ┌─                    ─┐\n    {{ ai }} e n g i n e e r i n g\n"
        f"  └─                    ─┘\n   v{__version__} · AI Governance Framework\n\n"
    )


def ask(question: str, default: bool, args) -> bool:
    if args.yes:
        return default
    if not sys.stdin.isatty():
        return default
    reply = input(f"◆ {question} ({'Y/n' if default else 'y/N'}) › ").strip().lower()
    return default if not reply else reply.startswith("y")


def parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser("ai-eng init", description=__doc__.splitlines()[0])
    p.add_argument("--global", dest="do_global", action="store_true", help="set up this machine")
    p.add_argument("--no-global", dest="skip_global", action="store_true")
    p.add_argument("--project", nargs="?", const=".", help="set up this repository")
    p.add_argument(
        "--harness", default="", help="comma-separated surface ids; default is all found"
    )
    p.add_argument("--overwrite", default="", help="comma-separated file names, or all")
    p.add_argument(
        "--dry-run", dest="dry", action="store_true", help="print the checklist, write nothing"
    )
    p.add_argument("-y", "--yes", action="store_true", help="take every default")
    return p.parse_args(argv)


def global_ready() -> bool:
    data = wiring.receipt()
    return bool(data.get("wrote")) and data.get("version") == __version__


def global_step(args) -> None:
    if args.skip_global or (global_ready() and not args.do_global):
        data = wiring.receipt()
        if data.get("wrote"):
            out(
                f"  Global ready — 8 skills, {len(data['wrote'])} entries, v{data.get('version')} "
                f"({wiring.receipt_path()})"
            )
        return

    only = [s for s in args.harness.split(",") if s] or None
    found = wiring.detect(only)
    out("\n◇ Global")
    for surface in wiring.table()["surface"]:
        mark = "found" if surface in found else "not installed — skipped"
        out(f"   {surface['name']:<18} {surface['detect'] or '—':<26} {mark}")
    out(
        f"\n   Writes 8 skills into {paths.home() / 'skills'}, symlinks from the roots above,\n"
        f"   and one guard entry in each found surface's own settings file.\n"
        f"   Nothing else is touched. Undo: `ai-eng uninstall`.\n"
    )

    if args.dry or not ask("Set up this machine?", True, args):
        out("   → skipped.")
        return

    written = wiring.install_skills()
    out(f"   ✓ 8 skills   → {paths.home() / 'skills'}/ai-*/")
    for row in written[1:]:
        out(f"   ✓ {row['how']:<8} → {row['path']}")
    for name, target, detail in wiring.install_guards(found):
        flag = "⚠" if "append" in detail else "✓"
        out(f"   {flag} guards     → {target or name} ({detail})")
        if "append" in detail:
            out(
                "     Codex will not run it until you approve it: type /hooks in Codex.\n"
                "     `doctor` reports it as INERT until then."
            )
    wiring.record(
        written
        + [
            {"path": s["settings"], "kind": "guard", "how": s["writer"]}
            for s in found
            if s["writer"] != "none"
        ]
    )
    out(f"   ✓ receipt    → {wiring.receipt_path()}")


def existing(root: Path) -> list[tuple[str, int, str]]:
    rows = []
    for name, (becomes, _) in OFFERS.items():
        path = root / name
        if path.exists():
            rows.append((name, len(path.read_text(errors="replace").splitlines()), becomes))
    return rows


def select(reply: str, rows: list[tuple[str, int, str]]) -> tuple[set[str], list[str]]:
    """One parser for the typed reply and for `--overwrite`, because they are one intent.
    Two of them five lines apart is how a comma came to select one file in silence in the
    prompt and two on the command line. Numbers and names both, separated by commas or
    spaces or both, and `all` in either spelling. Whatever it could not use comes back to
    be named, because a selection prompt that drops half of what you typed and says
    nothing is worse than one that refuses."""
    names = [name for name, _, _ in rows]
    picked: set[str] = set()
    ignored: list[str] = []
    for token in reply.replace(",", " ").split():
        if token.lower() == "all":
            picked.update(names)
        elif token.isdigit() and 0 < int(token) <= len(names):
            picked.add(names[int(token) - 1])
        elif token in names:
            picked.add(token)
        else:
            ignored.append(token)
    return picked, ignored


def choose(rows: list[tuple[str, int, str]], args) -> set[str]:
    if not rows:
        return set()
    if args.overwrite.strip() or args.yes or not sys.stdin.isatty():
        picked, ignored = select(args.overwrite, rows)
    else:
        out(f"\n◇ {len(rows)} files already exist and are not ours")
        out("   Type the numbers to overwrite, separated by spaces. Enter selects none.\n")
        for index, (name, lines, becomes) in enumerate(rows, 1):
            out(f"   {index}. {name:<18} {lines:>4} lines  →  {becomes}")
        picked, ignored = select(input("\n◆ Overwrite which? (Enter = none) › "), rows)
    if ignored:
        out(f"   → ignored, nothing on the list matches: {', '.join(ignored)}")
    return picked


def write_offer(root: Path, name: str, args) -> None:
    path = root / name
    if path.exists():
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{name}.bak-{stamp}")
        if not args.dry:
            shutil.copy2(path, backup)
        out(f"   ✓ {name} backup → {backup.name} written")
    if not args.dry:
        path.write_text(OFFERS[name][1](), encoding="utf-8")


def stacks(root: Path) -> list[str]:
    """A short detection, not a table of 29 binaries: the full list is documentation,
    where it costs no lines and cannot go stale inside a release."""
    markers = {
        "pyproject.toml": "python",
        "package.json": "node",
        "go.mod": "go",
        "Cargo.toml": "rust",
        "pom.xml": "java",
        "Gemfile": "ruby",
    }
    return sorted({name for marker, name in markers.items() if (root / marker).exists()})


def project_step(args) -> int:
    root = paths.repo_root(Path(args.project or "."))
    if root is None:
        out("\n◇ Project   not a git repository — nothing to set up here.")
        return 0
    pinned = root / ".ai" / "config.toml"
    if pinned.exists() and args.project is None:
        out(
            f"  Project ready — {pinned.relative_to(root)}, spec chain wired\n\n  Nothing to do. "
            f"`ai-eng doctor` for the full check."
        )
        return 0

    out(f"\n◇ Project   {root}   git repository, not set up")
    if not (args.project is not None or ask("Set up this project too?", sys.stdin.isatty(), args)):
        out("   → skipped. Nothing was written.")
        return 0

    if not args.dry:
        pinned.parent.mkdir(parents=True, exist_ok=True)
        pinned.write_text(skeletons.CONFIG_TOML.format(version=__version__), encoding="utf-8")
        (root / ".ai" / ".gitignore").write_text(skeletons.AI_GITIGNORE, encoding="utf-8")
        (root / "specs").mkdir(exist_ok=True)
        (root / "specs" / ".gitkeep").touch()
    out("   ✓ .ai/config.toml · .ai/.gitignore · specs/")
    if not args.dry:
        out(f"   ✓ core.hooksPath → {wiring.wire_git(root)}")

    # Before the loop, and that ordering is the whole of it: asked afterwards, the disk
    # answers yes for every file this run had just created, and the same screen that
    # reported writing them offers to overwrite them.
    rows = existing(root)
    for name in OFFERS:
        if not (root / name).exists():
            write_offer(root, name, args)
            out(f"   ✓ {name} written ({OFFERS[name][0]})")
    picked = choose(rows, args)
    for name in sorted(picked):
        write_offer(root, name, args)
    left = [name for name, _, _ in rows if name not in picked]
    if left:
        out(
            f"   → left as is: {', '.join(left)}. `doctor` lists them as unmanaged, "
            f"which is a valid state."
        )

    found = stacks(root)
    if found:
        out(
            f"\n   Stacks detected: {', '.join(found)}. The binaries each one needs are listed "
            f"in docs/tools.md; this installs none of them."
        )
    out("\n   Paste these lines into .github/workflows/check.yml:\n")
    out(
        "\n".join(
            f"   {line}" for line in skeletons.CHECK_YML.format(version=__version__).splitlines()
        )
    )
    return 0


def main(argv: list[str]) -> int:
    args = parse(argv)
    banner()
    global_step(args)
    return project_step(args)
