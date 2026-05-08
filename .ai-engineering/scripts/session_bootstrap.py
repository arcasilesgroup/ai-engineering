#!/usr/bin/env python3
"""Deterministic session bootstrap — JSON dashboard, no LLM (brief §16.2).

Replaces the 7-of-9 data-shuffling steps in ``/ai-start`` with a stdlib
script that emits a JSON dashboard in ≤ 300 ms. The skill body keeps
only the 3-line welcome banner that genuinely benefits from natural
language; everything else is regex / yaml.safe_load / subprocess.

Inputs (each one fail-open per field):

* ``git`` HEAD sha + subject + branch (``git log -1 --format=%h%n%s``).
* ``.ai-engineering/specs/spec.md`` frontmatter (yaml.safe_load).
* ``.ai-engineering/specs/plan.md`` (regex count of ``[x]`` vs ``[ ]``).
* ``.ai-engineering/state/framework-events.ndjson`` tail (last 7 d window).
* ``.ai-engineering/manifest.yml`` ``hooks_health`` field (default ``unknown``).

Output: a single JSON object on stdout shaped per brief §16.2:

```
{
  "schema_version": 1,
  "elapsed_ms": 287,
  "branch": "feat/spec-126-...",
  "last_commit": {"sha": "7e6a004f", "subject": "fix(integration): provider alias"},
  "active_spec": {"id": "spec-126", "state": "IN_PROGRESS", "tasks_total": 18, "tasks_done": 14},
  "recent_merges": [{"pr": 504, "title": "..."}],
  "hooks_health": "ok"
}
```

Time budget: < 300 ms wall-clock. If exceeded, the JSON includes
``"warnings": ["budget_exceeded"]`` so callers can flag the regression
in the audit chain. Stdlib only — pyyaml is the single allowed third-
party dep (already in the project venv).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

try:  # pyyaml ships in the project venv; degrade gracefully otherwise.
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - exercised only without venv
    yaml = None  # type: ignore[assignment]

SCHEMA_VERSION = 1
BUDGET_MS = 300.0
RECENT_WINDOW_DAYS = 7

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC_PATH = _REPO_ROOT / ".ai-engineering" / "specs" / "spec.md"
_PLAN_PATH = _REPO_ROOT / ".ai-engineering" / "specs" / "plan.md"
_EVENTS_PATH = _REPO_ROOT / ".ai-engineering" / "state" / "framework-events.ndjson"
_MANIFEST_PATH = _REPO_ROOT / ".ai-engineering" / "manifest.yml"


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path) -> str | None:
    """Run a git subcommand, return stdout stripped or None on failure."""
    try:
        result = subprocess.run(
            ("git", *args),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _read_git(cwd: Path) -> dict:
    """Return ``{branch, last_commit: {sha, subject}}`` (fail-open per field)."""
    out: dict = {"branch": None, "last_commit": None}
    branch = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    if branch:
        out["branch"] = branch
    log = _git("log", "-1", "--format=%h%n%s", cwd=cwd)
    if log:
        sha, _, subject = log.partition("\n")
        out["last_commit"] = {"sha": sha, "subject": subject}
    return out


# ---------------------------------------------------------------------------
# spec.md frontmatter
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _read_spec(path: Path) -> dict | None:
    """Return ``{id, state, title}`` or ``None`` when missing/placeholder."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.strip() or "no active spec" in text.lower()[:200]:
        return None

    match = _FRONTMATTER_RE.search(text)
    if not match or yaml is None:
        return None
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    spec_id = fm.get("id") or fm.get("spec_id")
    state = fm.get("status") or fm.get("state")
    title = fm.get("title")
    if not (spec_id or state or title):
        return None
    return {"id": spec_id, "state": state, "title": title}


# ---------------------------------------------------------------------------
# plan.md task counts
# ---------------------------------------------------------------------------

_TASK_RE = re.compile(r"^\s*-\s*\[([ xX])\]", re.MULTILINE)


def _read_plan(path: Path) -> dict:
    """Return ``{tasks_total, tasks_done}`` or zeros when missing."""
    if not path.is_file():
        return {"tasks_total": 0, "tasks_done": 0}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"tasks_total": 0, "tasks_done": 0}
    matches = _TASK_RE.findall(text)
    total = len(matches)
    done = sum(1 for m in matches if m in ("x", "X"))
    return {"tasks_total": total, "tasks_done": done}


# ---------------------------------------------------------------------------
# Recent NDJSON events (7-day window)
# ---------------------------------------------------------------------------


def _read_recent_events(path: Path, window_days: int = RECENT_WINDOW_DAYS) -> int:
    """Tail the audit chain; return count of events in the last N days.

    Bounded to the last 1000 lines so a giant log does not blow the
    300 ms budget. Older events drop out by ``ts`` filter on best-effort
    JSON parse; malformed lines are silently skipped (fail-open).
    """
    if not path.is_file():
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    count = 0
    try:
        # Use binary readline tail to avoid loading whole file.
        with path.open("rb") as fh:
            try:
                fh.seek(0, 2)
                size = fh.tell()
                read = min(size, 256 * 1024)  # last 256 KiB max
                fh.seek(size - read)
                tail = fh.read().decode("utf-8", errors="replace")
            except OSError:
                return 0
    except OSError:
        return 0

    for line in tail.splitlines()[-1000:]:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = evt.get("ts") or evt.get("timestamp")
        if not isinstance(ts, str):
            continue
        try:
            when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        if when >= cutoff:
            count += 1
    return count


# ---------------------------------------------------------------------------
# manifest.yml hooks_health
# ---------------------------------------------------------------------------


def _read_hooks_health(path: Path) -> str:
    """Return ``hooks_health`` string from manifest, defaulting to ``unknown``."""
    if not path.is_file() or yaml is None:
        return "unknown"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return "unknown"
    if not isinstance(data, dict):
        return "unknown"
    val = data.get("hooks_health")
    if isinstance(val, str):
        return val
    # Fall back to a structured ``hooks: { health: "..." }`` shape.
    hooks = data.get("hooks")
    if isinstance(hooks, dict):
        sub = hooks.get("health")
        if isinstance(sub, str):
            return sub
    return "unknown"


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------


def build_dashboard(repo_root: Path | None = None) -> dict:
    """Compose the JSON dashboard. Returns the dict (caller serialises)."""
    started = time.perf_counter()
    root = repo_root or _REPO_ROOT

    git_info = _read_git(root)
    spec = _read_spec(root / ".ai-engineering" / "specs" / "spec.md")
    plan = _read_plan(root / ".ai-engineering" / "specs" / "plan.md")
    recent_count = _read_recent_events(
        root / ".ai-engineering" / "state" / "framework-events.ndjson"
    )
    hooks_health = _read_hooks_health(root / ".ai-engineering" / "manifest.yml")

    elapsed_ms = (time.perf_counter() - started) * 1000.0

    dashboard: dict = {
        "schema_version": SCHEMA_VERSION,
        "elapsed_ms": round(elapsed_ms, 2),
        "branch": git_info.get("branch"),
        "last_commit": git_info.get("last_commit"),
        "active_spec": (
            None
            if spec is None
            else {
                "id": spec.get("id"),
                "state": spec.get("state"),
                "title": spec.get("title"),
                "tasks_total": plan["tasks_total"],
                "tasks_done": plan["tasks_done"],
            }
        ),
        "recent_events_7d": recent_count,
        "hooks_health": hooks_health,
    }
    if elapsed_ms > BUDGET_MS:
        dashboard["warnings"] = ["budget_exceeded"]
    return dashboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="session_bootstrap",
        description="Emit /ai-start JSON dashboard (deterministic, <300ms).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Override repo root (default: resolved from script location).",
    )
    args = parser.parse_args(argv)
    dashboard = build_dashboard(args.repo_root)
    sys.stdout.write(json.dumps(dashboard, indent=2, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
