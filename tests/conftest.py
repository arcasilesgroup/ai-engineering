"""Both halves of the product on the path: the package, and the guards.

The guards are deliberately not importable as part of the package — they are standard
library Python executed by path, because on the hot path `import ai_engineering` costs
about 110 ms. Tests reach them the same way the dispatcher does.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for folder in ("src", "hooks"):
    sys.path.insert(0, str(ROOT / folder))


@pytest.fixture(autouse=True)
def undecorated(monkeypatch):
    """Every test drives the plain rendering, which is what a person with NO_COLOR set, a
    dumb terminal or a redirected stream sees. Two reasons, and the second is the real one:
    an assertion on a string full of escape sequences is unreadable in a diff, and a suite
    that only ever exercises the decorated path leaves the path most CI logs take unheld.

    The console is rebuilt around each test because it captures the stream it was made
    with, and capsys replaces that stream after this module was imported."""
    from ai_engineering import ui

    monkeypatch.setenv("NO_COLOR", "1")
    ui.reset()
    yield
    ui.reset()


@pytest.fixture
def coloured(monkeypatch):
    """A terminal that asks for decoration even when the test runner is behind a pipe."""
    from ai_engineering import ui

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("FORCE_COLOR", "1")
    ui.reset()
    yield
    ui.reset()
