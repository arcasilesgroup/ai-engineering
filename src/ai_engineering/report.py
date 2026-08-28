"""The weekly paragraph a person reads.

22.6 MB nobody opened is not observability. This is local, on demand, no dependencies,
and the session hook says one line out loud when it has gone a week unread — because
the reader of this record is a person, and the reminder belongs to the person.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from ai_engineering import (
    accept,
    contract,
    doctor,
    issue,
    outcome,
    pages,
    paths,
    solution_intent,
    spec,
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

    return Counter(_verdict_key(e) for e in events if e.get("cls") in ("blocked", "bypassed"))


def _verdict_key(e: dict) -> str:
    """The key `_verdict_counts` assigns one denial — shared so two counters can subtract."""

    return f"{str(e['name'])[:64]} · {str((e.get('data') or {}).get('reason', ''))[:50]}"


def _scripted(events: list[dict]) -> Counter:
    """Rule 12's output, not its debt: denials the guard itself marked as the escalation
    (loop_guard's rule-12 moment, spec 042 / B-042-4). Keyed exactly like `_verdict_counts`
    so `repeats` can subtract the scripted judgements from the owed-ones pool, then print
    them relabelled — the escalation *is* the script the rule owes, and re-flagging it as
    a fresh debt would be the same judgement counted twice."""

    return Counter(
        _verdict_key(e)
        for e in events
        if e.get("cls") in ("blocked", "bypassed") and (e.get("data") or {}).get("escalated")
    )


def repeats(events: list[dict]) -> list[str]:
    """Rule 12's trigger, measured rather than felt: the same judgement resolving the
    same way three times or more is owed a script, and the prompt that made it goes away
    in the same commit. A judgement the guard already escalated is the script, not the
    debt, so it prints as scripted rather than owed."""
    scripted = _scripted(events)
    owed = _verdict_counts(events) - scripted
    rows = [
        f"    {label} {count}× same verdict each time → owed a script"
        for label, count in owed.most_common()
        if count >= OWED_A_SCRIPT
    ]
    rows += [
        f"    {label[:64]} {count}× → the script the guard owes (already escalated)"
        for label, count in scripted.most_common()
        if count >= OWED_A_SCRIPT
    ]
    return rows


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


# ---------------------------------------------------------------------------
# The visual records of specification 046: `report view` and `report recap`.
# ---------------------------------------------------------------------------

_SECRET_SHAPES = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|private[_-]?key)"
    r"(\s*[:=]\s*)([^\s\"']{8,})"
)
_PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")


def redact(text: str) -> str:
    """The last gate before a diff excerpt reaches a page. gitleaks guards commits;
    this guards the rendered view of one, because a page can be opened by a person
    whose machine has no scanner and whose clipboard has no redaction.
    """

    text = _PEM.sub("[redacted private key]", text)
    return _SECRET_SHAPES.sub(lambda hit: f"{hit.group(1)}{hit.group(2)}[redacted]", text)


def _spec_home(root: Path, wanted: str) -> Path | None:
    """The one directory whose identifier is `wanted`, or None, said loudly."""

    for folder in sorted((root / "specs").glob("*/")):
        if folder.name[:3] == wanted.zfill(3) and (folder / spec.SPEC_FILE).is_file():
            return folder
    print(f"  INCOMPLETE  no spec {wanted.zfill(3)} under specs/, so there is nothing to render")
    return None


def render_view(root: Path, args: argparse.Namespace) -> outcome.Result:
    """The spec and plan of one record as one self-contained review page.

    The page is a view, never an approval: it prints the canonical digests of the exact
    bytes it rendered — the same numbers `_digest` computes and the ADR signs — so a
    stale page is identifiable from its own header, and regenerating it is one command.
    Two runs over unchanged bytes leave the file byte-identical.
    """

    home = _spec_home(root, args.spec)
    if home is None:
        return outcome.result("INCOMPLETE")
    spec_body = (home / spec.SPEC_FILE).read_text(encoding="utf-8")
    plan_file = home / spec.PLAN_FILE
    plan_body = plan_file.read_text(encoding="utf-8") if plan_file.is_file() else ""
    title = next(
        (line[2:].strip() for line in spec_body.splitlines() if line.startswith("# ")),
        home.name,
    )
    meta = (
        f"spec {spec._digest(home / spec.SPEC_FILE)} · plan "
        f"{spec._digest(plan_file) if plan_file.is_file() else 'no plan'} · rendered "
        f"{date.today().isoformat()} · a view, not an approval"
    )
    body = pages.render_document(
        spec_body + "\n\n" + plan_body,
        kicker=f"spec {args.spec} · review surface",
        title=title[: contract.PAGE_TITLE_MAX],
        sub="The approved bytes and their tasks, rendered from the Markdown they were signed as.",
        meta=pages.esc(meta),
    )
    views = root / ".ai" / "views"
    views.mkdir(parents=True, exist_ok=True)
    where = views / f"{home.name[:3]}-{home.name[4:]}.html"
    written = where.read_text(encoding="utf-8") if where.is_file() else None
    if written != body:
        where.write_text(body, encoding="utf-8")
    print(f"  {'unchanged' if written == body else 'wrote'} {where.relative_to(root)}")
    print(f"  link: {where.resolve().as_uri()}")
    for line in meta.split(" · ")[:2]:
        print(f"  {line}")
    return outcome.result("PASS")


def _diff_hunks(root: Path, base: str, path: str, budget: int) -> str:
    """A real diff for one path, cut to the excerpt budget at hunk boundaries."""

    out = subprocess.run(
        ["git", "diff", "--unified=2", base, "--", path],
        capture_output=True,
        text=True,
        cwd=str(root),
        check=False,
        timeout=60,
    )
    if out.returncode:
        raise ValueError(
            f"git diff {base} -- {path} exited {out.returncode}: {out.stderr.strip()[:80]}"
        )
    kept: list[str] = []
    for line in out.stdout.splitlines():
        if line.startswith("@@") and len(kept) >= budget:
            break  # a later hunk will not fit; keep whole hunks, never half a line
        kept.append(line)
    return "\n".join(kept[:budget] if len(kept) > budget else kept)


def render_recap(root: Path, args: argparse.Namespace) -> outcome.Result:
    """What a finished build changed, as one record page.

    The file-tree and every diff excerpt come from `git diff` over the named range —
    mechanically, never reconstructed — because the harvested grounding rule says a
    recap block is a fact from the diff or it is not in the recap. The narrative is the
    caller's prose; the shape is this command's.
    """

    home = _spec_home(root, args.spec)
    if home is None:
        return outcome.result("INCOMPLETE")
    probe = subprocess.run(
        ["git", "rev-parse", "--verify", f"{args.base}^{{commit}}"],
        capture_output=True, text=True, cwd=str(root), check=False, timeout=30,
    )
    if probe.returncode:
        print(f"  INCOMPLETE  --base {args.base!r} is not a commit here")
        return outcome.result("INCOMPLETE")
    named = subprocess.run(
        ["git", "diff", "--name-status", args.base],
        capture_output=True, text=True, cwd=str(root), check=False, timeout=60,
    )
    if named.returncode:
        print("  INCOMPLETE  git diff could not read the range")
        return outcome.result("INCOMPLETE")
    changed: list[tuple[str, str]] = []
    for line in named.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            changed.append((parts[0][0], parts[-1]))
    if not changed:
        print(
            f"  INCOMPLETE  the range {args.base}..working tree changes nothing; a recap "
            "of nothing is a page of lies"
        )
        return outcome.result("INCOMPLETE")
    # Key changes: the most-touched files, capped by the contract's budget, never a
    # dump. A recap over the cap stops being a summary; under the floor, it says the
    # change is small and prints the tree instead.
    sizes = subprocess.run(
        ["git", "diff", "--numstat", args.base],
        capture_output=True, text=True, cwd=str(root), check=False, timeout=60,
    )
    weight: dict[str, int] = {}
    for line in sizes.stdout.splitlines():
        cols = line.split("\t")
        if len(cols) >= 3:
            added = int(cols[0]) if cols[0].isdigit() else 0
            removed = int(cols[1]) if cols[1].isdigit() else 0
            weight[cols[-1]] = added + removed
    order = sorted((p for _, p in changed), key=lambda p: -weight.get(p, 0))
    picks = order[: contract.RECAP_TABS_MAX]
    if len(picks) < contract.RECAP_TABS_MIN and len(picks) < len(order):
        picks = order[: contract.RECAP_TABS_MIN]
    excerpts = []
    for path in picks:
        try:
            text = _diff_hunks(root, args.base, path, contract.RECAP_EXCERPT_LINES_MAX)
        except ValueError as refused:
            print(f"  INCOMPLETE  {refused}")
            return outcome.result("INCOMPLETE")
        if text.strip():
            excerpts.append(
                {
                    "block": "diff",
                    "path": path,
                    "text": redact(text),
                    "summary": f"{weight.get(path, 0)} lines changed",
                }
            )
    tree = {
        "block": "file-tree",
        "title": "What changed",
        "entries": [{"path": path, "change": flag} for flag, path in changed],
    }
    blocks: list[dict] = [tree, {"block": "narrative", "text": args.summary}, *excerpts]
    spec_digest = spec._digest(home / spec.SPEC_FILE)
    meta = (
        f"spec {spec_digest} · base {args.base} · {len(changed)} files · rendered "
        f"{date.today().isoformat()}"
    )
    title = next(
        (
            line[2:].strip()
            for line in (home / spec.SPEC_FILE).read_text(encoding="utf-8").splitlines()
            if line.startswith("# ")
        ),
        home.name,
    )
    page = pages.render_page(
        kicker=f"spec {args.spec} · recap",
        title=f"Recap: {title}"[: contract.PAGE_TITLE_MAX],
        sub="What this work unit changed, derived from the diff and nothing else.",
        meta=pages.esc(meta),
        body="".join(pages.render_block(one) for one in blocks),
        warnings=[],
    )
    reports = root / ".ai" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    # Deterministic naming: the recap of one spec lives in one file, overwritten by its
    # own rerun. A fresh number per run would scatter a dozen half-truths across the
    # reports home and make "which recap is current" unanswerable.
    named = sorted(reports.glob(f"???-recap-{home.name[4:]}.html"))
    if named:
        where = named[0]
    else:
        taken = {p.name[:3] for p in reports.glob("[0-9][0-9][0-9]-*") if p.name[:3].isdigit()}
        number = max((int(n) for n in taken), default=0) + 1
        where = reports / f"{number:03d}-recap-{home.name[4:]}.html"
    where.write_text(page, encoding="utf-8")
    print(f"  wrote {where.relative_to(root)}")
    print(f"  link: {where.resolve().as_uri()}")
    print(f"  {meta}")
    return outcome.result("PASS")


def main(argv: list[str]) -> outcome.Result | outcome.Execution:
    parser = argparse.ArgumentParser(prog="ai-eng report")
    commands = parser.add_subparsers(dest="command")
    digest = commands.add_parser("digest")
    digest.add_argument("--weeks", type=int, default=1)
    # `view` and `recap` write pages, so each names the spec it renders and `recap` names
    # the base its diff runs against — the two things that make a rendered page auditable
    # rather than decorative (spec 046, D-046-01/02).
    view = commands.add_parser("view")
    view.add_argument("--spec", required=True, type=_filled)
    recap = commands.add_parser("recap")
    recap.add_argument("--spec", required=True, type=_filled)
    recap.add_argument("--base", required=True, type=_filled)
    recap.add_argument("--summary", required=True, type=_filled)
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
    if args.command in ("view", "recap"):
        root = paths.repo_root()
        if root is None:
            print("  INCOMPLETE  this is not a git repository, so there is no tree to render")
            return outcome.result("INCOMPLETE")
        return render_view(root, args) if args.command == "view" else render_recap(root, args)

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

    # The model distribution, from the product's own events (spec 042 / B-042-1, B-042-2).
    # Four states, never merged: `missing` (event predates the field), `undetermined`
    # (the surface did not say), `model` (what the surface actually reported) and
    # `tier_model` (what the pin says the verb routes to). The line names the state it is
    # counting, so a distribution of configured intent is never read as one of reported
    # actual. An event with no key at all is counted as predating the field, separately.
    command_events = [e for e in events if e.get("cls") == "command"]
    reported = Counter(str(e.get("model") or "missing") for e in command_events)
    routed = Counter(
        str((e.get("data") or {}).get("tier_model") or "missing") for e in command_events
    )
    model_detail = "  ".join(f"{k} {v}" for k, v in reported.most_common(6)) or "none observed"
    tier_detail = "  ".join(f"{k} {v}" for k, v in routed.most_common(6)) or "none observed"
    print(f"\n  Models, reported (surface `model`): {model_detail}")
    print(f"  Models, routed (pin `tier_model`): {tier_detail}")
    check_facts.append(
        outcome.fact("models-reported", "OBSERVED", "Models the surface reported", model_detail)
    )
    check_facts.append(
        outcome.fact("models-routed", "OBSERVED", "Models the pin routes to", tier_detail)
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
