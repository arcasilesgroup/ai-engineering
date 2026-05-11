"""no_suppression CLI — argparse front-door."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from no_suppression.allowlist import (
    DEFAULT_ALLOWLIST_PATH,
    DEFAULT_STATE_DB_PATH,
    AllowlistDecision,
    evaluate,
    load_allowlist,
)
from no_suppression.scanner import (
    DEFAULT_EXCLUDE_GLOBS,
    DEFAULT_INCLUDE_GLOBS,
    scan_paths,
)

__all__ = ("build_parser", "main", "run_check")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="no_suppression",
        description=(
            "Repo-wide anti-suppression gate (CONSTITUTION.md Article VII). "
            "Fails on suppression comments / Sonar directives without an "
            "allowlist entry."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Repository root to scan (default: cwd).",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=None,
        help=(
            "Path to suppression-allowlist.yml (default: "
            "<root>/.ai-engineering/suppression-allowlist.yml)."
        ),
    )
    parser.add_argument(
        "--state-db",
        type=Path,
        default=None,
        help=(
            "Path to state.db for DEC validation (default: <root>/.ai-engineering/state/state.db)."
        ),
    )
    parser.add_argument(
        "--include",
        action="append",
        default=None,
        help="Override include globs (repeatable).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        help="Override exclude globs (repeatable).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as a single JSON document on stdout.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress success summary on exit code 0.",
    )
    return parser


def _render_text(decisions: list[AllowlistDecision]) -> str:
    if not decisions:
        return "no_suppression: no suppression markers found in scanned paths.\n"
    lines: list[str] = []
    denied = [d for d in decisions if d.status != "allowed"]
    allowed = [d for d in decisions if d.status == "allowed"]
    if denied:
        lines.append("no_suppression: BLOCKED — unallowed suppression markers:")
        for d in denied:
            f = d.finding
            lines.append(
                f"  {f.path.as_posix()}:{f.line}:{f.column}  "
                f"[{f.rule_id}{('/' + f.rule_target) if f.rule_target and f.rule_target != f.rule_id else ''}]"
                f"  {d.status}: {d.reason}"
            )
            lines.append(f"      snippet: {f.snippet}")
    if allowed:
        lines.append(f"no_suppression: {len(allowed)} suppression(s) covered by allowlist.")
    return "\n".join(lines) + "\n"


def _render_json(decisions: list[AllowlistDecision]) -> str:
    payload = {
        "schema": "no-suppression/v1",
        "denied": [
            {
                "path": d.finding.path.as_posix(),
                "line": d.finding.line,
                "column": d.finding.column,
                "rule_id": d.finding.rule_id,
                "rule_target": d.finding.rule_target,
                "snippet": d.finding.snippet,
                "status": d.status,
                "reason": d.reason,
                "matched_entry": (
                    {
                        "path_glob": d.matched_entry.path_glob,
                        "rule_id": d.matched_entry.rule_id,
                        "pattern": d.matched_entry.pattern,
                        "spec_ref": d.matched_entry.spec_ref,
                        "expires_at": d.matched_entry.expires_at,
                        "dec_id": d.matched_entry.dec_id,
                    }
                    if d.matched_entry is not None
                    else None
                ),
            }
            for d in decisions
            if d.status != "allowed"
        ],
        "allowed": [
            {
                "path": d.finding.path.as_posix(),
                "line": d.finding.line,
                "rule_id": d.finding.rule_id,
                "rule_target": d.finding.rule_target,
                "spec_ref": d.matched_entry.spec_ref if d.matched_entry else "",
                "dec_id": d.matched_entry.dec_id if d.matched_entry else "",
            }
            for d in decisions
            if d.status == "allowed"
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def run_check(
    *,
    root: Path,
    allowlist_path: Path | None,
    state_db_path: Path | None,
    include: Sequence[str] | None,
    exclude: Sequence[str] | None,
) -> list[AllowlistDecision]:
    """Programmatic entry — exposed for tests + the gate orchestrator."""
    actual_allowlist = allowlist_path or (root / DEFAULT_ALLOWLIST_PATH)
    actual_state_db = state_db_path or (root / DEFAULT_STATE_DB_PATH)
    findings = scan_paths(
        root,
        include or DEFAULT_INCLUDE_GLOBS,
        exclude or DEFAULT_EXCLUDE_GLOBS,
    )
    entries = load_allowlist(actual_allowlist)
    return evaluate(findings, entries, state_db=actual_state_db)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    decisions = run_check(
        root=args.root.resolve(),
        allowlist_path=args.allowlist,
        state_db_path=args.state_db,
        include=args.include,
        exclude=args.exclude,
    )
    blocked = [d for d in decisions if d.status != "allowed"]
    output = _render_json(decisions) if args.json else _render_text(decisions)
    if blocked or not args.quiet:
        sys.stdout.write(output)
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
