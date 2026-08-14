"""Ten verbs, and the only way to run any of them.

Not six, which cannot express a dated risk acceptance signed by a named person, and not
seventy, which nobody can hold in their head. The table below is the whole surface, and
it is also what emits: an entry point does not exist until it is in this table, and this
table records that it ran.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import sys
import time
import uuid
from datetime import UTC, datetime

from ai_engineering import __version__, outcome, paths, wiring

VERBS: dict[str, str] = {
    "init": "Set up this machine, and this repository if you say yes.",
    "doctor": "The 20 assertions and the coverage line. Is the system healthy now?",
    "update": "Rewrite the pin and run the forward migrations.",
    "spec": "spec new | spec list | spec show — the record of what was decided.",
    "decide": "Add a decision to the spec, or promote it to an MADR with --madr.",
    "accept": "Accept a finding until a date, with a named owner and a reason.",
    "audit": "audit verify walks the whole chain; audit replay walks a session.",
    "report": "Produce the local governed report.",
    "exception": "Record a governed design exception, at a keyboard.",
    "uninstall": "Undo everything the receipt lists. The no-lock-in promise, as a command.",
}


def usage() -> None:
    """The ten verbs, with the verb itself in the brand style so the eye lands on the word
    you are going to type. The banner sits above it, on a terminal only.

    Still stdout, and still one verb per line: this is what a person pipes into a pager,
    and `ai-eng --help | grep spec` has to keep working."""
    from ai_engineering import ui

    ui.banner()
    ui.write("ai-eng <verb> [options]\n", data=True)
    for verb, text in VERBS.items():
        ui.pair(f"  {verb:<10}", text)
    ui.write("\n  ai-eng <verb> --help for the flags.", data=True)


def speakable() -> None:
    """Windows hands a bare `print()` a cp1252 stream, and a tick in a success line is not
    in cp1252 — so `ai-eng spec new` ended in a UnicodeEncodeError traceback on the Windows
    leg of the install matrix, the first time that matrix ever ran. Rich's own path was
    never affected, which is why this survived every local run and every Linux job. Fixed
    once, here, because the alternative is remembering it at each of the eleven print()
    calls that carry a glyph, and the twelfth is written by somebody who was not here."""
    for stream in (sys.stdout, sys.stderr):
        # getattr and not a suppressed AttributeError: a stream a test replaced with
        # something simpler has no reconfigure, and that is not an error to swallow.
        settable = getattr(stream, "reconfigure", None)
        if settable is not None:
            with contextlib.suppress(OSError, ValueError):
                settable(encoding="utf-8", errors="replace")


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _error(result: outcome.Result, code: str) -> dict | None:
    if result.exit_code == 0:
        return None
    return {
        "code": code,
        "message": result.reason,
        "retryable": result.outcome in {"FAIL", "INCOMPLETE"},
        "cure": result.next_action or None,
    }


def _envelope(
    command: str,
    result: outcome.Result,
    started_at: str,
    finished_at: str,
    error_code: str,
) -> dict:
    return {
        "schema_version": "1",
        "command": command,
        "operation_id": str(uuid.uuid4()),
        "started_at": started_at,
        "finished_at": finished_at,
        "outcome": result.outcome,
        "summary": result.reason,
        "changes": [],
        "checks": [],
        "remaining": [] if result.exit_code == 0 else [result.reason],
        "next_actions": [result.next_action] if result.next_action else [],
        "error": _error(result, error_code),
    }


def _json_dispatch(verb: str, rest: list[str]) -> int:
    """Run one verb without a terminal and expose only a canonical Result as success."""
    started_at = _timestamp()
    captured_out, captured_err = io.StringIO(), io.StringIO()
    previous_stdin = sys.stdin
    result = outcome.result("INCOMPLETE")
    error_code = "UNEXPECTED_ERROR"
    try:
        with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
            from ai_engineering import ui

            ui.reset()
            sys.stdin = io.StringIO("")
            try:
                module = importlib.import_module(f"ai_engineering.{verb}")
                returned = module.main(rest)
                if type(returned) is outcome.Result:
                    result = returned
                    error_code = result.outcome
                else:
                    error_code = "NONCANONICAL_RESULT"
            except KeyboardInterrupt:
                result = outcome.result("CANCELLED")
                error_code = "CANCELLED"
            except BaseException:
                result = outcome.result("INCOMPLETE")
                error_code = "UNEXPECTED_ERROR"
            finally:
                ui.reset()
    finally:
        sys.stdin = previous_stdin

    finished_at = _timestamp()
    payload = _envelope(verb, result, started_at, finished_at, error_code)
    with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
        paths.load("_emit").emit(
            verb,
            "command",
            verb=verb,
            exit=result.exit_code,
            outcome=result.outcome,
        )
    sys.stdout.write(
        json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    speakable()
    argv = list(sys.argv[1:] if argv is None else argv)
    json_flags = argv.count("--json")
    if json_flags > 1:
        sys.stderr.write("ai-eng: --json may be specified once.\n")
        return 2
    json_mode = json_flags == 1
    if json_mode:
        argv.remove("--json")
        if not argv:
            sys.stderr.write("ai-eng: --json requires one canonical verb.\n")
            return 2
    if "--adr" in argv:
        sys.stderr.write("ai-eng: there is no option '--adr'.\n")
        return 2
    if not argv or argv[0] in ("-h", "--help", "help"):
        usage()
        return 0
    if argv[0] in ("-V", "--version", "version"):
        # Plain, one line, no styling and no banner. This is the line another program
        # parses, and it is the only output here that is not for a person.
        sys.stdout.write(f"ai-engineering {__version__}\n")
        return 0

    verb, rest = argv[0], argv[1:]
    if verb not in VERBS:
        # The complaint on stderr, the list on stdout. A typo is not a reason to stop the
        # verb list being pipeable, and it is a reason for the error itself not to be.
        sys.stderr.write(f"ai-eng: there is no verb {verb!r}.\n\n")
        usage()
        return 2

    if json_mode:
        return _json_dispatch(verb, rest)

    module = importlib.import_module(f"ai_engineering.{verb}")
    started = time.perf_counter()
    try:
        returned = module.main(rest)
        if type(returned) is outcome.Result:
            from ai_engineering import ui

            ui.render_result(returned)
            code = returned.exit_code
        else:
            code = int(returned or 0)
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted; nothing was written.\n")
        code = 130
    except wiring.Unreadable as why:
        # One place, because every verb that writes reads first. A file we cannot parse is
        # not an empty file, and the only safe thing to do with one is to stop and name it:
        # the alternative, which this used to do, is to treat it as empty and save over it.
        sys.stderr.write(f"\n{why}\n")
        sys.stderr.write("Nothing was written. Fix that file, or move it aside and re-run.\n")
        paths.load("_emit").emit(verb, "error", error=repr(why))
        code = 2
    except Exception as exc:
        paths.load("_emit").emit(verb, "error", error=repr(exc))
        raise
    paths.load("_emit").emit(
        verb, "command", verb=verb, exit=code, ms=int((time.perf_counter() - started) * 1000)
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
