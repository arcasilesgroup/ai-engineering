"""The weekly paragraph a person reads.

22.6 MB nobody opened is not observability. This is local, on demand, no dependencies,
and the session hook says one line out loud when it has gone a week unread — because
the reader of this record is a person, and the reminder belongs to the person.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from ai_engineering import (
    accept,
    doctor,
    issue,
    outcome,
    paths,
    solution_intent,
    surface,
)
from ai_engineering import (
    blocked as ledger,
)


def within(events: list[dict], days: int) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return [e for e in events if str(e.get("ts", "")) >= cutoff]


def by_reason(events: list[dict], kind: str) -> Counter:
    return Counter(
        f"{str(e['name'])[:64]} — {str((e.get('data') or {}).get('reason', ''))[:70]}"
        for e in events
        if e.get("cls") == kind
    )


# The two numbers this file decides anything with, named rather than typed twice.
#
# `EP-057` asks for a stated prohibition and a numeric threshold for the same rule, and the
# audit found fourteen prohibitions carrying no number. These two carry one, and both were
# bare literals in the middle of a function — which is how a threshold changes without
# anybody arguing for it. `policy/pilot-register.toml` declares them beside the sentence each
# enforces, and `tests/test_pilot_register.py` refuses a register whose number and this
# file's have drifted apart.
#
# Rule 12's three: "The third time the same judgement resolves the same way it becomes a
# script." Three is the smallest count that is a pattern rather than a coincidence.
OWED_A_SCRIPT = 3
# And the bypass count, which is a different sentence about the same shape: a guard walked
# past three times is a guard to fix or to delete, because the fourth walk-past is somebody
# deciding the rule does not apply to them and being right.
BYPASSES_WORTH_A_LOOK = 3


def by_guard(events: list[dict], kind: str) -> Counter:
    """The same denials, counted per guard rather than per guard-and-reason.

    `by_reason` groups on the pair, which is the right key for "what keeps getting stopped"
    and the wrong one for "which control is doing the work". A guard that denied five calls
    for five different reasons appears there as five rows of one, and reads as five quiet
    controls rather than one busy one — the opposite of what happened.

    Both are printed, over the same window, because the two questions have different
    answers and a reader who only sees the pair cannot recover this from it.
    """

    return Counter(str(e["name"])[:64] for e in events if e.get("cls") == kind)


def _verdict_counts(events: list[dict]) -> Counter:
    """One key per judgement-and-reason, so two refusals for different reasons stay two."""

    return Counter(
        f"{str(e['name'])[:64]} · {str((e.get('data') or {}).get('reason', ''))[:50]}"
        for e in events
        if e.get("cls") in ("blocked", "bypassed")
    )


def repeats(events: list[dict]) -> list[str]:
    """Rule 12's trigger, measured rather than felt: the same judgement resolving the
    same way three times or more is owed a script, and the prompt that made it goes away
    in the same commit."""
    seen = _verdict_counts(events)
    return [
        f"    {label} {count}× same verdict each time → owed a script"
        for label, count in seen.most_common()
        if count >= OWED_A_SCRIPT
    ]


def measured_repeats(events: list[dict]) -> tuple[list[str], int, int]:
    """`repeats`, plus what it measured to get there.

    The rows alone cannot say whether the window was empty, and an empty window is the
    ordinary case — so the ordinary case looked exactly like the check not existing. Returning
    the count and the highest repetition lets the caller print a rule that is running even on
    the days it has nothing to say, which is most of them.
    """

    seen = _verdict_counts(events)
    return repeats(events), len(seen), (seen.most_common(1)[0][1] if seen else 0)


def surfaces(root: Path | None) -> outcome.Result:
    """The three states of every surface, with the age of each proof beside it.

    A subcommand and not an eleventh verb. `report` already exists to produce the local
    governed report, already carries subcommands, and its declared scope already covers
    reading this repository's records — so the exit criterion is answered without a
    doctrine change, without touching the two assertions that pin exactly ten verbs, and
    without changing what the installed wheel counts.

    Nothing here is invented. A state with no receipt prints as unproven, and one unproven
    state anywhere makes the whole answer INCOMPLETE: a surface is not proved by the one
    question somebody got round to answering."""

    if root is None:
        print("  INCOMPLETE: not inside a repository, so there are no receipts to read")
        return outcome.result("INCOMPLETE")

    report = surface.read(root, now=datetime.now(UTC))
    for row in report.rows:
        aged = "" if row.age_seconds is None else f"  {row.age_seconds}s"
        print(f"  {row.outcome:<11} {row.surface:<16} {row.state:<12} {row.code}{aged}")
    return report.result


def submit(payload: dict, written: Path) -> outcome.Execution:
    """Ask the keyboard, and then say where this would have gone.

    Two refusals, in this order. The person has to type the phrase carrying this payload's
    digest at the controlling terminal — not stdin, not a flag, not an environment variable,
    because a script can supply all three. And then there is nowhere to send: no destination
    is configured and this package has no transport. That is INCOMPLETE naming the thing
    that is missing, not PASS for work that did not happen.
    """

    phrase = issue.confirmation(payload)
    print(f"\n  To send this exact payload, type: {phrase}")
    if not accept.controlling_terminal_response(phrase):
        return outcome.execution(
            outcome.result("INCOMPLETE"),
            summary="Not confirmed at the keyboard; the draft is on disk and nothing was sent",
            checks=[
                outcome.fact(
                    "consent",
                    "INCOMPLETE",
                    "Typed confirmation",
                    "ISSUE_SUBMIT_NOT_CONFIRMED",
                    cure=f"rerun and type {phrase} at a terminal",
                )
            ],
            remaining=[f"The draft is at {written.name} and has not been sent"],
        )
    return outcome.execution(
        outcome.result("INCOMPLETE"),
        summary="Confirmed, and there is nowhere to send it: no destination is configured",
        checks=[
            outcome.fact(
                "consent", "PASS", "Typed confirmation", "confirmed at the controlling terminal"
            ),
            outcome.fact(
                "destination",
                "INCOMPLETE",
                "Submission destination",
                "ISSUE_SUBMIT_NO_DESTINATION",
                cure="send the previewed bytes yourself, by the route your organisation uses",
            ),
        ],
        remaining=[f"Nothing left this machine. The exact bytes are at {written.name}"],
    )


def report_issue(root: Path | None, args: argparse.Namespace) -> outcome.Result | outcome.Execution:
    """Draft one governed report, locally, and send nothing.

    The order is the whole control: build from the allow-list, scan the exact bytes, and
    only then write and show them. A refusal names the class it found and leaves no file,
    because the artefact a person can still send is the one that matters.
    """

    if root is None:
        print("  INCOMPLETE: not inside a repository, so there is nowhere to keep a draft")
        return outcome.result("INCOMPLETE")

    payload = issue.build(
        kind=args.kind,
        title=args.title,
        what_happened=args.what_happened,
        expected=args.expected,
        steps=args.step,
    )
    refused = issue.scan(root, payload)
    if refused:
        for finding in refused:
            print(f"  {finding.outcome:<11} {finding.code}: {finding.reason}")
        return outcome.execution(
            outcome.result("INCOMPLETE"),
            summary=f"{len(refused)} finding(s) stopped this report; nothing was written or sent",
            checks=[
                outcome.fact(
                    f"scan-{index}",
                    "FAIL" if finding.outcome == "FAIL" else "INCOMPLETE",
                    "Payload scan",
                    finding.reason,
                    cure="rewrite the field in your own words, without the value it carried",
                )
                for index, finding in enumerate(refused, 1)
            ],
            remaining=[finding.code for finding in refused],
        )

    if args.submit and payload["kind"] == "security":
        # Before the terminal, not after. A control that asks first and refuses second has
        # already put the wrong route in front of somebody at the end of a long day.
        print(f"  INCOMPLETE: a vulnerability never becomes a public issue. {issue.PRIVATE_ROUTE}")
        return outcome.execution(
            outcome.result("INCOMPLETE"),
            summary="A security finding routes to private disclosure; nothing was written",
            checks=[
                outcome.fact(
                    "route",
                    "INCOMPLETE",
                    "Disclosure route",
                    "ISSUE_SECURITY_ROUTE_IS_PRIVATE",
                    cure=f"report it privately: {issue.PRIVATE_ROUTE}",
                )
            ],
            remaining=[f"Disclose privately: {issue.PRIVATE_ROUTE}"],
        )

    written = issue.draft(root, payload)
    if args.submit:
        return submit(payload, written)
    return outcome.execution(
        outcome.result("PASS"),
        summary=f"Drafted a {payload['kind']} report locally; nothing has been sent",
        changes=[
            outcome.fact("issue-draft", "APPLIED", "Wrote the local draft", str(written.name))
        ],
        checks=[
            outcome.fact("scan", "PASS", "Payload scan", "no forbidden class in the exact bytes"),
            outcome.fact("digest", "OBSERVED", "Payload digest", issue.digest(payload)),
        ],
        remaining=["Nothing has been sent. Sending is a separate action a person confirms."],
    )


def _filled(value: str) -> str:
    """A flag that was given a value rather than an empty one.

    `required=True` checks presence, and `--what ""` is present. It produced a PASS over a
    row the collector then refused — a result claimed that the code did not observe.
    """

    if not value.strip():
        raise argparse.ArgumentTypeError("this cannot be blank")
    return value.strip()


def _said(value: str) -> str:
    """The fourth field, held to the rule the specification wrote it for.

    `--action TODO` is present and useless, and the placeholder check belongs here rather
    than on all four flags: the rule is about what would unstick the halt, and applying it to
    `--what` meant a run could not say "Todos los gates de 020 estan rojos" — ordinary
    Spanish for "all" — so the recorder crashed on the halt it exists to record.
    """

    if not ledger.usable(value):
        raise argparse.ArgumentTypeError(
            f"{value!r} says nothing a reader could act on; write what would unstick it"
        )
    return value.strip()


def record_stop(root: Path | None, args: argparse.Namespace) -> outcome.Result:
    """Write the halt down before halting.

    Every refusal here returns rather than raises. This runs when a build is already failing,
    and a recorder that throws while recording a stop turns a halt into a crash — the crash
    being what the person then reads instead of the record.
    """

    if root is None:
        print("  INCOMPLETE  this is not a git repository, so there is nowhere to record it")
        return outcome.result("INCOMPLETE")
    try:
        where = ledger.record(
            root, what=args.what, why=args.why, action=args.action, since=args.since
        )
    except (OSError, UnicodeEncodeError, ledger.Unreadable) as refused:
        # The path is relative even here. This message is the one people paste into issues,
        # and the PASS branch below already knew that.
        # `strerror`, not the exception. An OSError renders with the absolute filename it
        # failed on, and this message is the one people paste into issues.
        why = getattr(refused, "strerror", None) or type(refused).__name__
        print(f"  INCOMPLETE  {ledger.LEDGER.as_posix()} could not be written: {why}")
        return outcome.result("INCOMPLETE")
    print(f"  recorded in {where.relative_to(root)}")
    print(f"    {args.what}")
    print(f"    since {args.since} — {args.why}")
    print(f"    {args.action}")
    # Said here because the alternative is finding out from a red gate. The page carries a
    # digest of every record it was built from, so a new row makes the committed page stale
    # and `just check` fails on the next run — correctly, and for a reason nobody would guess
    # from a halt they recorded an hour earlier.
    print("  next: ai-eng report intent --html, so the page shows it")
    return outcome.result("PASS")


def main(argv: list[str]) -> outcome.Result | outcome.Execution:
    parser = argparse.ArgumentParser(prog="ai-eng report")
    commands = parser.add_subparsers(dest="command")
    digest = commands.add_parser("digest")
    digest.add_argument("--weeks", type=int, default=1)
    report = commands.add_parser("issue")
    report.add_argument("--kind", choices=issue.KINDS, required=True)
    report.add_argument("--title", required=True)
    report.add_argument("--what-happened", dest="what_happened", required=True)
    report.add_argument("--expected", required=True)
    report.add_argument("--step", action="append", default=[], required=True)
    report.add_argument("--submit", action="store_true")
    commands.add_parser("surfaces")
    # `--html` is required rather than defaulted, because the only thing this writes is an
    # HTML page and a bare `report intent` that silently wrote one would be a verb doing
    # something the caller did not name.
    page = commands.add_parser("intent")
    page.add_argument("--html", action="store_true", required=True)
    # Three required, and the third is the reason this exists. A run that can say it stopped
    # but not what would unstick it has recorded a complaint, and the section this feeds
    # refuses complaints. `--since` defaults because a halt happening now is the ordinary
    # case and the field is only interesting when a record is being backfilled.
    halt = commands.add_parser("blocked")
    for flag in ("--what", "--why"):
        halt.add_argument(flag, required=True, type=_filled)
    halt.add_argument("--action", required=True, type=_said)
    halt.add_argument("--since", default=date.today().isoformat(), type=_filled)
    args = parser.parse_args(argv)

    if args.command == "blocked":
        return record_stop(paths.repo_root(), args)

    if args.command == "surfaces":
        return surfaces(paths.repo_root())
    if args.command == "intent":
        root = paths.repo_root()
        if root is None:
            # Not a repository, so there are no records to render and nothing to render
            # them about. The page is a reading of a tree; without one it would be a file
            # asserting things about nothing.
            print("  INCOMPLETE  this is not a git repository, so there is no tree to read")
            return outcome.result("INCOMPLETE")
        written = solution_intent.write(root)
        print(f"  wrote {written.relative_to(root)}")
        return outcome.result("PASS")
    if args.command is None:
        print(
            "INCOMPLETE: bare report is planned for P2 and is not implemented; "
            "nothing was written or sent.",
            file=sys.stderr,
        )
        return outcome.result("INCOMPLETE")
    if args.command == "issue":
        return report_issue(paths.repo_root(), args)

    root = paths.repo_root()
    events = within(doctor.events(root), 7 * args.weeks)
    sessions = {e.get("session") for e in events}
    # Not `blocked`: this module now imports the ledger of the same name, and a local
    # binding anywhere in this function would shadow it everywhere in this function.
    blocked_calls = by_reason(events, "blocked")
    bypassed = by_reason(events, "bypassed")
    seen_commands = Counter(e["name"] for e in events if e.get("cls") == "command")
    errors = [e for e in events if e.get("cls") == "error"]
    check_facts = [
        outcome.fact("sessions", "OBSERVED", "Sessions observed", str(len(sessions))),
        outcome.fact("blocked", "OBSERVED", "Calls blocked", str(sum(blocked_calls.values()))),
        outcome.fact("bypassed", "OBSERVED", "Guard bypasses", str(sum(bypassed.values()))),
    ]

    since = (date.today() - timedelta(days=7 * args.weeks)).isoformat()
    print(f"\nWeek of {since}{'':>30}{len(sessions)} sessions\n")

    print(f"  Blocked {sum(blocked_calls.values())} times:")
    for label, count in blocked_calls.most_common(6):
        print(f"    {count}× {label}")
        check_facts.append(
            outcome.fact(
                f"blocked-{len(check_facts)}", "OBSERVED", "Blocked call", f"{count}× {label}"
            )
        )
    if not blocked_calls:
        print("    nothing. Either a quiet week, or a control that is no longer firing —")
        print("    assertion 7 is what tells the two apart.")

    # Per guard, over the same window. The list above is keyed on guard-and-reason, so a
    # guard that stopped five different things shows there as five rows of one.
    per_guard = by_guard(events, "blocked")
    if per_guard:
        detail = "  ".join(f"{name} {count}" for name, count in per_guard.most_common())
        print(f"\n  Per guard, in the {7 * args.weeks} days since {since}: {detail}")
        check_facts.append(
            outcome.fact("blocked-per-guard", "OBSERVED", "Denials per guard", detail)
        )

    print(f"\n  Bypassed {sum(bypassed.values())} times.")
    for label, count in bypassed.most_common(4):
        print(f"    {count}× {label}")
        check_facts.append(
            outcome.fact(
                f"bypassed-{len(check_facts)}",
                "OBSERVED",
                "Bypassed call",
                f"{count}× {label}",
            )
        )
    if sum(bypassed.values()) >= BYPASSES_WORTH_A_LOOK:
        print("    A guard you bypass three times is a guard to fix or to delete.")

    quiet = [
        name
        for name in (
            "injection_guard",
            "loop_guard",
            "no_verify_guard",
            "self_protect",
        )
        if not any(e["name"] == name and e["cls"] == "blocked" for e in events)
    ]
    if quiet:
        print("\n  Quiet controls — no real block this window; liveness is assertion 7's job:")
        print(f"    {', '.join(quiet)}")

    command_detail = (
        "  ".join(f"{str(name)[:64]} {count}" for name, count in seen_commands.most_common(20))
        or "none"
    )
    print("\n  Commands: " + command_detail)
    check_facts.append(outcome.fact("commands", "OBSERVED", "Commands observed", command_detail))
    error_detail = (
        f"latest: {(errors[-1].get('data') or {}).get('error', '')[:60]}" if errors else None
    )
    print(f"  Errors: {len(errors)}" + (f" ({error_detail})" if error_detail else ""))
    check_facts.append(
        outcome.fact("errors", "WARN" if errors else "PASS", "Command errors", str(len(errors)))
    )

    rows, counted, highest = measured_repeats(events)
    # Printed on every run, including the runs with nothing to report. It used to print only
    # when a judgement had crossed the threshold, so a reader could not tell rule 12 measured
    # and found nothing from rule 12 never having been measured — the two produce identical
    # silence, and one of them is a rule that is not running.
    print(
        f"\n  Rule 12 — {counted} judgement(s) counted in this window, "
        f"the most repeated {highest}×, owed a script at {OWED_A_SCRIPT}×:"
    )
    print("\n".join(rows) if rows else "    none has crossed it")

    settings = paths.load("_emit").config(root).get("observability", {})
    if settings.get("endpoint"):
        ok, detail = paths.load("_otlp").probe()
        print(
            f"\n  Sink: {settings.get('provider') or 'configured'} · {detail}"
            f"{'' if ok else '  ← nothing is arriving'}"
        )
        check_facts.append(
            outcome.fact("sink", "PASS" if ok else "WARN", "Observability sink", detail)
        )

    print("\n  Coverage — what actually blocks, by surface")
    coverage_lines = doctor.coverage(root)
    for index, line in enumerate(coverage_lines, 1):
        print(line)
        status = (
            "FAIL"
            if "MISMATCH" in line
            else "WARN"
            if any(word in line for word in ("INERT", "UNPROVEN", "OPEN"))
            else "PASS"
            if any(word in line for word in ("BLOCKS", "OK"))
            else "OBSERVED"
        )
        check_facts.append(outcome.fact(f"coverage-{index}", status, "Surface coverage", line))

    stamp = paths.home() / "cache" / "digest.json"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(json.dumps({"read": time.time()}))
    remaining = [
        *(f"No observed block for {name} in this window" for name in quiet),
        *(row.strip() for row in rows),
        *([f"Inspect {len(errors)} command error(s)"] if errors else []),
    ]
    return outcome.execution(
        outcome.result("PASS"),
        summary=(
            f"Digest since {since}: {len(sessions)} sessions, "
            f"{sum(blocked_calls.values())} blocked, {sum(bypassed.values())} bypassed "
            f"and {len(errors)} errors"
        ),
        changes=[
            outcome.fact("digest-read-receipt", "APPLIED", "Updated the local digest read receipt")
        ],
        checks=check_facts,
        remaining=remaining,
    )
