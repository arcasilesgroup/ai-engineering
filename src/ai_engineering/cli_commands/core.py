"""Core CLI commands: install, update, doctor, version.

These are the primary entry points for the ``ai-eng`` CLI.
Human-first Rich output by default; ``--json`` for agent consumption.
"""

from __future__ import annotations

import sys
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

if TYPE_CHECKING:
    from ai_engineering.doctor.models import DoctorReport
    from ai_engineering.installer.autodetect import DetectionResult

import typer

from ai_engineering import __version__
from ai_engineering.cli_commands._exit_codes import (
    EXIT_PREREQS_MISSING,
    EXIT_TOOLS_FAILED,
    PrereqMissing,
)
from ai_engineering.cli_envelope import NextAction, emit_success
from ai_engineering.cli_output import is_json_mode, set_json_mode
from ai_engineering.cli_progress import spinner, step_progress
from ai_engineering.cli_ui import (
    error,
    file_count,
    info,
    kv,
    print_stderr,
    print_stdout,
    render_update_tree,
    result_header,
    show_logo,
    status_line,
    suggest_next,
    warning,
)
from ai_engineering.commands.update_workflow import (
    UpdateWorkflowResult,
    UpdateWorkflowStatus,
    run_update_workflow,
)
from ai_engineering.config.loader import load_manifest_config
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
from ai_engineering.installer.phases.sdk_prereqs import check_sdk_prereqs
from ai_engineering.installer.service import install_with_pipeline
from ai_engineering.installer.ui import (
    StepStatus,
    render_detection,
    render_step,
    render_summary,
)
from ai_engineering.paths import resolve_project_root
from ai_engineering.prereqs.uv import check_uv_prereq
from ai_engineering.updater.service import _DIFF_MAX_LINES, update


def _doctor_follow_up_counts(report: DoctorReport) -> tuple[int, int]:
    """Return counts of fixable and manual follow-up issues in a doctor report."""
    fixable = 0
    manual = 0

    for phase_report in report.phases:
        for check in phase_report.checks:
            status = getattr(check.status, "value", check.status)
            if status not in {"fail", "warn"}:
                continue
            if getattr(check, "fixable", False):
                fixable += 1
            else:
                manual += 1

    for check in report.runtime:
        status = getattr(check.status, "value", check.status)
        if status in {"fail", "warn"}:
            manual += 1

    return fixable, manual


def install_cmd(  # audit:exempt:pre-existing-debt-out-of-spec-114-G7-scope
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
            help="AI providers to enable (e.g. claude-code, github-copilot).",
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
    fresh: Annotated[
        bool,
        typer.Option(
            "--fresh",
            help="Overwrite all framework files (typed confirmation required).",
        ),
    ] = False,
    reconfigure: Annotated[
        bool,
        typer.Option(
            "--reconfigure",
            help="Re-run the configuration wizard to change providers/stacks/IDEs.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Re-install every required tool, ignoring the idempotence skip (D-101-07).",
        ),
    ] = False,
    no_auto_remediate: Annotated[
        bool,
        typer.Option(
            "--no-auto-remediate",
            help=(
                "Disable spec-109 D-109-05 post-pipeline auto-remediation. "
                "Useful in CI to detect first-attempt failures."
            ),
        ),
    ] = False,
    engram: Annotated[
        bool,
        typer.Option(
            "--engram",
            help=(
                "Install the third-party Engram memory product without prompting "
                "(spec-123 D-123-12). Engram is a peer product, not a framework "
                "dependency."
            ),
        ),
    ] = False,
    no_engram: Annotated[
        bool,
        typer.Option(
            "--no-engram",
            help=(
                "Skip the Engram install prompt (spec-123 D-123-12). Default "
                "behaviour for non-interactive sessions."
            ),
        ),
    ] = False,
) -> None:
    """Install the ai-engineering governance framework."""
    if non_interactive:
        set_json_mode(True)

    root = resolve_project_root(target)
    _validate_install_target(root, non_interactive=non_interactive)

    if dry_run:
        _emit_install_dry_run_plan(
            root,
            stacks=stacks,
            ides=ides,
            vcs=vcs,
            providers=providers,
        )
        return

    if plan_file:
        _replay_plan(root, plan_file)
        return

    is_reinstall = _is_reinstall(root)
    mode = _resolve_install_mode(
        is_reinstall,
        fresh=fresh,
        reconfigure=reconfigure,
        non_interactive=non_interactive,
    )

    resolved_stacks, resolved_providers, resolved_ides, resolved_vcs = (
        _resolve_install_configuration(
            root,
            is_reinstall=is_reinstall,
            mode=mode,
            stacks=stacks,
            providers=providers,
            ides=ides,
            vcs=vcs,
        )
    )

    _confirm_reinstall_if_needed(
        is_reinstall=is_reinstall,
        non_interactive=non_interactive,
        mode=mode,
        resolved_stacks=resolved_stacks,
        resolved_providers=resolved_providers,
        resolved_ides=resolved_ides,
    )

    _render_install_detection_if_needed(resolved_vcs, resolved_providers)

    # spec-124 D-124-02: removed one-shot "What's new" banner. Install
    # pipeline starts directly with the prereq gates and phase output.

    _check_install_prerequisites(root, resolved_stacks)

    result, summary = _run_install_pipeline(
        root,
        mode=mode,
        resolved_stacks=resolved_stacks,
        resolved_ides=resolved_ides,
        resolved_vcs=resolved_vcs,
        resolved_providers=resolved_providers,
        force=force,
    )

    # spec-101 Corr-1 (Wave 28): in --non-interactive mode, emit one line
    # per skipped tool entry so downstream verifiers (the smoke-test
    # idempotence assertion) can match the ``tool:<name>:<marker>``
    # signature. Markers go to stderr to preserve stdout JSON purity for
    # --non-interactive consumers.
    _emit_noninteractive_skipped_tools(summary, non_interactive=non_interactive)

    # spec-109 D-109-04: ALWAYS render the pipeline step report BEFORE deciding
    # the exit code. The pre-spec-109 flow exited 80 first and rendered later,
    # so users saw "see warnings above" with no warnings printed.
    if not is_json_mode():
        _render_pipeline_steps(summary)

    # spec-109 D-109-05: invoke auto-remediation when the pipeline recorded
    # non-critical failures (today: ToolsPhase). Reuses doctor's fix paths
    # so the user does not have to run `ai-eng doctor --fix` manually.
    # spec-109 R-109-01: --no-auto-remediate disables the second pass so CI
    # callers can detect first-attempt failures (e.g. regression detection).
    non_critical_failures_list = _coerce_non_critical_failures(summary)
    auto_remediation_report = _run_auto_remediation(
        root,
        non_critical_failures_list,
        no_auto_remediate=no_auto_remediate,
    )

    if auto_remediation_report.invoked and not is_json_mode():
        _render_auto_remediation_summary(auto_remediation_report)

    # spec-109 D-109-06: exit code reflects reality.
    # - Critical phase failure  -> EXIT 80 (unchanged).
    # - Non-critical failure that auto-remediated successfully -> EXIT 0.
    # - Non-critical failure that survived remediation -> EXIT 80.
    _raise_install_failures(
        summary,
        non_critical_failures_list=non_critical_failures_list,
        auto_remediation_report=auto_remediation_report,
        no_auto_remediate=no_auto_remediate,
    )

    # spec-123 D-123-12 / D-123-29: Engram is a third-party memory product
    # wired at install time. Prompt fires post-deps; --engram / --no-engram
    # flags bypass deterministically; non-interactive sessions skip silently.
    _maybe_run_engram_install(
        root,
        engram=engram,
        no_engram=no_engram,
        non_interactive=non_interactive,
    )

    _render_install_success(
        root,
        result,
        resolved_vcs=resolved_vcs,
        auto_remediation_report=auto_remediation_report,
    )


_PROJECT_SIGNALS = (
    ".git",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "tsconfig.json",
)


def _validate_install_target(root: Path, *, non_interactive: bool) -> None:
    """Confirm the selected root looks like a project."""
    has_project = any((root / signal).exists() for signal in _PROJECT_SIGNALS)
    has_project = has_project or bool(list(root.glob("*.sln")))
    if has_project:
        return
    if non_interactive:
        typer.echo(f"Error: no project files detected in {root}.", err=True)
        raise typer.Exit(code=1)
    if not typer.confirm(f"No project files detected in {root}. Continue anyway?", abort=True):
        raise typer.Exit(code=1)


def _emit_install_dry_run_plan(
    root: Path,
    *,
    stacks: list[str] | None,
    ides: list[str] | None,
    vcs: str | None,
    providers: list[str] | None,
) -> None:
    """Run install dry-run mode and emit the JSON plan."""
    import json

    set_json_mode(True)
    from ai_engineering.installer.autodetect import detect_all as _detect_all

    detected = _detect_all(root)
    resolved_vcs = vcs or detected.vcs
    resolved_providers = (
        _resolve_ai_providers(providers) if providers else (detected.providers or ["claude-code"])
    )
    _result, summary = install_with_pipeline(
        root,
        stacks=stacks or detected.stacks or [],
        ides=ides or detected.ides or ["terminal"],
        vcs_provider=resolved_vcs,
        ai_providers=resolved_providers,
        dry_run=True,
    )
    plans = [p.to_dict() for p in summary.plans]
    print(json.dumps({"schema_version": "1", "plans": plans}, indent=2))


def _is_reinstall(root: Path) -> bool:
    """Return whether the target already has install state."""
    return (root / ".ai-engineering" / "state" / "install-state.json").exists()


def _resolve_install_mode(
    is_reinstall: bool,
    *,
    fresh: bool,
    reconfigure: bool,
    non_interactive: bool,
) -> InstallMode:
    """Resolve install mode from reinstall state and flags."""
    if not is_reinstall:
        return InstallMode.INSTALL
    if non_interactive:
        return InstallMode.REPAIR
    if fresh:
        return InstallMode.FRESH
    if reconfigure:
        return InstallMode.RECONFIGURE
    return InstallMode.REPAIR


def _build_install_overrides(
    *,
    stacks: list[str] | None,
    providers: list[str] | None,
    ides: list[str] | None,
    vcs: str | None,
) -> dict[str, Any]:
    """Convert CLI selection flags into installer override keys."""
    resolved: dict[str, Any] = {}
    if stacks:
        resolved["stacks"] = stacks
    if providers:
        resolved["providers"] = _resolve_ai_providers(providers)
    if ides:
        resolved["ides"] = ides
    if vcs is not None:
        resolved["vcs"] = "azure_devops" if vcs == "azdo" else vcs
    return resolved


def _resolve_install_configuration(
    root: Path,
    *,
    is_reinstall: bool,
    mode: InstallMode,
    stacks: list[str] | None,
    providers: list[str] | None,
    ides: list[str] | None,
    vcs: str | None,
) -> tuple[list[str], list[str], list[str], str | None]:
    """Resolve install stacks, providers, IDEs, and VCS selections."""
    from ai_engineering.installer.autodetect import detect_all

    detected = detect_all(root)
    overrides = _build_install_overrides(
        stacks=stacks,
        providers=providers,
        ides=ides,
        vcs=vcs,
    )
    if is_reinstall and mode == InstallMode.RECONFIGURE:
        return _resolve_wizard_configuration(detected, overrides)
    if is_reinstall:
        return _resolve_reinstall_configuration(root, overrides)
    return _resolve_first_install_configuration(detected, overrides)


def _resolve_wizard_configuration(
    detected: Any,
    overrides: dict[str, Any],
) -> tuple[list[str], list[str], list[str], str | None]:
    """Run the interactive wizard and return its selections."""
    if not is_json_mode():
        _show_detection_summary(detected)
    from ai_engineering.installer.wizard import run_wizard

    wizard_result = run_wizard(detected, overrides if overrides else None)
    return (
        wizard_result.stacks,
        wizard_result.providers,
        wizard_result.ides,
        wizard_result.vcs,
    )


def _resolve_reinstall_configuration(
    root: Path,
    overrides: dict[str, Any],
) -> tuple[list[str], list[str], list[str], str | None]:
    """Resolve reinstall selections from current manifest plus CLI overrides."""
    config = load_manifest_config(root)
    return (
        overrides.get("stacks", config.providers.stacks or ["python"]),
        overrides.get("providers", config.ai_providers.enabled or ["claude-code"]),
        overrides.get("ides", config.providers.ides or ["terminal"]),
        overrides.get("vcs", config.providers.vcs),
    )


def _resolve_first_install_configuration(
    detected: Any,
    overrides: dict[str, Any],
) -> tuple[list[str], list[str], list[str], str | None]:
    """Resolve first-install selections from flags, detection, or wizard."""
    if overrides or is_json_mode() or not sys.stdin.isatty():
        return (
            overrides.get("stacks", detected.stacks or ["python"]),
            overrides.get("providers", detected.providers or ["claude-code"]),
            overrides.get("ides", detected.ides or ["terminal"]),
            overrides.get("vcs", detected.vcs),
        )
    return _resolve_wizard_configuration(detected, overrides)


def _confirm_reinstall_if_needed(
    *,
    is_reinstall: bool,
    non_interactive: bool,
    mode: InstallMode,
    resolved_stacks: list[str],
    resolved_providers: list[str],
    resolved_ides: list[str],
) -> None:
    """Render reinstall confirmation prompts when the command is interactive."""
    if not is_reinstall or non_interactive:
        return
    if mode == InstallMode.FRESH:
        _confirm_fresh_reinstall()
    elif mode == InstallMode.RECONFIGURE:
        _confirm_reconfigure(resolved_stacks, resolved_providers, resolved_ides)
    else:
        _confirm_repair(resolved_stacks, resolved_providers, resolved_ides)


def _confirm_fresh_reinstall() -> None:
    """Ask for typed confirmation before a fresh reinstall."""
    typer.echo("\nAll framework files will be overwritten:")
    typer.echo("  [overwrite] .ai-engineering/ (all governance files)")
    typer.echo("  [overwrite] IDE configurations")
    typer.echo("  [overwrite] hook scripts")
    confirmation = typer.prompt(
        "\nType 'fresh' to confirm full overwrite, or anything else to cancel",
        default="",
    )
    if confirmation != "fresh":
        typer.echo("Cancelled. No changes were made.")
        raise typer.Exit(0)


def _confirm_reconfigure(
    resolved_stacks: list[str],
    resolved_providers: list[str],
    resolved_ides: list[str],
) -> None:
    """Render the reconfigure preview and confirmation."""
    typer.echo("\nReconfiguration preview:")
    typer.echo(f"  [added] New providers: {', '.join(resolved_providers)}")
    typer.echo(f"  [added] New stacks: {', '.join(resolved_stacks)}")
    typer.echo(f"  [added] New IDEs: {', '.join(resolved_ides)}")
    if not typer.confirm("Proceed?", default=True):
        raise typer.Exit(0)


def _confirm_repair(
    resolved_stacks: list[str],
    resolved_providers: list[str],
    resolved_ides: list[str],
) -> None:
    """Render the repair preview and confirmation."""
    typer.echo("\nReinstall preview (repair mode):")
    typer.echo(f"  Stacks: {', '.join(resolved_stacks)}")
    typer.echo(f"  Providers: {', '.join(resolved_providers)}")
    typer.echo(f"  IDEs: {', '.join(resolved_ides)}")
    if not typer.confirm("Proceed?", default=True):
        raise typer.Exit(0)


def _render_install_detection_if_needed(
    resolved_vcs: str | None,
    resolved_providers: list[str],
) -> None:
    """Show tool availability in interactive mode."""
    if is_json_mode():
        return
    import shutil as _shutil

    tools = {
        "gh": _shutil.which("gh") is not None,
        "gitleaks": _shutil.which("gitleaks") is not None,
        "ruff": _shutil.which("ruff") is not None,
    }
    render_detection(resolved_vcs, resolved_providers, tools)


def _check_install_prerequisites(root: Path, resolved_stacks: list[str]) -> None:
    """Run install prerequisite gates before tool installation."""
    try:
        check_uv_prereq(root)
        check_sdk_prereqs(resolved_stacks, root=root)
    except PrereqMissing as exc:
        error(str(exc))
        raise typer.Exit(code=EXIT_PREREQS_MISSING) from exc


def _run_install_pipeline(
    root: Path,
    *,
    mode: InstallMode,
    resolved_stacks: list[str],
    resolved_ides: list[str],
    resolved_vcs: str | None,
    resolved_providers: list[str],
    force: bool,
) -> tuple[Any, Any]:
    """Run the installer pipeline with progress translation."""
    from ai_engineering.installer.phases import PHASE_ORDER as _PHASE_ORDER

    with step_progress(
        total=len(_PHASE_ORDER), description="Installing ai-engineering framework..."
    ) as tracker:
        progress = partial(_render_install_phase_progress, tracker=tracker)
        return install_with_pipeline(
            root,
            mode=mode,
            stacks=resolved_stacks,
            ides=resolved_ides,
            vcs_provider=resolved_vcs,
            ai_providers=resolved_providers,
            force=force,
            progress_callback=progress,
        )


_PHASE_LABELS_PRETTY = {
    PHASE_DETECT: "Detecting environment",
    PHASE_GOVERNANCE: "Copying governance framework",
    PHASE_IDE_CONFIG: "Configuring IDE integrations",
    PHASE_STATE: "Initializing state files",
    PHASE_TOOLS: "Installing required tools",
    PHASE_HOOKS: "Installing git hooks",
}


def _render_install_phase_progress(message: str, *, tracker: Any) -> None:
    """Translate pipeline progress phase names into human labels.

    spec-124 D-124-04: StepTracker adds its own ``[N/M]`` prefix, so
    strip the incoming prefix from the pipeline notifier to avoid
    duplicate ``[5/6] [5/6] Installing required tools`` rendering.

    spec-124 D-124-03: per-tool / per-hook sub-step events from the
    InstallContext callback (``tool_started:<name>`` /
    ``hook_started:<name>``) refine the spinner WITHOUT incrementing
    the phase counter. ``tool_finished`` / ``hook_finished`` events
    are no-ops at the UI layer -- the next ``tool_started`` overrides
    the spinner anyway, and the parent step's label is preserved by
    the tracker so the spinner falls back gracefully when work
    transitions between tools.
    """
    if message.startswith("tool_started:"):
        tool_name = message.split(":", 1)[1]
        tracker.substep(f"Installing {tool_name}...")
        return
    if message.startswith("hook_started:"):
        hook_name = message.split(":", 1)[1]
        tracker.substep(f"Installing {hook_name} hook...")
        return
    if message.startswith("tool_finished:") or message.startswith("hook_finished:"):
        # Sub-step end is a no-op; the parent step or the next
        # tool_started/hook_started event drives the next spinner update.
        return

    try:
        _prefix, name = message.split(" ", 1)
    except ValueError:
        tracker.step(message)
        return
    label = _PHASE_LABELS_PRETTY.get(name.strip(), name.strip())
    tracker.step(label)


def _emit_noninteractive_skipped_tools(summary: Any, *, non_interactive: bool) -> None:
    """Print skipped tool markers for non-interactive verification."""
    if not non_interactive:
        return
    tools_phase_result = next(
        (r for r in summary.results if r.phase_name == PHASE_TOOLS),
        None,
    )
    if tools_phase_result is None or not tools_phase_result.skipped:
        return
    for skipped_entry in tools_phase_result.skipped:
        if skipped_entry.startswith("tool:"):
            print_stderr(skipped_entry)


def _coerce_non_critical_failures(summary: Any) -> list[Any]:
    """Coerce summary non-critical failures into a real list."""
    raw_failures = getattr(summary, "non_critical_failures", None) or []
    try:
        return list(raw_failures)
    except TypeError:
        return []


def _run_auto_remediation(
    root: Path,
    non_critical_failures: list[Any],
    *,
    no_auto_remediate: bool,
) -> Any:
    """Run or skip post-install auto-remediation."""
    from ai_engineering.installer.auto_remediate import (
        AutoRemediateReport,
        auto_remediate_after_install,
    )

    if no_auto_remediate:
        return AutoRemediateReport()
    return auto_remediate_after_install(root, non_critical_failures)


def _raise_install_failures(
    summary: Any,
    *,
    non_critical_failures_list: list[Any],
    auto_remediation_report: Any,
    no_auto_remediate: bool,
) -> None:
    """Raise the install command's compatibility exit codes."""
    if summary.failed_phase is not None:
        error(
            f"Install pipeline failed at phase {summary.failed_phase!r}. "
            f"Run '{_DOCTOR_COMMAND}' for diagnostics."
        )
        raise typer.Exit(code=EXIT_TOOLS_FAILED)

    if not non_critical_failures_list or auto_remediation_report.success:
        return
    if no_auto_remediate:
        message = (
            "Install pipeline finished with non-critical failures; "
            "auto-remediation disabled (--no-auto-remediate). "
            f"Run '{_DOCTOR_FIX_COMMAND}' to repair."
        )
    else:
        message = (
            "Install pipeline finished with unresolved issues; "
            "auto-remediation could not fix every gap. "
            f"Run '{_DOCTOR_FIX_COMMAND}' to retry."
        )
    error(message)
    raise typer.Exit(code=EXIT_TOOLS_FAILED)


def _maybe_run_engram_install(
    root: Path,
    *,
    engram: bool,
    no_engram: bool,
    non_interactive: bool,
) -> None:
    """Drive the spec-123 Engram install prompt.

    Engram is a third-party peer product, not an ai-engineering
    dependency.  This helper resolves the ``--engram`` / ``--no-engram``
    flags into the boolean ``force`` argument expected by
    :func:`maybe_install_engram`, then renders a one-line summary of
    the outcome to stderr.  Failures are non-blocking: the install
    continues regardless so a missing Engram never trips the framework
    install.
    """

    from ai_engineering.installer.engram import maybe_install_engram

    if engram and no_engram:
        # Conflicting flags -- prefer the explicit opt-out (safer).
        force: bool | None = False
    elif engram:
        force = True
    elif no_engram:
        force = False
    else:
        force = None

    interactive = not non_interactive and sys.stdin.isatty()

    try:
        outcome = maybe_install_engram(
            force=force,
            interactive=interactive,
            project_root=root,
        )
    except Exception as exc:  # pragma: no cover - defensive non-blocking guard.
        typer.echo(
            f"[engram] install attempt raised an unexpected error: {exc}",
            err=True,
        )
        return

    if outcome.skipped:
        return
    prefix = "[engram]"
    if outcome.success:
        typer.echo(f"{prefix} {outcome.message}", err=True)
    else:
        typer.echo(
            f"{prefix} install incomplete: {outcome.message}. "
            f"Re-run with `ai-eng install --engram` once resolved.",
            err=True,
        )


def _render_install_success(
    root: Path,
    result: Any,
    *,
    resolved_vcs: str | None,
    auto_remediation_report: Any,
) -> None:
    """Render install success in JSON or human mode."""
    canonical_config = load_manifest_config(root)
    active_providers = list(canonical_config.ai_providers.enabled)
    primary_provider = canonical_config.ai_providers.primary or (
        active_providers[0] if active_providers else "none"
    )
    if is_json_mode():
        _emit_install_success_json(
            root,
            result,
            resolved_vcs=resolved_vcs,
            active_providers=active_providers,
            primary_provider=primary_provider,
            auto_remediation_report=auto_remediation_report,
        )
        return
    _render_install_success_human(
        root,
        result,
        resolved_vcs=resolved_vcs,
        active_providers=active_providers,
    )


def _emit_install_success_json(
    root: Path,
    result: Any,
    *,
    resolved_vcs: str | None,
    active_providers: list[str],
    primary_provider: str,
    auto_remediation_report: Any,
) -> None:
    """Emit install success through the JSON envelope."""
    emit_success(
        "ai-eng install",
        {
            "root": str(root),
            "governance_files": len(result.governance_files.created),
            "project_files": len(result.project_files.created),
            "state_files": len(result.state_files),
            "vcs_provider": resolved_vcs,
            "ai_providers": active_providers,
            "primary_ai_provider": primary_provider,
            "readiness_status": result.readiness_status,
            "already_installed": result.already_installed,
            "manual_steps": result.manual_steps,
            "guide_text": result.guide_text,
            "auto_remediation": auto_remediation_report.to_dict(),
        },
        [
            NextAction(command=_DOCTOR_COMMAND, description="Run health diagnostics"),
            NextAction(
                command="/ai-start",
                description=(
                    "IDE assistant slash-command (Claude Code / Copilot / Codex / "
                    "Gemini): begin the first governed session"
                ),
            ),
        ],
    )


def _render_install_success_human(
    root: Path,
    result: Any,
    *,
    resolved_vcs: str | None,
    active_providers: list[str],
) -> None:
    """Render install success for humans."""
    print_stdout(f"Installed to: {root}")
    file_count("Governance", len(result.governance_files.created))
    file_count("Project", len(result.project_files.created))
    kv("State", f"{len(result.state_files)} files")
    kv("VCS", "azdo" if resolved_vcs == "azure_devops" else resolved_vcs)
    kv("AI Providers", ", ".join(active_providers))
    kv("Readiness", result.readiness_status)

    typer.echo("")
    _render_manual_install_steps(result.manual_steps)
    if result.already_installed:
        print_stdout("  (framework was already installed — skipped existing files)")

    typer.echo("")
    next_steps = [(_DOCTOR_COMMAND, "Run health diagnostics")]
    if result.guide_text:
        next_steps.append(("ai-eng guide", "View branch policy setup guide"))
    suggest_next(next_steps)
    info(
        "Open your AI assistant (Claude Code / Copilot / Codex / Gemini) "
        "and run /ai-start to begin the first governed session."
    )
    # spec-124 D-124-06: visual breathing room before the Install Complete panel
    typer.echo("")
    _render_install_summary_panel(result)
    if result.guide_text:
        typer.echo("")
        warning("Automatic branch policy application was not possible.")
        warning("You must configure branch protection manually to enforce governance gates.")


def _render_manual_install_steps(manual_steps: list[str]) -> None:
    """Render manual follow-up steps when install reports any."""
    if not manual_steps:
        return
    warning("Manual steps required:")
    for step in manual_steps:
        print_stdout(f"    - {step}")


def _render_install_summary_panel(result: Any) -> None:
    """Render the final Rich summary panel for install."""
    pending_setup = [
        ("ai-eng setup", step) for step in result.manual_steps if "setup" in step.lower()
    ]
    hooks_count = len(result.hooks.installed) if result.hooks.installed else 0
    render_summary(
        files_created=result.total_created,
        hooks_installed=hooks_count,
        warnings=[step for step in result.manual_steps if step],
        pending_setup=pending_setup,
        next_steps=[(_DOCTOR_COMMAND, "Verify everything works")],
    )


def _render_auto_remediation_summary(report: object) -> None:
    """Print a human-readable summary of auto-remediation outcomes.

    spec-109 D-109-05: auto-remediation runs after the pipeline when
    non-critical phases failed. Surface what was fixed and what survived so
    the user can see the second-pass behaviour explicitly. Silently no-op in
    JSON mode (caller already gates on ``not is_json_mode()``).

    spec-113 G-5: the message MUST honestly reflect what landed:

    * success line ("all non-critical failures repaired automatically") only
      fires when applied != [] AND failed == [] AND errors == [].
    * mixed/partial outcomes use the explicit count surface
      ``Auto-remediation: <N> repaired (<list>); <M> still require manual
      action (<list>)`` so the operator sees exactly what survived.
    """
    from ai_engineering.installer.auto_remediate import AutoRemediateReport

    if not isinstance(report, AutoRemediateReport):
        return

    typer.echo("")

    applied_count = len(report.applied)
    residue_count = len(report.failed) + len(report.errors)

    if report.success:
        # All gaps closed AND something actually landed.
        info("Auto-remediation: all non-critical failures repaired automatically.")
    elif applied_count and residue_count:
        # Partial outcome: some repairs landed, others survived.
        applied_labels = ", ".join(report.applied)
        residue_entries = list(report.failed) + list(report.errors)
        residue_labels = ", ".join(residue_entries)
        warning(
            f"Auto-remediation: {applied_count} repaired ({applied_labels}); "
            f"{residue_count} still require manual action ({residue_labels})"
        )
    elif applied_count:
        # Repairs landed but no residue, yet success is False -- rare path
        # (would require invoked=False which the caller short-circuits).
        info(f"Auto-remediation: {applied_count} repaired ({', '.join(report.applied)}).")
    else:
        # Nothing landed -- residue-only OR fully invoked-yet-empty.
        residue_entries = list(report.failed) + list(report.errors)
        if residue_entries:
            residue_labels = ", ".join(residue_entries)
            warning(
                f"Auto-remediation: 0 repaired; {residue_count} still require "
                f"manual action ({residue_labels})"
            )
        else:
            warning(
                f"Auto-remediation: no remediation applied; run '{_DOCTOR_FIX_COMMAND}' to retry."
            )

    for entry in report.applied:
        print_stderr(f"  → fixed   {entry}")
    for entry in report.failed:
        print_stderr(f"  → manual  {entry}")
    for entry in report.errors:
        print_stderr(f"  → error   {entry}")


def _render_pipeline_steps(summary: object) -> None:
    """Render each phase from the pipeline summary as a wizard step."""
    from ai_engineering.installer.phases.pipeline import PipelineSummary

    if not isinstance(summary, PipelineSummary):
        return

    from ai_engineering.installer.phases import PHASE_ORDER

    phase_names = list(PHASE_ORDER)
    non_critical_failures = set(getattr(summary, "non_critical_failures", []) or [])

    for i, name in enumerate(phase_names):
        status, detail = _pipeline_step_status(summary, name, non_critical_failures)
        label = _PHASE_LABELS.get(name, name)
        desc = _pipeline_step_description(label, status)
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


_PHASE_LABELS = {
    PHASE_DETECT: "Detection",
    PHASE_GOVERNANCE: "Governance framework",
    PHASE_IDE_CONFIG: "IDE configuration",
    PHASE_HOOKS: "Git hooks",
    PHASE_STATE: "State initialization",
    PHASE_TOOLS: "Tool verification",
}


def _pipeline_step_status(
    summary: Any,
    name: str,
    non_critical_failures: set[str],
) -> tuple[str, str]:
    """Return the display status and detail for one pipeline phase."""
    phase_result = next((r for r in summary.results if r.phase_name == name), None)
    if phase_result is None:
        return _missing_pipeline_step_status(summary, name)
    detail = _pipeline_step_detail(phase_result)
    if name in non_critical_failures:
        return "warn", _non_critical_pipeline_detail(detail)
    if phase_result.failed:
        return "fail", detail
    if phase_result.warnings:
        return "warn", detail
    return "ok", detail


def _missing_pipeline_step_status(summary: Any, name: str) -> tuple[str, str]:
    """Return the status for a phase that produced no result."""
    if summary.failed_phase and name not in summary.completed_phases:
        return "skip", "skipped"
    return "ok", ""


def _pipeline_step_detail(phase_result: Any) -> str:
    """Describe created and deleted file counts for a pipeline phase."""
    parts = []
    if phase_result.created:
        parts.append(f"{len(phase_result.created)} files")
    if phase_result.deleted:
        parts.append(f"{len(phase_result.deleted)} deleted")
    return ", ".join(parts) if parts else "up to date"


def _non_critical_pipeline_detail(detail: str) -> str:
    """Annotate a non-critical phase failure for auto-remediation."""
    retry_detail = "non-critical failure (auto-remediate will retry)"
    if not detail or detail == "up to date":
        return retry_detail
    return f"{detail} — non-critical (auto-remediate will retry)"


def _pipeline_step_description(label: str, status: str) -> str:
    """Build the user-facing pipeline step description."""
    prefix = "Skipped" if status == "skip" else "Setting up"
    return f"{prefix} {label.lower()}..."


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

    template_roots = [get_project_template_root(), get_ai_engineering_template_root()]
    for plan_data in data.get("plans", []):
        plan = PhasePlan.from_dict(plan_data)  # validates path security
        for action in plan.actions:
            _replay_plan_action(root, action, template_roots)

    typer.echo(f"Plan replayed successfully to {root}")


def _replay_plan_action(root: Path, action: Any, template_roots: list[Path]) -> None:
    """Replay one validated install-plan action."""
    if action.action_type == "skip":
        return
    dest = root / action.destination
    dest.parent.mkdir(parents=True, exist_ok=True)
    if action.source:
        _copy_plan_action_source(action, dest, template_roots)


def _copy_plan_action_source(action: Any, dest: Path, template_roots: list[Path]) -> None:
    """Copy a source-backed install-plan action when its template exists."""
    import shutil

    for template_root in template_roots:
        src = template_root / action.source
        if src.exists():
            shutil.copy2(src, dest)
            return


_PROVIDER_ALIASES: dict[str, str] = {
    "claude": "claude-code",
    "claude_code": "claude-code",
    "claude-code": "claude-code",
    "copilot": "github-copilot",
    "github_copilot": "github-copilot",
    "github-copilot": "github-copilot",
    "gemini": "gemini-cli",
    "gemini-cli": "gemini-cli",
    "codex": "codex",
}

_DOCTOR_COMMAND = "ai-eng doctor"
_DOCTOR_FIX_COMMAND = "ai-eng doctor --fix"
_UPDATE_COMMAND = "ai-eng update"
_UPDATE_APPLY_COMMAND = "ai-eng update --apply"


def _resolve_ai_providers(providers: list[str] | None) -> list[str]:
    """Resolve AI providers from explicit flag.

    Short names (claude, copilot, gemini, codex) are mapped to internal names.
    Returns default when no flag provided.
    """
    if providers:
        return [_PROVIDER_ALIASES.get(p, p) for p in providers]
    return ["claude-code"]


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
    json_requested = is_json_mode() or output_json
    interactive_tty = not json_requested and sys.stdin.isatty()
    update_runner = partial(_run_update_with_spinner, interactive_tty=interactive_tty)
    confirm_apply = partial(
        _confirm_update_apply,
        root=root,
        show_diff=show_diff,
        apply=apply,
    )

    try:
        workflow_result = run_update_workflow(
            root,
            apply=apply,
            interactive=interactive_tty,
            confirm_apply=confirm_apply if interactive_tty else None,
            update_runner=update_runner,
        )
    except Exception as exc:
        if json_requested:
            from ai_engineering.cli_envelope import emit_error

            emit_error(
                _UPDATE_COMMAND,
                message=str(exc),
                code="update_failed",
                fix=(
                    "Review file permissions or rerun without --apply to inspect the preview first."
                ),
                next_actions=[
                    NextAction(
                        command=_UPDATE_COMMAND, description="Preview changes without writing"
                    ),
                ],
            )
            raise typer.Exit(code=1) from exc
        error(f"Update failed while applying changes: {exc}")
        raise typer.Exit(code=1) from exc

    if _handle_interactive_update_result(
        workflow_result,
        root=root,
        show_diff=show_diff,
    ):
        return

    result = workflow_result.result

    if json_requested:
        result_data = result.to_dict()
        result_data["root"] = str(root)
        emit_success(
            _UPDATE_COMMAND,
            result_data,
            [
                NextAction(command=_DOCTOR_COMMAND, description="Verify framework health"),
                NextAction(command=_UPDATE_APPLY_COMMAND, description="Apply changes"),
            ],
        )
        return

    _render_update_result(result, root=root, show_diff=show_diff)


def _run_update_with_spinner(
    target_root: Path,
    *,
    dry_run: bool,
    interactive_tty: bool,
) -> Any:
    """Run the updater with CLI progress rendering."""
    if interactive_tty:
        message = "Previewing framework updates..." if dry_run else "Applying framework updates..."
    else:
        message = "Checking for updates..."
    with spinner(message):
        return update(target_root, dry_run=dry_run)


def _confirm_update_apply(
    preview: Any,
    *,
    root: Path,
    show_diff: bool,
    apply: bool,
) -> bool:
    """Render the preview and ask whether the update should be applied."""
    _render_update_result(preview, root=root, show_diff=show_diff)
    orphan_suffix = ""
    if preview.orphan_count:
        orphan_suffix = f", {preview.orphan_count} orphaned (will be removed)"
    prompt_msg = (
        f"{preview.available_count} available{orphan_suffix}. Apply these framework updates now?"
    )
    return typer.confirm(prompt_msg, default=apply)


def _handle_interactive_update_result(
    workflow_result: UpdateWorkflowResult,
    *,
    root: Path,
    show_diff: bool,
) -> bool:
    """Handle interactive-only update workflow statuses."""
    if workflow_result.status == UpdateWorkflowStatus.DECLINED:
        warning("Preview only. No changes were applied.")
        suggest_next([("ai-eng update --apply", "Apply the previewed changes non-interactively")])
        return True
    if workflow_result.status == UpdateWorkflowStatus.NO_CHANGES:
        _render_update_result(workflow_result.result, root=root, show_diff=show_diff)
        info("No framework-managed files require changes.")
        return True
    if (
        workflow_result.preview is not None
        and workflow_result.status == UpdateWorkflowStatus.APPLIED
    ):
        _render_update_result(workflow_result.result, root=root, show_diff=show_diff)
        return True
    return False


def _render_update_result(result: Any, *, root: Path, show_diff: bool) -> None:
    """Render human-facing update results."""
    mode = "APPLIED" if not result.dry_run else "PREVIEW"
    print_stdout(f"Update [{mode}]: {root}")

    kv("Available", result.available_count if result.dry_run else 0)
    kv("Applied", result.applied_count if not result.dry_run else 0)
    kv("Protected", result.protected_count)
    kv("Unchanged", result.unchanged_count)
    kv("Orphan", result.orphan_count)

    if result.dry_run:
        # Preview: full unified tree of all non-unchanged changes.
        render_update_tree(result.changes, root=root, dry_run=result.dry_run)
    else:
        # Post-apply: check for failures.
        failed = [c for c in result.changes if c.outcome(dry_run=False) == "failed"]
        if failed:
            # Show tree with only the failed changes.
            render_update_tree(failed, root=root, dry_run=result.dry_run)
        else:
            # Compact one-liner summary by action type.
            counts: dict[str, int] = {}
            for c in result.changes:
                counts[c.action] = counts.get(c.action, 0) + 1
            created = counts.get("create", 0)
            updated = counts.get("update", 0)
            removed = counts.get("remove", 0)
            orphaned = counts.get("orphan", 0)
            print_stdout(
                f"Done. {created} created, {updated} updated, "
                f"{removed} removed, {orphaned} orphans deleted."
            )

    if show_diff:
        for change in result.changes:
            _render_update_change(change, dry_run=result.dry_run, show_diff=show_diff)


def _render_update_change(change: Any, *, dry_run: bool, show_diff: bool) -> None:
    """Render a single file change for human output."""
    if not show_diff:
        return
    outcome = change.outcome(dry_run=dry_run)
    status = {
        "available": "ok",
        "applied": "ok",
        "protected": "warn",
        "unchanged": "info",
        "orphan": "warn",
        "removed": "warn",
        "failed": "fail",
    }.get(outcome, "fail")
    status_line(status, f"diff {change.path}", change.explanation)

    if change.action == "orphan" and change.path.is_file():
        _render_orphan_update_diff(change.path)
    elif change.diff:
        _render_limited_update_diff(change.diff)


def _render_orphan_update_diff(path: Path) -> None:
    """Render an orphaned file body as removed diff lines."""
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        typer.echo("    [binary or unreadable file]")
        return
    lines = _limited_diff_lines(content)
    for line in lines:
        typer.echo(f"    -{line}", nl=False)
    if lines and not lines[-1].endswith("\n"):
        typer.echo("")


def _render_limited_update_diff(diff_text: str) -> None:
    """Render a unified diff with the CLI diff line cap."""
    for line in _limited_diff_lines(diff_text):
        typer.echo(f"    {line}", nl=False)


def _limited_diff_lines(text: str) -> list[str]:
    """Return diff lines capped to the configured maximum."""
    lines = text.splitlines(keepends=True)
    if len(lines) <= _DIFF_MAX_LINES:
        return lines
    remaining = len(text.splitlines()) - _DIFF_MAX_LINES
    return [*lines[:_DIFF_MAX_LINES], f"    ... ({remaining} more lines)\n"]


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
    focused_check: Annotated[
        str | None,
        typer.Option(
            "--check",
            help="Run a focused sub-check (e.g., 'hot-path' for SLO budgets).",
        ),
    ] = None,
) -> None:
    """Diagnose and optionally fix framework health.

    Exit codes: 0 (pass), 1 (fail), 2 (warnings only). When ``--check
    hot-path`` is passed, runs the spec-114 advisory hot-path SLO
    audit and always exits 0 per D-114-03 (advisory through
    2026-05-31).
    """
    if output_json:
        set_json_mode(True)
    root = resolve_project_root(target)

    if _run_focused_doctor_check(root, focused_check):
        return

    if dry_run and not fix:
        fix = True  # --dry-run implies --fix

    with spinner("Running health diagnostics..."):
        report = diagnose(root, fix=fix, dry_run=dry_run, phase_filter=phase)
    fixable_count, manual_count = _doctor_follow_up_counts(report)

    if fix and not dry_run and not is_json_mode():
        _interactive_fix(root, report, phase)

    if is_json_mode():
        _emit_doctor_json(report, fixable_count=fixable_count)
    else:
        _render_doctor_human(
            root,
            report,
            fixable_count=fixable_count,
            manual_count=manual_count,
        )
    _exit_for_doctor_report(report)


def _run_focused_doctor_check(root: Path, focused_check: str | None) -> bool:
    """Run a focused doctor sub-check when requested."""
    if focused_check is None:
        return False
    if focused_check != "hot-path":
        raise typer.BadParameter(f"Unknown --check value: {focused_check!r}. Supported: hot-path.")
    from ai_engineering.cli_commands.doctor_hot_path import run_hot_path_check

    run_hot_path_check(root)
    return True


def _emit_doctor_json(report: DoctorReport, *, fixable_count: int) -> None:
    """Emit doctor results through the JSON envelope."""
    next_actions = []
    if fixable_count:
        next_actions = [
            NextAction(
                command=_DOCTOR_FIX_COMMAND,
                description="Attempt automatic repairs for fixable issues",
            ),
        ]
    emit_success(_DOCTOR_COMMAND, report.to_dict(), next_actions)


def _render_doctor_human(
    root: Path,
    report: DoctorReport,
    *,
    fixable_count: int,
    manual_count: int,
) -> None:
    """Render doctor results for humans."""
    status = "PASS" if report.passed else "FAIL"
    result_header("Doctor", status, str(root))
    if not report.installed:
        warning("Framework not installed. Run 'ai-eng install' first.")

    kv("Summary", report.summary)
    if fixable_count:
        kv("Auto-fix", f"{fixable_count} issue(s) can be attempted with {_DOCTOR_FIX_COMMAND}")
    if manual_count:
        kv("Manual follow-up", f"{manual_count} issue(s) require manual action")

    _render_doctor_phase_checks(report)
    _render_doctor_runtime_checks(report)
    _render_doctor_next_steps(report, fixable_count=fixable_count, manual_count=manual_count)


def _render_doctor_phase_checks(report: DoctorReport) -> None:
    """Render phase-level doctor checks."""
    for phase_report in report.phases:
        typer.echo(f"\n  {phase_report.name} [{phase_report.status.value}]")
        for doctor_check in phase_report.checks:
            status_line(
                doctor_check.status.value,
                doctor_check.name,
                doctor_check.message,
            )


def _render_doctor_runtime_checks(report: DoctorReport) -> None:
    """Render runtime doctor checks."""
    if not report.runtime:
        return
    typer.echo("\n  runtime")
    for doctor_check in report.runtime:
        status_line(
            doctor_check.status.value,
            doctor_check.name,
            doctor_check.message,
        )


def _render_doctor_next_steps(
    report: DoctorReport,
    *,
    fixable_count: int,
    manual_count: int,
) -> None:
    """Render doctor follow-up guidance."""
    if fixable_count:
        suggest_next([(_DOCTOR_FIX_COMMAND, "Attempt automatic repairs for fixable issues")])
        return
    if not manual_count:
        return
    if report.passed:
        warning(f"{manual_count} warning(s) for review above; project is functional.")
    else:
        warning("Manual follow-up required. Review the failing checks above.")


def _exit_for_doctor_report(report: DoctorReport) -> None:
    """Apply the doctor command's compatibility exit-code contract."""
    if not report.passed:
        raise typer.Exit(code=1)
    if report.has_warnings:
        raise typer.Exit(code=2)


def _interactive_fix(root: Path, report: DoctorReport, phase_filter: str | None) -> None:
    """Re-run diagnostics with interactive confirmation for each fixable failure."""
    from ai_engineering.doctor.models import CheckStatus

    fixable = _collect_fixable_doctor_checks(report)
    if not fixable:
        return

    typer.echo(f"\nFound {len(fixable)} fixable issue(s):\n")
    _prompt_for_doctor_fixes(fixable)

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


def _collect_fixable_doctor_checks(report: DoctorReport) -> list[tuple[str, Any]]:
    """Collect failing or warning checks that support automatic fixes."""
    from ai_engineering.doctor.models import CheckStatus

    fixable = []
    for phase_report in report.phases:
        for check in phase_report.checks:
            if check.status in (CheckStatus.FAIL, CheckStatus.WARN) and check.fixable:
                fixable.append((phase_report.name, check))
    return fixable


def _prompt_for_doctor_fixes(fixable: list[tuple[str, Any]]) -> None:
    """Prompt through fixable doctor checks before re-verification."""
    approve_all = False
    for phase_name, check in fixable:
        typer.echo(f"  [{phase_name}] {check.name}: {check.message}")
        approve_all = _prompt_for_doctor_fix(approve_all)


def _prompt_for_doctor_fix(approve_all: bool) -> bool:
    """Prompt for one doctor fix and return whether all remaining are approved."""
    if approve_all:
        return True
    response = typer.prompt("  Fix? (y/n/all)", default="y")
    return response.lower() == "all"


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
        print_stdout(f"ai-engineering {result.message}")
