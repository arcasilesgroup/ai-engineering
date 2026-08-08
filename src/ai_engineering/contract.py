"""The contract every SKILL.md meets, checked by a script rather than by taste.

The open standard defines six portable fields and treats anything else as a hard error
on the packaged-distribution path. This allows those six plus exactly three Claude Code
extensions and nothing else. The portability cost is paid deliberately and named in the
README: these files are not uploadable to claude.ai as-is, and the alternative is a
per-surface rewrite layer, which is the machinery this product exists to delete.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ai_engineering import text

SPEC_FIELDS = {"name", "description", "license", "compatibility", "allowed-tools", "version"}
EXTENSIONS = {"disable-model-invocation", "context", "background"}
JARGON = (
    "leverage",
    "utilise",
    "utilize",
    "synergy",
    "robust",
    "seamless",
    "delve",
    "holistic",
    "best-in-class",
    "cutting-edge",
)
CEILING = 80
DESCRIPTION_MAX = 1000

# The line ceiling for the whole repository, in one place so that raising it is a single
# reviewable edit. It moved from 5,000 to 5,600 once — see specs/001-v1-from-scratch, and
# the commit that did it. The test fails the build on the line after.
REPO_CEILING = 5600


def audit(root: Path) -> list[str]:
    problems: list[str] = []
    for skill in sorted(root.glob("ai-*/SKILL.md")):
        problems += audit_one(skill)
    if not problems and not list(root.glob("ai-*/SKILL.md")):
        problems.append(f"no skills found under {root}")
    return problems


def audit_one(path: Path) -> list[str]:
    name = path.parent.name
    found: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > CEILING:
        found.append(
            f"{name}: {len(lines)} lines. Over {CEILING} means it is a procedure "
            f"that should be a script."
        )
    try:
        header = text.frontmatter(path)
    except ValueError as why:
        return [*found, f"{name}: {why}"]

    unknown = set(header) - SPEC_FIELDS - EXTENSIONS
    if unknown:
        found.append(
            f"{name}: {sorted(unknown)} are not in the contract. Every extra field "
            f"is hidden behaviour in a file nobody re-reads."
        )
    if header.get("name") != name:
        found.append(f"{name}: the name field says {header.get('name')!r}")
    description = header.get("description", "")
    if not description:
        found.append(f"{name}: no description. That field is the routing decision.")
    if len(description) > DESCRIPTION_MAX:
        found.append(
            f"{name}: the description is {len(description)} characters, over {DESCRIPTION_MAX}"
        )
    if "Not for" not in description:
        found.append(
            f"{name}: the description has no 'Not for X — use /ai-Y' clause, which is "
            f"the line that stops the wrong skill from firing."
        )
    if header.get("context") == "fork" and header.get("background") != "false":
        found.append(
            f"{name}: context: fork without background: false. A forked skill runs in "
            f"the background by default, so its verdict lands out of order and /rewind "
            f"will not undo its edits."
        )
    if "when_to_use" in header:
        found.append(f"{name}: when_to_use shares the description's character budget")
    body = "\n".join(lines).lower()
    for word in JARGON:
        if word in body:
            found.append(f"{name}: {word!r} — write it so somebody who does not code can follow")
    return found


def repo_lines(root: Path) -> int:
    """Every committed line. The ceiling is the mechanism that prevents a second
    436,091: not discipline, an exit code."""
    names = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, timeout=30
    ).stdout.split()
    total = 0
    for name in names:
        try:
            total += len((root / name).read_bytes().decode("utf-8", "replace").splitlines())
        except OSError:
            continue
    return total
