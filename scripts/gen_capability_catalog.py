#!/usr/bin/env python3
"""Generate the capability catalog (skills + agents) for the README surfaces.

This is a read-only adapter over the canonical capability sources
(``.claude/skills/ai-*/SKILL.md`` and ``.claude/agents/ai-*.md`` frontmatter):
the rendered catalog is a *derived, rebuildable cache* — the skill/agent files
remain the single source of truth (spec-153 D-153-12 / D-153-15). The output is
wrapped in ``<!-- catalog:start -->`` / ``<!-- catalog:end -->`` markers so
``apply_to`` can replace it in place without disturbing surrounding prose.

Stdlib-only by design: this is a dev/install script, never a hot-path hook, so
it has no dependency on the ``ai_engineering`` package and works from a clean
checkout. (PyYAML is a project dep, but the frontmatter here is a flat set of
``key: "value"`` lines, so a tiny regex parser keeps the script self-contained.)

CLI:
    python scripts/gen_capability_catalog.py            # apply to .ai-engineering/README.md
    python scripts/gen_capability_catalog.py --check    # exit 1 on drift, no write
    python scripts/gen_capability_catalog.py <path>     # target a specific file
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CATALOG_START = "<!-- catalog:start -->"
CATALOG_END = "<!-- catalog:end -->"

# The live client manual and its install-template twin are byte-identical
# surfaces (guarded by tests/unit/docs/test_governance_readme_template_parity.py).
# Both carry the catalog block, so every regeneration MUST write BOTH or the
# parity gate breaks and drops the fix onto a manual `cp` (spec-187 W4).
_LIVE_TARGET_REL = (".ai-engineering", "README.md")
_TEMPLATE_TWIN_REL = (
    "src",
    "ai_engineering",
    "templates",
    ".ai-engineering",
    "README.md",
)

# Canonical glob patterns. The agent glob ``ai-*.md`` intentionally EXCLUDES the
# internal review-*/reviewer-*/verifier-* families (they do not start with
# ``ai-``); only the 9 user-facing agents match.
_SKILLS_GLOB = ".claude/skills/ai-*/SKILL.md"
_AGENTS_GLOB = ".claude/agents/ai-*.md"

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\n(.*?)\n---", re.DOTALL)
_FIELD_RE = re.compile(r"^(\w[\w-]*):[ \t]*(?:\"([^\"]*)\"|'([^']*)'|(.+))$")
_BLOCK_RE = re.compile(
    re.escape(CATALOG_START) + r".*?" + re.escape(CATALOG_END),
    re.DOTALL,
)


class MarkersNotFoundError(RuntimeError):
    """Raised when a target file has no ``catalog:start``/``catalog:end`` block.

    Callers (``ai-eng dev sync`` / install) treat this as a fail-open signal:
    the README has not yet had markers added (Wave 6's job), so catalog
    regeneration is skipped with a logged note rather than failing the run.
    """


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract flat ``key: value`` frontmatter pairs from a markdown file."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        m = _FIELD_RE.match(line.strip())
        if not m:
            continue
        key = m.group(1)
        value = (
            m.group(2)
            if m.group(2) is not None
            else m.group(3)
            if m.group(3) is not None
            else (m.group(4) or "")
        )
        result[key] = value.strip()
    return result


def _first_sentence(description: str) -> str:
    """Return a concise one-line how-to from a (possibly long) description.

    Skill/agent descriptions pack triggers and anti-triggers into one field;
    the catalog only needs the leading capability sentence for a quick scan.
    """
    text = description.strip()
    if not text:
        return ""
    # Cut at the first sentence boundary (". ") to keep rows scannable.
    head = text.split(". ", 1)[0].rstrip(".")
    return head + "."


def _collect(root: Path, glob: str) -> list[tuple[str, str]]:
    """Collect ``(name, description)`` pairs for a glob, sorted by name.

    ``name`` falls back to the file/dir stem when frontmatter omits it so a
    malformed file is still surfaced (never silently dropped).
    """
    entries: list[tuple[str, str]] = []
    for path in root.glob(glob):
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = _parse_frontmatter(text)
        # Skills live at ai-<name>/SKILL.md → use the parent dir name as the
        # stem fallback; agents are ai-<name>.md → use the file stem.
        stem = path.parent.name if path.name == "SKILL.md" else path.stem
        name = fm.get("name", stem)
        description = _first_sentence(fm.get("description", ""))
        entries.append((name, description))
    entries.sort(key=lambda item: item[0])
    return entries


def count_capabilities(root: Path) -> tuple[int, int]:
    """Return ``(skill_count, agent_count)`` from the on-disk sources."""
    skills = len(list(root.glob(_SKILLS_GLOB)))
    agents = len(list(root.glob(_AGENTS_GLOB)))
    return skills, agents


def _render_table(rows: list[tuple[str, str]]) -> list[str]:
    """Render a two-column ``Name | What it does`` markdown table."""
    lines = ["| Name | What it does |", "| --- | --- |"]
    for name, description in rows:
        cell = description.replace("|", r"\|")
        lines.append(f"| `/{name}` | {cell} |")
    return lines


def render_section(root: Path) -> str:
    """Render the full marker-delimited catalog block for *root*.

    Deterministic: entries are sorted by name, so repeated renders of the same
    sources produce byte-identical output.
    """
    skills = _collect(root, _SKILLS_GLOB)
    agents = _collect(root, _AGENTS_GLOB)

    lines: list[str] = [CATALOG_START]
    lines.append("")
    lines.append(
        f"_Generated by `scripts/gen_capability_catalog.py` — "
        f"{len(skills)} skills, {len(agents)} agents. Do not edit by hand; "
        f"run `ai-eng dev sync`._"
    )
    lines.append("")
    lines.append(f"### Skills ({len(skills)})")
    lines.append("")
    lines.append("Invoke a skill with `/ai-<name>` in your IDE agent surface.")
    lines.append("")
    lines.extend(_render_table([(n, d) for n, d in skills]))
    lines.append("")
    lines.append(f"### Agents ({len(agents)})")
    lines.append("")
    lines.append("Agents run in their own context window; dispatched by the skills above.")
    lines.append("")
    # Agents are addressed by name (not slash-invoked), so render without the
    # leading slash by stripping it back off in a dedicated row builder.
    agent_lines = ["| Name | What it does |", "| --- | --- |"]
    for name, description in agents:
        cell = description.replace("|", r"\|")
        agent_lines.append(f"| `{name}` | {cell} |")
    lines.extend(agent_lines)
    lines.append("")
    lines.append(CATALOG_END)
    return "\n".join(lines)


def apply_to(path: Path, root: Path | None = None) -> None:
    """Idempotently replace the marker block in *path* with a fresh render.

    Raises :class:`MarkersNotFoundError` when *path* has no marker block, so the
    caller can decide whether to fail open (README not yet marker-enabled).
    """
    root = root or _repo_root()
    content = path.read_text(encoding="utf-8")
    if CATALOG_START not in content or CATALOG_END not in content:
        raise MarkersNotFoundError(
            f"{path} has no {CATALOG_START}/{CATALOG_END} block; "
            "add the markers before regenerating the catalog."
        )
    section = render_section(root)
    updated = _BLOCK_RE.sub(lambda _m: section, content, count=1)
    if updated != content:
        path.write_text(updated, encoding="utf-8")


def _current_block(content: str) -> str | None:
    """Return the existing marker block (inclusive) or None if absent."""
    match = _BLOCK_RE.search(content)
    return match.group(0) if match else None


def check(path: Path, root: Path | None = None) -> bool:
    """Return True when *path*'s catalog block matches a fresh render.

    Returns False on drift (stale block or count mismatch). Raises
    :class:`MarkersNotFoundError` when no block is present.
    """
    root = root or _repo_root()
    content = path.read_text(encoding="utf-8")
    block = _current_block(content)
    if block is None:
        raise MarkersNotFoundError(f"{path} has no {CATALOG_START}/{CATALOG_END} block.")
    return block == render_section(root)


def template_twin_path(root: Path) -> Path:
    """Return the install-template twin of the live client manual for *root*."""
    return root.joinpath(*_TEMPLATE_TWIN_REL)


def apply_template_twin(root: Path) -> Path | None:
    """Regenerate the catalog block in the install-template twin, if present.

    The twin (``src/ai_engineering/templates/.ai-engineering/README.md``) is a
    source-repo-only file; consumer projects have no ``src/`` tree. Fail-open:
    an absent or marker-less twin is skipped (returns None), so this is safe to
    call from any project root. Renders from *root* so the twin's catalog block
    is byte-identical to the live one.
    """
    twin = template_twin_path(root)
    if not twin.is_file():
        return None
    try:
        apply_to(twin, root)
    except MarkersNotFoundError:
        return None
    return twin


def check_template_twin(root: Path) -> bool:
    """Return True when the twin is absent (nothing to check) or in sync.

    Returns False only when the twin exists, carries the catalog markers, and
    its block diverges from a fresh render (fail-open on absence/no-markers).
    """
    twin = template_twin_path(root)
    if not twin.is_file():
        return True
    try:
        return check(twin, root)
    except MarkersNotFoundError:
        return True


def _repo_root() -> Path:
    """Resolve the repository root (two levels up from this script)."""
    return Path(__file__).resolve().parents[1]


def _default_target(root: Path) -> Path:
    return root.joinpath(*_LIVE_TARGET_REL)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        default=None,
        help="Target markdown file (default: .ai-engineering/README.md).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the catalog block matches a fresh render; exit 1 on drift.",
    )
    args = parser.parse_args(argv)

    root = _repo_root()
    target = args.target or _default_target(root)
    # Only the default (live-manual) run mirrors into the install-template twin;
    # an explicit target is applied/checked in isolation.
    sync_twin = args.target is None

    if not target.is_file():
        print(f"error: target not found: {target}", file=sys.stderr)
        return 2

    try:
        if args.check:
            live_ok = check(target, root)
            twin_ok = check_template_twin(root) if sync_twin else True
            if live_ok and twin_ok:
                print(f"catalog in sync: {target}")
                return 0
            drifted = target if not live_ok else template_twin_path(root)
            print(f"catalog drift detected: {drifted}", file=sys.stderr)
            return 1
        apply_to(target, root)
        if sync_twin:
            twin = apply_template_twin(root)
            if twin is not None:
                print(f"catalog applied: {twin}")
        print(f"catalog applied: {target}")
        return 0
    except MarkersNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
