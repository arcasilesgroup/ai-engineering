"""Hot-path SLO check for `ai-eng doctor --check hot-path` (spec-114 T-2.7..T-2.8).

Reads the rolling window of `ide_hook` heartbeat events emitted by
`_lib/hook-common.run_hook_safe`, groups by component, computes p95
of `detail.duration_ms`, and compares against the manifest budget.

Per D-114-03 the check is *advisory* through 2026-05-31:

* exit code is always 0 (no blocking on transient slow hooks);
* violations append a `hot_path_violation` event with
  `detail.bug_tag = "infra:slow-hook"` so downstream tools can subscribe;
* a structured table is printed (hook | p95_ms | budget_ms | status).

The advisory window expires 2026-05-31 — at that point a follow-up
spec flips the check to blocking by raising `typer.Exit(2)` on
violation. Document the sunset in CHANGELOG when that change ships.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.config.manifest import HotPathSlosConfig

# ide_hook events whose `detail.hook_kind` starts with one of these prefixes
# are scored against the matching budget. Anything else (e.g. session-end,
# user-prompt-submit) falls back to skill_invocation_overhead_p95_ms so the
# table still shows it without misclassifying it as a pre-commit gate.
_PRE_COMMIT_HOOK_KINDS = frozenset({"pre-commit"})
_PRE_PUSH_HOOK_KINDS = frozenset({"pre-push", "pre-receive"})


def _budget_for_hook_kind(hook_kind: str, slos: HotPathSlosConfig) -> int:
    if hook_kind in _PRE_COMMIT_HOOK_KINDS:
        return slos.pre_commit_p95_ms
    if hook_kind in _PRE_PUSH_HOOK_KINDS:
        return slos.pre_push_p95_ms
    return slos.skill_invocation_overhead_p95_ms


def _read_recent_heartbeats(project_root: Path, window: int) -> list[dict]:
    """Return the last `window` ide_hook events from the NDJSON, oldest→newest."""
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not path.exists():
        return []
    heartbeats: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(event, dict) or event.get("kind") != "ide_hook":
            continue
        detail = event.get("detail") or {}
        if not isinstance(detail, dict):
            continue
        if not isinstance(detail.get("duration_ms"), int):
            continue
        heartbeats.append(event)
    return heartbeats[-window:]


def _p95_of(samples: list[int]) -> int:
    """Compute p95 from an arbitrary-length sample. Documented method.

    Implementation: sorted index `int(0.95 * n)` clamped to len-1. We
    avoid `statistics.quantiles(...)` because it requires `n >= 2` and
    interpolates, which inflates p95 on small windows. The clamped
    sorted-index method is monotonic and degrades cleanly when the
    rolling window is partial (e.g. 1-50 events).
    """
    if not samples:
        return 0
    if len(samples) == 1:
        return int(samples[0])
    ordered = sorted(samples)
    idx = min(int(0.95 * len(ordered)), len(ordered) - 1)
    return int(ordered[idx])


def _group_by_component(heartbeats: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for event in heartbeats:
        component = str(event.get("component") or "<unknown>")
        grouped.setdefault(component, []).append(event)
    return grouped


def _summarise_component(component: str, events: list[dict], slos: HotPathSlosConfig) -> dict:
    durations = [int(e["detail"]["duration_ms"]) for e in events]
    # All events in a component share the same hook_kind in practice; pick
    # the latest so we score against the budget the operator most recently
    # triggered.
    hook_kind = str(events[-1]["detail"].get("hook_kind") or "")
    budget = _budget_for_hook_kind(hook_kind, slos)
    p95 = _p95_of(durations)
    return {
        "component": component,
        "hook_kind": hook_kind,
        "p95_ms": p95,
        "budget_ms": budget,
        "samples": len(durations),
        "violation": p95 > budget,
    }


def _emit_violation(project_root: Path, summary: dict) -> None:
    """Append a `hot_path_violation` event with `bug_tag: infra:slow-hook`."""
    state_dir = project_root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "framework-events.ndjson"
    event = {
        "kind": "hot_path_violation",
        "engine": "ai_engineering",
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "component": "doctor.hot-path",
        "outcome": "warn",
        "correlationId": uuid.uuid4().hex,
        "schemaVersion": "1.0",
        "project": project_root.name,
        "source": "doctor",
        "detail": {
            "bug_tag": "infra:slow-hook",
            "hook": summary["component"],
            "hook_kind": summary["hook_kind"],
            "observed_p95_ms": summary["p95_ms"],
            "budget_ms": summary["budget_ms"],
            "samples": summary["samples"],
        },
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


def _format_table(summaries: list[dict]) -> str:
    """Render the structured table operators read in the terminal."""
    header = f"{'hook':<32} {'p95_ms':>8} {'budget_ms':>10} {'samples':>8} status"
    rows = [header, "-" * len(header)]
    for summary in summaries:
        status = "WARN" if summary["violation"] else "PASS"
        rows.append(
            f"{summary['component']:<32} {summary['p95_ms']:>8} "
            f"{summary['budget_ms']:>10} {summary['samples']:>8} {status}"
        )
    return "\n".join(rows)


def run_hot_path_check(project_root: Path) -> int:
    """Entry point used by `ai-eng doctor --check hot-path`.

    Returns the number of violations detected (always exit 0 in advisory
    mode per D-114-03; the caller decides whether to surface non-zero).
    """
    config = load_manifest_config(project_root)
    slos = config.hot_path_slos
    heartbeats = _read_recent_heartbeats(project_root, slos.rolling_window_events)
    if not heartbeats:
        print("doctor --check hot-path: no ide_hook events found (0 events scanned)")
        print("  Run a few hooks (commit, skill invocation) to populate the rolling window.")
        return 0
    grouped = _group_by_component(heartbeats)
    summaries = [
        _summarise_component(component, events, slos)
        for component, events in sorted(grouped.items())
    ]
    print(_format_table(summaries))
    violations = [s for s in summaries if s["violation"]]
    for summary in violations:
        _emit_violation(project_root, summary)
    if violations:
        print(
            f"\nADVISORY: {len(violations)} hook(s) exceeded the SLO budget "
            f"(window={slos.rolling_window_events}). Violations recorded as "
            f"hot_path_violation events with bug_tag=infra:slow-hook.\n"
            f"Advisory through 2026-05-31; blocking thereafter (spec-114 D-114-03)."
        )
    return len(violations)
