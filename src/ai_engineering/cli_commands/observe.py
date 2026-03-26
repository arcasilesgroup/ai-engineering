"""Observe CLI commands for ai-engineering.

Computes and displays observability metrics across 5 modes:
- engineer: code quality, security, test confidence, delivery velocity
- team: framework health, skill usage, guard governance
- ai: context efficiency, decision continuity, skill/agent efficiency
- dora: deployment frequency, lead time, MTTR, change failure rate
- health: aggregated 0-100 score with semaphore
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import typer

from ai_engineering.cli_envelope import NextAction
from ai_engineering.cli_output import output as route_output
from ai_engineering.cli_output import set_json_mode
from ai_engineering.lib.signals import (
    adoption_metrics,
    agent_dispatch_from,
    build_metrics_from,
    count_events_by_type,
    data_quality_from,
    decision_store_health,
    deploy_metrics_from,
    event_date_range_from,
    filter_events,
    gate_pass_rate_from,
    guard_advisory_from,
    guard_drift_from,
    lead_time_metrics,
    load_all_events,
    noise_ratio_from,
    scan_metrics_from,
    security_posture_metrics,
    skill_usage_from,
    sonar_detailed_metrics,
    test_confidence_metrics,
)
from ai_engineering.paths import find_project_root


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


def _sonar_metrics_data(project_root: Path) -> dict[str, Any]:
    """Fetch SonarCloud metrics for observe dashboard (silent-skip if unconfigured)."""
    try:
        from ai_engineering.policy.checks.sonar import query_sonar_quality_gate

        qg = query_sonar_quality_gate(project_root)
        if qg is None:
            return {"available": False}

        status = qg.get("status", "UNKNOWN")
        conditions = qg.get("conditions", [])
        coverage_val = ""
        for cond in conditions:
            if cond.get("metricKey") == "new_coverage":
                coverage_val = cond.get("actualValue", "N/A")
                break

        data: dict[str, Any] = {
            "available": True,
            "status": status,
            "conditions_count": len(conditions),
            "new_code_coverage": coverage_val if coverage_val else None,
        }

        # Enrich with detailed measures if available
        sonar = sonar_detailed_metrics(project_root)
        if sonar.get("available"):
            data["detailed"] = {
                "coverage_pct": sonar["coverage_pct"],
                "cognitive_complexity": sonar["cognitive_complexity"],
                "duplication_pct": sonar["duplication_pct"],
                "bugs": sonar["bugs"],
                "vulnerabilities": sonar["vulnerabilities"],
            }

        return data
    except Exception:
        return {"available": False}


# ---------------------------------------------------------------------------
# Mode functions: each returns a structured dict
# ---------------------------------------------------------------------------


def observe_engineer(project_root: Path) -> dict[str, Any]:
    """Generate engineer dashboard data."""
    all_events = load_all_events(project_root)
    dq = data_quality_from(all_events)
    gates = gate_pass_rate_from(all_events)
    git_stats = _git_log_stat(project_root)
    total_events = len(all_events)
    oldest, newest = event_date_range_from(all_events)
    days_span = (newest - oldest).days if oldest and newest else 0

    lt = lead_time_metrics(project_root)
    sonar_data = _sonar_metrics_data(project_root)
    scan = scan_metrics_from(all_events)
    build = build_metrics_from(all_events)
    sec = security_posture_metrics(project_root)
    tc = test_confidence_metrics(project_root)

    return {
        "data_quality": dq,
        "total_events": total_events,
        "days_span": days_span,
        "delivery_velocity": {
            "commits_per_week": git_stats["commits_per_week"],
            "total_commits_30d": git_stats["commits"],
            "lead_time_median_days": lt["median_days"],
        },
        "gate_health": {
            "total": gates["total"],
            "pass_rate": gates["pass_rate"],
            "most_failed_check": gates["most_failed_check"],
            "most_failed_count": gates["most_failed_count"],
        },
        "sonar": sonar_data,
        "lead_time": {
            "merges_analyzed": lt["merges_analyzed"],
            "median_days": lt["median_days"],
            "rating": lt["rating"],
        },
        "code_quality": {
            "total_scans": scan["total_scans"],
            "avg_quality_score": scan["avg_quality_score"],
            "avg_security_score": scan["avg_security_score"],
            "findings": scan["findings"] if scan["total_scans"] > 0 else None,
        },
        "build_activity": {
            "total_builds": build["total_builds"],
            "files_changed": build["files_changed"],
            "tests_added": build["tests_added"],
        },
        "security_posture": {
            "source": sec["source"],
            "vulnerabilities": sec["vulnerabilities"],
            "security_hotspots": sec["security_hotspots"],
            "security_rating": sec["security_rating"],
            "dep_vulns": sec["dep_vulns"],
        },
        "test_confidence": {
            "source": tc["source"],
            "coverage_pct": tc["coverage_pct"],
            "files_covered": tc.get("files_covered", 0),
            "files_total": tc.get("files_total", 0),
            "meets_threshold": tc["meets_threshold"],
            "untested_critical": tc.get("untested_critical", []),
        },
        "actions": [
            "Run `/ai-scan quality` for code quality metrics",
            "Run `/ai-scan security` for security posture",
            "Run `/ai-test gap` for test confidence",
        ],
    }


def _render_delivery_velocity(data: dict[str, Any]) -> None:
    """Render the delivery velocity section."""
    from ai_engineering.cli_ui import kv, section

    section("Delivery Velocity")
    dv = data["delivery_velocity"]
    kv("Commits/week", dv["commits_per_week"])
    kv("Total commits (30d)", dv["total_commits_30d"])
    kv("Lead time (median)", f"{dv['lead_time_median_days']} days")


def _render_gate_health(data: dict[str, Any]) -> None:
    """Render the gate health section."""
    from ai_engineering.cli_ui import kv, progress_bar, section, status_line

    section("Gate Health (last 30 days)")
    gh = data["gate_health"]
    kv("Total gate runs", gh["total"])
    progress_bar("Pass rate", gh["pass_rate"])
    if gh["most_failed_check"] and gh["most_failed_count"] > 0:
        status_line(
            "warn",
            gh["most_failed_check"],
            f"most failed ({gh['most_failed_count']}x)",
        )


def _render_sonar_section(data: dict[str, Any]) -> None:
    """Render the SonarCloud quality gate section (if available)."""
    from ai_engineering.cli_ui import kv, progress_bar, section

    sonar = data["sonar"]
    if not sonar.get("available"):
        return

    section("SonarCloud Quality Gate")
    kv("Status", sonar["status"])
    if sonar.get("new_code_coverage"):
        kv("New code coverage", f"{sonar['new_code_coverage']}%")
    kv("Conditions", sonar["conditions_count"])
    if "detailed" in sonar:
        d = sonar["detailed"]
        progress_bar("Coverage", d["coverage_pct"])
        kv("Complexity", d["cognitive_complexity"])
        kv("Duplication", f"{d['duplication_pct']}%")
        kv("Issues", f"{d['bugs']} bugs, {d['vulnerabilities']} vulnerabilities")


def _render_lead_time(data: dict[str, Any]) -> None:
    """Render the lead time section."""
    from ai_engineering.cli_ui import info, kv, section

    section("Lead Time")
    lt = data["lead_time"]
    if lt["merges_analyzed"] == 0:
        info("Insufficient merge data")
    else:
        kv("Median", f"{lt['median_days']} days")
        kv("Rating", lt["rating"])
        kv("Merges analyzed", lt["merges_analyzed"])


def _render_code_quality(data: dict[str, Any]) -> None:
    """Render the code quality section."""
    from ai_engineering.cli_ui import info, metric_table, progress_bar, section

    section("Code Quality (from scans)")
    cq = data["code_quality"]
    if cq["total_scans"] == 0:
        info("No scan data — run /ai-scan quality")
        return

    progress_bar("Quality score", cq["avg_quality_score"])
    progress_bar("Security score", cq["avg_security_score"])
    findings = cq["findings"]
    metric_table(
        [
            (
                "Critical findings",
                str(findings["critical"]),
                "fail" if findings["critical"] > 0 else "ok",
            ),
            (
                "High findings",
                str(findings["high"]),
                "warn" if findings["high"] > 0 else "ok",
            ),
        ]
    )


def _render_build_activity(data: dict[str, Any]) -> None:
    """Render the build activity section."""
    from ai_engineering.cli_ui import info, kv, section

    section("Build Activity (last 30d)")
    ba = data["build_activity"]
    if ba["total_builds"] == 0:
        info("No build data")
    else:
        kv("Builds", ba["total_builds"])
        kv("Files changed", ba["files_changed"])
        kv("Tests added", ba["tests_added"])


def _render_security_posture(data: dict[str, Any]) -> None:
    """Render the security posture section."""
    from ai_engineering.cli_ui import info, metric_table, section

    section("Security Posture")
    sp = data["security_posture"]
    if sp["source"] == "none":
        info("No data — run `ai-eng setup sonar` or install pip-audit")
        return

    vuln_status = "ok" if sp["vulnerabilities"] == 0 else "fail"
    metric_table(
        [
            (
                "Vulnerabilities",
                f"{sp['vulnerabilities']} ({sp['source']})",
                vuln_status,
            ),
            (
                "Security hotspots",
                str(sp["security_hotspots"]),
                "warn" if sp["security_hotspots"] > 0 else "ok",
            ),
            ("Security rating", sp["security_rating"], "none"),
            (
                "Dep vulnerabilities",
                str(sp["dep_vulns"]),
                "warn" if sp["dep_vulns"] > 0 else "ok",
            ),
        ]
    )


def _render_test_confidence(data: dict[str, Any]) -> None:
    """Render the test confidence section."""
    from ai_engineering.cli_ui import info, kv, progress_bar, section, status_line, warning

    section("Test Confidence")
    tc = data["test_confidence"]
    if tc["source"] == "none":
        info("No data — run `pytest --cov` or configure SonarCloud")
        return

    progress_bar("Coverage", tc["coverage_pct"], threshold=80)
    if tc["files_total"] > 0:
        kv("Files covered", f"{tc['files_covered']}/{tc['files_total']}")
    status = "ok" if tc["meets_threshold"] else "fail"
    status_line(
        status,
        "Threshold (80%)",
        "met" if tc["meets_threshold"] else "not met",
    )
    if tc["untested_critical"]:
        warning(f"Untested critical: {', '.join(tc['untested_critical'][:3])}")


def _render_engineer(data: dict[str, Any]) -> None:
    """Render engineer dashboard with Rich formatting."""
    from ai_engineering.cli_ui import header, kv, suggest_next

    header("Engineer Dashboard")
    kv(
        "Data quality",
        f"{data['data_quality']} ({data['total_events']} events, {data['days_span']} days)",
    )

    _render_delivery_velocity(data)
    _render_gate_health(data)
    _render_sonar_section(data)
    _render_lead_time(data)
    _render_code_quality(data)
    _render_build_activity(data)
    _render_security_posture(data)
    _render_test_confidence(data)

    suggest_next(
        [
            (
                a.split("for")[0].strip() if "for" in a else a,
                a.split("for")[1].strip() if "for" in a else "",
            )
            for a in data["actions"]
        ]
    )


def observe_team(project_root: Path) -> dict[str, Any]:
    """Generate team dashboard data."""
    all_events = load_all_events(project_root)
    dq = data_quality_from(all_events)
    gates = gate_pass_rate_from(all_events)

    dsh = decision_store_health(project_root)
    adopt = adoption_metrics(project_root)
    scan = scan_metrics_from(all_events)
    noise = noise_ratio_from(all_events)
    skills = skill_usage_from(all_events)
    agents = agent_dispatch_from(all_events)
    guard_adv = guard_advisory_from(all_events)
    guard_dft = guard_drift_from(all_events)

    hooks_status = "installed" if adopt["hooks_installed"] else "not installed"
    if adopt["hooks_installed"]:
        hooks_status += "/verified" if adopt["hooks_verified"] else "/unverified"

    return {
        "data_quality": dq,
        "total_events": len(all_events),
        "event_distribution": {
            "gate_events": gates["total"],
            "scan_events": count_events_by_type(all_events, "scan_complete"),
            "build_events": count_events_by_type(all_events, "build_complete"),
            "session_events": count_events_by_type(all_events, "session_metric"),
            "deploy_events": count_events_by_type(all_events, "deploy_complete"),
        },
        "gate_health": {
            "pass_rate": gates["pass_rate"],
            "most_friction": gates["most_failed_check"],
        },
        "decision_store": {
            "total": dsh["total"],
            "active": dsh["active"],
            "expired": dsh["expired"],
            "resolved": dsh["resolved"],
            "avg_age_days": dsh["avg_age_days"],
        },
        "adoption": {
            "stacks": adopt["stacks"],
            "primary_provider": adopt["providers"]["primary"],
            "ides": adopt["ides"],
            "hooks_status": hooks_status,
        },
        "scan_health": {
            "total_scans": scan["total_scans"],
            "avg_quality_score": scan["avg_quality_score"],
        },
        "noise_ratio": {
            "total_failures": noise["total_failures"],
            "fixable_failures": noise["fixable_failures"],
            "noise_ratio_pct": noise["noise_ratio_pct"],
        },
        "skill_usage": {
            "total_invocations": skills["total_invocations"],
            "by_skill": skills["by_skill"],
            "top_skill": skills["top_skill"],
            "least_skill": skills["least_skill"],
        },
        "agent_dispatch": {
            "total_dispatches": agents["total_dispatches"],
            "by_agent": agents["by_agent"],
        },
        "guard_governance": {
            "advisories": guard_adv["total_advisories"],
            "warnings": guard_adv["total_warnings"],
            "concerns": guard_adv["total_concerns"],
            "drift_checks": guard_dft["total_checks"],
            "alignment_pct": guard_dft["alignment_pct"],
            "critical_drifts": guard_dft["total_critical"],
        },
        "actions": [
            "Run `/ai-scan governance` for framework health",
            "Review decision store for expired decisions",
        ],
    }


def _render_team(data: dict[str, Any]) -> None:
    """Render team dashboard with Rich formatting."""
    from ai_engineering.cli_ui import (
        header,
        info,
        kv,
        metric_table,
        progress_bar,
        section,
        suggest_next,
        warning,
    )

    header("Team Dashboard")
    kv("Data quality", f"{data['data_quality']} ({data['total_events']} events)")

    # Event Distribution
    section("Event Distribution")
    ed = data["event_distribution"]
    metric_table(
        [
            ("Gate events", str(ed["gate_events"]), "ok" if ed["gate_events"] > 0 else "none"),
            ("Scan events", str(ed["scan_events"]), "ok" if ed["scan_events"] > 0 else "none"),
            ("Build events", str(ed["build_events"]), "ok" if ed["build_events"] > 0 else "none"),
            (
                "Session events",
                str(ed["session_events"]),
                "ok" if ed["session_events"] > 0 else "none",
            ),
            (
                "Deploy events",
                str(ed["deploy_events"]),
                "ok" if ed["deploy_events"] > 0 else "none",
            ),
        ]
    )

    # Gate Health
    section("Gate Health")
    gh = data["gate_health"]
    progress_bar("Pass rate", gh["pass_rate"])
    if gh["most_friction"]:
        kv("Most friction", gh["most_friction"])

    # Decision Store Health
    section("Decision Store Health")
    ds = data["decision_store"]
    if ds["total"] == 0:
        info("No decisions recorded")
    else:
        metric_table(
            [
                ("Active", str(ds["active"]), "ok"),
                (
                    "Expired (need review)",
                    str(ds["expired"]),
                    "warn" if ds["expired"] > 0 else "ok",
                ),
                ("Resolved", str(ds["resolved"]), "ok"),
            ]
        )
        kv("Avg age", f"{ds['avg_age_days']} days")

    # Adoption
    section("Adoption")
    ad = data["adoption"]
    kv("Stacks", ", ".join(ad["stacks"]) if ad["stacks"] else "none")
    kv("Providers", ad["primary_provider"])
    kv("IDEs", ", ".join(ad["ides"]) if ad["ides"] else "none")
    kv("Hooks", ad["hooks_status"])

    # Scan Health
    section("Scan Health")
    sh = data["scan_health"]
    if sh["total_scans"] == 0:
        info("No scan data")
    else:
        progress_bar("Quality score", sh["avg_quality_score"])
        kv("Scans run", sh["total_scans"])

    # Noise Ratio
    section("Noise Ratio")
    nr = data["noise_ratio"]
    if nr["total_failures"] == 0:
        info("No gate failures — all gates passing")
    else:
        kv("Total failures", nr["total_failures"])
        kv("Auto-fixable", nr["fixable_failures"])
        progress_bar("Noise ratio", nr["noise_ratio_pct"])
        if nr["noise_ratio_pct"] > 50:
            warning("High noise — run `ruff format` + `ruff check --fix` before committing")

    # Skill Usage
    section("Skill Usage")
    su = data["skill_usage"]
    if su["total_invocations"] == 0:
        info("No skill telemetry — skills emit events when ai-eng is available")
    else:
        kv("Total invocations", su["total_invocations"])
        kv("Top skill", su["top_skill"])
        kv("Least used", su["least_skill"])
        top_items = list(su["by_skill"].items())[:10]
        metric_table([(name, str(count), "ok") for name, count in top_items])

    # Agent Dispatch
    section("Agent Dispatch")
    ad_dispatch = data["agent_dispatch"]
    if ad_dispatch["total_dispatches"] == 0:
        info("No agent telemetry — agents emit events when ai-eng is available")
    else:
        kv("Total dispatches", ad_dispatch["total_dispatches"])
        metric_table([(name, str(count), "ok") for name, count in ad_dispatch["by_agent"].items()])

    # Actions
    suggest_next([(a, "") for a in data["actions"]])


def observe_ai(project_root: Path) -> dict[str, Any]:
    """Generate AI self-awareness dashboard data."""
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

    # Context efficiency from session events
    sessions_analyzed = len(session_events)
    avg_tokens = round(total_tokens / sessions_analyzed) if sessions_analyzed > 0 else 0

    # Skill/Agent efficiency
    skills = skill_usage_from(all_events)
    agents = agent_dispatch_from(all_events)

    # Self-Optimization Hints
    hints: list[str] = []
    if total_decisions > 0 and cache_hit_rate < 50:
        hints.append("Low decision reuse — save key decisions to decision-store")
    gates = gate_pass_rate_from(all_events)
    if gates["total"] > 0 and gates["pass_rate"] < 80:
        hints.append("High gate failure rate — run `ruff format` before committing")
    if not hints:
        hints.append("All patterns healthy — no optimization needed")

    return {
        "data_quality": dq,
        "context_efficiency": {
            "sessions_analyzed": sessions_analyzed,
            "total_tokens": total_tokens,
            "avg_tokens_per_session": avg_tokens,
            "tokens_available": 200_000,
            "utilization_pct": (
                round(total_tokens / (sessions_analyzed * 200_000) * 100, 1)
                if sessions_analyzed > 0
                else 0.0
            ),
            "skills_loaded": sorted(
                {
                    s
                    for e in session_events
                    if isinstance(e.get("detail"), dict)
                    for s in (e["detail"].get("skills_loaded") or [])
                    if isinstance(s, str)
                }
            ),
        },
        "decision_continuity": {
            "decisions_reused": decisions_reused,
            "decisions_reprompted": decisions_reprompted,
            "cache_hit_rate": cache_hit_rate,
        },
        "skill_agent_efficiency": {
            "skill_invocations": skills["total_invocations"],
            "unique_skills_used": len(skills["by_skill"]),
            "agent_dispatches": agents["total_dispatches"],
            "unique_agents_used": len(agents["by_agent"]),
        },
        "self_optimization_hints": hints,
        "actions": [
            "Review decision store for expiring decisions",
        ],
    }


def _render_ai(data: dict[str, Any]) -> None:
    """Render AI self-awareness dashboard with Rich formatting."""
    from ai_engineering.cli_ui import (
        header,
        info,
        kv,
        progress_bar,
        section,
        status_line,
        suggest_next,
    )

    header("AI Self-Awareness")
    kv("Data quality", data["data_quality"])

    # Context Efficiency
    section("Context Efficiency")
    ce = data["context_efficiency"]
    kv("Sessions analyzed", ce["sessions_analyzed"])
    kv("Total tokens (recent)", f"{ce['total_tokens']:,}")
    kv("Avg tokens/session", f"{ce['avg_tokens_per_session']:,}")
    progress_bar("Token utilization", ce["utilization_pct"])
    kv("Skills loaded", ", ".join(ce["skills_loaded"]) if ce["skills_loaded"] else "none")

    # Decision Continuity
    section("Decision Continuity")
    dc = data["decision_continuity"]
    kv("Decisions reused", dc["decisions_reused"])
    kv("Decisions re-prompted", dc["decisions_reprompted"])
    progress_bar("Cache hit rate", dc["cache_hit_rate"])

    # Skill & Agent Efficiency
    section("Skill & Agent Efficiency")
    sae = data["skill_agent_efficiency"]
    if sae["skill_invocations"] == 0 and sae["agent_dispatches"] == 0:
        info("No telemetry — skills/agents emit events when ai-eng is available")
    else:
        kv("Skill invocations", sae["skill_invocations"])
        kv("Unique skills", sae["unique_skills_used"])
        kv("Agent dispatches", sae["agent_dispatches"])
        kv("Unique agents", sae["unique_agents_used"])

    # Self-Optimization Hints
    section("Self-Optimization Hints")
    for hint in data["self_optimization_hints"]:
        # Determine status based on hint content
        if "healthy" in hint.lower() or "no optimization" in hint.lower():
            status_line("ok", "Status", hint)
        else:
            status_line("warn", "Hint", hint)

    # Actions
    suggest_next([(a, "") for a in data["actions"]])


def observe_dora(project_root: Path) -> dict[str, Any]:
    """Generate DORA metrics dashboard data."""
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

    lt = lead_time_metrics(project_root)
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

    return {
        "data_quality": dq,
        "deployment_frequency": {
            "merges_per_week": freq,
            "rating": freq_rating,
        },
        "lead_time": {
            "median_days": lt["median_days"],
            "rating": lt["rating"],
        },
        "change_failure_rate": {
            "total_deploys": deploy["total_deploys"],
            "rollbacks": deploy["rollbacks"],
            "rate_pct": cfr_pct,
            "rating": cfr_rating,
        },
        "delivery_velocity": {
            "commits_per_week": dora["commits_per_week"],
            "total_commits_30d": dora["total_commits_30d"],
        },
        "benchmarks": {
            "elite": "multiple deploys/day, lead time <1h",
            "high": "weekly deploys, lead time <1 week",
            "medium": "monthly deploys, lead time <1 month",
        },
    }


def _render_dora(data: dict[str, Any]) -> None:
    """Render DORA dashboard with Rich formatting."""
    from ai_engineering.cli_ui import (
        header,
        kv,
        metric_table,
        section,
    )

    header("DORA Metrics (last 30 days)")
    kv("Data quality", data["data_quality"])

    # Deployment Frequency
    section("Deployment Frequency")
    df = data["deployment_frequency"]
    kv("Merges to main/week", df["merges_per_week"])
    # Rating as colored metric
    rating_status = {"ELITE": "ok", "HIGH": "ok", "MEDIUM": "warn", "LOW": "fail"}
    metric_table([("Rating", df["rating"], rating_status.get(df["rating"], "none"))])

    # Lead Time
    section("Lead Time for Changes")
    lt = data["lead_time"]
    kv("Median", f"{lt['median_days']} days")
    metric_table([("Rating", lt["rating"], rating_status.get(lt["rating"], "none"))])

    # Change Failure Rate
    section("Change Failure Rate")
    cfr = data["change_failure_rate"]
    kv("Deployments", cfr["total_deploys"])
    kv("Rollbacks", cfr["rollbacks"])
    kv("Rate", f"{cfr['rate_pct']}%")
    metric_table([("Rating", cfr["rating"], rating_status.get(cfr["rating"], "none"))])

    # Delivery Velocity
    section("Delivery Velocity")
    dv = data["delivery_velocity"]
    kv("Commits/week", dv["commits_per_week"])
    kv("Total commits (30d)", dv["total_commits_30d"])

    # Benchmarks
    section("Benchmarks")
    bm = data["benchmarks"]
    metric_table(
        [
            ("Elite", bm["elite"], "ok"),
            ("High", bm["high"], "ok"),
            ("Medium", bm["medium"], "warn"),
        ]
    )


def _compute_component_scores(
    project_root: Path,
    all_events: list[dict[str, Any]],
    gates: dict[str, Any],
    git_stats: dict[str, Any],
    dora: dict[str, Any],
) -> dict[str, Any]:
    """Compute individual health component scores.

    Returns a dict with keys: components (name->score pairs), details (raw
    values for component_details output), and intermediate results needed
    by the caller (freq, noise).
    """
    gate_score = min(gates["pass_rate"], 100)
    velocity_score = min(git_stats["commits_per_week"] * 10, 100)

    components: list[float] = [gate_score, velocity_score]
    component_names: list[str] = ["Gate pass rate", "Delivery velocity"]

    scan = scan_metrics_from(all_events)
    if scan["total_scans"] > 0:
        scan_score: float | None = scan["avg_quality_score"]
        components.append(scan_score)
        component_names.append("Scan quality")
    else:
        scan_score = None

    dsh = decision_store_health(project_root)
    if dsh["total"] > 0:
        decision_score: float | None = max(0, 100 - dsh["expired"] * 20)
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

    sonar = sonar_detailed_metrics(project_root)
    if sonar.get("available") and sonar.get("coverage_pct", 0) > 0:
        sonar_score: float | None = sonar["coverage_pct"]
        components.append(sonar_score)
        component_names.append("SonarCloud coverage")
    else:
        sonar_score = None

    tc = test_confidence_metrics(project_root)
    if tc["source"] != "none" and tc["coverage_pct"] > 0:
        tc_score: float | None = tc["coverage_pct"]
        components.append(tc_score)
        component_names.append("Test confidence")
    else:
        tc_score = None

    noise = noise_ratio_from(all_events)
    if noise["total_failures"] > 0:
        noise_score: float | None = max(0, 100 - noise["noise_ratio_pct"])
        components.append(noise_score)
        component_names.append("Gate signal quality")
    else:
        noise_score = None

    return {
        "components": dict(zip(component_names, components, strict=True)),
        "component_values": components,
        "component_names": component_names,
        "details": {
            "gate_pass_rate": gates["pass_rate"],
            "commits_per_week": git_stats["commits_per_week"],
            "deployment_frequency_per_week": freq,
            "scan_score": scan_score,
            "decision_score": decision_score,
            "sonar_score": sonar_score,
            "tc_score": tc_score,
            "noise_score": noise_score,
            "noise_ratio_pct": noise["noise_ratio_pct"] if noise["total_failures"] > 0 else None,
        },
    }


def _compute_overall_health(
    component_scores: dict[str, float],
) -> tuple[int, str]:
    """Compute the overall health score and semaphore from component scores.

    Args:
        component_scores: Dict mapping component name to its score (0-100).

    Returns:
        Tuple of (overall_score, semaphore_color).
    """
    values = list(component_scores.values())
    overall = round(sum(values) / len(values))

    if overall >= 80:
        semaphore = "GREEN"
    elif overall >= 60:
        semaphore = "YELLOW"
    else:
        semaphore = "RED"

    return overall, semaphore


_HEALTH_ACTION_MAP: dict[str, str] = {
    "Gate pass rate": "Run `ruff format` + `ruff check --fix` before committing",
    "Delivery velocity": "Increase commit frequency — ship smaller changes",
    "Scan quality": "Run `/ai-scan quality` to improve code quality score",
    "Decision health": "Run `ai-eng decision expire-check` to review expired decisions",
    "DORA frequency": "Merge PRs more frequently — target weekly deploys",
    "SonarCloud coverage": "Run `ai-eng setup sonar` and increase test coverage",
    "Test confidence": "Run `pytest --cov` to generate coverage data",
    "Gate signal quality": "Run `ruff format` + `ruff check --fix` to reduce noise",
}


def _generate_health_actions(
    component_scores: dict[str, float],
) -> list[dict[str, Any]]:
    """Generate recommended actions based on weakest health components.

    Args:
        component_scores: Dict mapping component name to its score (0-100).

    Returns:
        List of action dicts with keys: action, potential_gain, component.
    """
    scored = sorted(component_scores.items(), key=lambda x: x[1])
    num_c = len(component_scores)
    actions: list[dict[str, Any]] = []

    for name, score in scored[:3]:
        if score >= 90:
            continue
        gain = round((100 - score) / num_c)
        cmd = _HEALTH_ACTION_MAP.get(name, f"Improve {name}")
        actions.append({"action": cmd, "potential_gain": gain, "component": name})

    if not actions:
        actions.append(
            {
                "action": "All components healthy — maintain current practices",
                "potential_gain": 0,
                "component": "all",
            }
        )

    return actions


def observe_health(project_root: Path) -> dict[str, Any]:
    """Generate aggregated health score data."""
    all_events = load_all_events(project_root)
    dq = data_quality_from(all_events)
    gates = gate_pass_rate_from(all_events)
    git_stats = _git_log_stat(project_root)
    dora = _dora_metrics(project_root, git_stats=git_stats)

    scores = _compute_component_scores(
        project_root,
        all_events,
        gates,
        git_stats,
        dora,
    )
    comp_dict = scores["components"]
    overall, semaphore = _compute_overall_health(comp_dict)
    actions = _generate_health_actions(comp_dict)

    return {
        "score": overall,
        "semaphore": semaphore,
        "data_quality": dq,
        "components": comp_dict,
        "component_details": scores["details"],
        "actions": actions,
    }


def _render_health(data: dict[str, Any]) -> None:
    """Render health dashboard with Rich formatting."""
    from ai_engineering.cli_ui import (
        header,
        kv,
        metric_table,
        progress_bar,
        score_badge,
        section,
        suggest_next,
    )

    header(f"Health Score: {data['score']}/100 ({data['semaphore']})")

    kv("Data quality", data["data_quality"])

    # Score badge
    score_badge(data["score"], "Overall")

    section("Components")
    # Progress bars for each component
    for name, score in data["components"].items():
        progress_bar(name, score)

    # Show "No data" items
    det = data["component_details"]
    no_data_items: list[tuple[str, str, str]] = []
    if det.get("scan_score") is None and "Scan quality" not in data["components"]:
        no_data_items.append(("Scan quality", "No data", "none"))
    if det.get("decision_score") is None and "Decision health" not in data["components"]:
        no_data_items.append(("Decision health", "No decisions", "none"))
    if det.get("sonar_score") is None and "SonarCloud coverage" not in data["components"]:
        no_data_items.append(("SonarCloud coverage", "No data", "none"))
    if det.get("tc_score") is None and "Test confidence" not in data["components"]:
        no_data_items.append(("Test confidence", "No data", "none"))
    if det.get("noise_score") is None and "Gate signal quality" not in data["components"]:
        no_data_items.append(("Gate signal quality", "No failures", "none"))
    if no_data_items:
        metric_table(no_data_items)

    section("Top Actions")
    # suggest_next expects list of (command, description) tuples
    action_steps: list[tuple[str, str]] = []
    for a in data["actions"]:
        gain = f"(+{a['potential_gain']} pts)" if a["potential_gain"] > 0 else ""
        action_steps.append((a["action"], gain))
    suggest_next(action_steps)


# ---------------------------------------------------------------------------
# Mode and render dispatch tables
# ---------------------------------------------------------------------------

_MODE_FUNCS: dict[str, Any] = {
    "engineer": observe_engineer,
    "team": observe_team,
    "ai": observe_ai,
    "dora": observe_dora,
    "health": observe_health,
}

_RENDER_FUNCS: dict[str, Any] = {
    "engineer": _render_engineer,
    "team": _render_team,
    "ai": _render_ai,
    "dora": _render_dora,
    "health": _render_health,
}

# Next actions per mode for JSON envelope
_NEXT_ACTIONS: dict[str, list[NextAction]] = {
    "engineer": [
        NextAction(command="observe team", description="View team dashboard"),
        NextAction(command="scan quality", description="Run code quality scan"),
        NextAction(command="scan security", description="Run security scan"),
    ],
    "team": [
        NextAction(command="observe engineer", description="View engineer dashboard"),
        NextAction(command="scan governance", description="Run governance scan"),
        NextAction(command="decision expire-check", description="Review expired decisions"),
    ],
    "ai": [
        NextAction(command="observe health", description="View health score"),
        NextAction(command="decision list", description="List active decisions"),
    ],
    "dora": [
        NextAction(command="observe health", description="View health score"),
        NextAction(command="observe engineer", description="View engineer dashboard"),
    ],
    "health": [
        NextAction(command="observe engineer", description="Drill into engineer metrics"),
        NextAction(command="observe dora", description="Drill into DORA metrics"),
        NextAction(command="scan quality", description="Improve quality score"),
    ],
}


def observe_cmd(
    mode: Annotated[
        str,
        typer.Argument(
            help="Dashboard mode: engineer | team | ai | dora | health",
        ),
    ] = "health",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output structured JSON instead of human-readable text",
        ),
    ] = False,
) -> None:
    """Generate observability dashboard for the specified audience."""
    if mode not in _MODE_FUNCS:
        typer.echo(
            f"Unknown mode: {mode}. Valid: {', '.join(_MODE_FUNCS)}",
            err=True,
        )
        raise typer.Exit(code=1)

    if json_output:
        set_json_mode(True)

    root = find_project_root()
    data = _MODE_FUNCS[mode](root)

    route_output(
        command=f"observe-{mode}",
        result=data,
        next_actions=_NEXT_ACTIONS.get(mode),
        human_fn=lambda: _RENDER_FUNCS[mode](data),
    )
