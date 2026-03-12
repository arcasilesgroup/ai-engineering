"""NDJSON signal read/write/query for the single event store.

The audit-log.ndjson is the single source of truth for all events
(gates, scans, builds, deploys, sessions). This module provides
query and aggregation utilities on top of state.io primitives.
"""

from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

AUDIT_LOG_REL = Path(".ai-engineering") / "state" / "audit-log.ndjson"


def audit_log_path(project_root: Path) -> Path:
    """Return the canonical audit-log.ndjson path."""
    return project_root / AUDIT_LOG_REL


def load_all_events(project_root: Path) -> list[dict[str, Any]]:
    """Load all events from audit-log.ndjson once.

    Returns:
        List of event dicts in file order (oldest first).
    """
    path = audit_log_path(project_root)
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def filter_events(
    events: list[dict[str, Any]],
    *,
    event_type: str | None = None,
    since: datetime | None = None,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Filter pre-loaded events in memory (no I/O).

    Args:
        events: Pre-loaded event list from load_all_events().
        event_type: Filter by event type.
        since: Only include events after this timestamp.
        limit: Max events to return (0 = unlimited).

    Returns:
        Filtered events, newest first.
    """
    result: list[dict[str, Any]] = []
    for event in events:
        if event_type and event.get("event") != event_type:
            continue
        if since:
            ts_str = event.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(
                    ts_str.replace("Z", "+00:00"),
                )
                if ts < since:
                    continue
            except (ValueError, AttributeError):
                continue
        result.append(event)

    result.reverse()  # newest first
    if limit > 0:
        result = result[:limit]
    return result


def read_events(
    project_root: Path,
    *,
    event_type: str | None = None,
    since: datetime | None = None,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Read events from audit-log.ndjson with optional filtering.

    Convenience wrapper: loads + filters in one call.
    For multiple queries, use load_all_events() + filter_events().
    """
    return filter_events(
        load_all_events(project_root),
        event_type=event_type,
        since=since,
        limit=limit,
    )


def _extract_timestamps(
    events: list[dict[str, Any]],
) -> list[datetime]:
    """Extract valid timestamps from events."""
    timestamps: list[datetime] = []
    for event in events:
        ts_str = event.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(
                ts_str.replace("Z", "+00:00"),
            )
            timestamps.append(ts)
        except (ValueError, AttributeError):
            continue
    return timestamps


def event_date_range_from(
    events: list[dict[str, Any]],
) -> tuple[datetime | None, datetime | None]:
    """Get date range from pre-loaded events (no I/O)."""
    timestamps = _extract_timestamps(events)
    if not timestamps:
        return None, None
    return min(timestamps), max(timestamps)


def event_date_range(
    project_root: Path,
) -> tuple[datetime | None, datetime | None]:
    """Get the date range of events in the audit log."""
    return event_date_range_from(load_all_events(project_root))


def data_quality_from(
    events: list[dict[str, Any]],
) -> str:
    """Compute data quality level from pre-loaded events (no I/O).

    Returns:
        "HIGH" (>=500 events, >=60 days),
        "MEDIUM" (>=100, >=14 days), or "LOW".
    """
    total = len(events)
    oldest, newest = event_date_range_from(events)
    if oldest is None or newest is None:
        return "LOW"
    days = (newest - oldest).days
    if total >= 500 and days >= 60:
        return "HIGH"
    if total >= 100 and days >= 14:
        return "MEDIUM"
    return "LOW"


def data_quality_level(project_root: Path) -> str:
    """Compute data quality level for dashboard confidence."""
    return data_quality_from(load_all_events(project_root))


def count_events(
    project_root: Path,
    *,
    since: datetime | None = None,
) -> int:
    """Count total events in the audit log."""
    return len(read_events(project_root, since=since))


def gate_pass_rate_from(
    events: list[dict[str, Any]],
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Compute gate pass rate from pre-loaded events (no I/O)."""
    since = datetime.now(tz=UTC) - timedelta(days=days)
    gate_events = filter_events(
        events,
        event_type="gate_result",
        since=since,
    )
    total = len(gate_events)
    passed = sum(1 for e in gate_events if _detail_field(e, "result") == "pass")
    failed = total - passed

    check_failures: dict[str, int] = {}
    for event in gate_events:
        detail = event.get("detail")
        if isinstance(detail, dict):
            for name in detail.get("failed_checks", []):
                check_failures[name] = check_failures.get(name, 0) + 1

    most_failed = (
        max(check_failures, key=check_failures.get)  # type: ignore[arg-type]
        if check_failures
        else "none"
    )

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": (round(passed / total * 100, 1) if total > 0 else 0.0),
        "most_failed_check": most_failed,
        "most_failed_count": check_failures.get(most_failed, 0),
    }


def gate_pass_rate(
    project_root: Path,
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Compute gate pass rate over the last N days."""
    return gate_pass_rate_from(
        load_all_events(project_root),
        days=days,
    )


def _detail_field(event: dict[str, Any], field: str) -> Any:
    """Extract a field from the detail dict of an event."""
    detail = event.get("detail")
    if isinstance(detail, dict):
        return detail.get(field)
    return None


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def scan_metrics_from(
    events: list[dict[str, Any]],
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Aggregate scan_complete events into metrics.

    Args:
        events: Pre-loaded event list from load_all_events().
        days: Window in days to consider.

    Returns:
        Dict with total_scans, avg_quality_score, avg_security_score,
        findings counts, and modes_scanned.
    """
    since = datetime.now(tz=UTC) - timedelta(days=days)
    scan_events = filter_events(events, event_type="scan_complete", since=since)

    total_scans = len(scan_events)

    # Quality scores
    scores: list[float] = []
    security_scores: list[float] = []
    findings: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    modes: set[str] = set()

    for event in scan_events:
        score = _detail_field(event, "score")
        if score is not None:
            with contextlib.suppress(TypeError, ValueError):
                scores.append(float(score))

        mode = _detail_field(event, "mode")
        if isinstance(mode, str):
            modes.add(mode)
            if mode == "security" and score is not None:
                with contextlib.suppress(TypeError, ValueError):
                    security_scores.append(float(score))

        event_findings = _detail_field(event, "findings")
        if isinstance(event_findings, dict):
            for sev in ("critical", "high", "medium", "low"):
                val = event_findings.get(sev, 0)
                with contextlib.suppress(TypeError, ValueError):
                    findings[sev] += int(val)

    avg_quality = round(sum(scores) / len(scores), 2) if scores else 0.0
    avg_security = round(sum(security_scores) / len(security_scores), 2) if security_scores else 0.0

    return {
        "total_scans": total_scans,
        "avg_quality_score": avg_quality,
        "avg_security_score": avg_security,
        "findings": findings,
        "modes_scanned": sorted(modes),
    }


def build_metrics_from(
    events: list[dict[str, Any]],
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Aggregate build_complete events into metrics.

    Args:
        events: Pre-loaded event list from load_all_events().
        days: Window in days to consider.

    Returns:
        Dict with total_builds, files_changed, lines_added,
        lines_removed, tests_added.
    """
    since = datetime.now(tz=UTC) - timedelta(days=days)
    build_events = filter_events(events, event_type="build_complete", since=since)

    total_builds = len(build_events)
    files_changed = 0
    lines_added = 0
    lines_removed = 0
    tests_added = 0

    for event in build_events:
        for field, acc_name in (
            ("files_changed", "files_changed"),
            ("lines_added", "lines_added"),
            ("lines_removed", "lines_removed"),
            ("tests_added", "tests_added"),
        ):
            val = _detail_field(event, field)
            if val is not None:
                try:
                    if acc_name == "files_changed":
                        files_changed += int(val)
                    elif acc_name == "lines_added":
                        lines_added += int(val)
                    elif acc_name == "lines_removed":
                        lines_removed += int(val)
                    elif acc_name == "tests_added":
                        tests_added += int(val)
                except (TypeError, ValueError):
                    pass

    return {
        "total_builds": total_builds,
        "files_changed": files_changed,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "tests_added": tests_added,
    }


def deploy_metrics_from(
    events: list[dict[str, Any]],
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Aggregate deploy_complete events into metrics.

    Args:
        events: Pre-loaded event list from load_all_events().
        days: Window in days to consider.

    Returns:
        Dict with total_deploys, rollbacks, failure_rate, strategies.
    """
    since = datetime.now(tz=UTC) - timedelta(days=days)
    deploy_events = filter_events(events, event_type="deploy_complete", since=since)

    total_deploys = len(deploy_events)
    rollbacks = 0
    strategies: dict[str, int] = {}

    for event in deploy_events:
        if _detail_field(event, "rollback") is True:
            rollbacks += 1
        strategy = _detail_field(event, "strategy")
        if isinstance(strategy, str):
            strategies[strategy] = strategies.get(strategy, 0) + 1

    failure_rate = round(rollbacks / total_deploys * 100, 1) if total_deploys > 0 else 0.0

    return {
        "total_deploys": total_deploys,
        "rollbacks": rollbacks,
        "failure_rate": failure_rate,
        "strategies": strategies,
    }


def noise_ratio_from(
    events: list[dict[str, Any]],
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Compute noise ratio from gate_result events.

    Noise ratio = fixable failures / total failures.
    High noise means most gate failures are auto-fixable (formatting, lint).

    Returns:
        Dict with total_failures, fixable_failures, noise_ratio_pct.
    """
    since = datetime.now(tz=UTC) - timedelta(days=days)
    gate_events = filter_events(events, event_type="gate_result", since=since)

    total_failures = 0
    fixable_failures = 0

    for event in gate_events:
        detail = event.get("detail")
        if not isinstance(detail, dict):
            continue
        failed = detail.get("failed_checks", [])
        fixable = detail.get("fixable_failures", [])
        if isinstance(failed, list):
            total_failures += len(failed)
        if isinstance(fixable, list):
            fixable_failures += len(fixable)

    noise_pct = round(fixable_failures / total_failures * 100, 1) if total_failures > 0 else 0.0

    return {
        "total_failures": total_failures,
        "fixable_failures": fixable_failures,
        "noise_ratio_pct": noise_pct,
    }


def skill_usage_from(
    events: list[dict[str, Any]],
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Aggregate skill_invoked events into usage metrics.

    Args:
        events: Pre-loaded event list from load_all_events().
        days: Window in days to consider.

    Returns:
        Dict with total_invocations, by_skill (sorted desc), top_skill, least_skill.
    """
    since = datetime.now(tz=UTC) - timedelta(days=days)
    skill_events = filter_events(events, event_type="skill_invoked", since=since)

    by_skill: dict[str, int] = {}
    for event in skill_events:
        name = _detail_field(event, "skill")
        if isinstance(name, str) and name:
            by_skill[name] = by_skill.get(name, 0) + 1

    sorted_skills = dict(sorted(by_skill.items(), key=lambda x: x[1], reverse=True))
    total = sum(sorted_skills.values())

    return {
        "total_invocations": total,
        "by_skill": sorted_skills,
        "top_skill": next(iter(sorted_skills), "none") if sorted_skills else "none",
        "least_skill": min(sorted_skills, key=sorted_skills.get) if sorted_skills else "none",  # type: ignore[arg-type]
    }


def agent_dispatch_from(
    events: list[dict[str, Any]],
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Aggregate agent_dispatched events into dispatch metrics.

    Args:
        events: Pre-loaded event list from load_all_events().
        days: Window in days to consider.

    Returns:
        Dict with total_dispatches, by_agent (sorted desc).
    """
    since = datetime.now(tz=UTC) - timedelta(days=days)
    agent_events = filter_events(events, event_type="agent_dispatched", since=since)

    by_agent: dict[str, int] = {}
    for event in agent_events:
        name = _detail_field(event, "agent")
        if isinstance(name, str) and name:
            by_agent[name] = by_agent.get(name, 0) + 1

    sorted_agents = dict(sorted(by_agent.items(), key=lambda x: x[1], reverse=True))
    total = sum(sorted_agents.values())

    return {
        "total_dispatches": total,
        "by_agent": sorted_agents,
    }


def session_metrics_from(
    events: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Aggregate session_metric events into metrics.

    Args:
        events: Pre-loaded event list from load_all_events().
        limit: Maximum number of sessions to analyze.

    Returns:
        Dict with sessions_analyzed, total_tokens, tokens_available,
        utilization_pct, skills_loaded, decisions_reused, decisions_reprompted.
    """
    session_events = filter_events(events, event_type="session_metric", limit=limit)

    sessions_analyzed = len(session_events)
    total_tokens = 0
    tokens_available = 200_000  # default
    skills: set[str] = set()
    decisions_reused = 0
    decisions_reprompted = 0

    for event in session_events:
        val = _detail_field(event, "tokens_used")
        if val is not None:
            with contextlib.suppress(TypeError, ValueError):
                total_tokens += int(val)

        avail = _detail_field(event, "tokens_available")
        if avail is not None:
            with contextlib.suppress(TypeError, ValueError):
                tokens_available = max(tokens_available, int(avail))

        event_skills = _detail_field(event, "skills_loaded")
        if isinstance(event_skills, list):
            for s in event_skills:
                if isinstance(s, str):
                    skills.add(s)

        reused = _detail_field(event, "decisions_reused")
        if reused is not None:
            with contextlib.suppress(TypeError, ValueError):
                decisions_reused += int(reused)

        reprompted = _detail_field(event, "decisions_reprompted")
        if reprompted is not None:
            with contextlib.suppress(TypeError, ValueError):
                decisions_reprompted += int(reprompted)

    utilization_pct = (
        round(total_tokens / (sessions_analyzed * tokens_available) * 100, 1)
        if sessions_analyzed > 0 and tokens_available > 0
        else 0.0
    )

    return {
        "sessions_analyzed": sessions_analyzed,
        "total_tokens": total_tokens,
        "tokens_available": tokens_available,
        "utilization_pct": utilization_pct,
        "skills_loaded": sorted(skills),
        "decisions_reused": decisions_reused,
        "decisions_reprompted": decisions_reprompted,
    }


# ---------------------------------------------------------------------------
# State-file readers
# ---------------------------------------------------------------------------


def decision_store_health(project_root: Path) -> dict[str, Any]:
    """Read decision-store.json and compute health metrics.

    Args:
        project_root: Repository root path.

    Returns:
        Dict with total, active, expired, resolved, avg_age_days.
        Returns zeroed dict on any error (fail-open).
    """
    empty: dict[str, Any] = {
        "total": 0,
        "active": 0,
        "expired": 0,
        "resolved": 0,
        "avg_age_days": 0,
    }
    try:
        path = project_root / ".ai-engineering" / "state" / "decision-store.json"
        if not path.exists():
            return empty

        data = json.loads(path.read_text(encoding="utf-8"))
        decisions = data.get("decisions", [])
        if not decisions:
            return empty

        now = datetime.now(tz=UTC)
        total = len(decisions)
        active = 0
        expired = 0
        resolved = 0
        ages: list[float] = []

        for d in decisions:
            status = d.get("status", "active")

            # Check expiry
            expires_str = d.get("expiresAt") or d.get("expires_at")
            is_expired = False
            if expires_str:
                try:
                    expires_at = datetime.fromisoformat(
                        expires_str.replace("Z", "+00:00"),
                    )
                    if expires_at < now:
                        is_expired = True
                except (ValueError, AttributeError):
                    pass

            if is_expired:
                expired += 1
            elif status in ("resolved", "remediated"):
                resolved += 1
            elif status == "active":
                active += 1

            # Age calculation
            created_str = d.get("decidedAt") or d.get("decided_at")
            if created_str:
                try:
                    created_at = datetime.fromisoformat(
                        created_str.replace("Z", "+00:00"),
                    )
                    ages.append((now - created_at).total_seconds() / 86400)
                except (ValueError, AttributeError):
                    pass

        avg_age = round(sum(ages) / len(ages), 1) if ages else 0

        return {
            "total": total,
            "active": active,
            "expired": expired,
            "resolved": resolved,
            "avg_age_days": avg_age,
        }
    except Exception:
        return empty


def adoption_metrics(project_root: Path) -> dict[str, Any]:
    """Read install-manifest.json and compute adoption metrics.

    Args:
        project_root: Repository root path.

    Returns:
        Dict with stacks, providers, ides, hooks_installed, hooks_verified.
        Returns defaults on any error (fail-open).
    """
    defaults: dict[str, Any] = {
        "stacks": [],
        "providers": {"primary": "unknown", "enabled": []},
        "ides": [],
        "hooks_installed": False,
        "hooks_verified": False,
    }
    try:
        path = project_root / ".ai-engineering" / "state" / "install-manifest.json"
        if not path.exists():
            return defaults

        data = json.loads(path.read_text(encoding="utf-8"))

        stacks = data.get("installedStacks", [])
        ides = data.get("installedIdes", [])

        providers_data = data.get("providers", {})
        providers = {
            "primary": providers_data.get("primary", "unknown"),
            "enabled": providers_data.get("enabled", []),
        }

        tooling = data.get("toolingReadiness", {})
        git_hooks = tooling.get("gitHooks", {})
        hooks_installed = git_hooks.get("installed", False)
        hooks_verified = git_hooks.get("integrityVerified", False)

        return {
            "stacks": stacks,
            "providers": providers,
            "ides": ides,
            "hooks_installed": hooks_installed,
            "hooks_verified": hooks_verified,
        }
    except Exception:
        return defaults


def checkpoint_status(project_root: Path) -> dict[str, Any]:
    """Read session-checkpoint.json and report status.

    Args:
        project_root: Repository root path.

    Returns:
        Dict with has_checkpoint, last_task, age, completed, total,
        progress_pct, blocked_on.
        Returns {"has_checkpoint": False} on any error (fail-open).
    """
    no_checkpoint: dict[str, Any] = {"has_checkpoint": False}
    try:
        path = project_root / ".ai-engineering" / "state" / "session-checkpoint.json"
        if not path.exists():
            return no_checkpoint

        raw = json.loads(path.read_text(encoding="utf-8"))

        # Support namespaced checkpoints: prefer agent-specific data
        # if "agents" section exists, use the most recent agent entry
        data = raw
        if "agents" in raw and isinstance(raw["agents"], dict):
            # Use top-level fields (backward compat) but note agents exist
            pass  # top-level is already populated by checkpoint_save

        # Parse progress like "3/5" or empty
        progress_str = data.get("progress", "")
        completed = 0
        total = 0
        progress_pct = 0.0
        if isinstance(progress_str, str) and "/" in progress_str:
            parts = progress_str.split("/")
            try:
                completed = int(parts[0])
                total = int(parts[1])
                progress_pct = round(completed / total * 100, 1) if total > 0 else 0.0
            except (ValueError, IndexError):
                pass

        # Calculate age
        ts_str = data.get("timestamp", "")
        age = "unknown"
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                now = datetime.now(tz=UTC)
                delta = now - ts
                total_hours = delta.total_seconds() / 3600
                if total_hours < 1:
                    age = f"{int(delta.total_seconds() / 60)}m ago"
                elif total_hours < 24:
                    age = f"{int(total_hours)}h ago"
                else:
                    age = f"{int(total_hours / 24)}d ago"
            except (ValueError, AttributeError):
                pass

        last_task = data.get("current_task", "")
        blocked_on = data.get("blocked_on")

        # Only report as having a checkpoint if there is meaningful data
        has_checkpoint = bool(last_task or progress_str)

        return {
            "has_checkpoint": has_checkpoint,
            "last_task": last_task,
            "age": age,
            "completed": completed,
            "total": total,
            "progress_pct": progress_pct,
            "blocked_on": blocked_on,
        }
    except Exception:
        return no_checkpoint


def lead_time_metrics(project_root: Path, *, days: int = 30) -> dict[str, Any]:
    """Compute lead time from git merge history.

    Uses subprocess to run git commands and calculate the time between
    the first commit on a branch and its merge to main.

    Args:
        project_root: Repository root path.
        days: Number of days to look back.

    Returns:
        Dict with median_days, merges_analyzed, rating.
        Returns zeroed dict on any error (fail-open).
    """
    import subprocess
    from statistics import median

    default: dict[str, Any] = {
        "median_days": 0,
        "merges_analyzed": 0,
        "rating": "LOW",
    }
    try:
        # Get merge commits to main in last N days
        result = subprocess.run(
            [
                "git",
                "log",
                "--merges",
                "--first-parent",
                "main",
                f"--since={days} days ago",
                "--format=%H %aI",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=30,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return default

        lead_times: list[float] = []
        for line in result.stdout.strip().splitlines():
            parts = line.strip().split(" ", 1)
            if len(parts) != 2:
                continue
            merge_sha, merge_date_str = parts

            try:
                merge_date = datetime.fromisoformat(merge_date_str)
            except ValueError:
                continue

            # Get the first commit in the merged branch
            branch_result = subprocess.run(
                [
                    "git",
                    "log",
                    "--format=%aI",
                    f"{merge_sha}^2",
                    "--not",
                    f"{merge_sha}^1",
                    "--reverse",
                ],
                capture_output=True,
                text=True,
                cwd=str(project_root),
                timeout=30,
            )
            if branch_result.returncode != 0 or not branch_result.stdout.strip():
                continue

            first_line = branch_result.stdout.strip().splitlines()[0]
            try:
                first_commit_date = datetime.fromisoformat(first_line.strip())
            except ValueError:
                continue

            lt = (merge_date - first_commit_date).total_seconds() / 86400
            if lt >= 0:
                lead_times.append(lt)

        if not lead_times:
            return default

        median_days = round(median(lead_times), 2)
        merges_analyzed = len(lead_times)

        if median_days < 1:
            rating = "ELITE"
        elif median_days < 7:
            rating = "HIGH"
        elif median_days < 30:
            rating = "MEDIUM"
        else:
            rating = "LOW"

        return {
            "median_days": median_days,
            "merges_analyzed": merges_analyzed,
            "rating": rating,
        }
    except Exception:
        return default


# ---------------------------------------------------------------------------
# SonarCloud detailed metrics
# ---------------------------------------------------------------------------

_sonar_cache: dict | None = None


def sonar_detailed_metrics(project_root: Path) -> dict:
    """Fetch detailed SonarCloud metrics with module-level cache.

    Returns dict with keys: coverage_pct, cognitive_complexity,
    duplication_pct, vulnerabilities, security_hotspots, security_rating,
    reliability_rating, bugs, ncloc, source, available.
    """
    global _sonar_cache
    if _sonar_cache is not None:
        return _sonar_cache

    try:
        from ai_engineering.policy.checks.sonar import query_sonar_measures

        raw = query_sonar_measures(project_root)
    except Exception:
        raw = None

    if raw is None:
        _sonar_cache = {"available": False, "source": "none"}
        return _sonar_cache

    rating_map = {1.0: "A", 2.0: "B", 3.0: "C", 4.0: "D", 5.0: "E"}

    _sonar_cache = {
        "available": True,
        "source": "sonarcloud",
        "coverage_pct": raw.get("coverage", 0.0),
        "cognitive_complexity": int(raw.get("cognitive_complexity", 0)),
        "duplication_pct": raw.get("duplicated_lines_density", 0.0),
        "vulnerabilities": int(raw.get("vulnerabilities", 0)),
        "security_hotspots": int(raw.get("security_hotspots", 0)),
        "security_rating": rating_map.get(raw.get("security_rating", 0), "?"),
        "reliability_rating": rating_map.get(raw.get("reliability_rating", 0), "?"),
        "bugs": int(raw.get("bugs", 0)),
        "ncloc": int(raw.get("ncloc", 0)),
    }
    return _sonar_cache


def _reset_sonar_cache() -> None:
    """Reset the sonar cache (for testing)."""
    global _sonar_cache
    _sonar_cache = None


# ---------------------------------------------------------------------------
# Test confidence metrics (fallback chain)
# ---------------------------------------------------------------------------


def test_confidence_metrics(project_root: Path) -> dict[str, Any]:
    """Compute test confidence from best available source.

    Fallback chain: SonarCloud -> coverage.json -> test_scope -> defaults.
    """
    # Source 1: SonarCloud coverage
    sonar = sonar_detailed_metrics(project_root)
    if sonar.get("available") and sonar.get("coverage_pct", 0) > 0:
        return {
            "source": "sonarcloud",
            "coverage_pct": sonar["coverage_pct"],
            "meets_threshold": sonar["coverage_pct"] >= 80,
            "files_total": 0,
            "files_covered": 0,
            "untested_critical": [],
        }

    # Source 2: Local coverage.json
    coverage_file = project_root / "coverage.json"
    if coverage_file.exists():
        try:
            data = json.loads(coverage_file.read_text(encoding="utf-8"))
            totals = data.get("totals", {})
            pct = totals.get("percent_covered", 0.0)
            # Count files
            file_data = data.get("files", {})
            files_total = len(file_data)
            files_covered = sum(
                1 for f in file_data.values() if f.get("summary", {}).get("percent_covered", 0) > 0
            )
            # Find untested files (0% coverage)
            untested = [
                name
                for name, info in file_data.items()
                if info.get("summary", {}).get("percent_covered", 0) == 0
            ]
            return {
                "source": "coverage.json",
                "coverage_pct": round(pct, 1),
                "meets_threshold": pct >= 80,
                "files_total": files_total,
                "files_covered": files_covered,
                "untested_critical": untested[:5],  # Top 5 untested
            }
        except Exception:
            pass

    # Source 3: Test scope mapping
    try:
        from ai_engineering.policy.test_scope import TEST_SCOPE_RULES

        # Count unique source globs across all rules
        all_source_globs: set[str] = set()
        for rule in TEST_SCOPE_RULES:
            all_source_globs.update(rule.source_globs)
        # Count source files in src/
        src_dir = project_root / "src"
        src_files = list(src_dir.rglob("*.py")) if src_dir.is_dir() else []
        src_files = [f for f in src_files if f.name != "__init__.py"]
        total = len(src_files)
        # Count files matching at least one scope rule glob
        from fnmatch import fnmatch

        mapped = 0
        for sf in src_files:
            rel = str(sf.relative_to(project_root))
            for glob_pattern in all_source_globs:
                if fnmatch(rel, glob_pattern):
                    mapped += 1
                    break
        pct = round(mapped / total * 100, 1) if total > 0 else 0.0
        return {
            "source": "test_scope",
            "coverage_pct": pct,
            "meets_threshold": pct >= 80,
            "files_total": total,
            "files_covered": mapped,
            "untested_critical": [],
        }
    except Exception:
        pass

    # Source 4: No data
    return {
        "source": "none",
        "coverage_pct": 0.0,
        "meets_threshold": False,
        "files_total": 0,
        "files_covered": 0,
        "untested_critical": [],
    }


# ---------------------------------------------------------------------------
# Security posture metrics (fallback chain)
# ---------------------------------------------------------------------------


def security_posture_metrics(project_root: Path) -> dict:
    """Compute security posture from best available source.

    Fallback chain: SonarCloud -> pip-audit -> defaults.
    """
    import subprocess

    result: dict[str, Any] = {
        "source": "none",
        "vulnerabilities": 0,
        "security_hotspots": 0,
        "security_rating": "?",
        "dep_vulns": 0,
    }

    # Source 1: SonarCloud
    sonar = sonar_detailed_metrics(project_root)
    if sonar.get("available"):
        result["source"] = "sonarcloud"
        result["vulnerabilities"] = sonar.get("vulnerabilities", 0)
        result["security_hotspots"] = sonar.get("security_hotspots", 0)
        result["security_rating"] = sonar.get("security_rating", "?")

    # Dependency vulnerabilities via pip-audit (independent of SonarCloud)
    try:
        proc = subprocess.run(
            ["pip-audit", "--format=json", "--output=-"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=project_root,
        )
        if proc.returncode == 0:
            audit_data = json.loads(proc.stdout)
            if isinstance(audit_data, list):
                result["dep_vulns"] = len(audit_data)
            elif isinstance(audit_data, dict):
                result["dep_vulns"] = len(audit_data.get("dependencies", []))
            if result["source"] == "none":
                result["source"] = "pip-audit"
            else:
                result["source"] += "+pip-audit"
        else:
            # pip-audit returns non-zero when vulns found
            try:
                audit_data = json.loads(proc.stdout)
                if isinstance(audit_data, list):
                    result["dep_vulns"] = len(audit_data)
                elif isinstance(audit_data, dict):
                    vulns = audit_data.get("dependencies", [])
                    result["dep_vulns"] = sum(1 for d in vulns if d.get("vulns"))
            except (json.JSONDecodeError, TypeError):
                pass
            if result["source"] == "none":
                result["source"] = "pip-audit"
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass

    return result


# ---------------------------------------------------------------------------
# Health history persistence
# ---------------------------------------------------------------------------

HEALTH_HISTORY_REL = Path(".ai-engineering") / "state" / "health-history.json"
_MAX_HISTORY_ENTRIES = 12


def save_health_snapshot(
    project_root: Path,
    overall: int,
    semaphore: str,
    components: dict[str, float],
) -> None:
    """Append a weekly health snapshot. Max 12 entries (rolling)."""
    path = project_root / HEALTH_HISTORY_REL
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    entries: list[dict[str, Any]] = []
    with contextlib.suppress(Exception):
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            entries = data.get("entries", [])

    # Deduplicate: replace entry for same date
    entries = [e for e in entries if e.get("date") != today]
    entries.append(
        {
            "date": today,
            "overall": overall,
            "semaphore": semaphore,
            "components": components,
        }
    )

    # Keep rolling window
    if len(entries) > _MAX_HISTORY_ENTRIES:
        entries = entries[-_MAX_HISTORY_ENTRIES:]

    with contextlib.suppress(Exception):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"entries": entries}, indent=2) + "\n",
            encoding="utf-8",
        )


def load_health_history(project_root: Path) -> list[dict[str, Any]]:
    """Load health history entries (oldest first)."""
    path = project_root / HEALTH_HISTORY_REL
    with contextlib.suppress(Exception):
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            entries = data.get("entries", [])
            if isinstance(entries, list):
                return entries
    return []


def health_direction(history: list[dict[str, Any]], current: int) -> str:
    """Compute direction indicator from history.

    Returns: "↑" (improving), "↓" (degrading), "→" (stable), "" (no history).
    """
    if len(history) < 1:
        return ""
    previous = history[-1].get("overall", current)
    diff = current - previous
    if diff > 2:
        return "↑"
    if diff < -2:
        return "↓"
    return "→"
