"""What the JSON boundary does with whatever a verb hands back, or throws.

`cli._json_dispatch` carried 137 surviving mutants — the largest pool behind any single
function in the tree, and the reason is that almost all of it is error handling. Error
handling is the part of a program that runs when something has already gone wrong, so a
test suite driven by things going right never reaches it, and a mutant that lives there
sits behind a branch nobody takes.

What this function is for is the sentence worth keeping: *there is exactly one JSON object
on stdout, whatever happened*. A verb that returns the wrong type, a parser that exits, a
crash, an interrupt, and an import that fails before there is anything to interrupt are
five different disasters, and a machine reading this stream has to get a well-formed
answer from every one of them — with a different code, so it can tell them apart.

The mode is chosen on purpose. These drive the boundary with a fake module rather than a
real verb, because a real verb ties the case to whatever that verb happens to do today and
the case is about the boundary.
"""

from __future__ import annotations

import importlib
import json
from types import SimpleNamespace
from typing import Any

import pytest

from ai_engineering import cli, wiring
from ai_engineering import outcome as outcome_module


def _driven(returns: Any = None, raises: BaseException | None = None, **kwargs: Any) -> tuple:
    """Run the boundary over a module that does exactly one thing, and read its JSON."""

    def main(_rest: list[str]) -> Any:
        if raises is not None:
            raise raises
        return returns

    with pytest.MonkeyPatch.context() as patched:
        patched.setattr(importlib, "import_module", lambda _name: SimpleNamespace(main=main))
        exit_code = cli._json_dispatch("doctor", [], **kwargs)
    return exit_code


def _payload(capsys) -> dict[str, Any]:
    printed = capsys.readouterr().out.strip().splitlines()
    assert len(printed) == 1, f"the boundary printed {len(printed)} lines, not one"
    return json.loads(printed[0])


def test_an_execution_handed_back_is_the_answer_unchanged(capsys):
    """The ordinary path, and the control the rest of this file needs. Without it every
    case below is satisfied by a boundary that reports a failure for everything."""

    given = outcome_module.execution(outcome_module.result("PASS"), summary="all good")

    exit_code = _driven(returns=given)
    payload = _payload(capsys)

    assert exit_code == given.exit_code
    assert payload["outcome"] == "PASS"
    assert payload["command"] == "doctor"


def test_a_bare_result_is_wrapped_rather_than_refused(capsys):
    """Most verbs return a result and not an execution, and both are canonical. Refusing
    the simpler one would make every verb carry a wrapper for the boundary's convenience."""

    exit_code = _driven(returns=outcome_module.result("FAIL"))
    payload = _payload(capsys)

    assert payload["outcome"] == "FAIL"
    assert exit_code == outcome_module.result("FAIL").exit_code


@pytest.mark.parametrize(
    "returned",
    [
        pytest.param(None, id="nothing at all"),
        pytest.param(0, id="an exit code"),
        pytest.param("PASS", id="the word"),
        pytest.param({"outcome": "PASS"}, id="a dictionary that looks right"),
    ],
)
def test_anything_that_is_not_a_canonical_result_is_incomplete_and_says_so(returned, capsys):
    """Four plausible wrong answers, and the last is the dangerous one: a dictionary
    carrying `outcome: PASS` is exactly what a verb would return if somebody built the
    envelope by hand, and passing it through would let prose decide a terminal result."""

    _driven(returns=returned)
    payload = _payload(capsys)

    assert payload["outcome"] == "INCOMPLETE"
    assert payload["error"]["code"] == "NONCANONICAL_RESULT"


def test_a_type_that_merely_subclasses_the_result_is_not_the_result(capsys):
    """`type(x) is Result` and not `isinstance`. A subclass can override `exit_code` or
    `outcome` and would then be answering for the boundary rather than through it."""

    import dataclasses

    class Pretender(outcome_module.Result):  # type: ignore[misc]
        pass

    honest = outcome_module.result("PASS")
    pretender = Pretender(**{f.name: getattr(honest, f.name) for f in dataclasses.fields(honest)})

    _driven(returns=pretender)

    assert _payload(capsys)["error"]["code"] == "NONCANONICAL_RESULT"


# --- the five ways a verb can stop rather than return ---------------------------------
#
# One table, because the shape of the answer is the same every time and only the words
# change: an outcome, a code, and a sentence a person can act on. Five separate functions
# let five assertions drift apart; a table cannot, and the row that fails still names
# itself.


class _Sideways(BaseException):
    """Outside the ordinary hierarchy, which is the point of the row that uses it."""


@pytest.mark.parametrize(
    ("raises", "outcome", "code", "says", "exit_code"),
    [
        # `--help` reaches here as `SystemExit(0)`. Not a failure, and not a terminal result
        # either — reporting it as INCOMPLETE makes every help request look like a broken
        # command to whatever is reading the stream.
        pytest.param(SystemExit(None), "PASS", None, "Help requested", 0, id="help, exit None"),
        pytest.param(SystemExit(0), "PASS", None, "Help requested", 0, id="help, exit 0"),
        # Its own code and its own status, because misuse of the command line is not an
        # outcome of the operation — nothing was attempted.
        pytest.param(
            SystemExit(outcome_module.invalid_cli_exit()),
            "INCOMPLETE",
            "INVALID_CLI",
            "Invalid arguments",
            outcome_module.invalid_cli_exit(),
            id="bad arguments",
        ),
        # Neither help nor misuse. A verb calling `sys.exit(3)` produced no terminal result,
        # and inventing one from the exit code would be the boundary deciding an outcome.
        pytest.param(
            SystemExit(3),
            "INCOMPLETE",
            "UNEXPECTED_ERROR",
            "stopped without a canonical terminal result",
            None,
            id="any other exit code",
        ),
        # A person pressing control-C did not find a defect. Recording it as one puts a false
        # failure into every record that counts them.
        pytest.param(KeyboardInterrupt(), "CANCELLED", None, None, None, id="an interrupt"),
        # The case the whole boundary exists for: a traceback on stdout is not JSON, and a
        # machine reading this stream gets nothing it can act on.
        pytest.param(
            RuntimeError("something deep"),
            "INCOMPLETE",
            "UNEXPECTED_ERROR",
            "failed before producing bounded execution facts",
            None,
            id="a crash",
        ),
        # `BaseException` and not `Exception`. A subclass written outside the ordinary
        # hierarchy would otherwise escape and print nothing at all, which is the one outcome
        # this function may not have.
        pytest.param(
            _Sideways("out of band"),
            "INCOMPLETE",
            "UNEXPECTED_ERROR",
            None,
            None,
            id="something that is not an Exception",
        ),
    ],
)
def test_a_verb_that_stops_still_leaves_one_well_formed_object(
    raises, outcome, code, says, exit_code, capsys
):
    returned = _driven(raises=raises)
    payload = _payload(capsys)

    assert payload["outcome"] == outcome
    if code is not None:
        assert payload["error"]["code"] == code
    if says is not None:
        assert says in json.dumps(payload)
    if exit_code is not None:
        assert returned == exit_code


def test_the_cure_for_bad_arguments_names_the_command_that_would_have_worked(capsys):
    """Separate because it is the only row whose value is a whole sentence built from the
    verb. The person who typed it wrong is one line away from typing it right."""

    _driven(raises=SystemExit(outcome_module.invalid_cli_exit()))

    assert _payload(capsys)["error"]["cure"] == "run ai-eng doctor --help"


def test_a_crash_never_carries_its_own_words_into_the_object(capsys):
    """The message a person sees is bounded and written here. An exception string can hold
    an absolute path, a username and the shape of somebody's filesystem."""

    _driven(raises=RuntimeError("something deep"))

    assert "something deep" not in json.dumps(_payload(capsys))


def test_the_traceback_reaches_a_person_only_when_it_was_asked_for(capsys):
    """A traceback is the fastest way to put an absolute path and a username onto a screen
    that is about to be pasted into an issue."""

    _driven(raises=RuntimeError("deep"), debug=False)
    quiet = capsys.readouterr()
    _driven(raises=RuntimeError("deep"), debug=True)
    loud = capsys.readouterr()

    assert "Traceback" not in quiet.err
    assert "Traceback" in loud.err


# --- what the boundary does to the process it runs inside ----------------------------


def test_the_verb_reads_an_empty_stdin_rather_than_the_callers(capsys, monkeypatch):
    """Nothing here has a terminal, so a verb that reads stdin would block forever waiting
    for a person who is not there. It gets an empty stream and finds out immediately."""

    seen: list[str] = []

    def main(_rest: list[str]) -> Any:
        import sys as system

        seen.append(system.stdin.read())
        return outcome_module.result("PASS")

    monkeypatch.setattr(importlib, "import_module", lambda _name: SimpleNamespace(main=main))
    cli._json_dispatch("doctor", [])
    capsys.readouterr()

    assert seen == [""]


def test_stdin_is_put_back_even_when_the_verb_explodes(capsys):
    """The `finally` that matters. A boundary that leaves stdin replaced breaks whatever
    runs after it in the same process, and the failure appears somewhere else entirely."""

    import sys as system

    before = system.stdin
    _driven(raises=RuntimeError("deep"))
    capsys.readouterr()

    assert system.stdin is before


def test_a_failure_before_the_verb_runs_is_reported_at_the_outer_boundary(capsys):
    """Setting up the console happens before the inner handler exists, so a failure there
    has to be caught further out — and it says something different on purpose, because
    "the command failed" and "there was never a command" are not the same news."""

    from ai_engineering import ui

    def refuse() -> None:
        raise RuntimeError("no console here")

    with pytest.MonkeyPatch.context() as patched:
        patched.setattr(ui, "reset", refuse)
        cli._json_dispatch("doctor", [])
    payload = _payload(capsys)

    assert payload["outcome"] == "INCOMPLETE"
    assert "before its execution boundary was available" in payload["summary"]


# --- cli.main: what happens before a verb is reached, and after it stops --------------
#
# 89 more survivors. `main` is a router with two modes, and almost everything it does
# happens either before a verb exists or after one has stopped — which is the same reason
# `_json_dispatch` was full of them: a suite that runs verbs never runs the router's own
# decisions.
#
# The two modes are not variations of each other. In JSON mode stdout carries exactly one
# object and every complaint is inside it. In the plain mode a complaint goes to stderr and
# the useful list stays on stdout, so a typo does not stop the verb list being pipeable.


def _ran(argv: list[str], capsys) -> tuple[int, str, str]:
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_the_version_line_is_plain_because_another_program_reads_it(capsys):
    """The only output here that is not for a person. A banner, a colour or a leading glyph
    turns a parseable line into something somebody has to strip first."""

    from ai_engineering import __version__

    code, out, _ = _ran(["--version"], capsys)

    assert code == 0
    assert out == f"ai-engineering {__version__}\n"


def test_an_unknown_verb_complains_on_stderr_and_leaves_the_list_on_stdout(capsys):
    """A typo is not a reason to stop the verb list being pipeable, and it is a reason for
    the error itself not to be."""

    code, out, err = _ran(["notaverb"], capsys)

    assert code == 2
    assert "there is no verb" in err and "notaverb" in err
    assert "doctor" in out and "there is no verb" not in out


def test_the_removed_flag_is_named_rather_than_treated_as_an_unknown_verb(capsys):
    """`--adr` was hard-removed. Saying so is the difference between somebody updating a
    script and somebody wondering why their command stopped working."""

    code, _, err = _ran(["decide", "--adr", "x"], capsys)

    assert code == 2
    assert "--adr" in err


def test_json_mode_may_be_asked_for_once(capsys):
    """Twice is a mistake worth naming rather than absorbing, because a caller repeating a
    global flag is usually a caller building a command line in two places."""

    code, out, _ = _ran(["--json", "--json", "doctor"], capsys)
    payload = json.loads(out.strip())

    assert code != 0
    assert payload["error"]["code"] == "INVALID_CLI"


def test_json_mode_with_no_command_says_so_inside_the_json(capsys):
    """The complaint has to be in the object. A machine that asked for JSON and got a line
    of prose on stderr has to parse prose to find out it made a mistake."""

    _, out, _ = _ran(["--json"], capsys)
    payload = json.loads(out.strip())

    assert payload["outcome"] == "INCOMPLETE"
    assert payload["error"]["cure"] == "run ai-eng --json --help"


def test_an_unknown_verb_in_json_mode_is_one_object_and_not_a_verb_list(capsys):
    _, out, err = _ran(["--json", "notaverb"], capsys)
    payload = json.loads(out.strip())

    assert payload["error"]["code"] == "INVALID_CLI"
    assert err == ""
    assert len(out.strip().splitlines()) == 1


@pytest.mark.parametrize("flag", ["-h", "--help", "help"])
def test_help_in_json_mode_is_an_object_and_not_the_usage_text(flag: str, capsys):
    _, out, _ = _ran(["--json", flag], capsys)

    assert json.loads(out.strip())["command"] == "help"


@pytest.mark.parametrize("flag", ["-V", "--version", "version"])
def test_the_version_in_json_mode_is_an_object_and_not_the_plain_line(flag: str, capsys):
    _, out, _ = _ran(["--json", flag], capsys)

    assert json.loads(out.strip())["command"] == "version"


@pytest.mark.parametrize("flag", ["--debug", "--non-interactive"])
def test_a_global_flag_never_reaches_the_verb(flag: str, capsys, monkeypatch):
    """Both are stripped here exactly as `--json` is. A verb that had to know about either
    is a verb that can disagree with the next one about what it means."""

    from ai_engineering import accept

    # Restored by the fixture. `--non-interactive` is process state rather than an
    # argument, so a test that set it and walked away would silence the confirmation
    # widget for every test that ran afterwards — which is how one of these leaked.
    monkeypatch.setattr(accept, "NON_INTERACTIVE", accept.NON_INTERACTIVE)
    seen: list[list[str]] = []
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda _n: SimpleNamespace(
            main=lambda rest: seen.append(rest) or outcome_module.result("PASS")
        ),
    )

    cli.main(["doctor", flag, "--fix"])
    capsys.readouterr()

    assert seen == [["--fix"]]


def test_non_interactive_is_set_where_the_verb_that_asks_will_read_it(capsys, monkeypatch):
    """It is not passed down as an argument; it is a fact about this process. A verb that
    took it as a flag could be given it by one caller and not the next, and a confirmation
    prompt would appear in a pipeline exactly once in a while."""

    from ai_engineering import accept

    monkeypatch.setattr(accept, "NON_INTERACTIVE", False)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda _n: SimpleNamespace(main=lambda _r: outcome_module.result("PASS")),
    )

    cli.main(["doctor", "--non-interactive"])
    capsys.readouterr()

    assert accept.NON_INTERACTIVE is True


def test_an_interrupt_in_plain_mode_is_a_hundred_and_thirty_and_not_a_crash(capsys, monkeypatch):
    """The shell's own convention for a signal, so a script that checks the code learns what
    happened rather than reading it as a failure of the work."""

    def stopped(_rest: list[str]) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(importlib, "import_module", lambda _n: SimpleNamespace(main=stopped))

    assert cli.main(["doctor"]) == 130
    capsys.readouterr()


def test_an_unreadable_file_stops_the_run_and_says_nothing_was_written(capsys, monkeypatch):
    """One place, because every verb that writes reads first. A file that cannot be parsed
    is not an empty file, and the only safe thing to do with one is stop and name it — the
    alternative, which this used to do, is treat it as empty and save over it."""

    def unreadable(_rest: list[str]) -> None:
        raise wiring.Unreadable("~/.claude/settings.json is not readable as JSON")

    monkeypatch.setattr(importlib, "import_module", lambda _n: SimpleNamespace(main=unreadable))

    code = cli.main(["doctor"])
    err = capsys.readouterr().err

    assert code == 2
    assert "Nothing was written" in err
    assert "settings.json" in err


def test_a_crash_in_plain_mode_carries_four_fields_and_no_traceback(capsys, monkeypatch):
    """A traceback is the fastest way to put an absolute path and a username onto a screen
    that is about to be pasted into an issue. What a person gets instead is a code, a
    message, whether it is worth retrying, and what to do next."""

    def broken(_rest: list[str]) -> None:
        raise RuntimeError("deep")

    monkeypatch.setattr(importlib, "import_module", lambda _n: SimpleNamespace(main=broken))

    cli.main(["doctor"])
    err = capsys.readouterr().err

    assert "Traceback" not in err
    assert "Retryable:" in err and "Next action:" in err
