"""Scan report formatter commands.

Formats raw scan findings JSON into the standard markdown scan output contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.lib.render import render_markdown


def _load_payload(path: Path | None, raw_json: str | None) -> dict:
    if path is not None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise typer.Exit(code=1) from exc
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise typer.Exit(code=1) from exc
    typer.echo("Provide either --input or --json.", err=True)
    raise typer.Exit(code=1)


def _severity_counts(findings: list[dict]) -> dict[str, int]:
    counts = {"blocker": 0, "critical": 0, "major": 0, "minor": 0, "info": 0}
    for finding in findings:
        severity = str(finding.get("severity", "info")).lower()
        if severity in counts:
            counts[severity] += 1
        else:
            counts["info"] += 1
    return counts


def scan_report_format(
    mode: Annotated[str, typer.Argument(help="Scan mode name (security, quality, ... )")],
    input_path: Annotated[
        Path | None,
        typer.Option("--input", help="Path to findings JSON"),
    ] = None,
    raw_json: Annotated[
        str | None,
        typer.Option("--json", help="Inline findings JSON payload"),
    ] = None,
    render: Annotated[bool, typer.Option(help="Render with rich markdown output")] = False,
) -> None:
    """Format scan findings JSON into the standard markdown report."""
    payload = _load_payload(input_path, raw_json)

    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        findings = []

    score = int(payload.get("score", 0))
    verdict = str(payload.get("verdict", "WARN")).upper()
    counts = _severity_counts(findings)

    lines = [
        f"# Scan Report: {mode}",
        "",
        f"## Score: {score}/100",
        f"## Verdict: {verdict}",
        "",
        "## Findings",
        "| # | Severity | Category | Description | Location | Remediation |",
        "|---|----------|----------|-------------|----------|-------------|",
    ]

    if findings:
        for index, finding in enumerate(findings, start=1):
            severity = str(finding.get("severity", "info"))
            category = str(finding.get("category", "general"))
            description = str(finding.get("description", ""))
            location = str(finding.get("location", "-"))
            remediation = str(finding.get("remediation", "-"))
            lines.append(
                "| "
                f"{index} | {severity} | {category} | {description} | "
                f"{location} | {remediation} |",
            )
    else:
        lines.append("| 1 | info | general | No findings reported | - | - |")

    lines.extend(
        [
            "",
            "## Signals",
            json.dumps(
                {
                    "mode": mode,
                    "score": score,
                    "findings": {
                        "blocker": counts["blocker"],
                        "critical": counts["critical"],
                        "major": counts["major"],
                        "minor": counts["minor"],
                    },
                },
            ),
            "",
            "## Gate Check",
            f"- Blocker findings: {counts['blocker']} (threshold: 0)",
            f"- Critical findings: {counts['critical']} (threshold: 0)",
            "- Verdict justification: "
            f"{payload.get('justification', 'Based on score and findings severity.')}",
        ],
    )

    report = "\n".join(lines)
    if render:
        render_markdown(report)
    else:
        typer.echo(report)
