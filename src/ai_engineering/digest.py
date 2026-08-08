"""The weekly paragraph a person reads.

22.6 MB nobody opened is not observability. This is local, on demand, no dependencies,
and the session hook says one line out loud when it has gone a week unread — because
the reader of this record is a person, and the reminder belongs to the person.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import date, timedelta

from ai_engineering import doctor, paths


def within(events: list[dict], days: int) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return [e for e in events if str(e.get("ts", "")) >= cutoff]


def by_reason(events: list[dict], kind: str) -> Counter:
    return Counter(
        f"{e['name']} — {(e.get('data') or {}).get('reason', '')[:70]}"
        for e in events
        if e.get("cls") == kind
    )


def repeats(events: list[dict]) -> list[str]:
    """Rule 12's trigger, measured rather than felt: the same judgement resolving the
    same way three times or more is owed a script, and the prompt that made it goes away
    in the same commit."""
    seen = Counter(
        f"{e['name']} · {(e.get('data') or {}).get('reason', '')[:50]}"
        for e in events
        if e.get("cls") in ("blocked", "bypassed")
    )
    return [
        f"    {label} {count}× same verdict each time → owed a script"
        for label, count in seen.most_common()
        if count >= 3
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser("ai-eng digest")
    parser.add_argument("--weeks", type=int, default=1)
    args = parser.parse_args(argv)

    root = paths.repo_root()
    events = within(doctor.events(root), 7 * args.weeks)
    sessions = {e.get("session") for e in events}
    blocked = by_reason(events, "blocked")
    bypassed = by_reason(events, "bypassed")
    commands = Counter(e["name"] for e in events if e.get("cls") == "command")
    errors = [e for e in events if e.get("cls") == "error"]

    since = (date.today() - timedelta(days=7 * args.weeks)).isoformat()
    print(f"\nWeek of {since}{'':>30}{len(sessions)} sessions\n")

    print(f"  Blocked {sum(blocked.values())} times:")
    for label, count in blocked.most_common(6):
        print(f"    {count}× {label}")
    if not blocked:
        print("    nothing. Either a quiet week, or a control that is no longer firing —")
        print("    assertion 7 is what tells the two apart.")

    print(f"\n  Bypassed {sum(bypassed.values())} times.")
    for label, count in bypassed.most_common(4):
        print(f"    {count}× {label}")
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

    print(
        "\n  Commands: "
        + ("  ".join(f"{name} {n}" for name, n in commands.most_common()) or "none")
    )
    print(
        f"  Errors: {len(errors)}"
        + (f" (latest: {(errors[-1].get('data') or {}).get('error', '')[:60]})" if errors else "")
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

    print("\n  Coverage — what actually blocks, by surface")
    for line in doctor.coverage(root):
        print(line)

    stamp = paths.home() / "cache" / "digest.json"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(json.dumps({"read": time.time()}))
    return 0
