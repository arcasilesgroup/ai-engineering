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
from datetime import date, timedelta

from ai_engineering import doctor, outcome, paths


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


def main(argv: list[str]) -> outcome.Result | outcome.Execution:
    parser = argparse.ArgumentParser(prog="ai-eng report")
    commands = parser.add_subparsers(dest="command")
    digest = commands.add_parser("digest")
    digest.add_argument("--weeks", type=int, default=1)
    commands.add_parser("issue")
    args = parser.parse_args(argv)

    if args.command is None:
        print(
            "INCOMPLETE: bare report is planned for P2 and is not implemented; "
            "nothing was written or sent.",
            file=sys.stderr,
        )
        return outcome.result("INCOMPLETE")
    if args.command == "issue":
        print(
            "INCOMPLETE: report issue is planned for P2 and is not implemented; "
            "nothing was written or sent.",
            file=sys.stderr,
        )
        return outcome.result("INCOMPLETE")

    root = paths.repo_root()
    events = within(doctor.events(root), 7 * args.weeks)
    sessions = {e.get("session") for e in events}
    blocked = by_reason(events, "blocked")
    bypassed = by_reason(events, "bypassed")
    commands = Counter(e["name"] for e in events if e.get("cls") == "command")
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
            "design_gate",
            "no_verify_guard",
            "self_protect",
        )
        if not any(e["name"] == name and e["cls"] == "blocked" for e in events)
    ]
    if quiet:
        print("\n  Quiet controls — no real block this window; liveness is assertion 7's job:")
        print(f"    {', '.join(quiet)}")

    command_detail = (
        "  ".join(f"{str(name)[:64]} {count}" for name, count in commands.most_common(20)) or "none"
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
