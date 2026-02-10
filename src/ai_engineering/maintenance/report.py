"""Maintenance report generation and PR creation.

Provides:
- Staleness analysis for governance documents.
- Health report generation summarising framework state.
- PR creation for maintenance updates.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ai_engineering.state.io import read_json_model, read_ndjson_entries
from ai_engineering.state.models import AuditEntry, DecisionStore, InstallManifest


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
    recent_audit_events: int = 0
    install_manifest_version: str = ""
    warnings: list[str] = field(default_factory=list)
    risk_active: int = 0
    risk_expiring: int = 0
    risk_expired: int = 0
    local_branches: int = 0
    merged_branches: int = 0

    @property
    def health_score(self) -> float:
        """Simple health score (0.0–1.0) based on staleness ratio.

        Returns:
            1.0 if no stale files, decreasing with more stale files.
        """
        if self.total_governance_files == 0:
            return 0.0
        stale_ratio = len(self.stale_files) / self.total_governance_files
        return max(0.0, 1.0 - stale_ratio)

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
        lines.append(f"- Recent audit events: {self.recent_audit_events}")
        lines.append(f"- Risk acceptances (active): {self.risk_active}")
        lines.append(f"- Risk acceptances (expiring): {self.risk_expiring}")
        lines.append(f"- Risk acceptances (expired): {self.risk_expired}")
        lines.append(f"- Local branches: {self.local_branches}")
        lines.append(f"- Merged branches (cleanup candidates): {self.merged_branches}")
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
    now = datetime.now(tz=timezone.utc)
    ai_eng_dir = target / ".ai-engineering"
    report = MaintenanceReport(generated_at=now)

    if not ai_eng_dir.is_dir():
        report.warnings.append("Framework not installed")
        return report

    # Load install manifest
    manifest_path = ai_eng_dir / "state" / "install-manifest.json"
    if manifest_path.exists():
        manifest = read_json_model(manifest_path, InstallManifest)
        report.install_manifest_version = manifest.framework_version
    else:
        report.warnings.append("Install manifest not found")

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
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        age_days = (now - mtime).days
        if age_days > staleness_days:
            report.stale_files.append(StaleFile(
                path=f.relative_to(ai_eng_dir),
                last_modified=mtime,
                age_days=age_days,
            ))

    # Count state files
    state_dir = ai_eng_dir / "state"
    if state_dir.is_dir():
        report.total_state_files = sum(
            1 for f in state_dir.iterdir() if f.is_file()
        )

    # Count recent audit events
    audit_path = ai_eng_dir / "state" / "audit-log.ndjson"
    if audit_path.exists():
        entries = read_ndjson_entries(audit_path, AuditEntry)
        report.recent_audit_events = len(entries)

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

    return report


def create_maintenance_pr(
    target: Path,
    report: MaintenanceReport,
    *,
    branch_name: str = "maintenance/framework-update",
) -> bool:
    """Create a PR with maintenance report and updates.

    Requires ``gh`` CLI to be available and authenticated.

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

        # Push and create PR
        subprocess.run(
            ["git", "push", "origin", branch_name],
            cwd=target,
            check=True,
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            [
                "gh", "pr", "create",
                "--title", "chore: framework maintenance report",
                "--body", report.to_markdown(),
            ],
            cwd=target,
            check=True,
            capture_output=True,
            timeout=30,
        )
        return True

    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False
