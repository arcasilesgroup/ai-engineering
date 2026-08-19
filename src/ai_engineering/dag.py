"""Which claims can run at the same time, decided the same way on every machine.

Two agents that both derive the plan have to derive the same plan, so nothing here depends
on dictionary order, set iteration or who was listed first. Where the direction of an edge
is genuinely arbitrary — two tasks that touch the same file, and neither has to be first —
it is taken by work item, which is arbitrary and identical everywhere.

Three sources of edge, and no fourth invented: two claims over the same path; a claim over
a file that another claim's file imports; and the resources that cannot be shared at all,
where two tasks rewriting one lockfile is a conflict their paths never showed.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from ai_engineering import outcome

# One writer at a time, whatever the paths say. A lockfile is regenerated wholesale, a
# migration is ordered by its position in a sequence, and a schema is the contract two
# tasks would each be editing a different copy of in their heads.
EXCLUSIVE = ("uv.lock", "package-lock.json", "poetry.lock", "Cargo.lock", "pnpm-lock.yaml")
EXCLUSIVE_PREFIXES = ("migrations/",)
EXCLUSIVE_SUFFIXES = (".schema.json",)


def _exclusive(path: str) -> str | None:
    """The resource a path belongs to, or None when it belongs to none."""

    name = path.rsplit("/", 1)[-1]
    if name in EXCLUSIVE:
        return name
    for prefix in EXCLUSIVE_PREFIXES:
        if path.startswith(prefix):
            return prefix
    for suffix in EXCLUSIVE_SUFFIXES:
        if path.endswith(suffix):
            return suffix
    return None


def _modules(path: str) -> set[str]:
    """Every spelling an import of this file can have.

    It used to return one — `src/a/b.py` as `src.a.b` — and that is the spelling a flat
    layout uses. This repository is a src layout, so its own imports read
    `from ai_engineering import claim`, whose module is `ai_engineering`, and nothing
    matched: `edges` over `dag.py`, `claim.py` and `checkpoint.py` returned nothing at all
    while the third imports the other two. The only spelling that worked was the one the
    fixture happened to use.

    So: the path with its separators as dots, the same with the source root stripped, and for
    `from <package> import <name>` the package on its own — because that node names the
    package and the module is the alias beside it.
    """

    stem = path.removesuffix(".py").removesuffix("/__init__")
    dotted = stem.replace("/", ".")
    spellings = {dotted, dotted.removeprefix("src.")}
    return {one for one in spellings if one}


class Unreadable(outcome.Unreadable):
    """A file whose edges cannot be worked out. Unknown is not none: scheduling two tasks
    in parallel on the strength of a file nobody could read is the fail-open direction."""


class Cycle(Unreadable):
    """Every claim is behind another one, so none of them can start.

    Its own type because `order` already tells these two apart and gives them different
    cures — a file that will not parse is fixed or excluded, and a cycle is split or merged.
    A caller that catches only `Unreadable` still catches this; one that cares can pick."""


def _imports(root: Path, path: str) -> set[str]:
    if not path.endswith(".py"):
        return set()
    where = root / path
    if not where.is_file():
        return set()
    try:
        tree = ast.parse(where.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError) as why:
        raise Unreadable(path) from why
    named: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            named.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            named.add(node.module)
            # `from pkg import mod` names the package, and the module is the alias. Both
            # readings are kept because either can be the file another task owns.
            named.update(f"{node.module}.{alias.name}" for alias in node.names)
    return named


def edges(root: Path, tasks: list[dict]) -> list[tuple[str, str]]:
    """Every edge, sorted, with each pair oriented once. Raises `Unreadable` when a claimed
    file exists and cannot be parsed."""

    owner: dict[str, str] = {}
    for one in sorted(tasks, key=lambda task: str(task["item"])):
        for path in one["paths"]:
            owner.setdefault(path, str(one["item"]))

    found: set[tuple[str, str]] = set()
    shared: dict[str, list[str]] = defaultdict(list)
    for one in sorted(tasks, key=lambda task: str(task["item"])):
        item = str(one["item"])
        for path in sorted(one["paths"]):
            shared[path].append(item)
            resource = _exclusive(path)
            if resource:
                shared[f"resource:{resource}"].append(item)
            for imported in sorted(_imports(root, path)):
                for other in sorted(tasks, key=lambda task: str(task["item"])):
                    if str(other["item"]) == item:
                        continue
                    if any(imported in _modules(each) for each in other["paths"]):
                        found.add((str(other["item"]), item))

    # Two claims on one thing: neither has to be first, and both machines have to agree
    # anyway, so the work item decides and the choice is recorded rather than hidden.
    for holders in shared.values():
        ordered = sorted(set(holders))
        for first, second in zip(ordered, ordered[1:], strict=False):
            found.add((first, second))
    return sorted(found)


def wave(root: Path, tasks: list[dict]) -> list[str]:
    """The claims with nothing in front of them, which is how many writers could start now.

    `order` computes exactly this set on every pass — `ready` at the top of its loop — and
    keeps only its first element, so the one question a caller with more than one writer
    wants answered was the one thing thrown away.

    A claim sharing a path with another is not refused, it is ordered by work item, so the
    first of the pair is in this set and the second is not. `Unreadable` propagates: a file
    nobody could parse is not a file with no edges, and a wave built on that reading would be
    the fail-open direction this module already names."""

    blocked = {second for _, second in edges(root, tasks)}
    items = {str(one["item"]) for one in tasks}
    ready = sorted(items - blocked)
    if items and not ready:
        # A cycle. Returning the empty set would make it indistinguishable from "no claims",
        # and a caller sizing a build on the length of this cannot tell a broken set from an
        # absent one. `order` reports the same state loudly; so does this.
        raise Cycle(f"these claims depend on each other: {', '.join(sorted(items))}")
    return ready


def sequence(result: outcome.Execution) -> list[str]:
    """The order out of the result, for a caller that wants the list rather than the facts."""

    for fact in result.checks:
        if fact.id == "dag-order" and fact.detail:
            return [item for item in fact.detail.split(", ") if item]
    return []


def order(root: Path, tasks: list[dict]) -> outcome.Execution:
    """A stable topological order, or INCOMPLETE naming what stopped it."""

    items = sorted({str(one["item"]) for one in tasks})
    try:
        links = edges(root, tasks)
    except Unreadable as why:
        message = f"the edges of {why} cannot be worked out, so no order can be trusted"
        return outcome.execution(
            outcome.result("INCOMPLETE"),
            summary=message,
            execution_error=outcome.error(
                "DAG_UNREADABLE", message, False, "fix or exclude the file and derive again"
            ),
        )

    after: dict[str, set[str]] = {item: set() for item in items}
    for first, second in links:
        after.setdefault(second, set()).add(first)
        after.setdefault(first, set())

    placed: list[str] = []
    remaining = dict(after)
    while remaining:
        # Sorted, not "any ready node": the tie-break is where a topological sort stops
        # being reproducible, and reproducible is the requirement.
        ready = sorted(item for item, needs in remaining.items() if not needs)
        if not ready:
            stuck = ", ".join(sorted(remaining))
            message = f"these claims depend on each other and cannot all be first: {stuck}"
            return outcome.execution(
                outcome.result("INCOMPLETE"),
                summary=message,
                execution_error=outcome.error(
                    "DAG_CYCLE", message, False, "split or merge the claims in the cycle"
                ),
            )
        taken = ready[0]
        placed.append(taken)
        remaining.pop(taken)
        for needs in remaining.values():
            needs.discard(taken)

    return outcome.execution(
        outcome.result("PASS"),
        summary=f"{len(placed)} claim(s) in a stable order with {len(links)} edge(s)",
        checks=[
            outcome.fact(
                "dag-order", "OBSERVED", "The order these claims run in", ", ".join(placed)
            ),
            outcome.fact(
                "dag-edges",
                "OBSERVED",
                "Why that order",
                "; ".join(f"{first} before {second}" for first, second in links) or "no edges",
            ),
        ],
    )
