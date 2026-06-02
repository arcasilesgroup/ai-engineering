"""Typer application factory for ai-engineering CLI.

Builds the main Typer app with all command groups registered.
The factory pattern allows tests to create isolated app instances.

Includes:
- Global ``--json`` flag for agent-friendly structured output.
- Version lifecycle callback that blocks deprecated versions on non-exempt commands.
- Centralized exception handler that converts path-related OS errors into
  clean user-facing messages (no tracebacks).
"""

from __future__ import annotations

import functools
import json
import sys
from collections.abc import Callable
from typing import Annotated

import typer
import yaml
from pydantic import ValidationError

from ai_engineering.cli_commands import (
    audit_cmd,
    check,
    core,
    decisions_cmd,
    dev_sync,
    gate,
    host_cmd,
    internal,
    issue,
    maintenance,
    ownership_cmd,
    plan_cmd,
    release,
    risk_cmd,
    setup,
    skills,
    spec_cmd,
    verify_cmd,
)
from ai_engineering.cli_commands import (
    cleanup as cleanup_mod,
)
from ai_engineering.cli_commands import (
    commit as commit_cmd_mod,
)
from ai_engineering.cli_commands import (
    config as config_cmd_mod,
)
from ai_engineering.cli_commands import (
    pr as pr_cmd_mod,
)
from ai_engineering.cli_commands import (
    status as status_cmd_mod,
)

# Commands exempt from deprecation blocking (needed for diagnosis and remediation).
_EXEMPT_COMMANDS: frozenset[str] = frozenset({"version", "update", "doctor", "internal"})

# spec-156 D-156-09: commands that must NEVER render the human update notice —
# automation / hot-path surfaces where a stderr line corrupts shim output or
# blows the pre-commit budget. The notice is rendered AFTER the command (so
# per-command ``--json`` is fully resolved via is_json_mode), never in the
# pre-command callback.
_NOTICE_EXEMPT: frozenset[str] = frozenset({"version", "internal", "gate"})

# The subcommand resolved by the app callback, read by the error boundary to
# decide whether to render the post-command update notice. Module-level because
# the per-command wrapper does not otherwise see the invoked command name.
_invoked_command: str | None = None

# Exceptions that should produce a clean one-line error instead of a traceback.
_USER_FACING_EXCEPTIONS: tuple[type[Exception], ...] = (
    FileNotFoundError,
    NotADirectoryError,
    PermissionError,
    json.JSONDecodeError,
    ValidationError,
    yaml.YAMLError,
)


def _cli_error_boundary(func: Callable[..., object]) -> Callable[..., object]:
    """Wrap a CLI command to catch user-facing errors and emit a clean message.

    Converts OS path errors (FileNotFoundError, NotADirectoryError,
    PermissionError) and data errors (JSONDecodeError, ValidationError)
    into a single-line ``Error: <message>`` on stderr with exit code 1,
    instead of a raw Python traceback.  In JSON mode, emits an error
    envelope instead.
    """

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        try:
            result = func(*args, **kwargs)
            from ai_engineering.cli_output import is_json_mode

            if not is_json_mode():
                from ai_engineering.cli_ui import get_console

                con = get_console()
                if con.is_terminal:
                    con.print()
            # spec-156 D-156-09: render the update notice AFTER the command, so
            # per-command ``--json`` (set inside the command, after the callback)
            # is fully resolved and machine/automation surfaces never see it.
            _maybe_render_post_command_notice()
            return result
        except _USER_FACING_EXCEPTIONS as exc:
            from ai_engineering.cli_output import is_json_mode

            if is_json_mode():
                from ai_engineering.cli_envelope import emit_error

                cmd_name = getattr(func, "__name__", "unknown")
                emit_error(
                    command=cmd_name.replace("_cmd", "").replace("_", "-"),
                    message=str(exc),
                    code=type(exc).__name__,
                    fix="Check the path exists and you have permission to access it.",
                )
            else:
                typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from None

    return wrapper


def _maybe_render_post_command_notice() -> None:
    """Render the human update notice after a command, when appropriate.

    spec-156 D-156-09: gated on the fully-resolved output mode
    (``is_json_mode()`` — true even for per-command ``--json`` set inside the
    command), the ``_NOTICE_EXEMPT`` automation/hot-path set, the
    ``AIENG_NO_UPDATE_CHECK`` env opt-out, and the manifest
    ``version_check.enabled`` flag.

    spec-157 review (F7): the manifest ``version_check`` block is parsed
    exactly ONCE here and threaded into the renderer, which previously
    re-loaded it — halving the per-command manifest parse on the CLI hot
    path. Fail-open: any error is swallowed by the notice renderer itself.
    """
    if _invoked_command is None or _invoked_command in _NOTICE_EXEMPT:
        return
    _render_update_notice_gated()


def _render_update_notice_gated() -> None:
    """Shared notice gate: JSON / env opt-out / manifest flag → cli_ui renderer.

    Extracted so both the post-command path and the bare ``ai-eng`` invocation
    (which exits in the app callback, never reaching the error boundary) render
    the notice through one set of gates. Fail-open: the renderer swallows errors.
    """
    import os

    from ai_engineering.cli_output import is_json_mode

    if is_json_mode():
        return
    if os.environ.get("AIENG_NO_UPDATE_CHECK", "").strip().lower() in {"1", "true", "yes", "on"}:
        return

    from ai_engineering.cli_ui import _load_version_check_config, maybe_render_update_notice

    config = _load_version_check_config()
    if not getattr(config, "enabled", True):
        return
    maybe_render_update_notice(config=config)


def _app_callback(
    ctx: typer.Context,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output structured JSON for agent consumption."),
    ] = False,
) -> None:
    """App-level callback: global flags + version lifecycle policy."""
    from ai_engineering.cli_output import set_json_mode

    set_json_mode(json_output)

    # spec-156 D-156-09: record the invoked command so the error boundary can
    # decide whether to render the post-command update notice.
    global _invoked_command
    _invoked_command = ctx.invoked_subcommand

    if ctx.invoked_subcommand is None:
        # No subcommand: show logo + help (human) or command tree (JSON)
        if json_output:
            from ai_engineering.cli_envelope import emit_success

            emit_success(
                "ai-eng",
                {
                    "commands": [
                        "install",
                        "update",
                        "doctor",
                        "check",
                        "verify",
                        "version",
                        "config",
                        "status",
                        "issue",
                        "gate",
                        "skill",
                        "maintenance",
                        "setup",
                        "release",
                        "decision",
                        "audit",
                        "commit",
                        "pr",
                        "risk",
                        "spec",
                        "cleanup",
                    ]
                },
            )
            raise typer.Exit(code=0)
        else:
            from ai_engineering.cli_ui import show_logo

            show_logo()
            typer.echo(ctx.get_help())
            # Bare `ai-eng` exits here, never reaching the error boundary, so
            # render the update notice inline before exiting.
            _render_update_notice_gated()
            raise typer.Exit(code=0)

    if not json_output and ctx.invoked_subcommand not in {"version", "internal"}:
        from ai_engineering.cli_ui import show_banner

        show_banner()

    from ai_engineering import __version__
    from ai_engineering.version.checker import check_version

    result = check_version(__version__)

    command = ctx.invoked_subcommand or ""

    if (result.is_deprecated or result.is_eol) and command not in _EXEMPT_COMMANDS:
        status_label = "deprecated" if result.is_deprecated else "end-of-life"
        sys.stderr.write(
            f"BLOCKED: ai-engineering {__version__} is {status_label}.\n"
            f"  {result.message}\n"
            f"  Run 'ai-eng version upgrade' to upgrade or 'ai-eng doctor' to diagnose.\n"
        )
        raise typer.Exit(code=1)

    # spec-156 D-156-09: the update notice is rendered AFTER the command by the
    # error boundary (see _maybe_render_post_command_notice), not here — the
    # pre-command callback cannot see a per-command ``--json`` flag, which leaked
    # the notice onto automation / agent surfaces and burned the once-per-TTL
    # throttle (audit high 5).

    # spec-133 D-133-23: stack-drift middleware (warn + optional block)
    _stack_drift_middleware(command)


def _safe(func: Callable) -> Callable:
    """Shorthand: apply the CLI error boundary to a command function."""
    return _cli_error_boundary(func)


# Commands exempt from stack-drift middleware (spec-133 D-133-23).
# install / doctor / version / internal must run regardless of drift state.
_DRIFT_EXEMPT: frozenset[str] = frozenset(
    {
        "install",
        "doctor",
        "version",
        "internal",
        "update",
    }
)


def _stack_drift_middleware(command: str) -> None:
    """spec-133 D-133-23 / B16 Gap 4: stack-drift warning + optional block.

    Reads manifest.providers.stacks, runs autodetect.detect_stacks, and
    emits a structured warning on drift. When AIENG_STACK_DRIFT_STRICT=1
    (env) and the command is mutation-class (commit/pr/gate), the
    middleware blocks with exit code 78 per D-133-24 cognitive contract.
    """
    if command in _DRIFT_EXEMPT or not command:
        return

    import os

    try:
        from ai_engineering.config.loader import load_manifest_config
        from ai_engineering.installer.autodetect import detect_stacks
        from ai_engineering.paths import resolve_project_root
    except ImportError:
        return  # framework not installed yet — silent no-op

    try:
        root = resolve_project_root(None)
    except Exception:
        return  # not a project root — silent no-op

    # spec-147 G1 T-1.9/1.10: a corrupt manifest must NOT silently disable
    # stack-drift detection. ``load_manifest_config`` returns defaults for a
    # missing manifest (legitimate) and raises ``InvalidManifestError`` for a
    # corrupt one — let that surface loud rather than swallowing it under a
    # bare ``except Exception``.
    cfg = load_manifest_config(root)

    configured = set(getattr(getattr(cfg, "providers", None), "stacks", []) or [])
    try:
        detected = set(detect_stacks(root))
    except Exception:
        return

    if not detected:
        return  # greenfield — nothing to drift against
    missing = detected - configured
    if not missing:
        return  # configured matches reality

    # spec-133 D-133-24: structured machine-readable exit envelope.
    msg_lines = [
        "WARNING: stack drift detected",
        f"  Detected stack(s): {sorted(missing)}",
        f"  Configured stack(s): {sorted(configured)}",
        "  Recovery: ai-eng doctor --fix",
    ]
    strict = os.environ.get("AIENG_STACK_DRIFT_STRICT") == "1"
    blocking_cmds = {"commit", "pr", "gate"}
    if strict and command in blocking_cmds:
        from ai_engineering.cli_commands._exit_codes import EXIT_STACK_DRIFT

        msg_lines.insert(0, "BLOCKED: stack drift in strict mode")
        sys.stderr.write("\n".join(msg_lines) + "\n")
        raise typer.Exit(code=EXIT_STACK_DRIFT)
    sys.stderr.write("\n".join(msg_lines) + "\n")


# spec-132 D-132-02..05: removed verbs map to their replacements. Each
# removed top-level verb is registered as a hidden command that prints
# ``removed; use <new>`` to stderr and exits 2 -- no soft-redirect.
_REMOVED_VERBS: dict[str, str] = {
    "validate": "check",
    "work-item": "issue",
    "stack": "config",
    "ide": "config",
    "provider": "config",
    "vcs": "config",
    "workflow": "ai-eng pr",
    "sync": "dev sync",
}


def _build_removed_handler(old: str, new: str) -> Callable[..., None]:
    """Build a Typer-compatible handler that surfaces the rename."""

    def _removed(
        extra_args: Annotated[
            list[str] | None,
            typer.Argument(),
        ] = None,
    ) -> None:
        del extra_args
        sys.stderr.write(f"removed; use '{new}'\n")
        raise typer.Exit(code=2)

    _removed.__name__ = f"removed_{old.replace('-', '_')}"
    _removed.__doc__ = f"removed; use '{new}'"
    return _removed


def create_app() -> typer.Typer:  # audit:exempt:pre-existing-debt-out-of-spec-114-G7-scope
    """Build and return the Typer application.

    Registers all command groups and sub-commands:
    - Core commands: install, update, doctor, version.
    - Stack/IDE commands: stack add/remove/list, ide add/remove/list.
    - Gate commands: gate pre-commit/commit-msg/pre-push/risk-check.
    - Skills commands: skill status.
    - Maintenance commands: maintenance report/pr/branch-cleanup/risk-status/repo-status/spec-reset.

    Returns:
        Configured Typer application instance.
    """
    from ai_engineering.core.cli import SmartTyperGroup

    app = typer.Typer(
        name="ai-eng",
        help="AI governance framework for secure software delivery.",
        no_args_is_help=False,
        rich_markup_mode="rich",
        callback=_app_callback,
        invoke_without_command=True,
        epilog="[dim]Docs & issues:[/dim] https://github.com/arcasilesgroup/ai-engineering",
        cls=SmartTyperGroup,
    )

    # Core commands (top-level) -- final 20-verb tree per D-132-02..05.
    app.command("install")(_safe(core.install_cmd))
    app.command("update")(_safe(core.update_cmd))
    app.command("doctor")(_safe(core.doctor_cmd))
    app.command("check")(_safe(check.check_cmd))
    app.command("verify")(_safe(verify_cmd.verify_cmd))
    version_app = typer.Typer(
        name="version",
        invoke_without_command=True,
        help="Show version and upgrade the package.",
    )
    # spec-156 D-156-14: route version commands through the CLI error boundary
    # (functools.wraps preserves the Typer signature) so OS/JSON/validation
    # errors emit a clean one-line message or JSON envelope, not a traceback.
    version_app.callback(invoke_without_command=True)(_safe(core.version_cmd))
    version_app.command("upgrade")(_safe(core.version_upgrade_cmd))
    app.add_typer(version_app, name="version")
    app.command("release")(_safe(release.release_cmd))
    app.command("status")(_safe(status_cmd_mod.status_cmd))
    app.command("commit")(_safe(commit_cmd_mod.commit_cmd))
    app.command("pr")(_safe(pr_cmd_mod.pr_cmd))

    # Config sub-group: inspection + single-axis Surface management.
    # spec-133 D-133-16 hard-cut collapsed `ide` + `provider` into
    # `surface`. The Surface enum is closed (domain.surface.SURFACE_IDS).
    config_app = typer.Typer(
        name="config",
        help="Inspect or interactively reconfigure stacks/Surfaces/VCS.",
        invoke_without_command=True,
    )
    config_app.callback()(_safe(config_cmd_mod.config_cmd))
    config_app.command("reconfigure")(_safe(config_cmd_mod.reconfigure_cmd))
    config_stack_app = typer.Typer(name="stack", no_args_is_help=True)
    config_stack_app.command("list")(_safe(config_cmd_mod.stack_list))
    config_app.add_typer(config_stack_app, name="stack")
    config_surface_app = typer.Typer(name="surface", no_args_is_help=True)
    config_surface_app.command("list")(_safe(config_cmd_mod.surface_list))
    config_app.add_typer(config_surface_app, name="surface")
    config_vcs_app = typer.Typer(name="vcs", no_args_is_help=True)
    config_vcs_app.command("status")(_safe(config_cmd_mod.vcs_status))
    config_app.add_typer(config_vcs_app, name="vcs")
    app.add_typer(config_app, name="config")

    # Gate sub-group
    gate_app = typer.Typer(
        name="gate",
        help="Run git hook quality gate checks.",
        no_args_is_help=True,
    )
    gate_app.command("pre-commit")(_safe(gate.gate_pre_commit))
    gate_app.command("commit-msg")(_safe(gate.gate_commit_msg))
    gate_app.command("pre-push")(_safe(gate.gate_pre_push))
    gate_app.command("risk-check")(_safe(gate.gate_risk_check))
    gate_app.command("all")(_safe(gate.gate_all))
    # spec-104 D-104-10: single-pass orchestrator + cache subcommands.
    gate_app.command("run")(_safe(gate.gate_run))
    gate_app.command("cache")(_safe(gate.gate_cache))
    app.add_typer(gate_app, name="gate")

    # Skill sub-group
    skill_app = typer.Typer(
        name="skill",
        help="Manage local skill eligibility diagnostics.",
        no_args_is_help=True,
    )
    skill_app.command("status")(_safe(skills.skill_status))
    app.add_typer(skill_app, name="skill")

    # Host sub-group (spec-139 M2 D-139-02): resource preflight probe.
    # ``ai-eng host probe`` prints the current HostProbe snapshot plus the
    # cap that ``resolve_wave_cap`` would recommend, for operator-facing
    # diagnosis of wave-fan-out decisions.
    host_app = typer.Typer(
        name="host",
        help="Inspect host capacity (cores, free RAM, memory pressure, swap).",
        no_args_is_help=True,
    )
    host_app.command("probe")(_safe(host_cmd.host_probe_cmd))
    app.add_typer(host_app, name="host")

    # Maintenance sub-group
    maint_app = typer.Typer(
        name="maintenance",
        help="Framework maintenance operations.",
        no_args_is_help=True,
    )
    maint_app.command("report")(_safe(maintenance.maintenance_report))
    maint_app.command("pr")(_safe(maintenance.maintenance_pr))
    maint_app.command("branch-cleanup")(_safe(maintenance.maintenance_branch_cleanup))
    maint_app.command("risk-status")(_safe(maintenance.maintenance_risk_status))
    maint_app.command("repo-status")(_safe(maintenance.maintenance_repo_status))
    maint_app.command("spec-reset")(_safe(maintenance.maintenance_spec_reset))
    maint_app.command("reset-events")(_safe(maintenance.maintenance_reset_events))
    maint_app.command("all")(_safe(maintenance.maintenance_all))
    cleanup_app = typer.Typer(
        name="cleanup",
        no_args_is_help=True,
        help="Git branch + runtime + spec cleanup (spec-133 D-133-03)",
    )
    app.add_typer(cleanup_app, name="cleanup")
    cleanup_app.command("branches")(_safe(cleanup_mod.cleanup_branches_cmd))
    cleanup_app.command("runtime")(_safe(cleanup_mod.cleanup_runtime_cmd))
    cleanup_app.command("specs")(_safe(cleanup_mod.cleanup_specs_cmd))
    cleanup_app.command("all")(_safe(cleanup_mod.cleanup_all_cmd))
    app.add_typer(maint_app, name="maintenance")

    # Setup sub-group
    setup_app = typer.Typer(
        name="setup",
        help="Configure platform credentials for governance workflows.",
        no_args_is_help=True,
    )
    setup_app.command("platforms")(_safe(setup.setup_platforms_cmd))
    setup_app.command("github")(_safe(setup.setup_github_cmd))
    setup_app.command("sonar")(_safe(setup.setup_sonar_cmd))
    setup_app.command("azure-devops")(_safe(setup.setup_azure_devops_cmd))
    setup_app.command("sonarlint")(_safe(setup.setup_sonarlint_cmd))
    app.add_typer(setup_app, name="setup")

    # Decision sub-group (v3: decision store management)
    decision_app = typer.Typer(
        name="decision",
        help="Manage the decision store.",
        no_args_is_help=True,
    )
    decision_app.command("list")(_safe(decisions_cmd.decision_list))
    decision_app.command("expire-check")(_safe(decisions_cmd.decision_expire_check))
    decision_app.command("record")(_safe(decisions_cmd.decision_record))
    decision_app.command("backfill")(_safe(decisions_cmd.decision_backfill))
    app.add_typer(decision_app, name="decision")

    # Ownership sub-group (spec-138 M3.T5: CODEOWNERS -> state.db importer).
    ownership_app = typer.Typer(
        name="ownership",
        help="Manage the canonical ownership map (state.db.ownership_map).",
        no_args_is_help=True,
    )
    ownership_app.command("import")(_safe(ownership_cmd.ownership_import))
    app.add_typer(ownership_app, name="ownership")

    # Audit sub-group (spec-107 D-107-10: hash-chained audit trail verifier;
    # spec-148: token rollups + replay computed over framework-events.ndjson)
    audit_app = typer.Typer(
        name="audit",
        help=(
            "Verify the hash-chained audit trail and report token usage over "
            "framework-events.ndjson."
        ),
        no_args_is_help=True,
    )
    # spec-148 (files-only): framework-events.ndjson is the single ledger.
    # `verify` checks the hash chain; `tokens`/`replay` compute over the NDJSON.
    # The SQLite-backed index/query/health/vacuum/retention verbs were removed.
    audit_app.command("verify")(_safe(audit_cmd.audit_verify))
    audit_app.command("tokens")(_safe(audit_cmd.audit_tokens))
    audit_app.command("replay")(_safe(audit_cmd.audit_replay))
    app.add_typer(audit_app, name="audit")

    # Risk sub-group (spec-105: risk acceptance lifecycle CLI namespace)
    risk_app = typer.Typer(
        name="risk",
        help="Manage risk-acceptance decisions (accept, renew, resolve, revoke, list, show).",
        no_args_is_help=True,
    )
    risk_app.command("accept")(_safe(risk_cmd.risk_accept))
    risk_app.command("accept-all")(_safe(risk_cmd.risk_accept_all))
    risk_app.command("renew")(_safe(risk_cmd.risk_renew))
    risk_app.command("resolve")(_safe(risk_cmd.risk_resolve))
    risk_app.command("revoke")(_safe(risk_cmd.risk_revoke))
    risk_app.command("list")(_safe(risk_cmd.risk_list))
    risk_app.command("show")(_safe(risk_cmd.risk_show))
    app.add_typer(risk_app, name="risk")

    # Spec sub-group (v3: spec lifecycle management)
    spec_app = typer.Typer(
        name="spec",
        help="Spec lifecycle: start a work plane, verify counters, list and show active spec.",
        no_args_is_help=True,
    )
    spec_app.command("start")(_safe(spec_cmd.spec_start))
    spec_app.command("activate", hidden=True)(_safe(spec_cmd.spec_activate))
    spec_app.command("verify")(_safe(spec_cmd.spec_verify))
    spec_app.command("list")(_safe(spec_cmd.spec_list))
    spec_app.command("show")(_safe(spec_cmd.spec_show))
    app.add_typer(spec_app, name="spec")

    # Plan sub-group (spec-139 M7.T2: deterministic DAG construction).
    plan_app = typer.Typer(
        name="plan",
        help="Plan-level deterministic helpers (DAG construction over sub-spec plans).",
        no_args_is_help=True,
    )
    plan_app.command("dag-build")(_safe(plan_cmd.plan_dag_build))
    app.add_typer(plan_app, name="plan")

    # Issue sub-group (D-132-03 -- renamed from work-item).
    issue_app = typer.Typer(
        name="issue",
        help="Sync specs to external issues (GitHub Issues / Azure DevOps Boards).",
        no_args_is_help=True,
    )
    issue_app.command("sync")(_safe(issue.issue_sync))
    app.add_typer(issue_app, name="issue")

    # Dev sub-group (D-132-05): source-repo helpers; hidden.
    dev_app = typer.Typer(
        name="dev",
        help="Source-repo developer helpers (hidden in consumer projects).",
        no_args_is_help=True,
        hidden=True,
    )
    dev_app.command("sync")(_safe(dev_sync.dev_sync_cmd))
    app.add_typer(dev_app, name="dev", hidden=True)

    internal_app = typer.Typer(
        name="internal",
        help="Internal framework commands.",
        no_args_is_help=True,
        hidden=True,
    )
    internal_app.command(
        "python",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        hidden=True,
    )(internal.internal_python)
    app.add_typer(internal_app, name="internal", hidden=True)

    # spec-132 D-132-02..05: removed verbs print ``removed; use <new>`` and
    # exit 2. No soft-redirect, no alias. Hidden so they don't pollute the
    # help tree but are still resolvable as commands.
    for old_verb, new_verb in _REMOVED_VERBS.items():
        app.command(old_verb, hidden=True)(_build_removed_handler(old_verb, new_verb))

    # spec-132 D-132-11: universal help-on-no-args wrapper applied at
    # registration time. The ``internal`` and ``dev`` groups opt out.
    from ai_engineering.core.cli import apply_no_args_help

    apply_no_args_help(app, opt_out_groups={"internal", "dev"})

    return app
