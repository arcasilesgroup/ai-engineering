"""Maintenance report generation and PR creation.

Provides:
- Staleness analysis for governance documents.
- Health report generation summarising framework state.
- PR creation for maintenance updates.
"""

from __future__ import annotations

import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.state.io import read_json_model, read_ndjson_entries
from ai_engineering.state.locking import artifact_lock
from ai_engineering.state.models import (
    DecisionStore,
    FrameworkEvent,
    TaskLedgerTask,
    TaskLifecycleState,
)
from ai_engineering.state.work_plane import read_task_ledger
from ai_engineering.vcs.factory import get_provider
from ai_engineering.vcs.protocol import VcsContext


@dataclass
class StaleFile:
    """A governance file that may need attention."""

    path: Path
    last_modified: datetime
    age_days: int


@dataclass
class MaintenanceReport:
    """Summary of framework health and staleness."""

    generated_at: datetime
    stale_files: list[StaleFile] = field(default_factory=list)
    total_governance_files: int = 0
    total_state_files: int = 0
    recent_framework_events: int = 0
    install_manifest_version: str = ""
    warnings: list[str] = field(default_factory=list)
    risk_active: int = 0
    risk_expiring: int = 0
    risk_expired: int = 0
    local_branches: int = 0
    merged_branches: int = 0
    remote_branches: int = 0
    open_prs: int = 0
    stale_branches: int = 0
    version_status: str = ""
    task_scorecard: TaskScorecard = field(default_factory=lambda: TaskScorecard())

    @property
    def health_score(self) -> float:
        """Simple health score (0.0-1.0) based on staleness ratio.

        Returns:
            1.0 if no stale files, decreasing with more stale files.
        """
        if self.total_governance_files == 0:
            return 0.0
        stale_ratio = len(self.stale_files) / self.total_governance_files
        return max(0.0, 1.0 - stale_ratio)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report as a plain dictionary for JSON output.

        Returns:
            Dictionary with all report fields; Paths as POSIX strings, dates as ISO.
        """
        return {
            "generated_at": self.generated_at.isoformat(),
            "health_score": round(self.health_score, 4),
            "total_governance_files": self.total_governance_files,
            "total_state_files": self.total_state_files,
            "recent_framework_events": self.recent_framework_events,
            "install_manifest_version": self.install_manifest_version,
            "stale_files": [
                {
                    "path": sf.path.as_posix(),
                    "last_modified": sf.last_modified.isoformat(),
                    "age_days": sf.age_days,
                }
                for sf in self.stale_files
            ],
            "risk_active": self.risk_active,
            "risk_expiring": self.risk_expiring,
            "risk_expired": self.risk_expired,
            "local_branches": self.local_branches,
            "merged_branches": self.merged_branches,
            "remote_branches": self.remote_branches,
            "open_prs": self.open_prs,
            "stale_branches": self.stale_branches,
            "version_status": self.version_status,
            "task_scorecard": self.task_scorecard.to_dict(),
            "warnings": self.warnings,
        }

    def to_markdown(self) -> str:
        """Render the report as Markdown.

        Returns:
            Markdown-formatted report string.
        """
        lines: list[str] = []
        lines.append("# Maintenance Report")
        lines.append("")
        lines.append(f"**Generated**: {self.generated_at.isoformat()}")
        lines.append(f"**Framework version**: {self.install_manifest_version}")
        lines.append(f"**Health score**: {self.health_score:.0%}")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Governance files: {self.total_governance_files}")
        lines.append(f"- State files: {self.total_state_files}")
        lines.append(f"- Stale files: {len(self.stale_files)}")
        lines.append(f"- Recent framework events: {self.recent_framework_events}")
        lines.append(f"- Risk acceptances (active): {self.risk_active}")
        lines.append(f"- Risk acceptances (expiring): {self.risk_expiring}")
        lines.append(f"- Risk acceptances (expired): {self.risk_expired}")
        lines.append(f"- Local branches: {self.local_branches}")
        lines.append(f"- Remote branches: {self.remote_branches}")
        lines.append(f"- Merged branches (cleanup candidates): {self.merged_branches}")
        lines.append(f"- Open PRs: {self.open_prs}")
        lines.append(f"- Stale branches (>30d): {self.stale_branches}")
        if self.version_status:
            lines.append(f"- Version status: {self.version_status}")
        lines.append(
            f"- Task resolution: {self.task_scorecard.resolved_tasks}/{self.task_scorecard.total_tasks} "
            f"({self.task_scorecard.resolution_score:.0%})"
        )
        lines.append(f"- Retrying tasks: {self.task_scorecard.retry_tasks}")
        lines.append(f"- Reworked tasks: {self.task_scorecard.rework_tasks}")
        lines.append(f"- Verification tax events: {self.task_scorecard.verification_tax_events}")
        lines.append(f"- Drift events: {self.task_scorecard.drift_events}")
        lines.append("")

        if self.task_scorecard.total_tasks or self.task_scorecard.drift_events:
            lines.append("## Task Scorecard")
            lines.append("")
            lines.append(f"- Total tasks: {self.task_scorecard.total_tasks}")
            lines.append(f"- Resolved tasks: {self.task_scorecard.resolved_tasks}")
            lines.append(f"- Open tasks: {self.task_scorecard.open_tasks}")
            lines.append(f"- Retrying tasks: {self.task_scorecard.retry_tasks}")
            lines.append(f"- Reworked tasks: {self.task_scorecard.rework_tasks}")
            lines.append(
                f"- Verification tax events: {self.task_scorecard.verification_tax_events}"
            )
            lines.append(f"- Drift events: {self.task_scorecard.drift_events}")
            lines.append("")

        if self.stale_files:
            lines.append("## Stale Files")
            lines.append("")
            lines.append("| File | Last Modified | Age (days) |")
            lines.append("|------|---------------|------------|")
            for sf in sorted(self.stale_files, key=lambda x: -x.age_days):
                lines.append(
                    f"| {sf.path.as_posix()} "
                    f"| {sf.last_modified.date().isoformat()} "
                    f"| {sf.age_days} |"
                )
            lines.append("")

        if self.warnings:
            lines.append("## Warnings")
            lines.append("")
            for w in self.warnings:
                lines.append(f"- {w}")
            lines.append("")

        return "\n".join(lines)


# Days after which a governance file is considered stale.
_STALENESS_THRESHOLD_DAYS: int = 90


@dataclass
class TaskScorecard:
    """Derived task and drift scorecard computed from authoritative state."""

    total_tasks: int = 0
    resolved_tasks: int = 0
    open_tasks: int = 0
    retry_tasks: int = 0
    rework_tasks: int = 0
    verification_tax_events: int = 0
    drift_events: int = 0

    @property
    def resolution_score(self) -> float:
        """Return the fraction of current tasks already resolved."""
        if self.total_tasks == 0:
            return 0.0
        return self.resolved_tasks / self.total_tasks

    def to_dict(self) -> dict[str, Any]:
        """Serialize the scorecard for JSON maintenance-report output."""
        return {
            "total_tasks": self.total_tasks,
            "resolved_tasks": self.resolved_tasks,
            "open_tasks": self.open_tasks,
            "retry_tasks": self.retry_tasks,
            "rework_tasks": self.rework_tasks,
            "verification_tax_events": self.verification_tax_events,
            "drift_events": self.drift_events,
            "resolution_score": round(self.resolution_score, 4),
        }


def build_task_scorecard(target: Path) -> TaskScorecard:
    """Derive task resolution and drift views from authoritative state inputs."""
    tasks, events = _read_task_scorecard_inputs(target)
    return _reduce_task_scorecard(tasks, events)


def _read_task_scorecard_inputs(target: Path) -> tuple[list[TaskLedgerTask], list[FrameworkEvent]]:
    """Read a consistent task-ledger and framework-events snapshot for reducers."""
    events_path = target / ".ai-engineering" / "state" / "framework-events.ndjson"
    with artifact_lock(target, "framework-events"):
        ledger = read_task_ledger(target)
        tasks = ledger.tasks if ledger is not None else []
        events = read_ndjson_entries(events_path, FrameworkEvent)
    return tasks, events


def _reduce_task_scorecard(
    tasks: list[TaskLedgerTask],
    events: list[FrameworkEvent],
) -> TaskScorecard:
    phase_history: dict[str, list[str]] = defaultdict(list)
    last_artifact_refs: dict[str, tuple[str, ...]] = {}
    verification_tax_events = 0
    drift_events = 0

    for event in events:
        if event.kind == "task_trace":
            task_id = event.detail.get("task_id")
            lifecycle_phase = event.detail.get("lifecycle_phase")
            if not isinstance(task_id, str) or not task_id.strip():
                continue
            if not isinstance(lifecycle_phase, str) or not lifecycle_phase.strip():
                continue

            normalized_task_id = task_id.strip()
            normalized_phase = lifecycle_phase.strip()
            artifact_refs = _event_artifact_refs(event)
            phases = phase_history[normalized_task_id]
            last_phase = phases[-1] if phases else None
            previous_refs = last_artifact_refs.get(normalized_task_id)

            if (
                last_phase == normalized_phase
                and previous_refs is not None
                and artifact_refs != previous_refs
            ):
                verification_tax_events += 1

            if last_phase != normalized_phase:
                phases.append(normalized_phase)

            last_artifact_refs[normalized_task_id] = artifact_refs
            continue

        if event.kind != "control_outcome":
            continue

        control = event.detail.get("control")
        drifted = event.detail.get("drifted", 0)
        if control != "guard-drift":
            continue
        if event.outcome != "success":
            drift_events += 1
            continue
        if isinstance(drifted, int) and drifted > 0:
            drift_events += 1

    resolved_tasks = sum(task.status == TaskLifecycleState.DONE for task in tasks)
    retry_tasks = sum(
        phases.count(TaskLifecycleState.IN_PROGRESS.value) > 1 for phases in phase_history.values()
    )
    rework_tasks = sum(
        TaskLifecycleState.DONE.value in phases[:-1] and phases[-1] != TaskLifecycleState.DONE.value
        for phases in phase_history.values()
    )

    return TaskScorecard(
        total_tasks=len(tasks),
        resolved_tasks=resolved_tasks,
        open_tasks=max(len(tasks) - resolved_tasks, 0),
        retry_tasks=retry_tasks,
        rework_tasks=rework_tasks,
        verification_tax_events=verification_tax_events,
        drift_events=drift_events,
    )


def _event_artifact_refs(event: FrameworkEvent) -> tuple[str, ...]:
    raw_refs = event.detail.get("artifact_refs")
    if not isinstance(raw_refs, list):
        return ()

    normalized: list[str] = []
    seen: set[str] = set()
    for value in raw_refs:
        if not isinstance(value, str):
            continue
        ref = value.strip()
        if not ref or ref in seen:
            continue
        seen.add(ref)
        normalized.append(ref)
    return tuple(normalized)


def generate_report(
    target: Path,
    *,
    staleness_days: int = _STALENESS_THRESHOLD_DAYS,
) -> MaintenanceReport:
    """Generate a maintenance report for the target project.

    Args:
        target: Root directory of the target project.
        staleness_days: Number of days after which a file is considered stale.

    Returns:
        MaintenanceReport with health and staleness data.
    """
    now = datetime.now(tz=UTC)
    ai_eng_dir = target / ".ai-engineering"
    report = MaintenanceReport(generated_at=now)

    if not ai_eng_dir.is_dir():
        report.warnings.append("Framework not installed")
        return report

    # Load framework version from manifest.yml
    cfg = load_manifest_config(target)
    if cfg.framework_version:
        report.install_manifest_version = cfg.framework_version
    else:
        report.warnings.append("Framework version not found in manifest")

    # Version lifecycle status
    try:
        from ai_engineering.version.checker import check_version

        version_result = check_version(report.install_manifest_version or "0.0.0")
        report.version_status = version_result.message
    except Exception:
        pass

    # Count and analyse governance files
    governance_dirs = ["standards", "skills", "context"]
    all_files: list[Path] = []
    for dirname in governance_dirs:
        d = ai_eng_dir / dirname
        if d.is_dir():
            all_files.extend(f for f in d.rglob("*") if f.is_file())

    report.total_governance_files = len(all_files)

    # Detect stale files
    for f in all_files:
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
        age_days = (now - mtime).days
        if age_days > staleness_days:
            report.stale_files.append(
                StaleFile(
                    path=f.relative_to(ai_eng_dir),
                    last_modified=mtime,
                    age_days=age_days,
                )
            )

    # Count state files
    state_dir = ai_eng_dir / "state"
    if state_dir.is_dir():
        report.total_state_files = sum(1 for f in state_dir.iterdir() if f.is_file())

    # Count recent framework events
    tasks, entries = _read_task_scorecard_inputs(target)
    report.recent_framework_events = len(entries)
    report.task_scorecard = _reduce_task_scorecard(tasks, entries)

    # Risk acceptance status
    ds_path = ai_eng_dir / "state" / "decision-store.json"
    if ds_path.exists():
        try:
            from ai_engineering.state.decision_logic import (
                list_expired_decisions,
                list_expiring_soon,
            )

            store = read_json_model(ds_path, DecisionStore)
            risk = store.risk_decisions()
            expired = list_expired_decisions(store)
            expiring = list_expiring_soon(store)
            report.risk_expired = len(expired)
            report.risk_expiring = len(expiring)
            report.risk_active = len(risk) - len(expired) - len(expiring)
        except (OSError, ValueError):
            report.warnings.append("Failed to parse decision store")

    # Branch status
    try:
        from ai_engineering.maintenance.branch_cleanup import (
            list_all_local_branches,
            list_merged_branches,
        )

        branches = list_all_local_branches(target)
        merged = list_merged_branches(target)
        report.local_branches = len(branches)
        report.merged_branches = len(merged)
    except (OSError, ValueError):
        pass  # git may not be available

    # Repo status (remote branches, PRs, stale)
    try:
        from ai_engineering.maintenance.repo_status import run_repo_status

        repo_status = run_repo_status(target, include_prs=True)
        report.remote_branches = len(repo_status.remote_branches)
        report.open_prs = len(repo_status.open_prs)
        report.stale_branches = len(repo_status.stale_branches)
    except (OSError, ValueError):
        pass  # git/gh may not be available

    return report


def create_maintenance_pr(
    target: Path,
    report: MaintenanceReport,
    *,
    branch_name: str = "maintenance/framework-update",
) -> bool:
    """Create a PR with maintenance report and updates.

    Uses the configured VCS provider (GitHub or Azure DevOps).

    Args:
        target: Root directory of the target project.
        report: Generated maintenance report.
        branch_name: Name of the branch to create.

    Returns:
        True if PR was created successfully.
    """
    # Write report to file
    report_path = target / ".ai-engineering" / "state" / "maintenance-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.to_markdown(), encoding="utf-8")

    try:
        # Create branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=target,
            check=True,
            capture_output=True,
        )

        # Stage and commit
        subprocess.run(
            ["git", "add", str(report_path)],
            cwd=target,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "chore: maintenance report"],
            cwd=target,
            check=True,
            capture_output=True,
        )

        # Push
        subprocess.run(
            ["git", "push", "origin", branch_name],
            cwd=target,
            check=True,
            capture_output=True,
            timeout=30,
        )

        # Create PR via provider
        provider = get_provider(target)
        ctx = VcsContext(
            project_root=target,
            title="chore: framework maintenance report",
            body=report.to_markdown(),
            branch=branch_name,
        )
        result = provider.create_pr(ctx)
        return result.success

    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False
