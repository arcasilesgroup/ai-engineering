"""Local maintenance report generation for context and governance health."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_engineering.paths import ai_engineering_root, repo_root


STALE_DAYS_THRESHOLD = 90
LARGE_FILE_LINES = 250


@dataclass
class ContextFileStat:
    """Computed metrics for a single context file."""

    path: Path
    lines: int
    chars: int
    stale_days: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _file_stats(path: Path) -> ContextFileStat:
    content = path.read_text(encoding="utf-8")
    lines = content.count("\n") + 1
    chars = len(content)
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    stale_days = max(0, (_now() - modified).days)
    return ContextFileStat(path=path, lines=lines, chars=chars, stale_days=stale_days)


def _context_files(ae_root: Path) -> list[Path]:
    context_root = ae_root / "context"
    return sorted([p for p in context_root.rglob("*.md") if p.is_file()])


def _report_markdown(
    *,
    generated_at: str,
    files: list[ContextFileStat],
    large_files: list[ContextFileStat],
    stale_files: list[ContextFileStat],
    approved_for_pr: bool,
) -> str:
    total_chars = sum(item.chars for item in files)
    approx_tokens = total_chars // 4

    lines: list[str] = []
    lines.append("# Maintenance Report\n")
    lines.append(f"Generated at: {generated_at}\n")
    lines.append("## Summary\n")
    lines.append(f"- Context files scanned: {len(files)}")
    lines.append(f"- Approximate context tokens: {approx_tokens}")
    lines.append(f"- Large files (> {LARGE_FILE_LINES} lines): {len(large_files)}")
    lines.append(f"- Stale files (> {STALE_DAYS_THRESHOLD} days): {len(stale_files)}")
    lines.append("")

    if large_files:
        lines.append("## Large Files\n")
        for entry in large_files:
            lines.append(f"- `{entry.path}` ({entry.lines} lines)")
        lines.append("")

    if stale_files:
        lines.append("## Stale Files\n")
        for entry in stale_files:
            lines.append(f"- `{entry.path}` ({entry.stale_days} days since update)")
        lines.append("")

    lines.append("## Recommendations\n")
    lines.append(
        "- Reduce repeated policy text by linking canonical files instead of duplicating content."
    )
    lines.append("- Split or compress oversized context files that exceed line guidance.")
    lines.append("- Review stale files and either refresh or archive with rationale.")
    lines.append("")
    lines.append("## PR Workflow\n")
    lines.append(
        "- Mode: "
        + (
            "approved for PR generation"
            if approved_for_pr
            else "local report only (default, approval pending)"
        )
    )
    lines.append("")

    return "\n".join(lines)


def generate_report(*, approve_pr: bool = False) -> dict[str, object]:
    """Generate local maintenance report and optional PR payload draft."""
    root = repo_root()
    ae_root = ai_engineering_root(root)
    files = [_file_stats(path) for path in _context_files(ae_root)]

    large_files = [item for item in files if item.lines > LARGE_FILE_LINES]
    stale_files = [item for item in files if item.stale_days > STALE_DAYS_THRESHOLD]

    generated_at = _now().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report = _report_markdown(
        generated_at=generated_at,
        files=files,
        large_files=large_files,
        stale_files=stale_files,
        approved_for_pr=approve_pr,
    )

    state_dir = ae_root / "state"
    report_path = state_dir / "maintenance_report.md"
    report_path.write_text(report + "\n", encoding="utf-8")

    branch_proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    head_branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else "main"

    payload_path = state_dir / "maintenance_pr_payload.json"
    payload: dict[str, object] = {
        "title": "maintenance: context compaction and governance alignment",
        "body": "Generated from maintenance report. Review recommendations before opening PR.",
        "base": "main",
        "head": head_branch,
        "approved": approve_pr,
        "generatedAt": generated_at,
    }
    if approve_pr:
        payload_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return {
        "reportPath": str(report_path),
        "payloadPath": str(payload_path) if approve_pr else None,
        "filesScanned": len(files),
        "largeFileCount": len(large_files),
        "staleFileCount": len(stale_files),
        "approved": approve_pr,
    }


def create_pr_from_payload() -> tuple[bool, str]:
    """Create PR from approved maintenance payload."""
    root = repo_root()
    payload_path = ai_engineering_root(root) / "state" / "maintenance_pr_payload.json"
    if not payload_path.exists():
        return (
            False,
            "missing maintenance_pr_payload.json; run maintenance report --approve-pr first",
        )

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    approved = bool(payload.get("approved"))
    if not approved:
        return False, "maintenance payload is not approved for PR creation"

    title = str(payload.get("title", "maintenance update"))
    body = str(payload.get("body", "maintenance report"))
    base = str(payload.get("base", "main"))
    head = str(payload.get("head", ""))

    args = ["gh", "pr", "create", "--base", base]
    if head:
        args.extend(["--head", head])
    args.extend(["--title", title, "--body", body])

    proc = subprocess.run(args, cwd=root, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return False, proc.stderr.strip() or proc.stdout.strip() or "failed to create PR"
    return True, proc.stdout.strip() or "PR created"
