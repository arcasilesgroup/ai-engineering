"""The same call repeated, or the same tool failing over and over with the arguments
tweaked each time — which is the retry pattern that actually happens.

Matching identical arguments alone never catches the second one, so failures are
recorded by signature (tool plus its first argument) and the cap applies to the
signature, not to the exact call.
"""

from __future__ import annotations

import hashlib
import json

from _emit import config, home, session_id
from _wrap import guard

WINDOW = 6  # how many recent calls are remembered
REPEATS = 3  # the same call this many times inside the window
FAILURES = 5  # the same signature failing this many times in a row
SIGNATURES = 20  # how many distinct failing signatures the state file remembers


def _printable(text: str) -> str:
    """Only the characters a denial message may carry.

    The signature that names the repeated call is built from surface-controlled input
    (tool name and first argument). A control character smuggled through it lands in a
    message a model reads verbatim and an operator reads on a console — a terminal
    escape is a cosmetic injection on the console and a prompt-shape injection for the
    model. The signature still identifies the call; it just cannot carry bytes that do
    something the wording did not intend."""

    return "".join(ch if ch.isprintable() else f"\\x{ord(ch):02x}" for ch in text)


def state_file():
    return home() / "cache" / "loop" / f"{session_id()}.json"


def load() -> dict:
    try:
        return json.loads(state_file().read_text())
    except (OSError, ValueError):
        return {"recent": [], "failures": {}}


def save(state: dict) -> None:
    path = state_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state))
    except OSError:
        pass


def signature(payload: dict) -> str:
    args = payload.get("tool_input") or {}
    first = ""
    if isinstance(args, dict):
        for key in ("command", "file_path", "path", "pattern", "url", "query"):
            if args.get(key):
                # The last sixty characters, not the first. A path is discriminated by its
                # tail, so truncating from the left made every file under one long
                # temporary directory the same call; a command is one token by then.
                # `or [""]` because an argument made only of whitespace splits to nothing, and
                # an IndexError here is a denial the guard inflicts on itself — reachable by
                # the model, in the guard's own name, on a call that did nothing wrong.
                first = (str(args[key]).split() or [""])[0][-60:]
                break
    return f"{payload.get('tool_name', '')}:{first}"


def exact(payload: dict) -> str:
    """The tool and the whole of its input. `signature` is coarse on purpose so the failure
    arm can see one tool failing with the arguments tweaked each time; counting repeats by
    it would make every git command in a session one key and deny the third one. The
    dispatcher's fingerprint is no use either: it carries the surface's tool_use_id, which
    is unique per call, so three identical calls were three distinct keys and this arm
    never fired on a real surface."""
    body = json.dumps(
        [payload.get("tool_name", ""), payload.get("tool_input", {})], sort_keys=True, default=str
    )
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def failed(payload: dict) -> bool:
    """Authoritative fields only. Scanning a tool's output for the word "error" makes a
    guard fire on a passing test suite that prints one."""
    response = payload.get("tool_response")
    if isinstance(response, dict):
        return bool(response.get("is_error") or response.get("isError"))
    return False


@guard("loop_guard")
def run(payload: dict) -> str | None:
    limits = config().get("guards", {})
    window = int(limits.get("loop_window", WINDOW))
    repeats = int(limits.get("loop_repeats", REPEATS))
    failures = int(limits.get("loop_failures", FAILURES))

    state = load()
    sig = signature(payload)

    if payload.get("_event") != "PreToolUse":
        if failed(payload):
            # Popped and reinserted, so a signature that is still failing moves to the end
            # and the trim below drops the ones nothing has touched. Bounding this by the
            # call window instead would put five failures inside six calls, which is a
            # threshold the failure arm can never reach once anything else happens.
            state["failures"][sig] = state["failures"].pop(sig, 0) + 1
        else:
            state["failures"].pop(sig, None)
        state["failures"] = dict(list(state["failures"].items())[-SIGNATURES:])
        save(state)
        return None

    call = exact(payload)
    state["recent"] = (state["recent"] + [call])[-window:]
    save(state)
    seen = state["recent"].count(call)
    if seen >= repeats:
        # A repetition count per window, carried in the state so the third identical
        # denial (rule 12: the same judgement has resolved the same way three times)
        # escalates instead of restating the identical verdict for the thousandth time.
        # The verdict is the script's first run; the escalation is the script itself,
        # naming the person channel (_wrap.py's bypass recipe) so the loop is handed to
        # somebody who can decide. Every repeat is still denied — fails closed.
        denials = state.setdefault("denials", {}).get(call, 0) + 1
        state["denials"][call] = denials
        state["denials"] = dict(list(state["denials"].items())[-window:])
        save(state)
        if denials >= 3:
            who = _printable(signature(payload))
            # The event says this denial is the escalation, so the digest can show it as
            # the script rule 12 owes instead of re-flagging it as a fresh owed script.
            payload["_escalated"] = True
            return (
                f"BLOCKED: {who} — this exact call has been denied {denials} times in "
                f"the last {window}. The loop is bounded; retrying returns what it "
                f"returned before, and a denial has already been issued for this call in "
                f"this window. Hand it to a person: "
                f'ai-eng exception --skip "<reason>" --guard loop_guard'
            )
        return (
            f"this exact call has been made {seen} times in the last {window}. Repeating "
            f"it will return what it returned before. Say what you expected and what you "
            f"got, and change the approach — or ask."
        )
    if state["failures"].get(sig, 0) >= failures:
        return (
            f"{_printable(sig)} has failed {state['failures'][sig]} times in a row with "
            f"the arguments tweaked each time. Stop and say what is failing; retrying "
            f"past this point is guessing, and it is being paid for by the person waiting."
        )
    return None
