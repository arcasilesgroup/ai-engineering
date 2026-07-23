"""Harness CLI commands (spec-194).

Deterministic context and safety harness: baseline, verify, compare.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.harness.adapters.antigravity import AntigravityAdapter
from ai_engineering.harness.adapters.claude import ClaudeAdapter
from ai_engineering.harness.adapters.codex import CodexAdapter
from ai_engineering.harness.adapters.copilot import CopilotAdapter
from ai_engineering.harness.adapters.cursor import CursorAdapter
from ai_engineering.harness.adapters.opencode import OpenCodeAdapter
from ai_engineering.harness.redactor import contains_secrets, redact_json
from ai_engineering.harness.schema import ContextSafetyReport

app = typer.Typer(help="Deterministic context and safety harness (spec-194)")

# Registry of all host adapters
ADAPTERS = {
    "claude": ClaudeAdapter,
    "codex": CodexAdapter,
    "opencode": OpenCodeAdapter,
    "copilot": CopilotAdapter,
    "cursor": CursorAdapter,
    "antigravity": AntigravityAdapter,
}


@app.command()
def baseline(
    host: Annotated[str, typer.Argument(help="Host adapter to use")] = "claude",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Capture a read-only baseline for a host."""
    adapter_class = ADAPTERS.get(host)
    if not adapter_class:
        typer.echo(f"Unknown host: {host}. Available: {', '.join(ADAPTERS.keys())}", err=True)
        raise typer.Exit(1)

    adapter = adapter_class()
    report = adapter.collect(fixture_name="live")

    # Redact the report
    report_json = report.to_json()
    if contains_secrets(report_json):
        report_json = redact_json(report_json)

    if output:
        output.write_text(report_json, encoding="utf-8")
        typer.echo(f"Baseline written to {output}")
    elif json_output:
        typer.echo(report_json)
    else:
        _print_human(report)


@app.command()
def verify(
    host: Annotated[str, typer.Argument(help="Host adapter to use")] = "claude",
    baseline_path: Annotated[Path | None, typer.Option("--baseline", "-b")] = None,
) -> None:
    """Verify current state against a baseline."""
    adapter_class = ADAPTERS.get(host)
    if not adapter_class:
        typer.echo(f"Unknown host: {host}", err=True)
        raise typer.Exit(1)

    adapter = adapter_class()
    current = adapter.collect(fixture_name="live")

    if baseline_path and baseline_path.exists():
        baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline = ContextSafetyReport.from_json(baseline_data)
        diffs = _compare_reports(baseline, current)
        if diffs:
            typer.echo("FAIL — differences found:")
            for d in diffs:
                typer.echo(f"  - {d}")
            raise typer.Exit(1)
        else:
            typer.echo("PASS — matches baseline")
    else:
        typer.echo(f"Verdict: {current.verdict}")
        if current.verdict == "fail":
            raise typer.Exit(1)


@app.command()
def compare(
    baseline_path: Annotated[Path, typer.Argument(help="Baseline report JSON")],
    current_path: Annotated[Path, typer.Argument(help="Current report JSON")],
) -> None:
    """Compare two reports and show differences."""
    baseline = ContextSafetyReport.from_json(json.loads(baseline_path.read_text(encoding="utf-8")))
    current = ContextSafetyReport.from_json(json.loads(current_path.read_text(encoding="utf-8")))

    diffs = _compare_reports(baseline, current)
    if diffs:
        typer.echo("Differences:")
        for d in diffs:
            typer.echo(f"  - {d}")
        raise typer.Exit(1)
    else:
        typer.echo("No differences")


def _compare_reports(baseline: ContextSafetyReport, current: ContextSafetyReport) -> list[str]:
    """Compare two reports and return list of differences."""
    diffs = []

    if baseline.root.bytes != current.root.bytes:
        diffs.append(
            f"root.bytes: {baseline.root.bytes} → {current.root.bytes} "
            f"(delta: {current.root.bytes - baseline.root.bytes})"
        )

    if baseline.root.estimated_tokens != current.root.estimated_tokens:
        diffs.append(
            f"root.estimated_tokens: {baseline.root.estimated_tokens} → {current.root.estimated_tokens}"
        )

    if baseline.root.mandatory_reads != current.root.mandatory_reads:
        diffs.append(
            f"root.mandatory_reads: {baseline.root.mandatory_reads} → {current.root.mandatory_reads}"
        )

    if baseline.catalog.unique_ids != current.catalog.unique_ids:
        diffs.append(
            f"catalog.unique_ids: {baseline.catalog.unique_ids} → {current.catalog.unique_ids}"
        )

    if baseline.catalog.duplicate_ids != current.catalog.duplicate_ids:
        diffs.append(
            f"catalog.duplicate_ids: {baseline.catalog.duplicate_ids} → {current.catalog.duplicate_ids}"
        )

    if baseline.hooks.injection_count != current.hooks.injection_count:
        diffs.append(
            f"hooks.injection_count: {baseline.hooks.injection_count} → {current.hooks.injection_count}"
        )

    if baseline.hooks.automatic_writes != current.hooks.automatic_writes:
        diffs.append(
            f"hooks.automatic_writes: {baseline.hooks.automatic_writes} → {current.hooks.automatic_writes}"
        )

    if baseline.mcp_residue.reachable_registrations != current.mcp_residue.reachable_registrations:
        diffs.append(
            f"mcp_residue.reachable_registrations: {baseline.mcp_residue.reachable_registrations} → {current.mcp_residue.reachable_registrations}"
        )

    if baseline.verdict != current.verdict:
        diffs.append(f"verdict: {baseline.verdict} → {current.verdict}")

    return diffs


def _print_human(report: ContextSafetyReport) -> None:
    """Print human-readable report."""
    typer.echo(f"Host: {report.host}")
    typer.echo(f"Fixture: {report.fixture}")
    typer.echo(f"Verdict: {report.verdict}")
    typer.echo()
    typer.echo("Root:")
    typer.echo(f"  Bytes: {report.root.bytes}")
    typer.echo(f"  Est. tokens: {report.root.estimated_tokens}")
    typer.echo(f"  Mandatory reads: {report.root.mandatory_reads}")
    typer.echo()
    typer.echo("Catalog:")
    typer.echo(f"  Unique IDs: {report.catalog.unique_ids}")
    typer.echo(f"  Duplicate IDs: {report.catalog.duplicate_ids}")
    typer.echo(f"  Total skills: {report.catalog.total_skills}")
    typer.echo()
    typer.echo("Hooks:")
    typer.echo(f"  Injections: {report.hooks.injection_count}")
    typer.echo(f"  Automatic writes: {report.hooks.automatic_writes}")
    typer.echo()
    typer.echo("MCP Residue:")
    typer.echo(f"  Registrations: {report.mcp_residue.reachable_registrations}")
    typer.echo(f"  Plugins: {report.mcp_residue.plugins}")
