"""Every question a person is asked goes through one door, and that door cannot be faked.

`EP-168` asks that a human answer outrank inference. Its note said no code detects an
interactive channel or a present human, and six modules do — but counting them would have been
the wrong check anyway. A guard repeated at nine call sites is nine chances to forget it.

The design is better than the note assumed: `accept.controlling_terminal_response` reads the
OS controlling terminal directly, and its docstring names precisely what it refuses to read
because a script can supply each one — `isatty`, a flag, an environment value, and piped
standard input. Inference does not lose to a human answer here; inference is not available.

So what is held is the door, not the count: the reader consults none of the four, refuses
under the mode that promises not to ask, and refuses rather than raising when there is no
terminal to open. A refusal is the safe answer and an exception is not — a traceback out of a
consent prompt is a consent prompt that crashed, and what happens next is whatever the caller
does with an exception it never expected.
"""

from __future__ import annotations

import ast
from pathlib import Path

from ai_engineering import accept

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "ai_engineering" / "accept.py"

# The four things a script can supply, in the reader's own words.
FAKEABLE = ("isatty", "environ", "getenv", "stdin")


def _reader() -> ast.FunctionDef:
    """The function with its docstring removed, which is the only version worth asking.

    The first version of this dumped the function whole and failed, because the docstring
    names all four of the things the code refuses to read — that is what a docstring is for.
    A check that cannot tell a mention of something from a use of it is the defect this
    repository has now found in a ledger row searching for its own id, in a grep counting a
    capability inside the comment explaining there are none, and here, in the test written to
    catch that class.
    """

    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    found = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "controlling_terminal_response"
    )
    first = found.body[0] if found.body else None
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        found.body = found.body[1:]
    return found


def test_the_reader_consults_nothing_a_script_can_supply():
    """The whole claim. `isatty` is true under a pty a script opened; an environment value and
    a flag are arguments; piped standard input is the oldest way to answer a prompt without
    being there. Reading any of them would make the answer available to a caller rather than
    to a person."""

    body = ast.dump(_reader())

    for fakeable in FAKEABLE:
        assert fakeable not in body, (
            f"the controlling-terminal reader consults {fakeable}, which a script supplies. "
            "The answer would then be available to whatever ran this, not to a person."
        )


def test_a_mode_that_promises_not_to_ask_is_observable_as_not_asking(monkeypatch):
    """`--non-interactive` returns no without opening the device. Opening it and discarding
    the answer would be the same result and a different fact: the terminal would have been
    read on a run that said it would not read one."""

    opened = []
    monkeypatch.setattr(accept, "NON_INTERACTIVE", True)
    monkeypatch.setattr(accept, "_open_terminal", lambda: opened.append(1))

    assert accept.controlling_terminal_response("yes") is False
    assert not opened, "the device was opened on a run that promised not to ask"


def test_no_terminal_is_a_refusal_and_never_a_traceback(monkeypatch):
    """The case that decides what a consent prompt does on a machine with no keyboard. A
    refusal is an answer the caller already handles; an exception is whatever it does with
    something it never expected, on the path where the answer is consent."""

    def missing():
        raise OSError("no such device")

    monkeypatch.setattr(accept, "NON_INTERACTIVE", False)
    monkeypatch.setattr(accept, "_open_terminal", missing)

    assert accept.controlling_terminal_response("yes") is False


def test_the_answer_has_to_be_the_exact_phrase(monkeypatch):
    """Not a prefix, not a yes, not a truthy line. The phrase is the whole of what
    distinguishes a person who read the question from one who typed something."""

    class _Line:
        def __init__(self, said: str) -> None:
            self.said = said

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def readline(self) -> str:
            return self.said

    monkeypatch.setattr(accept, "NON_INTERACTIVE", False)
    for said, expected in (("yes\n", True), ("yes please\n", False), ("y\n", False), ("", False)):
        monkeypatch.setattr(accept, "_open_terminal", lambda _s=said: _Line(_s))
        assert accept.controlling_terminal_response("yes") is expected, said
