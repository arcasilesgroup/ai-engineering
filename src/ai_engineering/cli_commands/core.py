"""Core CLI commands: install, update, doctor, version.

These are the primary entry points for the ``ai-eng`` CLI.
Human-first Rich output by default; ``--json`` for agent consumption.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import click
import click.exceptions
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
from ai_engineering.platforms.detector import detect_platforms
from ai_engineering.updater.service import _DIFF_MAX_LINES, update
from ai_engineering.vcs.factory import detect_from_remote


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
        resolved_vcs = _resolve_vcs_provider(vcs, root)
        resolved_providers = _resolve_ai_providers(providers)
        _result, summary = install_with_pipeline(
            root,
            stacks=stacks or [],
            ides=ides or [],
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
    manifest_path = root / ".ai-engineering" / "state" / "install-manifest.json"
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

    # Resolve VCS provider: explicit flag > autodetect > interactive prompt
    resolved_vcs = _resolve_vcs_provider(vcs, root)

    # Resolve AI providers: explicit flag > interactive prompt > default
    resolved_providers = _resolve_ai_providers(providers)

    # Prompt for stacks and IDEs when flags absent
    resolved_stacks = stacks or _prompt_stacks()
    resolved_ides = ides or _prompt_ides()

    # Optional external CI/CD documentation reference
    external_cicd_url = _prompt_external_cicd_docs()

    # Show detection summary in interactive mode
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

    # Write CI/CD standards URL to manifest.yml (not install-manifest.json)
    if external_cicd_url:
        _write_cicd_standards_url(root, external_cicd_url)

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

    # Optional platform onboarding prompt (D024-003: opt-in).
    if not is_json_mode():
        _offer_platform_onboarding(root, vcs_provider=resolved_vcs, non_interactive=non_interactive)


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


def _prompt_stacks() -> list[str]:
    """Prompt for stacks when --stack flag absent."""
    if is_json_mode():
        return ["python"]
    try:
        raw = typer.prompt("Technology stacks (comma-separated)", default="python")
        return [s.strip().lower() for s in raw.split(",") if s.strip()]
    except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
        return ["python"]


def _prompt_ides() -> list[str]:
    """Prompt for IDEs when --ide flag absent."""
    if is_json_mode():
        return ["terminal"]
    try:
        raw = typer.prompt("IDE integrations (comma-separated)", default="terminal")
        return [s.strip().lower() for s in raw.split(",") if s.strip()]
    except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
        return ["terminal"]


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


def _resolve_vcs_provider(vcs: str | None, root: Path) -> str:
    """Resolve VCS provider from flag, remote detection, or interactive prompt.

    Args:
        vcs: Explicit --vcs flag value, or None.
        root: Project root for remote detection.

    Returns:
        Resolved VCS provider string.
    """
    if vcs is not None:
        return "azure_devops" if vcs == "azdo" else vcs

    # Try autodetection from git remote
    from ai_engineering.git.operations import run_git

    ok, _ = run_git(["remote", "get-url", "origin"], root)
    if ok:
        return detect_from_remote(root)

    # No remote — prompt interactively (or default in non-interactive/JSON mode)
    if is_json_mode():
        return "github"

    try:
        choice = typer.prompt(
            "No git remote detected. VCS provider",
            default="github",
            type=click.Choice(["github", "azdo"]),
        )
        return "azure_devops" if choice == "azdo" else choice
    except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
        return "github"


_PROVIDER_ALIASES: dict[str, str] = {
    "claude": "claude_code",
    "copilot": "github_copilot",
    "gemini": "gemini",
    "codex": "codex",
}


def _prompt_external_cicd_docs() -> str:
    """Prompt for optional external CI/CD standards documentation URL."""
    if is_json_mode():
        return ""
    try:
        url = typer.prompt(
            "External CI/CD standards URL (optional, Enter to skip)",
            default="",
            show_default=False,
        )
        return url.strip()
    except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
        return ""


def _write_cicd_standards_url(root: Path, url: str) -> None:
    """Write CI/CD standards URL to the project's manifest.yml.

    Updates the ``cicd.standards_url`` field. If the manifest file does not
    exist or is unreadable, the write is silently skipped (install may not
    have created it yet in edge cases).
    """
    import yaml

    manifest_path = root / ".ai-engineering" / "manifest.yml"
    if not manifest_path.exists():
        return

    text = manifest_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    cicd = data.setdefault("cicd", {})
    cicd["standards_url"] = url
    manifest_path.write_text(
        yaml.safe_dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _resolve_ai_providers(providers: list[str] | None) -> list[str]:
    """Resolve AI providers from explicit flag or interactive prompt.

    Short names (claude, copilot, gemini, codex) are mapped to internal names.
    """
    if providers:
        return [_PROVIDER_ALIASES.get(p, p) for p in providers]

    if is_json_mode():
        return ["claude_code"]

    try:
        raw = typer.prompt(
            "AI assistants (comma-separated)",
            default="claude",
            show_default=True,
        )
        names = [n.strip().lower() for n in raw.split(",") if n.strip()]
        resolved = [_PROVIDER_ALIASES.get(n, n) for n in names]
        return resolved if resolved else ["claude_code"]
    except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
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

    for change in result.changes:
        st = "ok" if change.action in ("create", "update") else "fail"
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
    fix_hooks: Annotated[
        bool,
        typer.Option("--fix-hooks", help="Reinstall managed git hooks."),
    ] = False,
    fix_tools: Annotated[
        bool,
        typer.Option("--fix-tools", help="Install missing Python tools."),
    ] = False,
    check_platforms: Annotated[
        bool,
        typer.Option("--check-platforms", help="Validate stored platform credentials."),
    ] = False,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output report as JSON (deprecated: use global --json)."),
    ] = False,
) -> None:
    """Diagnose and optionally fix framework health."""
    root = resolve_project_root(target)
    with spinner("Running health diagnostics..."):
        report = diagnose(
            root,
            fix_hooks=fix_hooks,
            fix_tools=fix_tools,
            include_platforms=check_platforms,
        )

    if is_json_mode() or output_json:
        report_dict = report.to_dict()
        if is_json_mode():
            next_actions = []
            if not report.passed:
                next_actions = [
                    NextAction(
                        command="ai-eng doctor --fix-tools",
                        description="Install missing tools",
                    ),
                    NextAction(
                        command="ai-eng doctor --fix-hooks",
                        description="Reinstall git hooks",
                    ),
                ]
            emit_success("ai-eng doctor", report_dict, next_actions)
        else:
            # Legacy per-command --json: raw dict output
            import json

            typer.echo(json.dumps(report_dict, indent=2))
    else:
        status = "PASS" if report.passed else "FAIL"
        # Result header on stderr (CliRunner captures both by default)
        result_header("Doctor", status, str(root))
        kv("Summary", report.summary)

        for check in report.checks:
            status_line(check.status.value, check.name, check.message)

        if not report.passed:
            suggest_next(
                [
                    ("ai-eng doctor --fix-tools", "Install missing tools"),
                    ("ai-eng doctor --fix-hooks", "Reinstall git hooks"),
                ]
            )

    if not report.passed:
        raise typer.Exit(code=1)
    if report.has_warnings:
        raise typer.Exit(code=2)


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


def _offer_platform_onboarding(
    root: Path,
    *,
    vcs_provider: str | None = None,
    non_interactive: bool = False,
) -> None:
    """Offer optional platform credential setup after install.

    Detects platform markers and prompts the user to run setup.
    When no platforms are auto-detected, still offers manual setup.
    Always skippable (D024-003).
    """
    if non_interactive:
        return
    detected = detect_platforms(root, vcs_provider=vcs_provider)
    if detected:
        names = ", ".join(p.value for p in detected)
        typer.echo(f"\n  Detected platforms: {names}")
    else:
        typer.echo("\n  No platforms auto-detected.")

    # Offer SonarCloud/SonarQube setup directly (B.3)
    from ai_engineering.credentials.models import PlatformKind as PK

    if PK.SONAR not in detected:
        try:
            setup_sonar = typer.confirm("  Configure SonarCloud/SonarQube?", default=False)
        except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
            setup_sonar = False
        if setup_sonar:
            detected.append(PK.SONAR)

    try:
        run_setup = typer.confirm("  Configure platform credentials now?", default=False)
    except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
        return
    if run_setup:
        from ai_engineering.cli_commands.setup import setup_platforms_cmd

        setup_platforms_cmd(root, vcs_provider=vcs_provider)
