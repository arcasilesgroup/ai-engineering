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
import os
import sys
import time
import traceback
import uuid
from datetime import UTC, datetime
from types import ModuleType

from ai_engineering import __version__, blocked, outcome, paths, solution_intent, wiring

VERBS: dict[str, str] = {
    "init": "Set up this machine, and this repository if you say yes.",
    "doctor": "The 25 assertions and the coverage line. Is the system healthy now?",
    "update": "Rewrite the pin and run the forward migrations.",
    "spec": "spec new | list | show | claim | wave | checkpoint — the record and its coordination.",
    "decide": "Add a decision to the spec, or promote it to an MADR with --madr.",
    "accept": "Accept a finding until a date, with a named owner and a reason.",
    "audit": "audit verify walks the whole chain; audit replay walks a session.",
    # What it does, not what it was going to do. The bare verb returns INCOMPLETE — "planned
    # for P2 and is not implemented" — so a line promising "the local governed report" sent a
    # stranger to a refusal. Three subcommands work today and the summary names them.
    "report": "report digest | issue | surfaces | intent — what this install can show.",
    "exception": "Record a governed design exception, at a keyboard.",
    "uninstall": "Undo everything the receipt lists. The no-lock-in promise, as a command.",
}


# What each verb will touch, said before it touches it. The wording is deliberately about
# classes of destination and never about one machine's paths: a will is read by a person
# deciding whether to continue, and a home directory printed into it is a machine path in
# the record.
#
# The first version of this table said `network: none` for all ten verbs, and a test
# "proved" it by grepping `src/` for an egress import. Both were wrong. `doctor` and
# `report` reach an observability endpoint through `paths.load("_otlp")`, a hook loaded by
# path, which no grep of `src/` can see — so the product opened a socket while the command
# printed that it would not. The lesson is in the test beside this table now: a claim about
# what the product does is checked against every file the product can execute, not against
# the ones the claim's author happened to think of.
SCOPE: dict[str, tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "init": (
        "set this machine up, and this repository if you say yes",
        ("the receipt", "each agent surface's settings"),
        ("the application home", "surface settings", "git config", "this repository's records"),
        (),
    ),
    "doctor": (
        "run the assertions and report what they observed",
        ("the receipt", "surface settings", "this repository's records"),
        ("the files each --fix repairs, when --fix is given",),
        ("the configured observability endpoint, when one is configured",),
    ),
    "update": (
        "rewrite the pin and run the forward migrations",
        ("the pin", "the receipt"),
        ("the pin", "the files each migration names"),
        (),
    ),
    "spec": (
        "record what was decided, or list what already is",
        ("the Intent", "every spec"),
        (
            "one new spec directory, on `spec new` only",
            "one claim ref, on `spec claim` only",
            "the remote-tracking refs a fetch updates, on `spec claim`, `spec checkpoint` "
            "and `spec wave`",
        ),
        # `spec claim` is the only subcommand that reaches a remote, and a will that named
        # no network for the verb that can take a claim would be the exact defect the
        # comment above this table describes: a command that opens a connection while
        # printing that it will not.
        (
            "the git remote a claim is taken against, and the one `spec checkpoint` and "
            "`spec wave` read the claims back from",
        ),
    ),
    "decide": (
        "add a decision to its spec, or promote it to an MADR",
        ("the target spec",),
        ("that spec's decision block, or one MADR",),
        (),
    ),
    "accept": (
        "publish one immutable acceptance record",
        ("the target spec", "the evidence file", "every acceptance already recorded"),
        ("one new acceptance record beside its spec",),
        (),
    ),
    "audit": (
        "walk the chain and say whether it holds",
        ("the chain", "this repository's records"),
        (),
        (),
    ),
    "report": (
        "produce the local governed report",
        ("the events", "this repository's records"),
        ("the local digest read receipt", "the Solution Intent page under docs/"),
        ("the configured observability endpoint, when one is configured",),
    ),
    "exception": (
        "record one design exception, at a keyboard",
        ("the application home", "this repository's records"),
        ("one time-limited grant in the application home",),
        (),
    ),
    "uninstall": (
        "undo everything the receipt lists",
        ("the receipt", "surface settings"),
        ("only what the receipt records this install as having written",),
        (),
    ),
}

# What the dispatcher itself does, in order, once a verb has been resolved. Every one of
# these runs on every invocation, which is what makes the count worth printing: a total the
# run does not reach, or an index past it, is a decoration and `ui.running` refuses it.
STAGES = ("load the verb", "run it", "report the outcome", "record the command")

# One home. `policy/envelope-v1.schema.json` is the contract and this is its name; a test
# reads that file's `$id` against this constant, so the two cannot drift apart quietly.
ENVELOPE_SCHEMA = "urn:ai-engineering:envelope:1"

# Every verb writes this, on every run, whatever else it does or refuses to do. It was
# missing from all ten entries above, which made `writes none` on `audit` a false statement
# about a command that had just appended a line.
ALWAYS_WRITES = "this run's line in the event record"


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


@contextlib.contextmanager
def _silence():
    """Discard child prose without retaining an unbounded or privacy-bearing buffer."""

    with (
        open(os.devnull, "w", encoding="utf-8") as sink,
        contextlib.redirect_stdout(sink),
        contextlib.redirect_stderr(sink),
    ):
        yield


def _envelope(
    command: str,
    execution: outcome.Execution,
    started_at: str,
    finished_at: str,
) -> dict:
    return {
        # The envelope names its own contract. It carried a `schema_version` and no
        # `schema`, which is a version number for a document nobody could find: a reader
        # written against version 1 of *what* had no way to check it was reading the right
        # object, and `policy/` held eight schemas and none for the one thing every verb
        # prints. `outcome-v1` has said both from the start; this is the same rule applied
        # to the envelope that carries it.
        "schema": ENVELOPE_SCHEMA,
        "schema_version": "1",
        "command": command,
        "operation_id": str(uuid.uuid4()),
        "started_at": started_at,
        "finished_at": finished_at,
        "outcome": execution.outcome,
        "summary": execution.summary,
        "changes": [fact.as_dict() for fact in execution.changes],
        "checks": [fact.as_dict() for fact in execution.checks],
        "remaining": list(execution.remaining),
        "next_actions": list(execution.next_actions),
        "error": None if execution.error is None else execution.error.as_dict(),
    }


def _machine_result(
    command: str,
    execution: outcome.Execution,
    started_at: str,
    *,
    emit: bool,
    process_exit: int | None = None,
) -> None:
    """Write the sole JSON object after every child and telemetry stream is closed."""

    if emit:
        with _silence(), contextlib.suppress(BaseException):
            paths.load("_emit").emit(
                command,
                "command",
                verb=command,
                exit=execution.exit_code if process_exit is None else process_exit,
                outcome=execution.outcome,
            )
    finished_at = _timestamp()
    payload = _envelope(command, execution, started_at, finished_at)
    sys.stdout.write(
        json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(",", ":")) + "\n"
    )


def _invalid_json(command: str, message: str, cure: str | None = None) -> int:
    terminal = outcome.result("INCOMPLETE")
    execution = outcome.execution(
        terminal,
        summary=message,
        remaining=[message],
        next_actions=[] if cure is None else [cure],
        execution_error=outcome.error("INVALID_CLI", message, False, cure),
    )
    _machine_result(command, execution, _timestamp(), emit=False)
    return outcome.invalid_cli_exit()


def _global_json(command: str) -> int:
    if command == "help":
        execution = outcome.execution(
            outcome.result("PASS"),
            summary="Ten canonical commands are available",
            checks=[
                outcome.fact(f"command-{verb}", "OBSERVED", verb, description)
                for verb, description in VERBS.items()
            ],
            next_actions=["run one canonical command with its required arguments"],
        )
    else:
        execution = outcome.execution(
            outcome.result("PASS"),
            summary=f"ai-engineering {__version__}",
            checks=[outcome.fact("version", "OBSERVED", "Installed version", __version__)],
            next_actions=["run ai-eng --help to list canonical commands"],
        )
    _machine_result(command, execution, _timestamp(), emit=False)
    return 0


def _json_dispatch(verb: str, rest: list[str], *, debug: bool = False) -> int:
    """Run one verb without a terminal and retain only its bounded structured facts."""
    started_at = _timestamp()
    previous_stdin = sys.stdin
    terminal = outcome.result("INCOMPLETE")
    execution = outcome.execution(
        terminal,
        execution_error=outcome.error(
            "UNEXPECTED_ERROR", "The command did not produce a terminal result", False
        ),
    )
    process_exit = terminal.exit_code
    # Declared before the try so the `finally` below can still reset a console that was
    # built, and named apart from the module so that "not imported yet" and "the renderer"
    # are two things rather than one name meaning both.
    renderer: ModuleType | None = None
    # The real stderr, held before `_silence` swaps it for /dev/null. Without this the
    # `--debug` traceback below is written into the sink along with the child's prose, and
    # the flag whose only job is to show a person what happened shows them nothing — a
    # control that reads stronger than it is, in the one place a person looks when
    # something has already gone wrong.
    reachable = sys.stderr
    try:
        with _silence():
            from ai_engineering import ui

            renderer = ui
            renderer.reset()
            sys.stdin = io.StringIO("")
            try:
                module = importlib.import_module(f"ai_engineering.{verb}")
                returned = module.main(rest)
                if type(returned) is outcome.Execution:
                    execution = returned
                elif type(returned) is outcome.Result:
                    execution = outcome.execution(returned)
                else:
                    execution = outcome.execution(
                        outcome.result("INCOMPLETE"),
                        summary="The command returned a noncanonical result",
                        execution_error=outcome.error(
                            "NONCANONICAL_RESULT",
                            "The command returned a noncanonical result",
                            False,
                        ),
                    )
                process_exit = execution.exit_code
            except SystemExit as stopped:
                if stopped.code in (None, 0):
                    execution = outcome.execution(
                        outcome.result("PASS"),
                        summary=f"Help requested for {verb}",
                        checks=[outcome.fact("help", "OBSERVED", f"Help requested for {verb}")],
                        next_actions=[f"run ai-eng {verb} with valid arguments"],
                    )
                    process_exit = 0
                elif stopped.code == outcome.invalid_cli_exit():
                    message = f"Invalid arguments for {verb}"
                    cure = f"run ai-eng {verb} --help"
                    execution = outcome.execution(
                        outcome.result("INCOMPLETE"),
                        summary=message,
                        remaining=[message],
                        next_actions=[cure],
                        execution_error=outcome.error("INVALID_CLI", message, False, cure),
                    )
                    process_exit = outcome.invalid_cli_exit()
                else:
                    execution = outcome.execution(
                        outcome.result("INCOMPLETE"),
                        summary="The command stopped without a canonical terminal result",
                        execution_error=outcome.error(
                            "UNEXPECTED_ERROR",
                            "The command stopped without a canonical terminal result",
                            False,
                        ),
                    )
                    process_exit = execution.exit_code
            except KeyboardInterrupt:
                execution = outcome.execution(outcome.result("CANCELLED"))
                process_exit = execution.exit_code
            except BaseException:
                if debug:
                    traceback.print_exc(file=reachable)
                execution = outcome.execution(
                    outcome.result("INCOMPLETE"),
                    summary="The command failed before producing bounded execution facts",
                    execution_error=outcome.error(
                        "UNEXPECTED_ERROR",
                        "The command failed before producing bounded execution facts",
                        False,
                    ),
                )
                process_exit = execution.exit_code
            finally:
                with contextlib.suppress(BaseException):
                    if renderer is not None:
                        renderer.reset()
    except KeyboardInterrupt:
        execution = outcome.execution(outcome.result("CANCELLED"))
        process_exit = execution.exit_code
    except BaseException:
        if debug:
            traceback.print_exc()
        execution = outcome.execution(
            outcome.result("INCOMPLETE"),
            summary="The command failed before its execution boundary was available",
            execution_error=outcome.error(
                "UNEXPECTED_ERROR",
                "The command failed before its execution boundary was available",
                False,
            ),
        )
        process_exit = execution.exit_code
    finally:
        sys.stdin = previous_stdin

    _machine_result(verb, execution, started_at, emit=True, process_exit=process_exit)
    return process_exit


UNEXPECTED = "The command failed before producing bounded execution facts"


def crash(exc: BaseException, *, debug: bool) -> outcome.Error:
    """One bounded error for an unexpected failure, or the traceback if it was asked for.

    A traceback is the fastest way to put an absolute path, a username and the shape of
    somebody's filesystem onto a screen that is about to be pasted into an issue, so it is
    printed on request and never by default. The exception reaches the event record either
    way; what `--debug` changes is what a person sees.
    """

    if debug:
        raise exc
    return outcome.error("UNEXPECTED_ERROR", UNEXPECTED, False, "rerun with --debug for the trace")


def main(argv: list[str] | None = None) -> int:
    speakable()
    argv = list(sys.argv[1:] if argv is None else argv)
    # Both are global and both are stripped here, exactly as `--json` is: a verb that had to
    # know about either is a verb that can disagree with the next one about what it means.
    debug = "--debug" in argv
    if "--non-interactive" in argv:
        from ai_engineering import accept

        accept.NON_INTERACTIVE = True
    argv = [flag for flag in argv if flag not in ("--debug", "--non-interactive")]
    json_flags = argv.count("--json")
    json_mode = json_flags > 0
    if json_mode:
        argv = [argument for argument in argv if argument != "--json"]
        if json_flags > 1:
            return _invalid_json("ai-eng", "--json may be specified once")
        if not argv:
            return _invalid_json(
                "ai-eng", "JSON mode requires one canonical command", "run ai-eng --json --help"
            )
        if "--adr" in argv:
            return _invalid_json(
                "invalid", "The option --adr does not exist", "run ai-eng --json --help"
            )
        if argv[0] in ("-h", "--help", "help"):
            return _global_json("help")
        if argv[0] in ("-V", "--version", "version"):
            return _global_json("version")
        verb, rest = argv[0], argv[1:]
        if verb not in VERBS:
            return _invalid_json("invalid", "Unknown command", "run ai-eng --json --help")
        return _json_dispatch(verb, rest, debug=debug)
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

    from ai_engineering import ui

    # The will goes out before the verb is even loaded, so a person who reads it and stops
    # has stopped before anything happened. It goes to stderr with everything else a person
    # reads on the way past; stdout stays reserved for the one JSON object in JSON mode.
    action, reads, writes, network = SCOPE[verb]
    # Not for `--help`, which prints the flags and exits without doing any of this. A will
    # is a promise about a run, and a promise about a run that never happens is noise a
    # person learns to skip — which is how the real one stops being read.
    helping = any(flag in rest for flag in ("-h", "--help"))
    if not helping:
        ui.will(action, reads, (*writes, ALWAYS_WRITES), network)
    reached = 1
    if not helping:
        ui.running(reached, len(STAGES), STAGES[0])
    module = importlib.import_module(f"ai_engineering.{verb}")
    started = time.perf_counter()
    interrupted = False
    try:
        reached = 2
        if not helping:
            ui.running(reached, len(STAGES), f"{STAGES[1]}: {verb}")
        returned = module.main(rest)
        reached = 3
        if not helping:
            ui.running(reached, len(STAGES), STAGES[2])
        if type(returned) in (outcome.Result, outcome.Execution):
            terminal = returned.result if type(returned) is outcome.Execution else returned
            ui.render_result(terminal)
            code = returned.exit_code
        else:
            code = int(returned or 0)
    except KeyboardInterrupt:
        # Said after the last stage rather than here, so it is the last thing on the screen.
        # A person who pressed Ctrl-C is asking one question, and the answer to it should not
        # be followed by two more lines of bookkeeping.
        interrupted = True
        code = 130
    except (wiring.Unreadable, blocked.Unreadable, solution_intent.Unreadable) as why:
        # One place, because every verb that writes reads first. A file we cannot parse is
        # not an empty file, and the only safe thing to do with one is to stop and name it:
        # the alternative, which this used to do, is to treat it as empty and save over it.
        #
        # Three classes, not one. The two added here are the same condition in two more
        # readers, and reaching the handler below instead printed UNEXPECTED_ERROR over a
        # refusal the code named on purpose — "rerun with --debug for the trace" for a file
        # the operator has to go and fix.
        sys.stderr.write(f"\n{why}\n")
        sys.stderr.write("Nothing was written. Fix that file, or move it aside and re-run.\n")
        paths.load("_emit").emit(verb, "error", error=repr(why))
        code = 2
    except Exception as exc:
        paths.load("_emit").emit(verb, "error", error=repr(exc))
        failure = crash(exc, debug=debug)
        sys.stderr.write(
            f"\n✗ {failure.code}\n{failure.message}\n"
            f"Retryable: {'yes' if failure.retryable else 'no'}\nNext action: {failure.cure}\n"
        )
        code = outcome.result("INCOMPLETE").exit_code
    # The index is where the run actually reached, not the length of the list. A run that
    # was interrupted before its outcome could be reported did not perform four stages, and
    # printing 4/4 over three would make the count a decoration again.
    reached += 1
    if not helping:
        ui.running(reached, len(STAGES), STAGES[3])
    paths.load("_emit").emit(
        verb, "command", verb=verb, exit=code, ms=int((time.perf_counter() - started) * 1000)
    )
    if interrupted:
        sys.stderr.write("\ninterrupted; nothing was written.\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
