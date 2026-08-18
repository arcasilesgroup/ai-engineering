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

from ai_engineering import cli, outcome


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

    given = outcome.execution(outcome.result("PASS"), summary="all good")

    exit_code = _driven(returns=given)
    payload = _payload(capsys)

    assert exit_code == given.exit_code
    assert payload["outcome"] == "PASS"
    assert payload["command"] == "doctor"


def test_a_bare_result_is_wrapped_rather_than_refused(capsys):
    """Most verbs return a result and not an execution, and both are canonical. Refusing
    the simpler one would make every verb carry a wrapper for the boundary's convenience."""

    exit_code = _driven(returns=outcome.result("FAIL"))
    payload = _payload(capsys)

    assert payload["outcome"] == "FAIL"
    assert exit_code == outcome.result("FAIL").exit_code


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

    class Pretender(outcome.Result):  # type: ignore[misc]
        pass

    honest = outcome.result("PASS")
    pretender = Pretender(**{f.name: getattr(honest, f.name) for f in dataclasses.fields(honest)})

    _driven(returns=pretender)

    assert _payload(capsys)["error"]["code"] == "NONCANONICAL_RESULT"


# --- the four ways a verb can stop rather than return --------------------------------


@pytest.mark.parametrize("code", [None, 0])
def test_a_parser_printing_help_is_a_pass_and_exits_zero(code, capsys):
    """`--help` reaches here as `SystemExit(0)`, which is not a failure and is not a
    terminal result either. Reporting it as INCOMPLETE would make every help request look
    like a broken command to whatever is reading the stream."""

    exit_code = _driven(raises=SystemExit(code))
    payload = _payload(capsys)

    assert exit_code == 0
    assert payload["outcome"] == "PASS"
    assert "Help requested" in payload["summary"]


def test_bad_arguments_are_invalid_cli_and_carry_the_way_out(capsys):
    """Its own code and its own exit status, because misuse of the command line is not an
    outcome of the operation — nothing was attempted. And it carries a cure, because the
    person who typed it wrong is one line away from typing it right."""

    exit_code = _driven(raises=SystemExit(outcome.invalid_cli_exit()))
    payload = _payload(capsys)

    assert exit_code == outcome.invalid_cli_exit()
    assert payload["error"]["code"] == "INVALID_CLI"
    assert payload["error"]["cure"] == "run ai-eng doctor --help"


def test_an_exit_with_any_other_code_is_a_command_that_stopped(capsys):
    """Neither help nor misuse. A verb calling `sys.exit(3)` produced no terminal result,
    and inventing one from the exit code would be the boundary deciding an outcome."""

    _driven(raises=SystemExit(3))
    payload = _payload(capsys)

    assert payload["outcome"] == "INCOMPLETE"
    assert payload["error"]["code"] == "UNEXPECTED_ERROR"
    assert "stopped without a canonical terminal result" in payload["summary"]


def test_an_interrupt_is_cancelled_and_not_a_failure(capsys):
    """A person pressing control-C did not find a defect. Recording it as one puts a false
    failure into every record that counts them."""

    _driven(raises=KeyboardInterrupt())
    payload = _payload(capsys)

    assert payload["outcome"] == "CANCELLED"


def test_a_crash_still_produces_one_well_formed_object(capsys):
    """The case the whole boundary exists for. A traceback on stdout is not JSON, and a
    machine reading this stream gets nothing it can act on — including the fact that
    something went wrong."""

    _driven(raises=RuntimeError("something deep"))
    payload = _payload(capsys)

    assert payload["outcome"] == "INCOMPLETE"
    assert payload["error"]["code"] == "UNEXPECTED_ERROR"
    assert "something deep" not in json.dumps(payload)


def test_the_traceback_reaches_a_person_only_when_it_was_asked_for(capsys):
    """A traceback is the fastest way to put an absolute path and a username on a screen
    that is about to be pasted into an issue."""

    _driven(raises=RuntimeError("deep"), debug=False)
    quiet = capsys.readouterr()
    _driven(raises=RuntimeError("deep"), debug=True)
    loud = capsys.readouterr()

    assert "Traceback" not in quiet.err
    assert "Traceback" in loud.err


def test_an_exception_that_is_not_an_exception_is_still_caught(capsys):
    """`BaseException` and not `Exception`. A `GeneratorExit` or a subclass somebody wrote
    outside the ordinary hierarchy would otherwise escape the boundary and print nothing at
    all, which is the one outcome this function may not have."""

    class Sideways(BaseException):
        pass

    _driven(raises=Sideways("out of band"))

    assert _payload(capsys)["outcome"] == "INCOMPLETE"


# --- what the boundary does to the process it runs inside ----------------------------


def test_the_verb_reads_an_empty_stdin_rather_than_the_callers(capsys, monkeypatch):
    """Nothing here has a terminal, so a verb that reads stdin would block forever waiting
    for a person who is not there. It gets an empty stream and finds out immediately."""

    seen: list[str] = []

    def main(_rest: list[str]) -> Any:
        import sys as system

        seen.append(system.stdin.read())
        return outcome.result("PASS")

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
