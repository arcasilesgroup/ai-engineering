"""Core CLI commands: install, update, doctor, version.

These are the primary entry points for the ``ai-eng`` CLI.
Human-first Rich output by default; ``--json`` for agent consumption.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

if TYPE_CHECKING:
    from ai_engineering.doctor.models import DoctorReport
    from ai_engineering.installer.autodetect import DetectionResult

import typer

from ai_engineering.__version__ import __version__
from ai_engineering.cli_envelope import NextAction, emit_success
from ai_engineering.cli_output import is_json_mode, set_json_mode
from ai_engineering.cli_progress import spinner
from ai_engineering.cli_ui import (
    file_count,
    kv,
    print_stdout,
    result_header,
    show_logo,
    status_line,
    suggest_next,
    warning,
)
from ai_engineering.doctor.service import diagnose
from ai_engineering.installer.phases import (
    PHASE_DETECT,
    PHASE_GOVERNANCE,
    PHASE_HOOKS,
    PHASE_IDE_CONFIG,
    PHASE_STATE,
    PHASE_TOOLS,
    InstallMode,
    PhasePlan,
)
from ai_engineering.installer.service import install_with_pipeline
from ai_engineering.installer.ui import (
    StepStatus,
    render_detection,
    render_reinstall_options,
    render_step,
    render_summary,
)
from ai_engineering.paths import resolve_project_root
from ai_engineering.updater.service import _DIFF_MAX_LINES, update


def install_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    stacks: Annotated[
        list[str] | None,
        typer.Option("--stack", "-s", help="Technology stacks to enable."),
    ] = None,
    ides: Annotated[
        list[str] | None,
        typer.Option("--ide", "-i", help="IDE integrations to enable."),
    ] = None,
    vcs: Annotated[
        str | None,
        typer.Option("--vcs", help="VCS provider: github or azdo."),
    ] = None,
    providers: Annotated[
        list[str] | None,
        typer.Option(
            "--provider",
            "-p",
            help="AI providers to enable (e.g. claude_code, github_copilot).",
        ),
    ] = None,
    non_interactive: Annotated[
        bool,
        typer.Option(
            "--non-interactive",
            help="Run without interactive prompts, using defaults.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Output JSON plan to stdout, create zero files.",
        ),
    ] = False,
    plan_file: Annotated[
        Path | None,
        typer.Option(
            "--plan",
            help="Replay a saved install plan (JSON).",
        ),
    ] = None,
) -> None:
    """Install the ai-engineering governance framework."""
    if non_interactive:
        set_json_mode(True)

    root = resolve_project_root(target)

    # Dry-run mode: use pipeline, output JSON plan
    if dry_run:
        set_json_mode(True)
        from ai_engineering.installer.autodetect import detect_all as _detect_all

        _detected = _detect_all(root)
        resolved_vcs = vcs or _detected.vcs
        resolved_providers = (
            [_PROVIDER_ALIASES.get(p, p) for p in providers]
            if providers
            else (_detected.providers or ["claude_code"])
        )
        _result, summary = install_with_pipeline(
            root,
            stacks=stacks or _detected.stacks or [],
            ides=ides or _detected.ides or ["terminal"],
            vcs_provider=resolved_vcs,
            ai_providers=resolved_providers,
            dry_run=True,
        )
        import json

        plans = [p.to_dict() for p in summary.plans]
        print(json.dumps({"schema_version": "1", "plans": plans}, indent=2))
        return

    # Plan replay mode
    if plan_file:
        _replay_plan(root, plan_file)
        return

    # Check for existing installation
    manifest_path = root / ".ai-engineering" / "state" / "install-state.json"
    mode = InstallMode.INSTALL

    if manifest_path.exists() and not non_interactive:
        choice = render_reinstall_options()
        if choice == "cancel":
            raise typer.Exit(0)
        mode = {
            "fresh": InstallMode.FRESH,
            "repair": InstallMode.REPAIR,
            "reconfigure": InstallMode.RECONFIGURE,
        }[choice]
    elif manifest_path.exists() and non_interactive:
        mode = InstallMode.REPAIR

    # Auto-detect project configuration
    from ai_engineering.installer.autodetect import detect_all

    detected = detect_all(root)

    # Build resolved dict from CLI flags
    resolved: dict[str, Any] = {}
    if stacks:
        resolved["stacks"] = stacks
    if providers:
        resolved["providers"] = [_PROVIDER_ALIASES.get(p, p) for p in providers]
    if ides:
        resolved["ides"] = ides
    if vcs is not None:
        resolved["vcs"] = "azure_devops" if vcs == "azdo" else vcs

    # Determine final selections: flags > wizard > detection > defaults
    all_resolved = all(k in resolved for k in ("stacks", "providers", "ides", "vcs"))

    import sys

    if all_resolved or is_json_mode() or not sys.stdin.isatty():
        resolved_stacks = resolved.get("stacks", detected.stacks or ["python"])
        resolved_providers = resolved.get("providers", detected.providers or ["claude_code"])
        resolved_ides = resolved.get("ides", detected.ides or ["terminal"])
        resolved_vcs = resolved.get("vcs", detected.vcs)
    else:
        # Show detection summary
        if not is_json_mode():
            _show_detection_summary(detected)

        # Run wizard for unresolved categories
        from ai_engineering.installer.wizard import run_wizard

        wizard_result = run_wizard(detected, resolved if resolved else None)
        resolved_stacks = wizard_result.stacks
        resolved_providers = wizard_result.providers
        resolved_ides = wizard_result.ides
        resolved_vcs = wizard_result.vcs

    # Show tool availability in interactive mode
    if not is_json_mode():
        import shutil as _shutil

        tools = {
            "gh": _shutil.which("gh") is not None,
            "gitleaks": _shutil.which("gitleaks") is not None,
            "ruff": _shutil.which("ruff") is not None,
        }
        render_detection(resolved_vcs, resolved_providers, tools)

    # Run pipeline with step rendering
    with spinner("Installing governance framework..."):
        result, summary = install_with_pipeline(
            root,
            mode=mode,
            stacks=resolved_stacks,
            ides=resolved_ides,
            vcs_provider=resolved_vcs,
            ai_providers=resolved_providers,
        )

    # Render steps from pipeline summary
    if not is_json_mode():
        _render_pipeline_steps(summary)

    ai_label = ", ".join(resolved_providers)

    if is_json_mode():
        emit_success(
            "ai-eng install",
            {
                "root": str(root),
                "governance_files": len(result.governance_files.created),
                "project_files": len(result.project_files.created),
                "state_files": len(result.state_files),
                "vcs_provider": resolved_vcs,
                "ai_providers": providers or ["claude_code"],
                "readiness_status": result.readiness_status,
                "already_installed": result.already_installed,
                "manual_steps": result.manual_steps,
                "guide_text": result.guide_text,
            },
            [
                NextAction(command="ai-eng doctor", description="Run health diagnostics"),
                NextAction(
                    command="ai-eng setup platforms",
                    description="Configure platform credentials",
                ),
            ],
        )
    else:
        # Primary result on stdout (preserves test assertions)
        print_stdout(f"Installed to: {root}")

        # Decorated output on stderr
        file_count("Governance", len(result.governance_files.created))
        file_count("Project", len(result.project_files.created))
        kv("State", f"{len(result.state_files)} files")
        kv("VCS", "azdo" if resolved_vcs == "azure_devops" else resolved_vcs)
        kv("AI Providers", ai_label)
        kv("Readiness", result.readiness_status)

        typer.echo("")
        if result.manual_steps:
            warning("Manual steps required:")
            for step in result.manual_steps:
                print_stdout(f"    - {step}")

        if result.already_installed:
            print_stdout("  (framework was already installed \u2014 skipped existing files)")

        typer.echo("")
        next_steps = [
            ("ai-eng doctor", "Run health diagnostics"),
            ("ai-eng setup platforms", "Configure platform credentials"),
        ]
        if result.guide_text:
            next_steps.append(("ai-eng guide", "View branch policy setup guide"))
        suggest_next(next_steps)

        # Summary panel with next steps
        pending_setup: list[tuple[str, str]] = []
        next_steps_list: list[tuple[str, str]] = [
            ("ai-eng doctor", "Verify everything works"),
        ]
        if result.manual_steps:
            for step in result.manual_steps:
                if "setup" in step.lower():
                    pending_setup.append(("ai-eng setup", step))

        next_steps_list.append(("/ai-brainstorm", "Design your first spec"))

        hooks_count = len(result.hooks.installed) if result.hooks.installed else 0

        render_summary(
            files_created=result.total_created,
            hooks_installed=hooks_count,
            warnings=[s for s in result.manual_steps if s],
            pending_setup=pending_setup,
            next_steps=next_steps_list,
        )

        # Branch policy guide at the END -- only when automation failed
        if result.guide_text:
            typer.echo("")
            warning("Automatic branch policy application was not possible.")
            warning("You must configure branch protection manually to enforce governance gates.")


def _render_pipeline_steps(summary: object) -> None:
    """Render each phase from the pipeline summary as a wizard step."""
    from ai_engineering.installer.phases.pipeline import PipelineSummary

    if not isinstance(summary, PipelineSummary):
        return

    phase_names = [
        PHASE_DETECT,
        PHASE_GOVERNANCE,
        PHASE_IDE_CONFIG,
        PHASE_HOOKS,
        PHASE_STATE,
        PHASE_TOOLS,
    ]
    phase_labels = {
        PHASE_DETECT: "Detection",
        PHASE_GOVERNANCE: "Governance framework",
        PHASE_IDE_CONFIG: "IDE configuration",
        PHASE_HOOKS: "Git hooks",
        PHASE_STATE: "State initialization",
        PHASE_TOOLS: "Tool verification",
    }

    for i, name in enumerate(phase_names):
        phase_result = next((r for r in summary.results if r.phase_name == name), None)
        status = "ok"
        detail = ""
        if phase_result:
            count = len(phase_result.created)
            del_count = len(phase_result.deleted)
            parts = []
            if count:
                parts.append(f"{count} files")
            if del_count:
                parts.append(f"{del_count} deleted")
            detail = ", ".join(parts) if parts else "up to date"
            if phase_result.failed:
                status = "fail"
            elif phase_result.warnings:
                status = "warn"
        elif summary.failed_phase and name not in summary.completed_phases:
            status = "skip"
            detail = "skipped"

        label = phase_labels.get(name, name)
        desc = f"{'Setting up' if status != 'skip' else 'Skipped'} {label.lower()}..."
        render_step(
            StepStatus(
                number=i + 1,
                total=len(phase_names),
                name=label,
                description=desc,
                status=status,
                detail=detail,
            )
        )


def _show_detection_summary(detected: DetectionResult) -> None:
    """Show auto-detection results before the wizard."""
    parts = []
    if detected.stacks:
        parts.append(f"Stacks: {', '.join(detected.stacks)}")
    if detected.providers:
        parts.append(f"Providers: {', '.join(detected.providers)}")
    if detected.ides:
        parts.append(f"IDEs: {', '.join(detected.ides)}")
    if parts:
        typer.echo(f"\n  Detected: {' | '.join(parts)}\n")
    else:
        typer.echo("\n  No project markers detected.\n")


def _replay_plan(root: Path, plan_path: Path) -> None:
    """Replay a saved install plan with security validation.

    Reads a JSON plan file and executes the file operations it describes.
    All paths are validated against traversal attacks by PhasePlan.from_dict.

    Args:
        root: Target project root directory.
        plan_path: Path to the JSON plan file.
    """
    import json
    import shutil

    data = json.loads(plan_path.read_text(encoding="utf-8"))

    schema_version = data.get("schema_version")
    if schema_version != "1":
        typer.echo(
            f"Error: plan schema version mismatch (expected 1, got {schema_version})",
            err=True,
        )
        raise typer.Exit(code=1)

    from ai_engineering.installer.templates import (
        get_ai_engineering_template_root,
        get_project_template_root,
    )

    for plan_data in data.get("plans", []):
        plan = PhasePlan.from_dict(plan_data)  # validates path security
        for action in plan.actions:
            if action.action_type == "skip":
                continue
            dest = root / action.destination
            dest.parent.mkdir(parents=True, exist_ok=True)
            if action.source:
                for template_root in [
                    get_project_template_root(),
                    get_ai_engineering_template_root(),
                ]:
                    src = template_root / action.source
                    if src.exists():
                        shutil.copy2(src, dest)
                        break

    typer.echo(f"Plan replayed successfully to {root}")


_PROVIDER_ALIASES: dict[str, str] = {
    "claude": "claude_code",
    "copilot": "github_copilot",
    "gemini": "gemini",
    "codex": "codex",
}


def _resolve_ai_providers(providers: list[str] | None) -> list[str]:
    """Resolve AI providers from explicit flag.

    Short names (claude, copilot, gemini, codex) are mapped to internal names.
    Returns default when no flag provided.
    """
    if providers:
        return [_PROVIDER_ALIASES.get(p, p) for p in providers]
    return ["claude_code"]


def update_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Apply changes (dry-run by default)."),
    ] = False,
    show_diff: Annotated[
        bool,
        typer.Option("--diff", "-d", help="Show unified diffs for updated files."),
    ] = False,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output report as JSON (deprecated: use global --json)."),
    ] = False,
) -> None:
    """Update framework-managed governance files."""
    root = resolve_project_root(target)
    with spinner("Checking for updates..."):
        result = update(root, dry_run=not apply)

    if is_json_mode() or output_json:
        emit_success(
            "ai-eng update",
            {
                "mode": "APPLIED" if not result.dry_run else "DRY-RUN",
                "root": str(root),
                "applied": result.applied_count,
                "denied": result.denied_count,
                "changes": [
                    {"path": str(c.path), "action": c.action, "diff": c.diff}
                    for c in result.changes
                ],
            },
            [
                NextAction(command="ai-eng doctor", description="Verify framework health"),
                NextAction(command="ai-eng update --apply", description="Apply changes"),
            ],
        )
        return

    mode = "APPLIED" if not result.dry_run else "DRY-RUN"
    # Primary result on stdout
    print_stdout(f"Update [{mode}]: {root}")

    # Decorated output on stderr
    kv("Applied", result.applied_count)
    kv("Denied", result.denied_count)

    _STATUS_MAP = {
        "create": "ok",
        "update": "ok",
        "skip-unchanged": "info",
        "skip-denied": "fail",
    }

    for change in result.changes:
        st = _STATUS_MAP.get(change.action, "fail")
        status_line(st, str(change.path), change.action)

        if show_diff and change.diff:
            diff_text = change.diff
            lines = diff_text.splitlines(keepends=True)
            if len(lines) > _DIFF_MAX_LINES:
                lines = lines[:_DIFF_MAX_LINES]
                remaining = len(diff_text.splitlines()) - _DIFF_MAX_LINES
                lines.append(f"    ... ({remaining} more lines)\n")
            for line in lines:
                typer.echo(f"    {line}", nl=False)


def doctor_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Interactive fix: confirm each remediation."),
    ] = False,
    phase: Annotated[
        str | None,
        typer.Option("--phase", help="Run only this phase (e.g., hooks, tools, governance)."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what --fix would do without executing."),
    ] = False,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output report as JSON for agent consumption."),
    ] = False,
) -> None:
    """Diagnose and optionally fix framework health.

    Exit codes: 0 (pass), 1 (fail), 2 (warnings only).
    """
    if output_json:
        set_json_mode(True)
    root = resolve_project_root(target)

    if dry_run and not fix:
        fix = True  # --dry-run implies --fix

    with spinner("Running health diagnostics..."):
        report = diagnose(root, fix=fix, dry_run=dry_run, phase_filter=phase)

    if fix and not dry_run and not is_json_mode():
        _interactive_fix(root, report, phase)

    if is_json_mode():
        report_dict = report.to_dict()
        next_actions = []
        if not report.passed:
            next_actions = [
                NextAction(command="ai-eng doctor --fix", description="Fix all issues"),
            ]
        emit_success("ai-eng doctor", report_dict, next_actions)
    else:
        status = "PASS" if report.passed else "FAIL"
        result_header("Doctor", status, str(root))

        if not report.installed:
            warning("Framework not installed. Run 'ai-eng install' first.")

        kv("Summary", report.summary)

        for phase_report in report.phases:
            typer.echo(f"\n  {phase_report.name} [{phase_report.status.value}]")
            for check in phase_report.checks:
                status_line(check.status.value, check.name, check.message)

        if report.runtime:
            typer.echo("\n  runtime")
            for check in report.runtime:
                status_line(check.status.value, check.name, check.message)

        if not report.passed:
            suggest_next([("ai-eng doctor --fix", "Fix all issues")])

    if not report.passed:
        raise typer.Exit(code=1)
    if report.has_warnings:
        raise typer.Exit(code=2)


def _interactive_fix(root: Path, report: DoctorReport, phase_filter: str | None) -> None:
    """Re-run diagnostics with interactive confirmation for each fixable failure."""
    from ai_engineering.doctor.models import CheckStatus

    fixable = []
    for phase_report in report.phases:
        for check in phase_report.checks:
            if check.status in (CheckStatus.FAIL, CheckStatus.WARN) and check.fixable:
                fixable.append((phase_report.name, check))

    if not fixable:
        return

    typer.echo(f"\nFound {len(fixable)} fixable issue(s):\n")
    approve_all = False
    for phase_name, check in fixable:
        typer.echo(f"  [{phase_name}] {check.name}: {check.message}")
        if not approve_all:
            response = typer.prompt("  Fix? (y/n/all)", default="y")
            if response.lower() == "all":
                approve_all = True
            elif response.lower() != "y":
                continue

    # Re-run with fix enabled (fixes were already applied in diagnose with fix=True)
    typer.echo("\nRe-verifying fixes...")
    with spinner("Verifying..."):
        re_report = diagnose(root, fix=False, phase_filter=phase_filter)

    fixed_count = sum(1 for p in report.phases for c in p.checks if c.status == CheckStatus.FIXED)
    if fixed_count:
        typer.echo(f"  {fixed_count} issue(s) fixed.")

    # Update the report with re-verification results
    report.phases = re_report.phases
    report.runtime = re_report.runtime


def version_cmd() -> None:
    """Show the installed ai-engineering version and lifecycle status."""
    from ai_engineering.version.checker import check_version, load_registry

    if is_json_mode():
        registry = load_registry()
        result = check_version(__version__, registry)
        emit_success(
            "ai-eng version",
            {"version": __version__, "message": result.message},
        )
    else:
        show_logo()
        registry = load_registry()
        result = check_version(__version__, registry)
        typer.echo(f"ai-engineering {result.message}")
