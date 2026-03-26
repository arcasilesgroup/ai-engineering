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


def count_events_by_type(
    events: list[dict[str, Any]],
    event_type: str,
) -> int:
    """Count events of a specific type from a pre-loaded list.

    Args:
        events: Pre-loaded event list from load_all_events().
        event_type: The event type string to match against each event's "event" field.

    Returns:
        Number of events matching the given type.
    """
    return sum(1 for e in events if e.get("event") == event_type)


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
    _ACC_FIELDS = ("files_changed", "lines_added", "lines_removed", "tests_added")
    accumulators: dict[str, int] = dict.fromkeys(_ACC_FIELDS, 0)

    for event in build_events:
        for field in _ACC_FIELDS:
            val = _detail_field(event, field)
            if val is not None:
                with contextlib.suppress(TypeError, ValueError):
                    accumulators[field] += int(val)

    return {"total_builds": total_builds, **accumulators}


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
            # Normalize: lowercase + ensure ai- prefix
            name = name.lower().removeprefix("ai-").removeprefix("ai:")
            name = f"ai-{name}"
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
            # Normalize: lowercase + ensure ai- prefix
            name = name.lower().removeprefix("ai-").removeprefix("ai:")
            name = f"ai-{name}"
            by_agent[name] = by_agent.get(name, 0) + 1

    sorted_agents = dict(sorted(by_agent.items(), key=lambda x: x[1], reverse=True))
    total = sum(sorted_agents.values())

    return {
        "total_dispatches": total,
        "by_agent": sorted_agents,
    }


def guard_advisory_from(
    events: list[dict[str, Any]],
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Aggregate guard_advisory events into advisory metrics.

    Args:
        events: Pre-loaded event list from load_all_events().
        days: Window in days to consider.

    Returns:
        Dict with total_advisories, total_warnings, total_concerns.
    """
    since = datetime.now(tz=UTC) - timedelta(days=days)
    advisory_events = filter_events(events, event_type="guard_advisory", since=since)

    total_warnings = 0
    total_concerns = 0
    for event in advisory_events:
        total_warnings += _detail_field(event, "warnings") or 0
        total_concerns += _detail_field(event, "concerns") or 0

    return {
        "total_advisories": len(advisory_events),
        "total_warnings": total_warnings,
        "total_concerns": total_concerns,
    }


def guard_drift_from(
    events: list[dict[str, Any]],
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Aggregate guard_drift events into drift metrics.

    Args:
        events: Pre-loaded event list from load_all_events().
        days: Window in days to consider.

    Returns:
        Dict with total_checks, total_drifted, total_critical, alignment_pct.
    """
    since = datetime.now(tz=UTC) - timedelta(days=days)
    drift_events = filter_events(events, event_type="guard_drift", since=since)

    total_checked = 0
    total_drifted = 0
    total_critical = 0
    for event in drift_events:
        total_checked += _detail_field(event, "decisions_checked") or 0
        total_drifted += _detail_field(event, "drifted") or 0
        total_critical += _detail_field(event, "critical") or 0

    if total_checked > 0:
        alignment_pct = round((1 - total_drifted / total_checked) * 100, 1)
    else:
        alignment_pct = 0.0

    return {
        "total_checks": len(drift_events),
        "total_decisions_checked": total_checked,
        "total_drifted": total_drifted,
        "total_critical": total_critical,
        "alignment_pct": alignment_pct,
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
    """Read manifest.yml config and install-state.json to compute adoption metrics.

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
        from ai_engineering.config.loader import load_manifest_config
        from ai_engineering.state.service import load_install_state

        config = load_manifest_config(project_root)
        state_dir = project_root / ".ai-engineering" / "state"
        state = load_install_state(state_dir)

        stacks = list(config.providers.stacks)
        ides = list(config.providers.ides)
        providers = {
            "primary": config.ai_providers.primary,
            "enabled": list(config.ai_providers.enabled),
        }

        git_hooks_entry = state.tooling.get("git_hooks")
        hooks_installed = git_hooks_entry.installed if git_hooks_entry else False
        hooks_verified = git_hooks_entry.integrity_verified if git_hooks_entry else False

        return {
            "stacks": stacks,
            "providers": providers,
            "ides": ides,
            "hooks_installed": hooks_installed,
            "hooks_verified": hooks_verified,
        }
    except Exception:
        return defaults


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

    Fallback chain: SonarCloud -> coverage.json -> defaults.
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

    # Source 3: No data
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
