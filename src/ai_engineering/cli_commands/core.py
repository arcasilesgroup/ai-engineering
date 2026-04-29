"""Core CLI commands: install, update, doctor, version.

These are the primary entry points for the ``ai-eng`` CLI.
Human-first Rich output by default; ``--json`` for agent consumption.
"""

from __future__ import annotations

import sys
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
) -> None:
    """Install the ai-engineering governance framework."""
    if non_interactive:
        set_json_mode(True)

    root = resolve_project_root(target)

    # --- Project validation guard ---
    _PROJECT_SIGNALS = (
        ".git",
        "pyproject.toml",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "tsconfig.json",
    )
    has_project = any((root / s).exists() for s in _PROJECT_SIGNALS) or list(root.glob("*.sln"))
    if not has_project:
        if non_interactive:
            typer.echo(f"Error: no project files detected in {root}.", err=True)
            raise typer.Exit(code=1)
        if not typer.confirm(f"No project files detected in {root}. Continue anyway?", abort=True):
            raise typer.Exit(code=1)

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

    # Detect existing installation
    state_path = root / ".ai-engineering" / "state" / "install-state.json"
    is_reinstall = state_path.exists()
    mode = InstallMode.INSTALL

    if is_reinstall:
        # --- Reinstall path: no menu, mode from flags or auto-infer ---
        if fresh:
            mode = InstallMode.FRESH
        elif reconfigure:
            mode = InstallMode.RECONFIGURE
        else:
            mode = InstallMode.REPAIR

        if non_interactive:
            mode = InstallMode.REPAIR
    # First install: mode stays INSTALL (handled below)

    # --- Resolve configuration selections ---
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

    if is_reinstall and mode == InstallMode.RECONFIGURE:
        # --reconfigure: run wizard for new selections
        if not is_json_mode():
            _show_detection_summary(detected)
        from ai_engineering.installer.wizard import run_wizard

        wizard_result = run_wizard(detected, resolved if resolved else None)
        resolved_stacks = wizard_result.stacks
        resolved_providers = wizard_result.providers
        resolved_ides = wizard_result.ides
        resolved_vcs = wizard_result.vcs
    elif is_reinstall:
        # Default/fresh reinstall: read config from existing manifest.yml
        config = load_manifest_config(root)
        resolved_stacks = resolved.get("stacks", config.providers.stacks or ["python"])
        resolved_providers = resolved.get(
            "providers", config.ai_providers.enabled or ["claude_code"]
        )
        resolved_ides = resolved.get("ides", config.providers.ides or ["terminal"])
        resolved_vcs = resolved.get("vcs", config.providers.vcs)
    else:
        # First install: flags > wizard > detection > defaults
        any_resolved = bool(resolved)

        if any_resolved or is_json_mode() or not sys.stdin.isatty():
            resolved_stacks = resolved.get("stacks", detected.stacks or ["python"])
            resolved_providers = resolved.get("providers", detected.providers or ["claude_code"])
            resolved_ides = resolved.get("ides", detected.ides or ["terminal"])
            resolved_vcs = resolved.get("vcs", detected.vcs)
        else:
            # First install in interactive TTY: run the wizard
            if not is_json_mode():
                _show_detection_summary(detected)

            from ai_engineering.installer.wizard import run_wizard

            wizard_result = run_wizard(detected, resolved if resolved else None)
            resolved_stacks = wizard_result.stacks
            resolved_providers = wizard_result.providers
            resolved_ides = wizard_result.ides
            resolved_vcs = wizard_result.vcs

    # --- Reinstall confirmation gates ---
    if is_reinstall and not non_interactive:
        if mode == InstallMode.FRESH:
            # Show all files as overwrite
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
        elif mode == InstallMode.RECONFIGURE:
            # Show diff tree with added/removed markers
            typer.echo("\nReconfiguration preview:")
            typer.echo(f"  [added] New providers: {', '.join(resolved_providers)}")
            typer.echo(f"  [added] New stacks: {', '.join(resolved_stacks)}")
            typer.echo(f"  [added] New IDEs: {', '.join(resolved_ides)}")
            if not typer.confirm("Proceed?", default=True):
                raise typer.Exit(0)
        else:
            # Default REPAIR: preview + Y/n
            typer.echo("\nReinstall preview (repair mode):")
            typer.echo(f"  Stacks: {', '.join(resolved_stacks)}")
            typer.echo(f"  Providers: {', '.join(resolved_providers)}")
            typer.echo(f"  IDEs: {', '.join(resolved_ides)}")
            if not typer.confirm("Proceed?", default=True):
                raise typer.Exit(0)

    # Show tool availability in interactive mode
    if not is_json_mode():
        import shutil as _shutil

        tools = {
            "gh": _shutil.which("gh") is not None,
            "gitleaks": _shutil.which("gitleaks") is not None,
            "ruff": _shutil.which("ruff") is not None,
        }
        render_detection(resolved_vcs, resolved_providers, tools)

    # spec-101 Compat-2 (Wave 27): emit the one-shot BREAKING banner BEFORE
    # the prereq gates so a first-upgrade run hitting EXIT 81 still gets
    # the banner explaining the new EXIT 80 / EXIT 81 contract. The
    # banner_seen flag (persisted to install-state.json) prevents
    # double-emission on subsequent runs.
    from ai_engineering.installer.phases.pipeline import (
        emit_breaking_banner_for_target,
    )

    emit_breaking_banner_for_target(root)

    # spec-101 D-101-11: prereqs precede tools. Missing/out-of-range uv yields
    # EXIT 81 BEFORE the tools phase ever runs. Strict precedence -- when the
    # user's environment is broken at the prereq layer, the tools phase never
    # gets a chance to surface its own EXIT 80.
    try:
        check_uv_prereq(root)
    except PrereqMissing as exc:
        error(str(exc))
        raise typer.Exit(code=EXIT_PREREQS_MISSING) from exc

    # spec-101 D-101-14: per-stack SDK prereq gate. Iterates the 9 SDK-required
    # stacks declared by the project, applies the D-101-13 stack-level carve-out
    # (e.g. swift on linux is filtered before probing), and probes each SDK via
    # ``prereqs/sdk.py.probe_sdk``. Any absent/out-of-range SDK aggregates into
    # a single EXIT 81 with install links + verify commands per failing stack.
    try:
        check_sdk_prereqs(resolved_stacks, root=root)
    except PrereqMissing as exc:
        error(str(exc))
        raise typer.Exit(code=EXIT_PREREQS_MISSING) from exc

    # spec-109 D-109-07: live multi-step progress replaces the single-spinner
    # UX. Each phase reports its name as it begins; the CLI shows
    # "[N/M] phase_name" so the user can see exactly what's happening.
    from ai_engineering.installer.phases import PHASE_ORDER as _PHASE_ORDER

    _phase_labels_pretty = {
        PHASE_DETECT: "Detecting environment",
        PHASE_GOVERNANCE: "Copying governance framework",
        PHASE_IDE_CONFIG: "Configuring IDE integrations",
        PHASE_STATE: "Initializing state files",
        PHASE_TOOLS: "Installing required tools",
        PHASE_HOOKS: "Installing git hooks",
    }

    with step_progress(
        total=len(_PHASE_ORDER), description="Installing ai-engineering framework..."
    ) as _tracker:

        def _phase_progress(message: str) -> None:
            # message arrives as "[i/N] phase_name"; translate phase_name to a
            # human label when known, keep the [i/N] prefix verbatim.
            try:
                prefix, name = message.split(" ", 1)
            except ValueError:
                _tracker.step(message)
                return
            label = _phase_labels_pretty.get(name.strip(), name.strip())
            _tracker.step(f"{prefix} {label}")

        result, summary = install_with_pipeline(
            root,
            mode=mode,
            stacks=resolved_stacks,
            ides=resolved_ides,
            vcs_provider=resolved_vcs,
            ai_providers=resolved_providers,
            force=force,
            progress_callback=_phase_progress,
        )

    # spec-101 Corr-1 (Wave 28): in --non-interactive mode, emit one line
    # per skipped tool entry so downstream verifiers (the smoke-test
    # idempotence assertion) can match the ``tool:<name>:<marker>``
    # signature. Markers go to stderr to preserve stdout JSON purity for
    # --non-interactive consumers.
    if non_interactive:
        tools_phase_result = next(
            (r for r in summary.results if r.phase_name == PHASE_TOOLS),
            None,
        )
        if tools_phase_result is not None and tools_phase_result.skipped:
            for skipped_entry in tools_phase_result.skipped:
                if skipped_entry.startswith("tool:"):
                    print_stderr(skipped_entry)

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
    from ai_engineering.installer.auto_remediate import (
        AutoRemediateReport,
        auto_remediate_after_install,
    )

    # Coerce to a real list so MagicMock-shaped test summaries do not surface
    # as truthy non-critical failures with empty iteration.
    raw_failures = getattr(summary, "non_critical_failures", None) or []
    try:
        non_critical_failures_list = list(raw_failures)
    except TypeError:
        non_critical_failures_list = []

    if no_auto_remediate:
        auto_remediation_report = AutoRemediateReport()
    else:
        auto_remediation_report = auto_remediate_after_install(root, non_critical_failures_list)

    if auto_remediation_report.invoked and not is_json_mode():
        _render_auto_remediation_summary(auto_remediation_report)

    # spec-109 D-109-06: exit code reflects reality.
    # - Critical phase failure  -> EXIT 80 (unchanged).
    # - Non-critical failure that auto-remediated successfully -> EXIT 0.
    # - Non-critical failure that survived remediation -> EXIT 80.
    if summary.failed_phase is not None:
        error(
            f"Install pipeline failed at phase {summary.failed_phase!r}. "
            "Run 'ai-eng doctor' for diagnostics."
        )
        raise typer.Exit(code=EXIT_TOOLS_FAILED)

    if non_critical_failures_list and not auto_remediation_report.success:
        # When auto-remediate is disabled (--no-auto-remediate) any non-critical
        # failure also surfaces EXIT 80 -- preserves CI fail-on-first-attempt
        # detection per spec-109 R-109-01.
        if no_auto_remediate:
            error(
                "Install pipeline finished with non-critical failures; "
                "auto-remediation disabled (--no-auto-remediate). "
                "Run 'ai-eng doctor --fix' to repair."
            )
        else:
            error(
                "Install pipeline finished with unresolved issues; "
                "auto-remediation could not fix every gap. "
                "Run 'ai-eng doctor --fix' to retry."
            )
        raise typer.Exit(code=EXIT_TOOLS_FAILED)

    canonical_config = load_manifest_config(root)
    active_providers = list(canonical_config.ai_providers.enabled)
    primary_provider = canonical_config.ai_providers.primary or (
        active_providers[0] if active_providers else "none"
    )
    ai_label = ", ".join(active_providers)

    if is_json_mode():
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
                # spec-109 D-109-05: auto_remediation is additive; CI consumers
                # who want to detect "first attempt failed but auto-fixed" can
                # check `auto_remediation.invoked == True` while the install
                # itself succeeded.
                "auto_remediation": auto_remediation_report.to_dict(),
            },
            [
                NextAction(command="ai-eng doctor", description="Run health diagnostics"),
                NextAction(
                    command="/ai-start",
                    description=(
                        "IDE assistant slash-command (Claude Code / Copilot / Codex / "
                        "Gemini): begin the first governed session"
                    ),
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
        # spec-109 follow-up: /ai-start is an IDE assistant slash command,
        # NOT a shell command. Surface only ``ai-eng *`` shell commands here;
        # the IDE-side hint is rendered as a separate guidance line below.
        next_steps = [
            ("ai-eng doctor", "Run health diagnostics"),
        ]
        if result.guide_text:
            next_steps.append(("ai-eng guide", "View branch policy setup guide"))
        suggest_next(next_steps)

        # IDE assistant guidance (separate from shell next steps).
        info(
            "Open your AI assistant (Claude Code / Copilot / Codex / Gemini) "
            "and run /ai-start to begin the first governed session."
        )

        # Summary panel with next steps
        pending_setup: list[tuple[str, str]] = []
        next_steps_list: list[tuple[str, str]] = [
            ("ai-eng doctor", "Verify everything works"),
        ]
        if result.manual_steps:
            for step in result.manual_steps:
                if "setup" in step.lower():
                    pending_setup.append(("ai-eng setup", step))

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


def _render_auto_remediation_summary(report: object) -> None:
    """Print a human-readable summary of auto-remediation outcomes.

    spec-109 D-109-05: auto-remediation runs after the pipeline when
    non-critical phases failed. Surface what was fixed and what survived so
    the user can see the second-pass behaviour explicitly. Silently no-op in
    JSON mode (caller already gates on ``not is_json_mode()``).
    """
    from ai_engineering.installer.auto_remediate import AutoRemediateReport

    if not isinstance(report, AutoRemediateReport):
        return

    typer.echo("")
    if report.success:
        info("Auto-remediation: all non-critical failures repaired automatically.")
    else:
        warning(
            "Auto-remediation: some issues still need manual follow-up "
            "(run 'ai-eng doctor --fix' to retry)."
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
    phase_labels = {
        PHASE_DETECT: "Detection",
        PHASE_GOVERNANCE: "Governance framework",
        PHASE_IDE_CONFIG: "IDE configuration",
        PHASE_HOOKS: "Git hooks",
        PHASE_STATE: "State initialization",
        PHASE_TOOLS: "Tool verification",
    }

    non_critical_failures = set(getattr(summary, "non_critical_failures", []) or [])

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
            # spec-109 D-109-02: a non-critical failure is rendered as WARN
            # rather than FAIL because the pipeline kept going AND auto-remediate
            # gets a second chance. Critical failures still surface as FAIL.
            if name in non_critical_failures:
                status = "warn"
                detail = (
                    "non-critical failure (auto-remediate will retry)"
                    if not detail or detail == "up to date"
                    else f"{detail} — non-critical (auto-remediate will retry)"
                )
            elif phase_result.failed:
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

_UPDATE_COMMAND = "ai-eng update"


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
    json_requested = is_json_mode() or output_json
    interactive_tty = not json_requested and sys.stdin.isatty()

    if interactive_tty:
        with spinner("Previewing framework updates..."):
            preview = update(root, dry_run=True)
        _render_update_result(preview, root=root, show_diff=show_diff)
        if preview.available_count == 0 and preview.orphan_count == 0:
            info("No framework-managed files require changes.")
            return

        orphan_suffix = ""
        if preview.orphan_count:
            orphan_suffix = f", {preview.orphan_count} orphaned (will be removed)"
        prompt_msg = (
            f"{preview.available_count} available{orphan_suffix}. "
            "Apply these framework updates now?"
        )
        should_apply = typer.confirm(prompt_msg, default=apply)
        if not should_apply:
            warning("Preview only. No changes were applied.")
            suggest_next(
                [("ai-eng update --apply", "Apply the previewed changes non-interactively")]
            )
            return

        try:
            with spinner("Applying framework updates..."):
                applied_result = update(root, dry_run=False)
        except Exception as exc:
            error(f"Update failed while applying changes: {exc}")
            raise typer.Exit(code=1) from exc

        _render_update_result(applied_result, root=root, show_diff=show_diff)
        return

    try:
        with spinner("Checking for updates..."):
            result = update(root, dry_run=not apply)
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

    if json_requested:
        result_data = result.to_dict()
        result_data["root"] = str(root)
        emit_success(
            _UPDATE_COMMAND,
            result_data,
            [
                NextAction(command="ai-eng doctor", description="Verify framework health"),
                NextAction(command="ai-eng update --apply", description="Apply changes"),
            ],
        )
        return

    _render_update_result(result, root=root, show_diff=show_diff)


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
        try:
            content = change.path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            typer.echo("    [binary or unreadable file]")
        else:
            lines = content.splitlines(keepends=True)
            if len(lines) > _DIFF_MAX_LINES:
                lines = lines[:_DIFF_MAX_LINES]
                remaining = len(content.splitlines()) - _DIFF_MAX_LINES
                lines.append(f"    ... ({remaining} more lines)\n")
            for line in lines:
                typer.echo(f"    -{line}", nl=False)
            if lines and not lines[-1].endswith("\n"):
                typer.echo("")
    elif change.diff:
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

    if focused_check == "hot-path":
        from ai_engineering.cli_commands.doctor_hot_path import run_hot_path_check

        run_hot_path_check(root)
        return
    if focused_check is not None:
        raise typer.BadParameter(f"Unknown --check value: {focused_check!r}. Supported: hot-path.")

    if dry_run and not fix:
        fix = True  # --dry-run implies --fix

    with spinner("Running health diagnostics..."):
        report = diagnose(root, fix=fix, dry_run=dry_run, phase_filter=phase)
    fixable_count, manual_count = _doctor_follow_up_counts(report)

    if fix and not dry_run and not is_json_mode():
        _interactive_fix(root, report, phase)

    if is_json_mode():
        report_dict = report.to_dict()
        next_actions = []
        if fixable_count:
            next_actions = [
                NextAction(
                    command="ai-eng doctor --fix",
                    description="Attempt automatic repairs for fixable issues",
                ),
            ]
        emit_success("ai-eng doctor", report_dict, next_actions)
    else:
        status = "PASS" if report.passed else "FAIL"
        result_header("Doctor", status, str(root))

        if not report.installed:
            warning("Framework not installed. Run 'ai-eng install' first.")

        kv("Summary", report.summary)
        if fixable_count:
            kv("Auto-fix", f"{fixable_count} issue(s) can be attempted with ai-eng doctor --fix")
        if manual_count:
            kv("Manual follow-up", f"{manual_count} issue(s) require manual action")

        for phase_report in report.phases:
            typer.echo(f"\n  {phase_report.name} [{phase_report.status.value}]")
            for doctor_check in phase_report.checks:
                status_line(
                    doctor_check.status.value,
                    doctor_check.name,
                    doctor_check.message,
                )

        if report.runtime:
            typer.echo("\n  runtime")
            for doctor_check in report.runtime:
                status_line(
                    doctor_check.status.value,
                    doctor_check.name,
                    doctor_check.message,
                )

        if fixable_count:
            suggest_next([("ai-eng doctor --fix", "Attempt automatic repairs for fixable issues")])
        elif manual_count:
            # Distinguish failing checks (blocking) from warnings (advisory).
            # `report.passed` is True when no FAIL exists — only WARN-level
            # follow-ups remain, so the project is functional.
            if report.passed:
                warning(f"{manual_count} warning(s) for review above; project is functional.")
            else:
                warning("Manual follow-up required. Review the failing checks above.")

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
        print_stdout(f"ai-engineering {result.message}")
