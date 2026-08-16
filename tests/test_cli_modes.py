"""D-012-06: two flags and one equivalence proof, not a rewrite.

The JSON envelope, the will/running/cure lines, the seven outcomes and the `NO_COLOR`
handling were measured present. What was measured absent is `--debug` and
`--non-interactive`, and the fact that nothing proved the three renderings agree — which is
the one that matters, because a person and a script reading the same run and getting
different answers is the whole failure this product is about.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r"\x1b\[[0-9;]*m")
OUTCOMES = ("PASS", "FAIL", "INCOMPLETE", "WARN", "SKIPPED", "OBSERVED", "APPLIED", "WOULD_CHANGE")

# A verb that raises where the dispatcher calls it. The substitution lives here and not in
# the product: a crash path reached through an environment variable the product reads is a
# way to make it crash, shipped to everybody, so that a test could watch.
CRASHING = (
    "import sys; from ai_engineering import cli, doctor;"
    " doctor.main = lambda argv: 1 / 0;"
    " sys.exit(cli.main(sys.argv[1:]))"
)


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Every path with a `~` in it, and the framework's own folder, inside tmp_path."""
    fake = tmp_path / "home"
    fake.mkdir()
    monkeypatch.setenv("HOME", str(fake))
    monkeypatch.setenv("USERPROFILE", str(fake))
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(fake / ".ai-engineering"))
    return fake


def run(arguments: list[str], script: str = "", **environment) -> subprocess.CompletedProcess[str]:
    """One real process, because "the same run in three renderings" cannot be proved by
    three calls into one interpreter that caches its console after the first."""

    source = os.environ.get("AI_ENG_REAL_SRC") or str(ROOT / "src")
    entry = ["-c", script] if script else ["-m", "ai_engineering.cli"]
    inherited = {**os.environ, "PYTHONPATH": source, **environment}
    if "FORCE_COLOR" in environment:
        # The suite runs with `NO_COLOR` set for every test, and `NO_COLOR` outranks
        # `FORCE_COLOR` by design. A child asked for the decorated rendering has to be
        # asked for it cleanly, or this leg is the undecorated one twice over.
        inherited.pop("NO_COLOR", None)
        inherited.pop("TERM", None)
    return subprocess.run(
        [sys.executable, *entry, *arguments],
        cwd=ROOT,
        env=inherited,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def spoken(text: str) -> str:
    """The outcome word out of a rendering a person reads."""

    plain = ANSI.sub("", text)
    found = [word for word in OUTCOMES if word in plain]
    return found[0] if found else ""


def test_the_three_renderings_of_one_run_agree_on_outcome_and_exit_code():
    """EP-025, EP-234. Executed in all three, and not asserted about.

    A person on a colour terminal, a person piping into a file and a script reading `--json`
    are looking at the same run. If the three disagree, one of them is being told something
    that is not true about what happened — and until this test existed, nothing in this
    repository would have noticed."""

    from ai_engineering import outcome

    coloured = run(["spec", "list"], FORCE_COLOR="1")
    piped = run(["spec", "list"], NO_COLOR="1")
    machine = run(["--json", "spec", "list"], NO_COLOR="1")

    assert coloured.returncode == piped.returncode == machine.returncode
    payload = json.loads(machine.stdout)
    assert spoken(coloured.stdout) == spoken(piped.stdout) == payload["outcome"] != ""
    # The declared outcome and the code the shell received, which is the pair a script acts
    # on. The envelope itself carries no `exit_code` field — that gap belongs to EP-090 and
    # to a specification nobody has approved, so this reads the mapping rather than
    # pre-empting it, and says so here instead of quietly asserting less.
    assert outcome.result(payload["outcome"]).exit_code == machine.returncode

    # EP-230: one object on stdout, no chrome, no prompt, no escape sequence.
    assert machine.stdout.count("\n") == 1
    assert "\x1b" not in machine.stdout
    # And the colour is real in the first one, or FORCE_COLOR proved nothing.
    assert "\x1b" in coloured.stdout + coloured.stderr
    assert "\x1b" not in piped.stdout


def test_a_traceback_is_bounded_into_four_fields_unless_debug_is_asked_for():
    """EP-233. Without `--debug`, an unexpected failure carries a stable code, a human
    message, whether it is worth retrying and a cure — and nothing else.

    A traceback is the fastest way to put an absolute path, a username and the shape of
    somebody's filesystem onto a screen that is about to be pasted into an issue. The
    exception is still recorded in the event record either way; what changes is what is
    printed."""

    from ai_engineering import cli

    interior = RuntimeError("/Users/somebody/secrets and the interior detail")
    quiet = cli.crash(interior, debug=False)

    assert quiet.code == "UNEXPECTED_ERROR"
    assert quiet.retryable is False
    assert quiet.cure and "--debug" in quiet.cure
    assert "RuntimeError" not in quiet.message
    assert "/Users/somebody" not in quiet.message

    with pytest.raises(RuntimeError):
        cli.crash(interior, debug=True)


def test_the_unexpected_failure_prints_four_fields_and_no_traceback():
    """The same rule, executed rather than unit-tested: a verb that raises on a real run
    prints the bounded error, and the same run with `--debug` prints the traceback."""

    quiet = run(["--json", "doctor"], script=CRASHING, NO_COLOR="1")
    loud = run(["doctor", "--debug"], script=CRASHING, NO_COLOR="1")

    assert quiet.returncode == 1
    payload = json.loads(quiet.stdout)
    assert payload["error"]["code"] == "UNEXPECTED_ERROR"
    assert "Traceback" not in quiet.stdout and "Traceback" not in quiet.stderr
    assert "ZeroDivisionError" not in quiet.stdout + quiet.stderr

    assert "Traceback" in loud.stderr and "ZeroDivisionError" in loud.stderr
    assert loud.returncode != 0


def test_non_interactive_refuses_a_missing_decision_without_reading_the_terminal(monkeypatch):
    """EP-236. The flag fails when a decision is missing; it does not choose the default.

    This is the rule the acceptance reader already keeps — a consent a script can supply is
    not a consent — moved to the flag a script actually passes."""

    from ai_engineering import accept

    monkeypatch.setattr(accept, "NON_INTERACTIVE", True)
    opened: list[str] = []
    monkeypatch.setattr(accept, "_open_terminal", lambda: opened.append("terminal"))

    assert accept.controlling_terminal_response("SEND anything") is False
    assert opened == [], "the terminal was read in the mode that promised not to ask"


def test_non_interactive_installs_nothing_it_was_not_told_to_install(home, capsys, monkeypatch):
    """`init` asks one question whose default is yes, and a mode that answers it for you is a
    mode that sets a machine up on nobody's word."""

    from ai_engineering import accept, init

    monkeypatch.setattr(accept, "NON_INTERACTIVE", True)
    result = init.global_step(init.parse(["--global"]))

    assert result.exit_code != 0
    assert "DECISION_REQUIRED" in capsys.readouterr().err
    assert not (home / ".ai-engineering").exists()


def test_both_flags_are_global_and_the_verb_never_sees_them():
    """Stripped before the verb is dispatched, exactly as `--json` already is. A verb that
    had to know about them is a verb that can disagree with the next one about what they
    mean.

    Measured against the same command without the flag, and not against zero. Asserting
    `returncode == 0` looked stricter and was a different claim: it said `spec list`
    succeeds, which depends on where it runs. The mutation gate runs the suite from an
    rsync'd copy with no `.git` in it, where `spec list` correctly answers INCOMPLETE with
    "not inside a repository" and exits 1 — so this test failed there while passing here,
    and its message said "the flag reached the verb" about a run where it plainly had not.
    Comparing the two runs proves the actual rule: the verb cannot tell the flag was
    passed, wherever the verb happens to be standing."""

    plain = run(["spec", "list"], NO_COLOR="1")
    for flag in ("--non-interactive", "--debug"):
        listed = run([flag, "spec", "list"], NO_COLOR="1")
        assert "unrecognized arguments" not in listed.stderr, f"{flag} reached the verb"
        assert listed.returncode == plain.returncode, f"{flag} changed the outcome"
        assert listed.stdout == plain.stdout, f"{flag} changed what the verb printed"
