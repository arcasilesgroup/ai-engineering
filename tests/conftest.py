"""Both halves of the product on the path: the package, and the guards.

The guards are deliberately not importable as part of the package — they are standard
library Python executed by path, because on the hot path `import ai_engineering` costs
about 110 ms. Tests reach them the same way the dispatcher does.
"""

import os
import subprocess
from pathlib import Path

import pytest

# Imported here and not in the fixture: the fixture replaces this function, so the handle
# to the real one has to be taken before anything can have replaced it.
from ai_engineering import wiring as _wiring

_REAL_CLI_PROBE = _wiring.cli_answers


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


@pytest.fixture(autouse=True)
def answering_anchor(monkeypatch):
    """The interpreter running the suite can import the product; the child it spawns with
    `PYTHONSAFEPATH` may not, because `src` reaches this process through conftest and not
    through the environment.

    That asymmetry is real and the installer is right to refuse on it — a git anchor naming
    an interpreter that cannot run the product is the defect it was added to catch. But it
    is an ambient fact, and a test about where files land must not turn on it. Inside the
    mutation harness's sandbox it does not hold, and the tests that inherited it failed
    there for a reason they do not test, stopping the gate before it collected a baseline.

    Tests that are about the probe itself do not take this fixture."""

    from ai_engineering import __version__, wiring

    monkeypatch.setattr(
        wiring,
        "cli_answers",
        lambda: subprocess.CompletedProcess([], 0, f"ai-engineering {__version__}\n", ""),
    )


@pytest.fixture
def real_anchor(monkeypatch):
    """Put the probe back, for the tests that are about the probe.

    The fixture above is autouse because the fact it states is ambient and almost no test
    is about it. Almost: one test asserts the exact argument list the installer executes
    before it persists an anchor, and that one has to watch the real thing run."""

    from ai_engineering import wiring

    monkeypatch.setattr(wiring, "cli_answers", _REAL_CLI_PROBE)


def repository() -> Path:
    """This repository, from a suite that is not always running inside it.

    `just mutate` runs the suite out of mutmut's `mutants/` tree: it holds the package and
    the tests, none of the repository's root files, and no `.git`. Assertions about *this
    repository* — its manifests, its lock file, which policy files something reads — ask a
    different tree there, and it answers wrongly rather than not at all. Three did, all
    added on the same day, and each took the whole-tree lane down on a true statement: an
    absent `package-lock.json`, an absent `package.json`, and a `git grep` with no
    repository under it that reported every policy file as read by nothing.

    The harness already exports the real `src/` for this exact reason, so the real root is
    its parent. Unset, it is the tree this file is in, which is the ordinary case.

    This lives here because it is the third time the same judgement resolved the same way,
    which is when rule 12 says it stops being a judgement.
    """

    real = os.environ.get("AI_ENG_REAL_SRC")
    return Path(real).resolve().parent if real else Path(__file__).resolve().parents[1]
