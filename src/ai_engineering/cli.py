"""Ten verbs, and the only way to run any of them.

Not six, which cannot express a dated risk acceptance signed by a named person, and not
seventy, which nobody can hold in their head. The table below is the whole surface, and
it is also what emits: an entry point does not exist until it is in this table, and this
table records that it ran.
"""

from __future__ import annotations

import importlib
import sys
import time

from ai_engineering import __version__, paths

VERBS: dict[str, str] = {
    "init": "Set up this machine, and this repository if you say yes.",
    "doctor": "The 20 assertions and the coverage line. Is the system healthy now?",
    "update": "Rewrite the pin and run the forward migrations.",
    "spec": "spec new | spec list | spec show — the record of what was decided.",
    "decide": "Add a decision to the spec, or promote it to an ADR with --adr.",
    "accept": "Accept a finding until a date, with a named owner and a reason.",
    "audit": "audit verify walks the whole chain; audit replay walks a session.",
    "digest": "The weekly paragraph a person reads.",
    "plan": 'plan --skip "<reason>" — record a design exception, at a keyboard.',
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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
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

    module = importlib.import_module(f"ai_engineering.{verb}")
    started = time.perf_counter()
    try:
        code = int(module.main(rest) or 0)
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted; nothing was written.\n")
        code = 130
    except Exception as exc:
        paths.load("_emit").emit(verb, "error", error=repr(exc))
        raise
    paths.load("_emit").emit(
        verb, "command", verb=verb, exit=code, ms=int((time.perf_counter() - started) * 1000)
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
