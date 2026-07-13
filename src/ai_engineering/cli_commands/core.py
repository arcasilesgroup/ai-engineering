"""Core CLI commands: install, update, doctor, version.

These are the primary entry points for the ``ai-eng`` CLI.
Human-first Rich output by default; ``--json`` for agent consumption.
"""

from __future__ import annotations

import subprocess
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
    success,
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
    surfaces: Annotated[
        list[str] | None,
        typer.Option(
            "--surface",
            "-S",
            help=(
                "Surface(s) to enable — closed enum: claude-code, codex, "
                "github-copilot, opencode, cursor, antigravity."
            ),
        ),
    ] = None,
    vcs: Annotated[
        str | None,
        typer.Option("--vcs", help="VCS provider: github or azdo."),
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
            hidden=True,
            help="Internal — invoked by `ai-eng config` to re-run the wizard.",
        ),
    ] = False,
) -> None:
    """Install the ai-engineering governance framework.

    Behaviour knobs honoured via environment variables (KISS — keep
    the CLI surface small):

    * ``AIENG_AUTO_REMEDIATE=0`` — disable spec-109 D-109-05 post-pipeline
      auto-remediation. Useful in CI to detect first-attempt failures.
    """
    import os

    if non_interactive:
        set_json_mode(True)

    no_auto_remediate = os.environ.get("AIENG_AUTO_REMEDIATE", "1").lower() in {"0", "false", "no"}

    root = resolve_project_root(target)
    _validate_install_target(root, non_interactive=non_interactive)

    if dry_run:
        _emit_install_dry_run_plan(
            root,
            stacks=stacks,
            surfaces=surfaces,
            vcs=vcs,
        )
        return

    is_reinstall = _is_reinstall(root)
    mode = _resolve_install_mode(
        is_reinstall,
        fresh=fresh,
        reconfigure=reconfigure,
        non_interactive=non_interactive,
    )

    resolved_stacks, resolved_surfaces, resolved_vcs = _resolve_install_configuration(
        root,
        is_reinstall=is_reinstall,
        mode=mode,
        stacks=stacks,
        surfaces=surfaces,
        vcs=vcs,
    )

    _confirm_reinstall_if_needed(
        is_reinstall=is_reinstall,
        non_interactive=non_interactive,
        mode=mode,
        resolved_stacks=resolved_stacks,
        resolved_surfaces=resolved_surfaces,
    )

    _render_install_detection_if_needed(resolved_vcs, resolved_surfaces)

    _check_install_prerequisites(root, resolved_stacks)

    result, summary = _run_install_pipeline(
        root,
        mode=mode,
        resolved_stacks=resolved_stacks,
        resolved_surfaces=resolved_surfaces,
        resolved_vcs=resolved_vcs,
    )

    _emit_noninteractive_skipped_tools(summary, non_interactive=non_interactive)
    _emit_noninteractive_failed_tools(summary, non_interactive=non_interactive)

    non_critical_failures_list = _coerce_non_critical_failures(summary)
    auto_remediation_report = _run_auto_remediation(
        root,
        non_critical_failures_list,
        no_auto_remediate=no_auto_remediate,
    )

    if not is_json_mode():
        _render_pipeline_steps(summary, auto_remediation_report=auto_remediation_report)

    if auto_remediation_report.invoked and not is_json_mode():
        _render_auto_remediation_summary(auto_remediation_report)

    _raise_install_failures(
        summary,
        non_critical_failures_list=non_critical_failures_list,
        auto_remediation_report=auto_remediation_report,
        no_auto_remediate=no_auto_remediate,
    )

    _finalize_hooks_manifest(root)

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
    surfaces: list[str] | None,
    vcs: str | None,
) -> None:
    """Run install dry-run mode and emit the JSON plan."""
    import json

    set_json_mode(True)
    from ai_engineering.installer.autodetect import detect_all as _detect_all

    detected = _detect_all(root)
    resolved_vcs = vcs or detected.vcs
    resolved_surfaces = surfaces or detected.surfaces or ["claude-code"]
    _result, summary = install_with_pipeline(
        root,
        stacks=stacks or detected.stacks or [],
        surfaces=resolved_surfaces,
        vcs_provider=resolved_vcs,
        dry_run=True,
    )
    plans = [p.to_dict() for p in summary.plans]
    print(json.dumps({"schema_version": "1", "plans": plans}, indent=2))


def _is_reinstall(root: Path) -> bool:
    """Return whether the target already has install state.

    spec-148 P4 (files-only): ``install-state.json`` is the canonical
    install-completed signal. Its presence means a previous install, so
    the reinstall preview path fires for upgrade scenarios.
    """
    return (root / ".ai-engineering" / "state" / "install-state.json").is_file()


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
    surfaces: list[str] | None,
    vcs: str | None,
) -> dict[str, Any]:
    """Convert CLI selection flags into installer override keys."""
    resolved: dict[str, Any] = {}
    if stacks:
        resolved["stacks"] = stacks
    if surfaces:
        resolved["surfaces"] = surfaces
    if vcs is not None:
        resolved["vcs"] = "azure_devops" if vcs == "azdo" else vcs
    return resolved


def _resolve_install_configuration(
    root: Path,
    *,
    is_reinstall: bool,
    mode: InstallMode,
    stacks: list[str] | None,
    surfaces: list[str] | None,
    vcs: str | None,
) -> tuple[list[str], list[str], str | None]:
    """Resolve install stacks, surfaces, and VCS selections."""
    from ai_engineering.installer.autodetect import detect_all

    detected = detect_all(root)
    overrides = _build_install_overrides(
        stacks=stacks,
        surfaces=surfaces,
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
) -> tuple[list[str], list[str], str | None]:
    """Run the interactive wizard and return its selections."""
    if not is_json_mode():
        _show_detection_summary(detected)
    from ai_engineering.installer.wizard import run_wizard

    wizard_result = run_wizard(detected, overrides if overrides else None)
    return (
        wizard_result.stacks,
        wizard_result.surfaces,
        wizard_result.vcs,
    )


def _resolve_reinstall_configuration(
    root: Path,
    overrides: dict[str, Any],
) -> tuple[list[str], list[str], str | None]:
    """Resolve reinstall selections from current manifest plus CLI overrides."""
    config = load_manifest_config(root)
    return (
        overrides.get("stacks", config.providers.stacks or ["python"]),
        overrides.get("surfaces", config.surfaces.enabled or ["claude-code"]),
        overrides.get("vcs", config.providers.vcs),
    )


def _resolve_first_install_configuration(
    detected: Any,
    overrides: dict[str, Any],
) -> tuple[list[str], list[str], str | None]:
    """Resolve first-install selections from flags, detection, or wizard."""
    if overrides or is_json_mode() or not sys.stdin.isatty():
        return (
            overrides.get("stacks", detected.stacks or ["python"]),
            overrides.get("surfaces", detected.surfaces or ["claude-code"]),
            overrides.get("vcs", detected.vcs or "github"),
        )
    return _resolve_wizard_configuration(detected, overrides)


def _confirm_reinstall_if_needed(
    *,
    is_reinstall: bool,
    non_interactive: bool,
    mode: InstallMode,
    resolved_stacks: list[str],
    resolved_surfaces: list[str],
) -> None:
    """Render reinstall confirmation prompts when the command is interactive."""
    if not is_reinstall or non_interactive:
        return
    if mode == InstallMode.FRESH:
        _confirm_fresh_reinstall()
    elif mode == InstallMode.RECONFIGURE:
        _confirm_reconfigure(resolved_stacks, resolved_surfaces)
    else:
        _confirm_repair(resolved_stacks, resolved_surfaces)


def _confirm_fresh_reinstall() -> None:
    """Ask for typed confirmation before a fresh reinstall."""
    typer.echo("\nAll framework files will be overwritten:")
    typer.echo("  [overwrite] .ai-engineering/ (all governance files)")
    typer.echo("  [overwrite] Surface configurations")
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
    resolved_surfaces: list[str],
) -> None:
    """Render the reconfigure preview and confirmation."""
    typer.echo("\nReconfiguration preview:")
    typer.echo(f"  [added] Surfaces: {', '.join(resolved_surfaces)}")
    typer.echo(f"  [added] Stacks:   {', '.join(resolved_stacks)}")
    if not typer.confirm("Proceed?", default=True):
        raise typer.Exit(0)


def _confirm_repair(
    resolved_stacks: list[str],
    resolved_surfaces: list[str],
) -> None:
    """Render the repair preview and confirmation."""
    typer.echo("\nReinstall preview (repair mode):")
    typer.echo(f"  Surfaces: {', '.join(resolved_surfaces)}")
    typer.echo(f"  Stacks:   {', '.join(resolved_stacks)}")
    if not typer.confirm("Proceed?", default=True):
        raise typer.Exit(0)


def _render_install_detection_if_needed(
    resolved_vcs: str | None,
    resolved_surfaces: list[str],
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
    render_detection(resolved_vcs, resolved_surfaces, tools)  # ty:ignore[invalid-argument-type]


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
    resolved_surfaces: list[str],
    resolved_vcs: str | None,
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
            surfaces=resolved_surfaces,
            vcs_provider=resolved_vcs,  # ty:ignore[invalid-argument-type]
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


def _emit_noninteractive_failed_tools(summary: Any, *, non_interactive: bool) -> None:
    """Print failed tool markers so non-interactive logs name the gap.

    Symmetrical to :func:`_emit_noninteractive_skipped_tools`. Without this
    the install pipeline surfaces the aggregate ``EXIT 80`` ("unresolved
    issues") but never names WHICH required tool failed, forcing operators to
    reverse-engineer the gap from CI logs. Emitting the per-tool
    ``tool:<name>:<reason>`` markers (recorded by ``ToolsPhase`` in
    ``result.failed``) makes the failing tool observable on every OS -- the
    same contract the skipped markers already provide.
    """
    if not non_interactive:
        return
    tools_phase_result = next(
        (r for r in summary.results if r.phase_name == PHASE_TOOLS),
        None,
    )
    if tools_phase_result is None or not tools_phase_result.failed:
        return
    for failed_entry in tools_phase_result.failed:
        if failed_entry.startswith("tool:"):
            print_stderr(failed_entry)


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


def _render_install_success(
    root: Path,
    result: Any,
    *,
    resolved_vcs: str | None,
    auto_remediation_report: Any,
) -> None:
    """Render install success in JSON or human mode."""
    canonical_config = load_manifest_config(root)
    active_surfaces = list(canonical_config.surfaces.enabled)
    if is_json_mode():
        _emit_install_success_json(
            root,
            result,
            resolved_vcs=resolved_vcs,
            active_surfaces=active_surfaces,
            auto_remediation_report=auto_remediation_report,
        )
        return
    _render_install_success_human(
        root,
        result,
        resolved_vcs=resolved_vcs,
        active_surfaces=active_surfaces,
    )


def _warn_hooks_unpinned(root: Path, detail: str) -> None:
    """Loud, actionable stderr block when the hook manifest is not pinned.

    spec-168: a stale or unpinned manifest silently disables every hook
    under ``AIENG_HOOK_INTEGRITY_MODE=enforce`` (the default). The previous
    one-line ``warning:`` was easy to miss, so installs slid into a
    dead-hooks state unnoticed. Make it impossible to miss and name the
    one-line recovery command. ASCII-only — install stderr is non-tty on
    Windows where non-ASCII glyphs crash the cp1252 console.
    """
    repin = "python3 .ai-engineering/scripts/regenerate-hooks-manifest.py"
    print(
        "\n".join(
            [
                "",
                "  WARNING: ai-engineering hooks-manifest may be STALE or UNPINNED.",
                f"    cause:  {detail}",
                "    effect: under AIENG_HOOK_INTEGRITY_MODE=enforce (default) every",
                "            hook REFUSES to run until the manifest is re-pinned.",
                f"    fix:    cd {root} && {repin}",
                "",
            ]
        ),
        file=sys.stderr,
    )


def _finalize_hooks_manifest(root: Path) -> None:
    """spec-142 D-142-05: regenerate hooks-manifest after install.

    Re-pins every hook's sha256 against the bytes just written so
    ``AIENG_HOOK_INTEGRITY_MODE=enforce`` does not kill freshly-installed
    hooks. Fail-open (never aborts the install) but FAIL-LOUD (spec-168):
    a missing script, a non-zero exit, OR a post-write ``--check`` that
    still reports drift emits the recovery block via
    :func:`_warn_hooks_unpinned`. The post-condition matters because a
    clean write whose manifest still mismatches the bytes is the exact
    silent state that disabled hooks in fresh installs.
    """
    regen = root / ".ai-engineering" / "scripts" / "regenerate-hooks-manifest.py"
    if not regen.is_file():
        _warn_hooks_unpinned(root, f"{regen} is missing")
        return
    try:
        result = subprocess.run(
            [sys.executable, str(regen)],
            cwd=root,
            check=False,
            timeout=30,
            capture_output=True,
            text=True,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        _warn_hooks_unpinned(root, f"regenerate-hooks-manifest failed to run: {exc}")
        return
    if result.returncode != 0:
        _warn_hooks_unpinned(
            root,
            f"regenerate-hooks-manifest exited {result.returncode}: "
            f"{(result.stderr or '').strip()[:200]}",
        )
        return
    # Post-condition: a clean write that still fails --check means the
    # manifest is stale vs the written bytes — the silent dead-hooks state.
    try:
        check = subprocess.run(
            [sys.executable, str(regen), "--check"],
            cwd=root,
            check=False,
            timeout=30,
            capture_output=True,
            text=True,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        _warn_hooks_unpinned(root, f"hooks-manifest verification failed to run: {exc}")
        return
    if check.returncode != 0:
        _warn_hooks_unpinned(
            root,
            f"hooks-manifest still stale after regeneration ({(check.stderr or '').strip()[:200]})",
        )


def _finalize_update_hooks_manifest(workflow_result: Any, root: Path) -> None:
    """spec-159 D-159-03: re-pin hooks-manifest after an update applies changes.

    Deploying new hook bytes without refreshing their sha256 makes
    ``AIENG_HOOK_INTEGRITY_MODE=enforce`` kill the very hooks the update
    just shipped. Mirror ``install_cmd``'s post-apply finalize, but gate
    on an apply that actually mutated files — never on preview/dry-run or
    a no-op apply, so a clean preview never rewrites the manifest.
    """
    if workflow_result.status != UpdateWorkflowStatus.APPLIED:
        return
    result = workflow_result.result
    if getattr(result, "dry_run", True):
        return
    if not (result.applied_count or result.orphan_count):
        return
    _finalize_hooks_manifest(root)


def _emit_install_success_json(
    root: Path,
    result: Any,
    *,
    resolved_vcs: str | None,
    active_surfaces: list[str],
    auto_remediation_report: Any,
) -> None:
    """Emit install success through the JSON envelope."""
    primary_surface = active_surfaces[0] if active_surfaces else "none"
    emit_success(
        "ai-eng install",
        {
            "root": str(root),
            "governance_files": len(result.governance_files.created),
            "project_files": len(result.project_files.created),
            "state_files": len(result.state_files),
            "vcs_provider": resolved_vcs,
            "surfaces": active_surfaces,
            "primary_surface": primary_surface,
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
                    "Antigravity): begin the first governed session"
                ),
            ),
        ],
    )


def _render_install_success_human(
    root: Path,
    result: Any,
    *,
    resolved_vcs: str | None,
    active_surfaces: list[str],
) -> None:
    """Render install success for humans."""
    print_stdout(f"Installed to: {root}")
    file_count("Governance", len(result.governance_files.created))
    file_count("Project", len(result.project_files.created))
    kv("State", f"{len(result.state_files)} files")
    kv("VCS", "azdo" if resolved_vcs == "azure_devops" else resolved_vcs)
    kv("Surfaces", ", ".join(active_surfaces))
    kv("Readiness", result.readiness_status)

    typer.echo("")
    _render_manual_install_steps(result.manual_steps)
    if result.already_installed:
        print_stdout("  (framework was already installed — skipped existing files)")

    typer.echo("")
    next_steps = [(_DOCTOR_COMMAND, "Run health diagnostics")]
    suggest_next(next_steps)
    info(
        "Open your AI assistant (Claude Code / Copilot / Codex / Antigravity) "
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


def _render_pipeline_steps(summary: object, *, auto_remediation_report: Any = None) -> None:
    """Render each phase from the pipeline summary as a wizard step.

    When ``auto_remediation_report`` is supplied AND it reconciled every
    non-critical failure successfully, those phases render as ``ok``
    instead of ``warn`` — the failure was transient and is already fixed
    by the time the user reads the line.
    """
    from ai_engineering.installer.phases.pipeline import PipelineSummary

    if not isinstance(summary, PipelineSummary):
        return

    from ai_engineering.installer.phases import PHASE_ORDER

    phase_names = list(PHASE_ORDER)
    non_critical_failures = set(getattr(summary, "non_critical_failures", []) or [])
    auto_resolved: set[str] = set()
    if auto_remediation_report is not None and getattr(auto_remediation_report, "success", False):
        auto_resolved = set(non_critical_failures)

    for i, name in enumerate(phase_names):
        status, detail = _pipeline_step_status(
            summary,
            name,
            non_critical_failures,
            auto_resolved=auto_resolved,
        )
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
    *,
    auto_resolved: set[str] | None = None,
) -> tuple[str, str]:
    """Return the display status and detail for one pipeline phase.

    Phases listed in ``auto_resolved`` are treated as ``ok`` even if they
    were originally non-critical failures — auto-remediation already
    repaired them, so showing a ⚠ to the user is misleading.
    """
    phase_result = next((r for r in summary.results if r.phase_name == name), None)
    if phase_result is None:
        return _missing_pipeline_step_status(summary, name)
    detail = _pipeline_step_detail(phase_result)
    if name in non_critical_failures:
        if auto_resolved and name in auto_resolved:
            return "ok", _auto_resolved_pipeline_detail(detail)
        return "warn", _non_critical_pipeline_detail(detail)
    if phase_result.failed:
        return "fail", detail
    if phase_result.warnings:
        return "warn", detail
    return "ok", detail


def _auto_resolved_pipeline_detail(detail: str) -> str:
    """Annotate a phase that auto-remediation already repaired."""
    suffix = "auto-repaired"
    if not detail or detail == "up to date":
        return suffix
    return f"{detail} — {suffix}"


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
    if detected.surfaces:
        parts.append(f"Surfaces: {', '.join(detected.surfaces)}")
    if parts:
        typer.echo(f"\n  Detected: {' | '.join(parts)}\n")
    else:
        typer.echo("\n  No project markers detected.\n")


_DOCTOR_COMMAND = "ai-eng doctor"
_DOCTOR_FIX_COMMAND = "ai-eng doctor --fix"
_UPDATE_COMMAND = "ai-eng update"
_UPDATE_APPLY_COMMAND = "ai-eng update --apply"
# spec-133 D-133-16: provider/IDE aliases deleted. ``SurfacesConfig``
# validates against the closed enum in ``ai_engineering.domain.surface``.


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

    # spec-159 D-159-03: after an apply that mutated hook bytes, re-pin
    # hooks-manifest.json so enforce-mode does not kill the freshly
    # deployed hooks. No-op on preview/dry-run/no-change applies.
    _finalize_update_hooks_manifest(workflow_result, root)

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

    # Show only the count that can be non-zero in this mode; the other is
    # structurally always zero and would be pure noise.
    if result.dry_run:
        kv("Available", result.available_count)
    else:
        kv("Applied", result.applied_count)
    kv("Protected", result.protected_count)
    kv("Unchanged", result.unchanged_count)
    kv("Orphan", result.orphan_count)

    # spec-158 D-158-03: surface the hook-command migration inside the
    # protected settings.json (never silent — Hard Rule "no silent caps").
    migration = getattr(result, "hook_migration", None)
    if migration is not None and (migration.migrated_count or migration.skipped_count):
        verb = "migrated" if not result.dry_run else "to migrate"
        kv("Hook commands", f"{migration.migrated_count} {verb}, {migration.skipped_count} skipped")
        for command in migration.skipped:
            warning(f"  hook command needs manual review: {command}")

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
            help="Run a focused sub-check: 'hot-path' (SLO budgets, advisory).",
        ),
    ] = None,
) -> None:
    """Diagnose and optionally fix framework health.

    Exit codes: 0 (pass), 1 (fail), 2 (warnings only). When ``--check
    hot-path`` is passed, runs the spec-114 advisory hot-path SLO
    audit and always exits 0 per D-114-03 (advisory through
    2026-05-31). ``--check`` supports only 'hot-path'.
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
    """Run a focused doctor sub-check when requested.

    Supported values:
    * ``hot-path`` -- spec-114 advisory SLO audit (D-114-03).

    (spec-148 removed ``state-db``: there is no state.db in the files-only
    model.)
    """
    if focused_check is None:
        return False
    if focused_check == "hot-path":
        from ai_engineering.cli_commands.doctor_hot_path import run_hot_path_check

        run_hot_path_check(root)
        return True
    raise typer.BadParameter(f"Unknown --check value: {focused_check!r}. Supported: hot-path.")


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
        noun = "warning(s)" if report.passed else "issue(s)"
        kv("Manual follow-up", f"{manual_count} {noun} for human review")

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
        suggest_next(
            [
                (_DOCTOR_FIX_COMMAND, "Attempt automatic remediation"),
                ("ai-eng doctor --json", "Re-run doctor with structured output"),
            ]
        )
    else:
        warning("Manual follow-up required. Review the failing checks above.")
        suggest_next(
            [
                (_DOCTOR_FIX_COMMAND, "Attempt automatic remediation for fixable issues"),
            ]
        )


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


def version_cmd(ctx: typer.Context) -> None:
    """Show the installed ai-engineering version and lifecycle status.

    Serves as the ``version`` Typer sub-group callback: when a subcommand
    (e.g. ``upgrade``) is invoked, this returns early so the subcommand owns
    the output and there is no double render.

    The latest-version figure comes from the single SSOT resolver
    (``resolve_latest_known``) — the newer of the bundled registry and the PyPI
    cache — so this surface can never contradict the inline update notice (the
    old dual ``message`` + ``latest known release`` lines could disagree).
    """
    if ctx.invoked_subcommand is not None:
        return

    from ai_engineering.cli_ui import get_console, render_version_status
    from ai_engineering.version import resolve_latest_known
    from ai_engineering.version.checker import check_version
    from ai_engineering.version.compare import is_newer

    result = check_version(__version__)
    latest = resolve_latest_known()
    update_available = bool(latest) and is_newer(latest, __version__)

    if is_json_mode():
        emit_success(
            "ai-eng version",
            {
                "version": __version__,
                "latest": latest,
                "update_available": update_available,
                "status": result.status.value if result.status else None,
                "message": result.message,
            },
        )
        return

    show_logo()
    render_version_status(__version__, latest)
    # Deprecated / EOL are security-relevant lifecycle states — surface the
    # registry message beyond the one-line version status.
    if result.is_deprecated or result.is_eol:
        get_console().print(f"  [warning]{result.message}[/warning]")


_MANUAL_UPGRADE_COMMANDS: tuple[str, ...] = (
    "pipx upgrade ai-engineering",
    "uv tool upgrade ai-engineering",
    "pip install -U ai-engineering",
)
"""Likely manual upgrade commands shown when the install method is unknown."""


def _emit_manual_upgrade_guidance() -> None:
    """Surface manual upgrade commands when no runnable method was detected.

    Used when ``install_method.detect`` returns ``unknown`` (e.g. a pipx/uv
    standalone tool with no importable pip). We never execute a doomed command;
    instead we print the commands the operator can run by hand. The caller exits
    non-zero so an un-upgraded install is never reported as success.
    """
    message = (
        "Could not determine how ai-engineering was installed; not running a "
        "guessed command. Upgrade manually with whichever installed it:"
    )
    if is_json_mode():
        from ai_engineering.cli_envelope import emit_error

        emit_error(
            command="version-upgrade",
            message=message,
            code="UpgradeMethodUnknown",
            fix="; ".join(_MANUAL_UPGRADE_COMMANDS),
        )
        return
    error(message)
    for command in _MANUAL_UPGRADE_COMMANDS:
        print_stdout(f"  {command}")


def version_upgrade_cmd(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print the upgrade command without running it."),
    ] = False,
) -> None:
    """Upgrade ai-engineering using the detected install method.

    Detects the install method (pipx / uv tool / brew / pip) and runs the
    matching upgrade command. ``--dry-run`` prints the exact command and runs
    nothing. A non-zero return code fails loudly: it surfaces the manual
    command and exits non-zero so an interrupted upgrade is never silent.
    """
    from ai_engineering.version import install_method

    method, argv = install_method.detect()

    if method == "unknown":
        _emit_manual_upgrade_guidance()
        raise typer.Exit(code=1)

    command_str = " ".join(argv)

    if dry_run:
        if is_json_mode():
            emit_success(
                "ai-eng version upgrade",
                {"method": method, "command": command_str, "dry_run": True},
            )
        else:
            show_logo()
            info(f"Detected install method: {method}")
            print_stdout(command_str)
        return

    if not is_json_mode():
        show_logo()
        info(f"Upgrading via {method}: {command_str}")

    # spec-156 D-156-14: in JSON mode the upgrade tool's stdout/stderr would
    # interleave with — and corrupt — the success envelope, so redirect both to
    # DEVNULL. Human mode streams the tool output so the operator sees progress.
    if is_json_mode():
        completed = subprocess.run(
            argv, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    else:
        completed = subprocess.run(argv, check=False)

    if completed.returncode != 0:
        if is_json_mode():
            from ai_engineering.cli_envelope import emit_error

            emit_error(
                command="version-upgrade",
                message=f"Upgrade via {method} failed (exit {completed.returncode}).",
                code="UpgradeFailed",
                fix=f"Run the upgrade manually: {command_str}",
            )
        else:
            error(f"Upgrade via {method} failed (exit {completed.returncode}).")
            error(f"Run it manually: {command_str}")
        raise typer.Exit(code=1)

    if is_json_mode():
        emit_success(
            "ai-eng version upgrade",
            {"method": method, "command": command_str, "upgraded": True},
        )
    else:
        success(f"Upgraded ai-engineering via {method}.")
