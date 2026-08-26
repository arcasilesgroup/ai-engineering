"""The deterministic context trimmer, spec 033 / B-033-1.

Keeps the head and tail of a tool's output, marks the elided middle, and never elides a line
containing a failure marker — the fix make-claude-code-last-longer measured as the
context-economy relief: trim before the context reads it, and never hide the line that
answers the failure. Deterministic: same input, same trimmed output.
"""

from __future__ import annotations

# A line the session cannot afford to lose. A naive head/tail would hide it in the middle
# exactly when the failure is what the run was about, so these stay even if they sit in the
# would-be-elided span.
_FAILURE = ("ERROR", "FAILED", "FAIL:", "Traceback", "fatal:", "ModuleNotFoundError")


def _is_failure(line: str) -> bool:
    return any(mark in line for mark in _FAILURE)


def _mark(elided: int) -> str:
    return f"… {elided} lines elided …"


def trim_output(text: str, max_lines: int = 80) -> str:
    """Return `text` trimmed to `max_lines`: half head, half tail, elision marked.

    Failure-marker lines from the elided middle are spliced back in before the tail, and
    the head yields space when the total would exceed the budget — the failure is the
    point, and a trimmed output never drops it. An output that fits is returned unchanged.
    """
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text

    half = max_lines // 2
    head = lines[:half]
    tail = lines[-half:]
    elided = lines[half:-half]
    survivors = [line for line in elided if _is_failure(line)]

    # The mark occupies one of the budget's lines; head yields until everything fits.
    mark = _mark(len(elided) - len(survivors))
    head_room = max_lines - len(tail) - len(survivors) - 1
    head = head[:head_room]
    body = [*head, *survivors, mark, *tail]
    # No trailing newline: the trimmed form counts line 1..N exactly against the budget.
    return "\n".join(body)
