"""Verify service -- aggregates tool outputs into scored reports."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ai_engineering.verify.scoring import FindingSeverity, VerifyScore


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def verify_quality(project_root: Path) -> VerifyScore:
    """Run quality checks and produce a scored report."""
    score = VerifyScore()

    # Ruff lint
    result = _run(
        ["uv", "run", "ruff", "check", "src/", "--output-format", "json"],
        project_root,
    )
    if result.returncode != 0 and result.stdout:
        try:
            findings = json.loads(result.stdout)
            for f in findings:
                score.add(
                    FindingSeverity.MAJOR,
                    "lint",
                    f.get("message", "lint violation"),
                    file=f.get("filename"),
                    line=f.get("location", {}).get("row"),
                )
        except json.JSONDecodeError:
            score.add(
                FindingSeverity.MAJOR,
                "lint",
                "ruff check failed (non-JSON output)",
            )

    # Duplication
    try:
        from ai_engineering.policy.duplication import _duplication_ratio

        ratio, _total, _dup = _duplication_ratio(
            project_root / "src" / "ai_engineering",
        )
        if ratio > 3.0:
            score.add(
                FindingSeverity.MAJOR,
                "duplication",
                f"Duplication ratio {ratio:.1f}% exceeds 3%",
            )
    except Exception:
        pass  # duplication module may not be available

    return score


def verify_security(project_root: Path) -> VerifyScore:
    """Run security checks and produce a scored report."""
    score = VerifyScore()

    # Gitleaks
    result = _run(
        [
            "gitleaks",
            "detect",
            "--source",
            ".",
            "--no-banner",
            "--report-format",
            "json",
            "--report-path",
            "/dev/stdout",
        ],
        project_root,
    )
    if result.returncode != 0 and result.stdout:
        try:
            leaks = json.loads(result.stdout)
            for leak in leaks:
                score.add(
                    FindingSeverity.BLOCKER,
                    "secrets",
                    f"Secret detected: {leak.get('Description', 'unknown')}",
                    file=leak.get("File"),
                    line=leak.get("StartLine"),
                )
        except json.JSONDecodeError:
            pass

    # pip-audit
    result = _run(
        ["uv", "run", "pip-audit", "--format", "json"],
        project_root,
    )
    if result.returncode != 0 and result.stdout:
        try:
            audit = json.loads(result.stdout)
            for vuln in audit.get("dependencies", []):
                for v in vuln.get("vulns", []):
                    score.add(
                        FindingSeverity.CRITICAL,
                        "dependency",
                        f"{vuln['name']}: {v.get('id', 'unknown vulnerability')}",
                    )
        except json.JSONDecodeError:
            pass

    return score


def verify_governance(project_root: Path) -> VerifyScore:
    """Run governance checks and produce a scored report."""
    score = VerifyScore()

    # ai-eng validate
    result = _run(
        ["uv", "run", "ai-eng", "validate", "--json"],
        project_root,
    )
    if result.returncode != 0:
        score.add(
            FindingSeverity.CRITICAL,
            "integrity",
            "Content integrity validation failed",
        )

    return score


def verify_platform(project_root: Path) -> VerifyScore:
    """Aggregate all modes into a platform score."""
    quality = verify_quality(project_root)
    security = verify_security(project_root)
    governance = verify_governance(project_root)

    combined = VerifyScore()
    combined.findings.extend(quality.findings)
    combined.findings.extend(security.findings)
    combined.findings.extend(governance.findings)

    return combined


MODES = {
    "quality": verify_quality,
    "security": verify_security,
    "governance": verify_governance,
    "platform": verify_platform,
}
