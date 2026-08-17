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

from ai_engineering import accept, doctor, issue, outcome, paths, surface


def within(events: list[dict], days: int) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return [e for e in events if str(e.get("ts", "")) >= cutoff]


def by_reason(events: list[dict], kind: str) -> Counter:
    return Counter(
        f"{str(e['name'])[:64]} — {str((e.get('data') or {}).get('reason', ''))[:70]}"
        for e in events
        if e.get("cls") == kind
    )


def repeats(events: list[dict]) -> list[str]:
    """Rule 12's trigger, measured rather than felt: the same judgement resolving the
    same way three times or more is owed a script, and the prompt that made it goes away
    in the same commit."""
    seen = Counter(
        f"{str(e['name'])[:64]} · {str((e.get('data') or {}).get('reason', ''))[:50]}"
        for e in events
        if e.get("cls") in ("blocked", "bypassed")
    )
    return [
        f"    {label} {count}× same verdict each time → owed a script"
        for label, count in seen.most_common()
        if count >= 3
    ]


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
    args = parser.parse_args(argv)

    if args.command == "surfaces":
        return surfaces(paths.repo_root())
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
    blocked = by_reason(events, "blocked")
    bypassed = by_reason(events, "bypassed")
    seen_commands = Counter(e["name"] for e in events if e.get("cls") == "command")
    errors = [e for e in events if e.get("cls") == "error"]
    check_facts = [
        outcome.fact("sessions", "OBSERVED", "Sessions observed", str(len(sessions))),
        outcome.fact("blocked", "OBSERVED", "Calls blocked", str(sum(blocked.values()))),
        outcome.fact("bypassed", "OBSERVED", "Guard bypasses", str(sum(bypassed.values()))),
    ]

    since = (date.today() - timedelta(days=7 * args.weeks)).isoformat()
    print(f"\nWeek of {since}{'':>30}{len(sessions)} sessions\n")

    print(f"  Blocked {sum(blocked.values())} times:")
    for label, count in blocked.most_common(6):
        print(f"    {count}× {label}")
        check_facts.append(
            outcome.fact(
                f"blocked-{len(check_facts)}", "OBSERVED", "Blocked call", f"{count}× {label}"
            )
        )
    if not blocked:
        print("    nothing. Either a quiet week, or a control that is no longer firing —")
        print("    assertion 7 is what tells the two apart.")

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
    if sum(bypassed.values()) >= 3:
        print("    A guard you bypass three times is a guard to fix or to delete.")

    quiet = [
        name
        for name in (
            "injection_guard",
            "loop_guard",
            "change_scope_guard",
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

    rows = repeats(events)
    if rows:
        print("\n  Rule 12 — the same judgement, three times or more:")
        print("\n".join(rows))

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
            f"Digest since {since}: {len(sessions)} sessions, {sum(blocked.values())} blocked, "
            f"{sum(bypassed.values())} bypassed and {len(errors)} errors"
        ),
        changes=[
            outcome.fact("digest-read-receipt", "APPLIED", "Updated the local digest read receipt")
        ],
        checks=check_facts,
        remaining=remaining,
    )
