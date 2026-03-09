"""Observe CLI commands for ai-engineering.

Computes and displays observability metrics across 5 modes:
- engineer: code quality, security, test confidence, delivery velocity
- team: framework health, skill usage, token economy
- ai: context efficiency, decision continuity, session recovery
- dora: deployment frequency, lead time, MTTR, change failure rate
- health: aggregated 0-100 score with semaphore
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import typer

from ai_engineering.lib.signals import (
    data_quality_from,
    event_date_range_from,
    filter_events,
    gate_pass_rate_from,
    load_all_events,
)


def _project_root() -> Path:
    """Resolve project root from CWD."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".ai-engineering").is_dir():
            return parent
    return cwd


def _git_log_stat(project_root: Path, days: int = 30) -> dict:
    """Get git log statistics for the last N days."""
    since = (datetime.now(tz=UTC) - timedelta(days=days)).strftime(
        "%Y-%m-%d",
    )
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--oneline"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        commits = len(result.stdout.strip().splitlines()) if result.stdout.strip() else 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        commits = 0

    weeks = max(days / 7, 1)
    return {
        "commits": commits,
        "commits_per_week": round(commits / weeks, 1),
        "period_days": days,
    }


def _dora_metrics(
    project_root: Path,
    git_stats: dict | None = None,
) -> dict:
    """Compute DORA metrics from git history."""
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "--merges",
                "--first-parent",
                "main",
                "--since=30 days ago",
                "--oneline",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        merges = len(result.stdout.strip().splitlines()) if result.stdout.strip() else 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        merges = 0

    deploy_freq = round(merges / 4.3, 1)
    if git_stats is None:
        git_stats = _git_log_stat(project_root)

    return {
        "deployment_frequency_per_week": deploy_freq,
        "total_merges_30d": merges,
        "commits_per_week": git_stats["commits_per_week"],
        "total_commits_30d": git_stats["commits"],
    }


def _sonar_metrics(project_root: Path) -> list[str]:
    """Fetch SonarCloud metrics for observe dashboard (silent-skip if unconfigured)."""
    try:
        from ai_engineering.policy.checks.sonar import query_sonar_quality_gate

        qg = query_sonar_quality_gate(project_root)
        if qg is None:
            return []

        status = qg.get("status", "UNKNOWN")
        conditions = qg.get("conditions", [])
        coverage_val = ""
        for cond in conditions:
            if cond.get("metricKey") == "new_coverage":
                coverage_val = cond.get("actualValue", "N/A")
                break

        lines = [
            "",
            "## SonarCloud Quality Gate",
            f"- Status: {status}",
        ]
        if coverage_val:
            lines.append(f"- New code coverage: {coverage_val}%")
        lines.append(f"- Conditions: {len(conditions)}")
        return lines
    except Exception:
        return []


def observe_engineer(project_root: Path) -> str:
    """Generate engineer dashboard."""
    all_events = load_all_events(project_root)
    dq = data_quality_from(all_events)
    gates = gate_pass_rate_from(all_events)
    git_stats = _git_log_stat(project_root)
    total_events = len(all_events)
    oldest, newest = event_date_range_from(all_events)
    days_span = (newest - oldest).days if oldest and newest else 0

    lines = [
        "# Engineer Dashboard",
        "",
        f"Data quality: {dq} ({total_events} events, {days_span} days)",
        "",
        "## Delivery Velocity",
        f"- Commits/week: {git_stats['commits_per_week']}",
        f"- Total commits (30d): {git_stats['commits']}",
        "",
        "## Gate Health (last 30 days)",
        f"- Total gate runs: {gates['total']}",
        f"- Pass rate: {gates['pass_rate']}%",
        f"- Most failed check: {gates['most_failed_check']} ({gates['most_failed_count']}x)",
    ]

    lines.extend(_sonar_metrics(project_root))

    lines.extend(
        [
            "",
            "## Actions",
            "- Run `/ai:scan quality` for code quality metrics",
            "- Run `/ai:scan security` for security posture",
            "- Run `/ai:test gap` for test confidence",
        ]
    )
    return "\n".join(lines)


def _count_by_type(
    all_events: list[dict[str, Any]],
    event_type: str,
) -> int:
    """Count events of a specific type from pre-loaded list."""
    return sum(1 for e in all_events if e.get("event") == event_type)


def observe_team(project_root: Path) -> str:
    """Generate team dashboard."""
    all_events = load_all_events(project_root)
    dq = data_quality_from(all_events)
    gates = gate_pass_rate_from(all_events)

    lines = [
        "# Team Dashboard",
        "",
        f"Data quality: {dq} ({len(all_events)} events)",
        "",
        "## Event Distribution",
        f"- Gate events: {gates['total']}",
        f"- Scan events: {_count_by_type(all_events, 'scan_complete')}",
        f"- Build events: {_count_by_type(all_events, 'build_complete')}",
        f"- Session events: {_count_by_type(all_events, 'session_metric')}",
        "",
        "## Gate Health",
        f"- Pass rate: {gates['pass_rate']}%",
        f"- Most friction: {gates['most_failed_check']}",
        "",
        "## Actions",
        "- Run `/ai:scan governance` for framework health",
        "- Review decision store for expired decisions",
    ]
    return "\n".join(lines)


def observe_ai(project_root: Path) -> str:
    """Generate AI self-awareness dashboard."""
    all_events = load_all_events(project_root)
    dq = data_quality_from(all_events)
    session_events = filter_events(
        all_events,
        event_type="session_metric",
        limit=10,
    )

    total_tokens = 0
    decisions_reused = 0
    decisions_reprompted = 0
    for event in session_events:
        detail = event.get("detail", {})
        if isinstance(detail, dict):
            total_tokens += detail.get("tokens_used", 0)
            decisions_reused += detail.get("decisions_reused", 0)
            decisions_reprompted += detail.get(
                "decisions_reprompted",
                0,
            )

    total_decisions = decisions_reused + decisions_reprompted
    if total_decisions > 0:
        cache_hit_rate = round(
            decisions_reused / total_decisions * 100,
            1,
        )
    else:
        cache_hit_rate = 0.0

    lines = [
        "# AI Self-Awareness",
        "",
        f"Data quality: {dq}",
        "",
        "## Context Efficiency",
        f"- Recent sessions analyzed: {len(session_events)}",
        f"- Total tokens used (recent): {total_tokens:,}",
        "",
        "## Decision Continuity",
        f"- Decisions reused: {decisions_reused}",
        f"- Decisions re-prompted: {decisions_reprompted}",
        f"- Cache hit rate: {cache_hit_rate}%",
        "",
        "## Actions",
        "- Review decision store for expiring decisions",
        "- Check session checkpoint for recovery state",
    ]
    return "\n".join(lines)


def observe_dora(project_root: Path) -> str:
    """Generate DORA metrics dashboard."""
    all_events = load_all_events(project_root)
    dq = data_quality_from(all_events)
    dora = _dora_metrics(project_root)

    freq = dora["deployment_frequency_per_week"]
    if freq >= 5:
        freq_rating = "ELITE"
    elif freq >= 1:
        freq_rating = "HIGH"
    elif freq >= 0.25:
        freq_rating = "MEDIUM"
    else:
        freq_rating = "LOW"

    lines = [
        "# DORA Metrics (last 30 days)",
        "",
        f"Data quality: {dq}",
        "",
        "## Deployment Frequency",
        f"- Merges to main/week: {freq}",
        f"- Rating: {freq_rating}",
        "",
        "## Delivery Velocity",
        f"- Commits/week: {dora['commits_per_week']}",
        f"- Total commits (30d): {dora['total_commits_30d']}",
        "",
        "## Benchmarks",
        "- Elite: multiple deploys/day, lead time <1h",
        "- High: weekly deploys, lead time <1 week",
        "- Medium: monthly deploys, lead time <1 month",
    ]
    return "\n".join(lines)


def observe_health(project_root: Path) -> str:
    """Generate aggregated health score."""
    all_events = load_all_events(project_root)
    dq = data_quality_from(all_events)
    gates = gate_pass_rate_from(all_events)
    git_stats = _git_log_stat(project_root)
    dora = _dora_metrics(project_root, git_stats=git_stats)

    gate_score = min(gates["pass_rate"], 100)
    velocity_score = min(git_stats["commits_per_week"] * 10, 100)
    overall = round((gate_score + velocity_score) / 2)

    if overall >= 80:
        semaphore = "GREEN"
    elif overall >= 60:
        semaphore = "YELLOW"
    else:
        semaphore = "RED"

    lines = [
        f"# Health Score: {overall}/100 ({semaphore})",
        "",
        f"Data quality: {dq}",
        "",
        "## Components",
        f"- Gate pass rate: {gates['pass_rate']}%",
        f"- Delivery velocity: {git_stats['commits_per_week']} commits/week",
        f"- Deploy frequency: {dora['deployment_frequency_per_week']}/week",
        "",
        "## Semaphore",
        f"- Status: {semaphore}",
        f"- Score: {overall}/100",
        "",
        "## Top Actions",
        "- Run `/ai:scan platform` for full dimensional assessment",
        "- Run `/ai:observe dora` for delivery benchmarks",
        "- Run `/ai:observe engineer` for code quality details",
    ]
    return "\n".join(lines)


_MODE_FUNCS = {
    "engineer": observe_engineer,
    "team": observe_team,
    "ai": observe_ai,
    "dora": observe_dora,
    "health": observe_health,
}


def observe_cmd(
    mode: Annotated[
        str,
        typer.Argument(
            help="Dashboard mode: engineer | team | ai | dora | health",
        ),
    ] = "health",
) -> None:
    """Generate observability dashboard for the specified audience."""
    if mode not in _MODE_FUNCS:
        typer.echo(
            f"Unknown mode: {mode}. Valid: {', '.join(_MODE_FUNCS)}",
            err=True,
        )
        raise typer.Exit(code=1)

    root = _project_root()
    output = _MODE_FUNCS[mode](root)
    typer.echo(output)
