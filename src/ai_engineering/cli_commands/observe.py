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
    adoption_metrics,
    build_metrics_from,
    checkpoint_status,
    data_quality_from,
    decision_store_health,
    deploy_metrics_from,
    event_date_range_from,
    filter_events,
    gate_pass_rate_from,
    health_direction,
    lead_time_metrics,
    load_all_events,
    load_health_history,
    save_health_snapshot,
    scan_metrics_from,
    security_posture_metrics,
    session_metrics_from,
    sonar_detailed_metrics,
    test_confidence_metrics,
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

        # Enrich with detailed measures if available
        sonar = sonar_detailed_metrics(project_root)
        if sonar.get("available"):
            lines.append(f"- Coverage: {sonar['coverage_pct']}%")
            lines.append(f"- Complexity: {sonar['cognitive_complexity']}")
            lines.append(f"- Duplication: {sonar['duplication_pct']}%")
            lines.append(
                f"- Issues: {sonar['bugs']} bugs, {sonar['vulnerabilities']} vulnerabilities"
            )

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

    lt = lead_time_metrics(project_root)

    lines = [
        "# Engineer Dashboard",
        "",
        f"Data quality: {dq} ({total_events} events, {days_span} days)",
        "",
        "## Delivery Velocity",
        f"- Commits/week: {git_stats['commits_per_week']}",
        f"- Total commits (30d): {git_stats['commits']}",
        f"- Lead time (median): {lt['median_days']} days",
        "",
        "## Gate Health (last 30 days)",
        f"- Total gate runs: {gates['total']}",
        f"- Pass rate: {gates['pass_rate']}%",
        f"- Most failed check: {gates['most_failed_check']} ({gates['most_failed_count']}x)",
    ]

    lines.extend(_sonar_metrics(project_root))

    # Lead Time section
    lines.append("")
    lines.append("## Lead Time")
    if lt["merges_analyzed"] == 0:
        lines.append("- Insufficient merge data")
    else:
        lines.append(f"- Median: {lt['median_days']} days")
        lines.append(f"- Rating: {lt['rating']}")
        lines.append(f"- Merges analyzed: {lt['merges_analyzed']}")

    # Code Quality from scans
    scan = scan_metrics_from(all_events)
    lines.append("")
    lines.append("## Code Quality (from scans)")
    if scan["total_scans"] == 0:
        lines.append("- No scan data — run /ai:scan quality")
    else:
        lines.append(f"- Quality score: {scan['avg_quality_score']}/100")
        lines.append(f"- Security score: {scan['avg_security_score']}/100")
        findings = scan["findings"]
        lines.append(
            f"- Findings: {findings['critical']} critical, {findings['high']} high",
        )

    # Build Activity
    build = build_metrics_from(all_events)
    lines.append("")
    lines.append("## Build Activity (last 30d)")
    if build["total_builds"] == 0:
        lines.append("- No build data")
    else:
        lines.append(f"- Builds: {build['total_builds']}")
        lines.append(
            f"- Files changed: {build['files_changed']}, Tests added: {build['tests_added']}",
        )

    # Security Posture
    sec = security_posture_metrics(project_root)
    lines.append("")
    lines.append("## Security Posture")
    if sec["source"] == "none":
        lines.append("- No data — run `ai-eng setup sonar` or install pip-audit")
    else:
        lines.append(f"- Vulnerabilities: {sec['vulnerabilities']} ({sec['source']})")
        lines.append(f"- Security hotspots: {sec['security_hotspots']}")
        lines.append(f"- Security rating: {sec['security_rating']}")
        lines.append(f"- Dependency vulnerabilities: {sec['dep_vulns']}")

    # Test Confidence
    tc = test_confidence_metrics(project_root)
    lines.append("")
    lines.append("## Test Confidence")
    if tc["source"] == "none":
        lines.append("- No data — run `pytest --cov` or configure SonarCloud")
    else:
        lines.append(f"- Coverage: {tc['coverage_pct']}% ({tc['source']})")
        if tc["files_total"] > 0:
            lines.append(f"- Files covered: {tc['files_covered']}/{tc['files_total']}")
        threshold_status = "yes" if tc["meets_threshold"] else "no"
        lines.append(f"- Meets threshold (80%): {threshold_status}")
        if tc["untested_critical"]:
            lines.append(f"- Untested critical: {', '.join(tc['untested_critical'][:3])}")

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
        f"- Deploy events: {_count_by_type(all_events, 'deploy_complete')}",
        "",
        "## Gate Health",
        f"- Pass rate: {gates['pass_rate']}%",
        f"- Most friction: {gates['most_failed_check']}",
    ]

    # Decision Store Health
    dsh = decision_store_health(project_root)
    lines.append("")
    lines.append("## Decision Store Health")
    if dsh["total"] == 0:
        lines.append("- No decisions recorded")
    else:
        lines.append(
            f"- Active: {dsh['active']}, Expired (need review): {dsh['expired']}, "
            f"Resolved: {dsh['resolved']}",
        )
        lines.append(f"- Avg age: {dsh['avg_age_days']} days")

    # Adoption
    adopt = adoption_metrics(project_root)
    lines.append("")
    lines.append("## Adoption")
    lines.append(f"- Stacks: {', '.join(adopt['stacks']) if adopt['stacks'] else 'none'}")
    lines.append(f"- Providers: {adopt['providers']['primary']}")
    lines.append(f"- IDEs: {', '.join(adopt['ides']) if adopt['ides'] else 'none'}")
    hooks_status = "installed" if adopt["hooks_installed"] else "not installed"
    if adopt["hooks_installed"]:
        hooks_status += "/verified" if adopt["hooks_verified"] else "/unverified"
    lines.append(f"- Hooks: {hooks_status}")

    # Scan Health
    scan = scan_metrics_from(all_events)
    lines.append("")
    lines.append("## Scan Health")
    if scan["total_scans"] == 0:
        lines.append("- No scan data")
    else:
        lines.append(f"- Avg quality score: {scan['avg_quality_score']}/100")
        lines.append(f"- Scans run: {scan['total_scans']}")

    lines.extend(
        [
            "",
            "## Actions",
            "- Run `/ai:scan governance` for framework health",
            "- Review decision store for expired decisions",
        ]
    )
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

    # Expanded context efficiency via session_metrics_from
    sm = session_metrics_from(all_events)
    skills_list = ", ".join(sm["skills_loaded"]) if sm["skills_loaded"] else "none"

    lines = [
        "# AI Self-Awareness",
        "",
        f"Data quality: {dq}",
        "",
        "## Context Efficiency",
        f"- Sessions analyzed: {sm['sessions_analyzed']}",
        f"- Total tokens (recent): {sm['total_tokens']:,}",
        f"- Token utilization: {sm['total_tokens']}/{sm['tokens_available']}"
        f" ({sm['utilization_pct']}%)",
        f"- Skills loaded: {skills_list}",
        "",
        "## Decision Continuity",
        f"- Decisions reused: {decisions_reused}",
        f"- Decisions re-prompted: {decisions_reprompted}",
        f"- Cache hit rate: {cache_hit_rate}%",
    ]

    # Session Recovery
    cp = checkpoint_status(project_root)
    lines.append("")
    lines.append("## Session Recovery")
    if not cp["has_checkpoint"]:
        lines.append("- No checkpoint found")
    else:
        lines.append(f"- Last checkpoint: {cp['last_task']} ({cp['age']})")
        lines.append(
            f"- Progress: {cp['completed']}/{cp['total']} ({cp['progress_pct']}%)",
        )
        blocked = cp.get("blocked_on") or "nothing"
        lines.append(f"- Blocked on: {blocked}")

    # Self-Optimization Hints
    hints: list[str] = []
    if total_decisions > 0 and cache_hit_rate < 50:
        hints.append("- Low decision reuse — save key decisions to decision-store")
    gates = gate_pass_rate_from(all_events)
    if gates["total"] > 0 and gates["pass_rate"] < 80:
        hints.append("- High gate failure rate — run `ruff format` before committing")
    if not cp["has_checkpoint"]:
        hints.append("- No checkpoint — use `ai-eng checkpoint save` for session recovery")
    if sm["utilization_pct"] > 90:
        hints.append("- Token utilization >90% — sessions near context limit")
    if sm["sessions_analyzed"] == 0:
        hints.append("- No session data — checkpoint save emits session metrics")
    if not hints:
        hints.append("- All patterns healthy — no optimization needed")

    lines.append("")
    lines.append("## Self-Optimization Hints")
    lines.extend(hints)

    lines.extend(
        [
            "",
            "## Actions",
            "- Review decision store for expiring decisions",
            "- Check session checkpoint for recovery state",
        ]
    )
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
    ]

    # Lead Time for Changes
    lt = lead_time_metrics(project_root)
    lines.append("")
    lines.append("## Lead Time for Changes")
    lines.append(f"- Median: {lt['median_days']} days")
    lines.append(f"- Rating: {lt['rating']}")

    # Change Failure Rate
    deploy = deploy_metrics_from(all_events)
    cfr_pct = deploy["failure_rate"]
    if cfr_pct <= 15:
        cfr_rating = "ELITE"
    elif cfr_pct <= 30:
        cfr_rating = "HIGH"
    elif cfr_pct <= 45:
        cfr_rating = "MEDIUM"
    else:
        cfr_rating = "LOW"

    lines.append("")
    lines.append("## Change Failure Rate")
    lines.append(f"- Deployments: {deploy['total_deploys']}")
    lines.append(f"- Rollbacks: {deploy['rollbacks']}")
    lines.append(f"- Rate: {cfr_pct}%")
    lines.append(f"- Rating: {cfr_rating}")

    lines.extend(
        [
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
    )
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

    # Multi-variable weighted score
    components: list[float] = [gate_score, velocity_score]
    component_names: list[str] = ["Gate pass rate", "Delivery velocity"]

    scan = scan_metrics_from(all_events)
    if scan["total_scans"] > 0:
        scan_score = scan["avg_quality_score"]
        components.append(scan_score)
        component_names.append("Scan quality")
    else:
        scan_score = None

    dsh = decision_store_health(project_root)
    if dsh["total"] > 0:
        decision_score = max(0, 100 - dsh["expired"] * 20)
        components.append(decision_score)
        component_names.append("Decision health")
    else:
        decision_score = None

    freq = dora["deployment_frequency_per_week"]
    if freq >= 5:
        dora_score: float = 100
    elif freq >= 1:
        dora_score = 75
    elif freq >= 0.25:
        dora_score = 50
    else:
        dora_score = 25
    components.append(dora_score)
    component_names.append("DORA frequency")

    # SonarCloud score (from detailed measures)
    sonar = sonar_detailed_metrics(project_root)
    if sonar.get("available") and sonar.get("coverage_pct", 0) > 0:
        sonar_score: float | None = sonar["coverage_pct"]
        components.append(sonar_score)
        component_names.append("SonarCloud coverage")
    else:
        sonar_score = None

    # Test confidence score
    tc = test_confidence_metrics(project_root)
    if tc["source"] != "none" and tc["coverage_pct"] > 0:
        tc_score: float | None = tc["coverage_pct"]
        components.append(tc_score)
        component_names.append("Test confidence")
    else:
        tc_score = None

    overall = round(sum(components) / len(components))

    if overall >= 80:
        semaphore = "GREEN"
    elif overall >= 60:
        semaphore = "YELLOW"
    else:
        semaphore = "RED"

    # Direction indicator from history
    history = load_health_history(project_root)
    direction = health_direction(history, overall)
    direction_suffix = f" {direction}" if direction else ""

    lines = [
        f"# Health Score: {overall}/100 ({semaphore}){direction_suffix}",
        "",
        f"Data quality: {dq}",
        "",
        "## Components",
        f"- Gate pass rate: {gates['pass_rate']}% -> {gate_score}/100",
        f"- Delivery velocity: {git_stats['commits_per_week']}/week -> {velocity_score}/100",
    ]
    if scan_score is not None:
        lines.append(f"- Scan quality: {scan_score}/100")
    else:
        lines.append("- Scan quality: No data")
    if decision_score is not None:
        lines.append(f"- Decision health: {decision_score}/100")
    else:
        lines.append("- Decision health: No decisions")
    lines.append(f"- DORA frequency: {freq}/week -> {dora_score}/100")
    if sonar_score is not None:
        lines.append(f"- SonarCloud coverage: {sonar_score}% -> {sonar_score}/100")
    else:
        lines.append("- SonarCloud coverage: No data")
    if tc_score is not None:
        lines.append(f"- Test confidence: {tc_score}% -> {tc_score}/100")
    else:
        lines.append("- Test confidence: No data")

    lines.extend(
        [
            "",
            f"## Semaphore: {semaphore}",
        ]
    )

    # Smart actions: find weakest components and suggest fixes
    _ACTION_MAP: dict[str, str] = {
        "Gate pass rate": "Run `ruff format` + `ruff check --fix` before committing",
        "Delivery velocity": "Increase commit frequency — ship smaller changes",
        "Scan quality": "Run `/ai:scan quality` to improve code quality score",
        "Decision health": "Run `ai-eng decision expire-check` to review expired decisions",
        "DORA frequency": "Merge PRs more frequently — target weekly deploys",
        "SonarCloud coverage": "Run `ai-eng setup sonar` and increase test coverage",
        "Test confidence": "Run `pytest --cov` to generate coverage data",
    }
    scored = list(zip(component_names, components, strict=True))
    scored.sort(key=lambda x: x[1])
    num_c = len(components)
    actions: list[str] = []
    for name, score in scored[:3]:
        if score >= 90:
            continue
        gain = round((100 - score) / num_c)
        cmd = _ACTION_MAP.get(name, f"Improve {name}")
        actions.append(f"- {cmd} (+{gain} pts)")
    if not actions:
        actions.append("- All components healthy — maintain current practices")
    lines.append("")
    lines.append("## Top Actions")
    lines.extend(actions)

    # Persist snapshot for trend tracking
    comp_dict = dict(zip(component_names, components, strict=True))
    save_health_snapshot(project_root, overall, semaphore, comp_dict)

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
