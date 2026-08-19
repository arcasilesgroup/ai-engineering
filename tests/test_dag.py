"""The order two claims run in, decided the same way every time.

Specification 013: the DAG is deterministic. Imports, lockfiles, migrations and schemas
create explicit edges; exclusive resources serialize; a stable topological order is
recorded; any cycle is INCOMPLETE.

"Deterministic" is the whole requirement, so the tests assert the order and not merely that
one exists — an ordering that is correct and different on each run is one two machines
cannot both follow.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def task(item: str, *paths: str) -> dict:
    return {"item": item, "paths": list(paths)}


def test_two_claims_over_the_same_path_are_serialized_and_never_parallel(tmp_path):
    """The overlap case, which is the one a merge finds out about too late. The direction is
    by work item and it is arbitrary — what matters is that both machines choose the same
    arbitrary answer."""

    from ai_engineering import dag

    tasks = [task("work-9", "src/thing.py"), task("work-2", "src/thing.py")]
    result = dag.order(tmp_path, tasks)

    assert result.outcome == "PASS"
    assert dag.sequence(result) == ["work-2", "work-9"]
    assert ("work-2", "work-9") in dag.edges(tmp_path, tasks)


def test_an_import_puts_the_imported_file_first(tmp_path):
    """An explicit edge, read out of the code rather than declared by hand: a task that
    changes what another task imports lands first, because the second one has to build
    against it."""

    from ai_engineering import dag

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "base.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "src" / "leaf.py").write_text("from src.base import VALUE\n", encoding="utf-8")

    tasks = [task("work-leaf", "src/leaf.py"), task("work-base", "src/base.py")]
    result = dag.order(tmp_path, tasks)

    assert dag.sequence(result) == ["work-base", "work-leaf"]
    assert ("work-base", "work-leaf") in dag.edges(tmp_path, tasks)


def test_an_exclusive_resource_serializes_everything_that_touches_it(tmp_path):
    """A lockfile, a migration and a schema are one resource each: two tasks that both
    rewrite `uv.lock` cannot both be right, and nothing about their paths overlapping says
    so — they claim different files."""

    from ai_engineering import dag

    # Different files, one resource. Two tasks both claiming `uv.lock` would be an overlap
    # and the overlap rule alone would order them — so this fixture uses two migrations and
    # two schemas, where nothing about the paths says the tasks collide. Removing the
    # exclusive-resource edge has to turn this red, and with `uv.lock` on both sides it did
    # not: the fixture was proving the rule beside the one it named.
    tasks = [
        task("work-b", "src/b.py", "migrations/002_add.sql"),
        task("work-a", "src/a.py", "migrations/001_init.sql"),
        task("work-c", "src/c.py"),
        task("work-e", "policy/two-v1.schema.json"),
        task("work-d", "policy/one-v1.schema.json"),
    ]
    ordered = dag.sequence(dag.order(tmp_path, tasks))
    found = dag.edges(tmp_path, tasks)

    assert ordered.index("work-a") < ordered.index("work-b")
    assert ("work-a", "work-b") in found, "two migrations ran in parallel"
    assert ("work-d", "work-e") in found, "two schemas ran in parallel"
    # The task that touches nothing exclusive is not dragged into the queue behind them.
    assert not any("work-c" in edge for edge in found)


def test_the_order_is_the_same_on_every_run_whatever_order_the_tasks_arrive_in(tmp_path):
    """Two machines reading the same claims have to reach the same plan, so the answer
    cannot depend on dictionary order, set iteration, or who was listed first."""

    from ai_engineering import dag

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "base.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "src" / "leaf.py").write_text("from src.base import VALUE\n", encoding="utf-8")
    tasks = [
        task("work-leaf", "src/leaf.py"),
        task("work-base", "src/base.py"),
        task("work-lock", "uv.lock"),
        task("work-alone", "docs/notes.md"),
    ]

    first = dag.sequence(dag.order(tmp_path, tasks))
    assert first == ["work-alone", "work-base", "work-leaf", "work-lock"], first
    for rotation in range(1, len(tasks)):
        shuffled = tasks[rotation:] + tasks[:rotation]
        assert dag.sequence(dag.order(tmp_path, shuffled)) == first, rotation

    # And in another process, with another hash seed. Set iteration is stable inside one
    # interpreter and varies between them, so a version of this that only looped in-process
    # would call an ordering deterministic on the strength of the one thing that cannot
    # show otherwise.
    import json
    import os
    import subprocess
    import sys

    script = (
        "import json,sys;"
        "sys.path.insert(0, sys.argv[1]);"
        "from pathlib import Path;"
        "from ai_engineering import dag;"
        "print(json.dumps(dag.sequence(dag.order(Path(sys.argv[2]), json.loads(sys.argv[3])))))"
    )
    for seed in ("0", "1", "12345"):
        done = subprocess.run(
            [sys.executable, "-c", script, str(ROOT / "src"), str(tmp_path), json.dumps(tasks)],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
            check=True,
        )
        assert json.loads(done.stdout) == first, seed


def test_a_cycle_is_incomplete_and_names_what_is_in_it(tmp_path):
    """No guess. A cycle means the claims cannot all be true at once, and the honest answer
    is to say which ones are involved and stop."""

    from ai_engineering import dag

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "one.py").write_text("from src.two import X\n", encoding="utf-8")
    (tmp_path / "src" / "two.py").write_text("from src.one import Y\n", encoding="utf-8")

    result = dag.order(tmp_path, [task("work-one", "src/one.py"), task("work-two", "src/two.py")])

    assert result.outcome == "INCOMPLETE"
    assert result.error is not None and result.error.code == "DAG_CYCLE"
    assert "work-one" in result.error.message and "work-two" in result.error.message


def test_a_file_it_cannot_read_is_not_read_as_having_no_imports(tmp_path):
    """The fail-open direction for this module: a file that cannot be parsed has unknown
    edges, and treating unknown as none would schedule two tasks in parallel on the strength
    of a file nobody could read."""

    from ai_engineering import dag

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "broken.py").write_text("def (\n", encoding="utf-8")
    (tmp_path / "src" / "base.py").write_text("VALUE = 1\n", encoding="utf-8")

    result = dag.order(
        tmp_path, [task("work-broken", "src/broken.py"), task("work-base", "src/base.py")]
    )

    assert result.outcome == "INCOMPLETE"
    assert result.error is not None and result.error.code == "DAG_UNREADABLE"


def test_the_recorded_order_is_a_fact_a_person_can_read(tmp_path):
    """The order is recorded, not just returned: whatever runs the tasks has to be able to
    show which plan it followed."""

    from ai_engineering import dag

    result = dag.order(Path(tmp_path), [task("work-b", "src/b.py"), task("work-a", "src/a.py")])
    recorded = [fact for fact in result.checks if fact.id == "dag-order"]

    assert recorded and recorded[0].detail == "work-a, work-b"


def test_a_package_import_puts_the_imported_file_first(tmp_path):
    """The spelling this repository actually uses, which the edge reader could not see.

    `_module` turned `src/ai_engineering/claim.py` into `src.ai_engineering.claim`, and the
    syntax tree of `from ai_engineering import claim` yields the module `ai_engineering`.
    Neither matched, so a src-layout package produced no import edges at all: over this
    repository's own `dag.py`, `claim.py` and `checkpoint.py` — where the third imports the
    other two — `edges` returned nothing, and a wave derived from it would have called them
    independent. Unknown is not none, and this was worse: known and read as none.
    """

    from ai_engineering import dag

    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "base.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "leaf.py").write_text("from pkg import base\n", encoding="utf-8")

    tasks = [task("work-leaf", "src/pkg/leaf.py"), task("work-base", "src/pkg/base.py")]

    assert ("work-base", "work-leaf") in dag.edges(tmp_path, tasks)
    assert dag.sequence(dag.order(tmp_path, tasks)) == ["work-base", "work-leaf"]


def test_the_wave_is_the_claims_with_nothing_in_front_of_them(tmp_path):
    """`order` computes this set on every pass and keeps only its first element.

    A caller that wants to know how many writers a plan could carry needs the set, not the
    sequence — and the sequence is what the module returned. Three claims, two of them over
    one path: the two sharing a path are ordered by work item, so the first of them is in
    front of nothing and the second is behind it.
    """

    from ai_engineering import dag

    (tmp_path / "src").mkdir()
    for name in ("a.py", "b.py"):
        (tmp_path / "src" / name).write_text("VALUE = 1\n", encoding="utf-8")

    tasks = [
        task("work-1", "src/a.py"),
        task("work-2", "src/b.py"),
        task("work-3", "src/a.py"),
    ]

    # work-3 shares a path with work-1 and is behind it; work-1 and work-2 have nothing in
    # front of them and could start together.
    assert dag.wave(tmp_path, tasks) == ["work-1", "work-2"]

    # One claim on its own is a wave of one, and no claims is a wave of none.
    assert dag.wave(tmp_path, [task("work-1", "src/a.py")]) == ["work-1"]
    assert dag.wave(tmp_path, []) == []


def test_a_wave_over_a_file_nobody_can_parse_refuses(tmp_path):
    """The same fail-closed direction `edges` already takes: a file that cannot be read is
    not a file with no edges."""

    from ai_engineering import dag

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "broken.py").write_text("def (\n", encoding="utf-8")

    with pytest.raises(dag.Unreadable):
        dag.wave(tmp_path, [task("work-1", "src/broken.py"), task("work-2", "src/broken.py")])


def test_a_wave_of_claims_that_depend_on_each_other_says_so_by_type(tmp_path):
    """`order` gives a cycle its own code and its own cure — split or merge the claims,
    rather than fix or exclude the file. `wave` raised the file exception for both, so a
    caller could not pick the cure the module had already decided was different."""

    from ai_engineering import dag

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("from src import b\n", encoding="utf-8")
    (tmp_path / "src" / "b.py").write_text("from src import a\n", encoding="utf-8")

    tasks = [task("work-a", "src/a.py"), task("work-b", "src/b.py")]

    with pytest.raises(dag.Cycle) as refused:
        dag.wave(tmp_path, tasks)
    assert "work-a" in str(refused.value) and "work-b" in str(refused.value)

    # And it is still caught by anything reading for an unreadable graph.
    assert issubclass(dag.Cycle, dag.Unreadable)
