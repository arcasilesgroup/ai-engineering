"""Performance benchmarks for spec-104 goals G-1, G-2, G-3.

These tests are opt-in via ``pytest -m perf``. The default test runs
(``uv run pytest``) skip them automatically because pytest selects only
tests that match the supplied ``-m`` expression. CI invokes them on a
nightly schedule -- not on every PR -- to avoid flakiness from runner
load jitter colliding with wall-clock budget assertions.
"""
