"""CLI command for ``ai-eng verify``.

Runs every verification specialist (governance, security, architecture,
quality, feature) against the target project and reports a single scored
report. There is no ``MODE`` argument and no ``--full`` flag: verify is
deliberately simple — one command, every specialist, one consolidated
verdict. The legacy ``platform`` mode is the implementation.
"""

from __future__ import annotations

import contextlib
import time as _time
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.core.output import NextAction, Renderer
from ai_engineering.paths import resolve_project_root
from ai_engineering.state.locking import artifact_lock
from ai_engineering.verify.service import (
    verify_platform,
)
from ai_engineering.verify.service import (
    verify_release as verify_release_readiness,
)


def verify_cmd(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Project root to verify. Defaults to cwd."),
    ] = None,
    release: Annotated[
        str | None,
        typer.Option("--release", help="Run release-readiness GO/NO-GO for VERSION."),
    ] = None,
) -> None:
    """Run every verification specialist and emit a scored report."""
    root = resolve_project_root(target)
    renderer = Renderer.from_app("verify")

    if release:
        _verify_release_cmd(renderer, root, release)
        return

    t0 = _time.monotonic()
    renderer.header()
    renderer.action("Verifying", "all specialists", detail=str(root))
    with artifact_lock(root, "mirror-sync"):
        result = verify_platform(root)
    elapsed_ms = int((_time.monotonic() - t0) * 1000)

    _emit_telemetry(root, result, elapsed_ms)
    _render_report(renderer, result, root)

    if result.verdict.value == "FAIL":
        next_actions = [
            NextAction(label="Re-run health diagnostics", command="ai-eng doctor"),
            NextAction(label="Re-check content integrity", command="ai-eng check"),
        ]
        renderer.error(
            f"verify failed: {result.score}/100 — verdict {result.verdict.value}",
            code="VERIFY_FAILED",
            fix="Inspect specialist findings above and address each blocker.",
            next_actions=next_actions,
        )

    renderer.ok(
        f"verify completed: {result.score}/100",
        result={
            "score": result.score,
            "verdict": result.verdict.value,
            "summary": result.summary(),
            "specialists": [
                {
                    "name": specialist.name,
                    "label": specialist.label,
                    "applicable": specialist.applicable,
                    "rationale": specialist.rationale,
                    "score": specialist.score,
                    "verdict": specialist.verdict.value,
                    "summary": specialist.summary(),
                }
                for specialist in result.specialists
            ],
            "findings": [
                {
                    "severity": f.severity.value,
                    "category": f.category,
                    "message": f.message,
                    "file": f.file,
                    "line": f.line,
                    "specialist": f.specialist,
                }
                for f in result.findings
            ],
        },
    )


def _verify_release_cmd(renderer: Renderer, root: Path, version: str) -> None:
    t0 = _time.monotonic()
    renderer.header()
    renderer.action("Verifying", "release readiness", detail=f"{version} @ {root}")
    with artifact_lock(root, "release-readiness"):
        report = verify_release_readiness(root, version)
    elapsed_ms = int((_time.monotonic() - t0) * 1000)
    _emit_release_telemetry(root, report, elapsed_ms)
    _render_release_report(renderer, report)

    payload = {"version": version, "release_readiness": report.to_dict()}
    if report.verdict == "NO-GO":
        if renderer.is_json:
            renderer.ok("release readiness: NO-GO", result=payload)
            raise typer.Exit(code=1)
        renderer.error(
            "release readiness: NO-GO",
            code="RELEASE_READINESS_FAILED",
            fix="Resolve failed readiness dimensions or record governed risk acceptance.",
        )
    renderer.ok(f"release readiness: {report.verdict}", result=payload)


def _render_release_report(renderer: Renderer, report) -> None:
    renderer.kv("Release", report.version)
    renderer.kv("Verdict", report.verdict)
    renderer.kv("Artifact", report.artifact_path)
    renderer.section("Release readiness")
    for name, dimension in report.dimensions.items():
        status = str(dimension.get("status", "UNKNOWN"))
        summary = str(dimension.get("summary", ""))
        renderer.check_result(
            name,
            status == "PASS",
            detail=summary,
            warn=status == "CONDITIONAL",
        )
    if report.conditions:
        renderer.section("Conditions")
        for condition in report.conditions:
            renderer.step(f"    {condition}")


def _emit_release_telemetry(root: Path, report, elapsed_ms: int) -> None:
    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_scan_event

        emit_scan_event(
            root,
            mode="release",
            score=100 if report.allows_release else 0,
            findings={
                "verdict": report.verdict,
                "conditions": len(report.conditions),
            },
            duration_ms=elapsed_ms,
            outcome="success" if report.allows_release else "failure",
        )


def _emit_telemetry(root: Path, result, elapsed_ms: int) -> None:
    """Emit scan + advisory events; fail-open on telemetry errors."""
    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_scan_event

        emit_scan_event(
            root,
            mode="platform",
            score=result.score,
            findings=result.summary(),
            duration_ms=elapsed_ms,
            outcome="failure" if result.verdict.value == "FAIL" else "success",
        )

    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_guard_advisory

        summary = result.summary()
        emit_guard_advisory(
            root,
            files_checked=len({f.file for f in result.findings if f.file}),
            warnings=summary.get("blocker", 0)
            + summary.get("critical", 0)
            + summary.get("major", 0),
            concerns=summary.get("minor", 0) + summary.get("info", 0),
        )


def _render_report(renderer: Renderer, result, root: Path) -> None:
    """Render the consolidated verdict and per-specialist breakdown."""
    renderer.kv("Score", f"{result.score}/100")
    renderer.kv("Verdict", result.verdict.value)

    if not result.specialists:
        renderer.check_result("No findings", True, detail="All checks passed")
        return

    renderer.section("Specialists")
    for specialist in result.specialists:
        if not specialist.applicable:
            renderer.check_result(
                specialist.label,
                True,
                detail=specialist.rationale or "not applicable",
                skipped=True,
            )
            continue

        summary_pairs = sorted(specialist.summary().items())
        summary_str = ", ".join(f"{sev}: {count}" for sev, count in summary_pairs)
        verdict_label = specialist.verdict.value
        detail = f"{verdict_label} {specialist.score}/100"
        if summary_str:
            detail += f" ({summary_str})"

        if verdict_label == "FAIL":
            renderer.check_result(specialist.label, False, detail=detail)
        elif verdict_label == "WARN":
            renderer.check_result(specialist.label, False, detail=detail, warn=True)
        else:
            renderer.check_result(specialist.label, True, detail=detail)

        for finding in result.findings_for_specialist(specialist.name):
            location = ""
            if finding.file:
                rel = _relative(finding.file, root)
                location = f" ({rel}:{finding.line})" if finding.line else f" ({rel})"
            renderer.step(
                f"    [{finding.severity.value}] {finding.category}: {finding.message}{location}"
            )


def _relative(file: str, root: Path) -> str:
    """Render finding file as a project-relative path when possible."""
    try:
        return str(Path(file).resolve().relative_to(root.resolve()))
    except (ValueError, OSError):
        return file
