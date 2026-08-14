"""A versioned migration, not a pull.

Pulling a clone was an unauthenticated code-execution channel into seven surfaces at
once. Integrity now comes from the wheel's hash, checked by tools the user already
trusts. Auto-update stays off, because a change of governance is never silent — and a
keyboard confirmation was never as good as a reviewed commit: the record of an update
is the diff of .ai/config.toml inside a pull request, signed by whoever merged it.

It never touches AGENTS.md or CONSTITUTION.md. Those are yours.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from ai_engineering import __version__, outcome, paths, wiring

OWNED = ("justfile", "CLAUDE.md", ".ai/config.toml")
_VERSION = re.compile(
    r'(?m)^[ \t]*version[ \t]*=[ \t]*(?P<quote>["\'])(?P<value>[^"\']*)'
    r"(?P=quote)[ \t]*(?:#.*)?$"
)


class Undecidable(RuntimeError):
    """Update cannot safely derive or complete its exact change set."""


def dirty(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--", *OWNED],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise Undecidable("git could not inspect framework-owned files") from error
    if result.returncode:
        raise Undecidable("git could not inspect framework-owned files")
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


def migrations(pinned: str, target: str) -> list[Path]:
    folder = paths.shipped("migrations")
    steps = []
    for path in sorted(folder.glob("*/")):
        low, _, high = path.name.partition("..")
        if low <= target and high >= pinned:
            steps += sorted(path.glob("*.py"))
    return steps


def _pin_change(pin: Path, target: str) -> tuple[str, str]:
    """Read one regular canonical pin and replace only its framework version value."""
    try:
        if pin.is_symlink() or not pin.is_file():
            raise OSError("the pin is not a regular file")
        body = pin.read_text(encoding="utf-8")
        parsed = tomllib.loads(body)
        pinned = parsed["framework"]["version"]
        section = re.search(r"(?ms)^\[framework\][^\r\n]*\r?\n(?P<body>.*?)(?=^\[|\Z)", body)
        rows = list(_VERSION.finditer(section.group("body"))) if section else []
        if not isinstance(pinned, str) or not pinned or len(rows) != 1:
            raise ValueError("the framework version is not exact")
        row = rows[0]
        if row.group("value") != pinned or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", target):
            raise ValueError("the framework version is not exact")
        start = section.start("body") + row.start("value")
        end = section.start("body") + row.end("value")
    except (KeyError, OSError, TypeError, ValueError) as error:
        raise Undecidable("the pin cannot be read as one canonical framework version") from error
    return pinned, body[:start] + target + body[end:]


def _guard_plan() -> tuple[list[dict], list[dict]]:
    """Return recorded live guards and the non-append-only subset update may rewrite."""
    try:
        receipt = wiring.receipt()
        if not isinstance(receipt, dict):
            raise TypeError("receipt is not canonical")
        rows = receipt.get("wrote", [])
        if not isinstance(rows, list):
            raise TypeError("receipt is not canonical")
        if any(
            not isinstance(row, dict)
            or not all(isinstance(row.get(key), str) for key in ("path", "kind", "how"))
            for row in rows
        ):
            raise TypeError("receipt ownership is incomplete")
        # Ownership narrows what this explicit invocation may rewrite. It does not grant
        # permission and is never proof that an update ran or succeeded.
        mine = {row["path"] for row in rows if row["kind"] == "guard"}
        found = [surface for surface in wiring.detect() if surface.get("settings") in mine]
        rewritten = [surface for surface in found if not surface.get("append_only")]
        for surface in rewritten:
            target = wiring.expand(surface["settings"])
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise OSError("a recorded guard target is not a regular file")
            if target.exists() and surface["writer"].startswith("json_"):
                wiring.read_json(target)
            elif target.exists():
                target.read_text(encoding="utf-8")
    except (KeyError, OSError, TypeError, ValueError, wiring.Unreadable) as error:
        raise Undecidable("recorded guard state cannot be safely evaluated") from error
    return found, rewritten


def main(argv: list[str]) -> outcome.Result:
    parser = argparse.ArgumentParser("ai-eng update")
    parser.add_argument("--to", default=__version__, help="the version to move this repository to")
    parser.add_argument("--force", action="store_true", help="print what would be discarded")
    parser.add_argument(
        "--dry-run", action="store_true", help="print exact changes and write nothing"
    )
    args = parser.parse_args(argv)

    root = paths.repo_root()
    if root is None:
        print("not inside a repository")
        return outcome.result("INCOMPLETE")
    pin = root / ".ai" / "config.toml"
    if not pin.exists() and not pin.is_symlink():
        print("  this repository is not set up. `ai-eng init` first.")
        return outcome.result("INCOMPLETE")
    try:
        pinned, pin_after = _pin_change(pin, args.to)
        changes = dirty(root)
    except Undecidable as why:
        print(f"  INCOMPLETE — {why}. Nothing changed.")
        return outcome.result("INCOMPLETE")
    print(f"  {pinned} → {args.to}")
    print(f"  would rewrite pin: {pin}")

    if changes:
        print(f"  REFUSED — these are framework-owned and have uncommitted changes: {changes}")
        print(
            "  Commit or discard them first. --force prints exactly what it would discard;"
            " it never overwrites silently."
        )
        if not args.force:
            return outcome.result("INCOMPLETE")
        print(f"  --force would discard: {changes}")
        return outcome.result("INCOMPLETE")

    try:
        steps = migrations(pinned, args.to)
        found, rewritten_plan = _guard_plan()
    except (OSError, Undecidable) as why:
        print(f"  INCOMPLETE — {why}. Nothing changed.")
        return outcome.result("INCOMPLETE")
    print(
        f"  {len(steps)} migration(s) to run: "
        f"{', '.join(step.parent.name + '/' + step.name for step in steps) or 'none'}"
    )
    if not found:
        print("  → no guard entry of ours is recorded here. `ai-eng init --global` wires one.")
    else:
        for surface in rewritten_plan:
            print(f"  would rewrite guard entry: {surface['settings']}")
        for surface in [surface for surface in found if surface.get("append_only")]:
            print(f"  would leave append-only guard untouched: {surface['settings']}")
    if args.dry_run:
        if steps:
            print(
                "  INCOMPLETE — migration scripts do not expose exact file changes. "
                "Nothing changed."
            )
            return outcome.dry_run(exact_changes=False)
        print("  dry run complete. Nothing changed.")
        return outcome.dry_run(exact_changes=True)
    if not sys.stdin.isatty():
        print("  an update is a person's decision and there is no keyboard here. Nothing changed.")
        return outcome.result("INCOMPLETE")
    if input("  Type y to run them › ").strip().lower() != "y":
        print("  nothing changed.")
        return outcome.result("CANCELLED")

    try:
        for step in steps:
            subprocess.run([sys.executable, str(step), str(root)], check=True, timeout=600)
        pin.write_text(pin_after, encoding="utf-8")
    except (OSError, subprocess.SubprocessError) as why:
        print(f"  INCOMPLETE — update stopped before it could finish: {why}.")
        return outcome.result("INCOMPLETE")
    print(f"  ✓ the pin now reads {args.to} — that diff is the record of this update.")

    # What this machine chose, and never everything that happens to be installed on it.
    # This walked `detect()`, so declining Cursor at `init` and updating a week later wired
    # it — failClosed, which is what makes Cursor deny rather than advise — from a verb the
    # person ran to move a version number. And nothing was recorded, so `uninstall`
    # afterwards listed what init had written, took the consent, and left the rest running.
    if not found:
        return outcome.result("PASS")
    try:
        rewritten = wiring.install_guards(rewritten_plan)
        for name, target, detail in rewritten:
            print(f"  ✓ rewrote {target or name} ({detail})")
        # Written down, because an entry nothing recorded is an entry uninstall cannot find.
        if rewritten_plan:
            wiring.record(
                [
                    {"path": surface["settings"], "kind": "guard", "how": surface["writer"]}
                    for surface in rewritten_plan
                ]
            )
    except (KeyError, OSError, TypeError, wiring.Unreadable) as why:
        print(f"  INCOMPLETE — guard rewrite stopped before it could finish: {why}.")
        return outcome.result("INCOMPLETE")
    for surface in [s for s in found if s.get("append_only")]:
        print(
            f"  → {surface['name']} left untouched. Its trust is a hash of the whole handler "
            f"and of its position, so it is only rewritten when the entry genuinely changes."
        )
    print(
        "\n  Read the diff and make the commit. `uv tool install ai-engineering=="
        f"{args.to}` installs the wheel this pin now names."
    )
    return outcome.result("PASS")
