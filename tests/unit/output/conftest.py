"""Test fixtures for the Renderer unit suite.

The renderer delegates human-mode output to ``cli_ui``, which uses an
``lru_cache``d Rich ``Console`` bound to ``sys.stderr`` at first call.
``capsys`` replaces ``sys.stderr`` per-test, so the cache must be cleared
before each test to let Rich rebind to the captured stream.
"""

from __future__ import annotations

import pytest

from ai_engineering.cli_ui import get_console


@pytest.fixture(autouse=True)
def _reset_console_cache() -> None:
    """Clear cached Rich console so capsys can intercept stderr."""
    get_console.cache_clear()
