"""Conftest for ``tests/perf/`` -- auto-skip perf tests unless opted in.

Default pytest semantics collect every test regardless of marker. Plain
``-m perf`` filters DOWN to perf-marked tests, but that is a deselection,
not an opt-in. The contract spec-104 T-9.1 requires is the OPPOSITE:

* ``uv run pytest`` (default)               -> perf tests SKIP
* ``uv run pytest -m perf`` (opt-in)        -> perf tests EXECUTE
* ``uv run pytest -m 'not perf'``           -> perf tests SKIP (already)
* ``AIENG_RUN_PERF=1 uv run pytest``        -> perf tests EXECUTE (env opt-in)

The hook below honours that by inserting a ``skip(reason=...)`` mark on
every perf-marked item UNLESS the user supplied either:

1. ``-m`` containing the literal substring ``perf`` (covers ``-m perf``,
   ``-m "perf or unit"``, ``-m perf and not slow`` etc.), OR
2. The env var ``AIENG_RUN_PERF=1`` (CI nightly opt-in).

This way the default ``uv run pytest`` invocation is fast and never gets
trapped by a 90s cold-cache benchmark, while CI nightly remains a single
``-m perf`` flag away.
"""

from __future__ import annotations

import os

import pytest


def _perf_opted_in(config: pytest.Config) -> bool:
    """Return True when the caller has explicitly asked for perf tests.

    Two opt-in surfaces:

    * ``-m`` expression mentions ``perf`` (substring-checked).
    * ``AIENG_RUN_PERF=1`` env var (boolean truthy).
    """

    markexpr = config.getoption("markexpr", default="") or ""
    if "perf" in markexpr:
        return True

    env = os.environ.get("AIENG_RUN_PERF", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip every ``@pytest.mark.perf`` test unless the user opted in.

    Runs once after collection. Walks each item; if it carries the
    ``perf`` marker AND the caller did not opt in (per ``_perf_opted_in``),
    we attach a ``pytest.mark.skip`` so the test is reported as SKIPPED
    instead of executed.
    """

    if _perf_opted_in(config):
        return

    skip_perf = pytest.mark.skip(
        reason=(
            "perf benchmark skipped by default (spec-104 T-9.1). "
            "Run with `-m perf` or set `AIENG_RUN_PERF=1` to execute."
        )
    )
    # ``iter_markers("perf")`` is the precise check: True only when the
    # test (or any parent scope) carries an explicit ``@pytest.mark.perf``.
    # We deliberately do NOT use ``"perf" in item.keywords`` because
    # ``keywords`` also reflects the test function name, falsely matching
    # functions like ``test_perf_marker_is_registered``.
    for item in items:
        if any(item.iter_markers("perf")):
            item.add_marker(skip_perf)
