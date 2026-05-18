"""Plan-level CLI commands (deterministic, zero-token).

Provides commands that operate over the multi-sub-spec autopilot manifest
tree without invoking an LLM.

- ``ai-eng plan dag-build <subdir>`` -- walk ``sub-*/plan.md`` files for
  their ``exports:`` / ``imports:`` frontmatter lists, build the
  dependency DAG, topologically sort into waves, and emit JSON with
  conflict diagnostics for cycles or unresolvable deps (spec-139 M7.T2).
"""

from __future__ import annotations

import json as _json
import re
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.paths import find_project_root

_PLAN_FILENAME = "plan.md"
_SUB_PREFIX = "sub-"

# Match list entries inside the ``exports:`` / ``imports:`` frontmatter
# blocks. Accepts both single-line flow syntax (``exports: [a, b]``) and
# block-style YAML lists (``- token``). Tokens are stripped of trailing
# punctuation and surrounding quotes so common syntactic variants behave
# identically. The captured group uses a greedy ``.*`` (linear-time)
# rather than a reluctant quantifier + trailing ``\s*$`` (potential
# catastrophic backtracking, SonarCloud python:S5852); _normalize_token
# strips the trailing whitespace.
_LIST_ITEM_RE = re.compile(r"^\s*-\s+(.*)$")
_FLOW_LIST_RE = re.compile(r"^\s*(exports|imports)\s*:\s*\[(.*)\]\s*$")
_BLOCK_KEY_RE = re.compile(r"^\s*(exports|imports)\s*:\s*$")
_FRONTMATTER_FENCE_RE = re.compile(r"^---\s*$")


def _normalize_token(raw: str) -> str:
    """Strip whitespace and surrounding quotes from a YAML list token."""
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value.strip()


def _parse_exports_imports(text: str) -> tuple[list[str], list[str]]:
    """Extract ``exports:`` and ``imports:`` lists from frontmatter.

    Returns ``([], [])`` when the file has no frontmatter or the keys are
    absent. Tolerates both flow (``[a, b]``) and block-style YAML lists.
    Order is preserved.
    """
    lines = text.splitlines()
    if not lines or not _FRONTMATTER_FENCE_RE.match(lines[0]):
        return [], []

    block: list[str] = []
    for line in lines[1:]:
        if _FRONTMATTER_FENCE_RE.match(line):
            break
        block.append(line)

    exports: list[str] = []
    imports: list[str] = []
    active: str | None = None
    for line in block:
        flow_match = _FLOW_LIST_RE.match(line)
        if flow_match:
            key = flow_match.group(1)
            payload = flow_match.group(2)
            items = [_normalize_token(tok) for tok in payload.split(",") if tok.strip()]
            if key == "exports":
                exports.extend(items)
            else:
                imports.extend(items)
            active = None
            continue

        block_match = _BLOCK_KEY_RE.match(line)
        if block_match:
            active = block_match.group(1)
            continue

        if active is not None:
            item_match = _LIST_ITEM_RE.match(line)
            if item_match:
                token = _normalize_token(item_match.group(1))
                if token:
                    if active == "exports":
                        exports.append(token)
                    else:
                        imports.append(token)
                continue
            # Any non-list, non-empty line ends the active list.
            if line.strip() and not line.lstrip().startswith("#"):
                active = None

    return exports, imports


def _discover_sub_plans(subdir: Path) -> dict[str, tuple[list[str], list[str]]]:
    """Return ``{sub_name: (exports, imports)}`` for every ``sub-*/plan.md``.

    ``sub_name`` is the canonical directory name (e.g. ``sub-001``). The
    walk is non-recursive beyond the immediate sub-NNN directories so
    deeply nested fixtures cannot accidentally pollute the DAG.
    """
    plans: dict[str, tuple[list[str], list[str]]] = {}
    for child in sorted(subdir.iterdir()):
        if not child.is_dir() or not child.name.startswith(_SUB_PREFIX):
            continue
        plan_path = child / _PLAN_FILENAME
        if not plan_path.is_file():
            continue
        exports, imports = _parse_exports_imports(plan_path.read_text(encoding="utf-8"))
        plans[child.name] = (exports, imports)
    return plans


def _build_dependency_edges(
    plans: dict[str, tuple[list[str], list[str]]],
) -> tuple[dict[str, set[str]], list[str]]:
    """Resolve ``imports`` -> producer sub-name edges.

    Returns ``(edges, unresolved)`` where ``edges[node]`` is the set of
    upstream sub-names that must finish before ``node`` can run, and
    ``unresolved`` is a list of human-readable conflict messages for
    imports that no sibling exports.
    """
    producer_index: dict[str, str] = {}
    duplicate_exports: list[str] = []
    for sub_name, (exports, _imports) in plans.items():
        for token in exports:
            if token in producer_index and producer_index[token] != sub_name:
                duplicate_exports.append(
                    f"duplicate export {token!r}: {producer_index[token]} and {sub_name}"
                )
            else:
                producer_index[token] = sub_name

    edges: dict[str, set[str]] = {name: set() for name in plans}
    unresolved: list[str] = list(duplicate_exports)
    for sub_name, (_exports, imports) in plans.items():
        for token in imports:
            producer = producer_index.get(token)
            if producer is None:
                unresolved.append(f"{sub_name} imports {token!r} but no sibling exports it")
                continue
            if producer == sub_name:
                # Self-imports are no-ops; do not introduce a self-edge.
                continue
            edges[sub_name].add(producer)
    return edges, unresolved


def _topological_waves(
    plans: dict[str, tuple[list[str], list[str]]],
    edges: dict[str, set[str]],
) -> tuple[list[list[str]], list[str]]:
    """Return ``(waves, cycle_messages)`` via Kahn-style layering.

    Each wave is the sorted list of sub-names whose remaining dependency
    count is zero at that step. Cycles surface as a non-empty
    ``cycle_messages`` list naming the sub-specs that never reach
    in-degree zero.
    """
    remaining: dict[str, set[str]] = {name: set(deps) for name, deps in edges.items()}
    waves: list[list[str]] = []
    placed: set[str] = set()
    while remaining:
        ready = sorted(name for name, deps in remaining.items() if not deps)
        if not ready:
            cycle = sorted(remaining)
            return waves, [f"cycle detected involving: {', '.join(cycle)}"]
        waves.append(ready)
        placed.update(ready)
        for name in ready:
            del remaining[name]
        for deps in remaining.values():
            deps.difference_update(placed)
    return waves, []


def plan_dag_build(
    subdir: Annotated[
        Path | None,
        typer.Argument(
            help=(
                "Directory containing sub-*/plan.md files. Defaults to "
                ".ai-engineering/runtime/autopilot/<active>/."
            ),
        ),
    ] = None,
) -> None:
    """Build the sub-spec dependency DAG and emit a JSON wave plan.

    Walks ``<subdir>/sub-*/plan.md``, parses each plan's ``exports:`` and
    ``imports:`` frontmatter lists, builds the dependency graph, and runs
    a topological sort to assign waves. Exits 0 when the DAG resolves
    cleanly; exits 1 when conflicts (cycles or unresolvable imports) are
    present. Pure Python — no LLM. spec-139 M7.T2.
    """
    if subdir is None:
        root = find_project_root()
        subdir = root / ".ai-engineering" / "runtime" / "autopilot"

    target = subdir if subdir.is_absolute() else Path.cwd() / subdir
    if not target.exists() or not target.is_dir():
        typer.echo(
            _json.dumps(
                {
                    "waves": [],
                    "conflicts": [f"subdir not found: {target}"],
                }
            ),
            err=True,
        )
        raise typer.Exit(code=1)

    plans = _discover_sub_plans(target)
    edges, unresolved = _build_dependency_edges(plans)
    waves, cycle_messages = _topological_waves(plans, edges)
    conflicts = unresolved + cycle_messages

    payload = {
        "waves": waves,
        "conflicts": conflicts,
    }
    typer.echo(_json.dumps(payload))
    raise typer.Exit(code=0 if not conflicts else 1)
