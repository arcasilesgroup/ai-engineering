"""Gate CLI commands: pre-commit, commit-msg, pre-push, risk-check, all, run, cache.

Invoked by git hooks to run quality gate checks.
Performance-critical: no logo, no stage banner, minimal colour.

spec-104 D-104-10 adds:
* ``ai-eng gate run`` — single-pass collector with cache-aware/--no-cache/--force
  override flags, ``--mode={local,ci}``, and ``--json`` envelope emission.
* ``ai-eng gate cache --status`` — read-only enumeration of cache entries with
  remaining max-age and total size.
* ``ai-eng gate cache --clear`` — interactive (or ``--yes``) wipe of the
  ``.ai-engineering/state/gate-cache/`` directory only — sibling state files
  are preserved.
"""

from __future__ import annotations

import contextlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import NextAction, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import (
    header,
    info,
    print_stdout,
    result_header,
    status_line,
    success,
    suggest_next,
    warning,
)
from ai_engineering.paths import resolve_project_root
from ai_engineering.policy import gate_cache as gate_cache_module
from ai_engineering.policy import mode_dispatch
from ai_engineering.policy import orchestrator as orchestrator_module
from ai_engineering.policy.gates import GateResult, run_gate
from ai_engineering.state.decision_logic import list_expired_decisions, list_expiring_soon
from ai_engineering.state.models import GateFindingsDocument, GateHook, GateSeverity
from ai_engineering.state.service import StateService

# spec-104 D-104-10: severity threshold for gate exit-code-1 failures.
_FAILURE_SEVERITIES: frozenset[GateSeverity] = frozenset(
    {GateSeverity.CRITICAL, GateSeverity.HIGH, GateSeverity.MEDIUM}
)


def _print_gate_result(result: GateResult) -> None:
    """Print gate results and exit with appropriate code."""
    status = "PASS" if result.passed else "FAIL"

    if is_json_mode():
        next_actions = []
        if not result.passed:
            next_actions = [
                NextAction(command="ruff check --fix .", description="Auto-fix lint issues"),
            ]
        emit_success(
            f"ai-eng gate {result.hook.value}",
            {
                "hook": result.hook.value,
                "passed": result.passed,
                "checks": [
                    {"name": c.name, "passed": c.passed, "output": c.output} for c in result.checks
                ],
            },
            next_actions,
        )
    else:
        # Primary result on stdout (preserves test assertions)
        print_stdout(f"Gate [{result.hook.value}] {status}")
        for check in result.checks:
            st = "ok" if check.passed else "fail"
            status_line(st, check.name, "passed" if check.passed else "failed")
            show_output = not check.passed
            if show_output and check.output:
                for line in check.output.splitlines()[:5]:
                    info(f"  {line}")

    if not result.passed:
        raise typer.Exit(code=1)


def gate_pre_commit(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Run pre-commit gate checks (format, lint, gitleaks)."""
    root = resolve_project_root(target)
    result = run_gate(GateHook.PRE_COMMIT, root)
    _print_gate_result(result)


def gate_commit_msg(
    msg_file: Annotated[
        Path,
        typer.Argument(help="Path to the commit message file."),
    ],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Run commit-msg gate checks (message format validation)."""
    root = resolve_project_root(target)
    result = run_gate(GateHook.COMMIT_MSG, root, commit_msg_file=msg_file)
    _print_gate_result(result)


def gate_pre_push(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Run pre-push gate checks (semgrep, pip-audit, tests, ty)."""
    root = resolve_project_root(target)
    result = run_gate(GateHook.PRE_PUSH, root)
    _print_gate_result(result)


def _check_risk_inline(root: Path, strict: bool) -> bool:
    """Check risk acceptance status inline. Returns True if any failure detected."""
    ds_path = root / ".ai-engineering" / "state" / "decision-store.json"

    if not ds_path.exists():
        info("No decision store found — no risk acceptances to evaluate")
        return False

    store = StateService(root).load_decisions()
    expired = list_expired_decisions(store)
    expiring = list_expiring_soon(store)

    if not expired and not expiring:
        success("All risk acceptances are current")
        return False

    if expiring:
        warning(f"{len(expiring)} risk acceptance(s) expiring soon:")
        for d in expiring:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "unknown"
            info(f"  - {d.id}: expires {exp}")

    if expired:
        warning(f"{len(expired)} expired risk acceptance(s):")
        for d in expired:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "unknown"
            info(f"  - {d.id}: expired {exp}")

    return bool(expired or (strict and expiring))


def gate_risk_check(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Fail on any expired risk acceptance."),
    ] = False,
) -> None:
    """Check risk acceptance status (expired and expiring-soon).

    Without --strict: reports status, exits 0 unless expired.
    With --strict: exits 1 if any expired risk acceptances exist.
    """
    root = resolve_project_root(target)
    failed = _check_risk_inline(root, strict)

    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_guard_gate

        emit_guard_gate(root, verdict="fail" if failed else "pass", task="risk-check")

    if failed:
        raise typer.Exit(code=1)


def gate_all(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Fail on expiring risk acceptances too."),
    ] = False,
) -> None:
    """Run all gate checks (pre-commit + pre-push + risk-check).

    For manual use before committing. Not for git hooks.
    Excludes commit-msg (requires a message file).
    """
    root = resolve_project_root(target)
    any_failed = False
    all_results: list[GateResult] = []

    for hook in (GateHook.PRE_COMMIT, GateHook.PRE_PUSH):
        result = run_gate(hook, root)
        all_results.append(result)
        if not result.passed:
            any_failed = True

    risk_failed = _check_risk_inline(root, strict)
    if risk_failed:
        any_failed = True

    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_guard_gate

        total_failed = sum(len(r.failed_checks) for r in all_results)
        emit_guard_gate(
            root,
            verdict="fail" if any_failed else "pass",
            task="gate-all",
            findings=total_failed,
        )

    if is_json_mode():
        checks = []
        for r in all_results:
            checks.extend(
                {"gate": r.hook.value, "name": c.name, "passed": c.passed, "output": c.output}
                for c in r.checks
            )
        emit_success(
            "ai-eng gate all",
            {"passed": not any_failed, "checks": checks},
            []
            if not any_failed
            else [NextAction(command="ai-eng doctor", description="Diagnose issues")],
        )
    else:
        overall = "PASS" if not any_failed else "FAIL"
        result_header("Gate All", overall)
        for r in all_results:
            header(f"gate {r.hook.value}")
            for check in r.checks:
                st = "ok" if check.passed else "fail"
                status_line(st, check.name, "passed" if check.passed else "failed")
        if any_failed:
            suggest_next(
                [
                    ("ai-eng doctor --fix --phase tools", "Install missing tools"),
                    ("ai-eng gate pre-commit", "Re-run specific gate"),
                ]
            )

    if any_failed:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# spec-104 D-104-10: gate run — single-pass orchestrator entrypoint.
# ---------------------------------------------------------------------------


def run_orchestrator_gate(
    staged_files: list[str],
    *,
    mode: str = "local",
    disabled: bool = False,
    force: bool = False,
    cache_dir: Path,
    project_root: Path,
    produced_by: str = "ai-commit",
) -> GateFindingsDocument:
    """Thin adapter from the CLI surface to ``policy.orchestrator.run_gate``.

    Exists primarily as a mock target for ``test_cli_gate_run_flags`` — the
    CLI tests patch ``ai_engineering.cli_commands.gate.run_orchestrator_gate``
    to inject a deterministic ``GateFindingsDocument`` without invoking any
    real subprocess. In production it forwards to ``orchestrator.run_gate``;
    cache invalidation for ``force=True`` is performed by ``gate_run`` BEFORE
    invoking this adapter so it survives the patched mock.

    ``produced_by`` is forwarded so the emitted document carries the correct
    skill-caller discriminator (``ai-commit`` / ``ai-pr`` / ``watch-loop``)
    per D-104-06 cross-IDE attribution rules.
    """
    return orchestrator_module.run_gate(
        staged_files=staged_files,
        mode=mode,
        cache_dir=cache_dir,
        cache_disabled=disabled,
        project_root=project_root,
        produced_by=produced_by,
    )


# ---------------------------------------------------------------------------
# spec-104 D-104-06: persist gate-findings.json beside any --json emission.
# ---------------------------------------------------------------------------


_GATE_FINDINGS_RELATIVE_PATH = Path(".ai-engineering") / "state" / "gate-findings.json"


def _persist_gate_findings(document: GateFindingsDocument, project_root: Path) -> Path:
    """Atomically persist the GateFindingsDocument to the canonical location.

    Default path is ``<project_root>/.ai-engineering/state/gate-findings.json``.
    Always called from ``gate_run`` (regardless of the ``--json`` flag) so the
    ``/ai-commit`` and ``/ai-pr`` skill instructions can reliably parse the
    JSON file after the orchestrator exits.

    Uses tempfile + ``os.replace`` for atomic publish: readers either see the
    previous version or the new one, never a partial write.
    """
    import os
    import tempfile

    output_path = project_root / _GATE_FINDINGS_RELATIVE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = document.model_dump_json(by_alias=True)

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=str(output_path.parent),
            prefix=f"{output_path.name}.",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp_path = tmp.name
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
    except BaseException:
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
        raise
    os.replace(tmp_path, str(output_path))
    return output_path


def _force_clear_cache(cache_dir: Path) -> None:
    """Implement ``--force`` semantics: wipe matching cache entries.

    Called from ``gate_run`` before ``run_orchestrator_gate`` so the
    ``clear_entry`` invocations are observable even when the orchestrator
    adapter is patched out by tests. When the cache directory is empty or
    missing, we still issue at least one ``clear_entry`` call against a
    sentinel name so ``--force`` always surfaces its contract on the spy.
    """
    if cache_dir.exists():
        entries = list(cache_dir.glob("*.json"))
        if entries:
            for entry_path in entries:
                cache_key = entry_path.stem
                with contextlib.suppress(Exception):
                    gate_cache_module.clear_entry(cache_dir, cache_key)
            return
    # Empty / missing cache dir — emit one sentinel clear so the
    # ``--force`` contract holds even on a cold cache.
    with contextlib.suppress(Exception):
        gate_cache_module.clear_entry(cache_dir, "force-sentinel")


def _document_has_failure(document: GateFindingsDocument) -> bool:
    """Return True when any finding has severity in ``_FAILURE_SEVERITIES``."""
    return any(finding.severity in _FAILURE_SEVERITIES for finding in document.findings)


def _emit_mode_banner(project_root: Path, *, no_color: bool = False) -> None:
    """Print the spec-105 D-105-02 / D-105-03 mode banner to stdout.

    Behavior:
      * Manifest declares ``regulated`` -> no banner (the default; quiet).
      * Manifest declares ``prototyping``, no escalation trigger fires ->
        emit ``[PROTOTYPING MODE -- ...]`` warning so the user remembers to
        flip back before merge.
      * Manifest declares ``prototyping``, escalation trigger fires ->
        emit ``[REGULATED MODE -- escalated from prototyping due to: ...]``
        with the human-readable reason from
        :func:`mode_dispatch.explain_escalation_reason`.

    Suppressed in JSON mode -- the banner is operator-facing UX, not part
    of the machine-readable envelope.
    """
    if is_json_mode():
        return
    try:
        from ai_engineering.config.loader import load_manifest_config

        manifest_mode = load_manifest_config(project_root).gates.mode
        resolved = mode_dispatch.resolve_mode(project_root)
        reason = mode_dispatch.explain_escalation_reason(project_root)
    except Exception:
        # Fail-open: never let the banner crash a gate run.
        return

    text = mode_dispatch.banner_for_mode(resolved, manifest_mode=manifest_mode, reason=reason)
    if not text:
        return
    # Yellow-tint when escalating; cyan-tint when prototyping warning.
    if not no_color:
        color_code = "33" if resolved == "regulated" else "36"
        text = f"\033[{color_code}m{text}\033[0m"
    print_stdout(text)


def _staged_files_from_git(project_root: Path) -> list[str]:
    """Return the list of staged files relative to ``project_root``.

    Best-effort: returns an empty list on any failure (no git, no staged
    changes, etc.). The orchestrator handles empty staged_files gracefully.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "diff", "--name-only", "--cached"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def gate_run(
    cache_aware: Annotated[
        bool,
        typer.Option(
            "--cache-aware/--no-cache-aware",
            help="Use the gate cache (default: ON). Pair with --no-cache to disable.",
        ),
    ] = True,
    no_cache: Annotated[
        bool,
        typer.Option(
            "--no-cache",
            help="Skip cache lookup; equivalent to AIENG_CACHE_DISABLED=1.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Skip lookup AND clear matching cache entries before running fresh.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit the GateFindingsDocument JSON envelope to stdout.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help=(
                "Verbose output: also print per-check inline detail in addition "
                "to the spec-105 D-105-08 compact summary."
            ),
        ),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option(
            "--no-color",
            help=(
                "Strip ANSI color codes from compact output. TTY auto-detect "
                "default ON; honors NO_COLOR / FORCE_COLOR=1 env vars."
            ),
        ),
    ] = False,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help="Check set: 'local' (fast-slice, default) or 'ci' (full).",
            case_sensitive=False,
        ),
    ] = "local",
    produced_by: Annotated[
        str,
        typer.Option(
            "--produced-by",
            help=(
                "Skill caller attribution for the emitted document. "
                "One of 'ai-commit' (default), 'ai-pr', or 'watch-loop'."
            ),
            case_sensitive=False,
        ),
    ] = "ai-commit",
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Run the spec-104 single-pass gate orchestrator.

    Implements D-104-10 override flags::

        --cache-aware (default ON)   --no-cache    --force
        --json                       --mode={local,ci}

    Exit codes::

        0  -- no findings, or only ``severity < medium`` findings.
        1  -- at least one finding with ``severity in {medium, high, critical}``.
        2  -- ``--mode`` rejected (Typer surfaces non-zero on validation error).
    """
    # Validate --mode early so the orchestrator never sees a bogus value.
    legal_modes = {"local", "ci"}
    mode_value = (mode or "").strip().lower()
    if mode_value not in legal_modes:
        sys.stderr.write(
            f"Error: invalid --mode value {mode!r}. "
            f"Legal values are: {sorted(legal_modes)} (use --mode=local or --mode=ci).\n"
        )
        raise typer.Exit(code=2)

    # Validate --produced-by against the GateProducedBy enum so the persisted
    # document never carries an attribution that downstream consumers can't
    # parse. Reject early with the same exit-code convention as --mode.
    legal_producers = {"ai-commit", "ai-pr", "watch-loop"}
    produced_by_value = (produced_by or "").strip().lower()
    if produced_by_value not in legal_producers:
        sys.stderr.write(
            f"Error: invalid --produced-by value {produced_by!r}. "
            f"Legal values are: {sorted(legal_producers)} "
            "(ai-commit, ai-pr, watch-loop).\n"
        )
        raise typer.Exit(code=2)

    root = resolve_project_root(target)

    # Override semantics:
    # - ``--force`` implies cache_disabled=True for the run AND clears entries.
    # - ``--no-cache`` (or AIENG_CACHE_DISABLED=1) disables cache lookup.
    # - default is cache-aware.
    import os as _os

    env_disabled = _os.environ.get("AIENG_CACHE_DISABLED") == "1"
    cache_disabled = bool(no_cache or force or env_disabled or not cache_aware)

    cache_dir = root / ".ai-engineering" / "state" / "gate-cache"
    staged = _staged_files_from_git(root)

    # spec-105 D-105-02 / D-105-03: emit the mode banner BEFORE the run so
    # the user sees the resolved mode in real time. The orchestrator also
    # resolves the mode internally for tier filtering -- this surface call
    # is purely cosmetic / informative.
    _emit_mode_banner(root, no_color=no_color)

    # ``--force`` precedes the orchestrator call so the ``clear_entry``
    # invocations are observable even when ``run_orchestrator_gate`` is
    # patched out by CLI tests.
    if force:
        _force_clear_cache(cache_dir)

    document = run_orchestrator_gate(
        staged,
        mode=mode_value,
        disabled=cache_disabled,
        force=force,
        cache_dir=cache_dir,
        project_root=root,
        produced_by=produced_by_value,
    )

    # Persist the canonical gate-findings.json artefact regardless of the
    # ``--json`` flag — /ai-commit and /ai-pr skill instructions parse the
    # file unconditionally after this command returns. Suppress any IO
    # failure (best-effort persist) so a read-only filesystem doesn't
    # mask the more important findings exit-code signal.
    with contextlib.suppress(OSError):
        _persist_gate_findings(document, root)

    failed = _document_has_failure(document)

    if json_output:
        # Emit the canonical ``GateFindingsDocument`` JSON to stdout. We
        # serialise via ``model_dump_json(by_alias=True)`` so the literal
        # ``"schema": "ai-engineering/gate-findings/v1"`` is preserved.
        payload = document.model_dump_json(by_alias=True)
        sys.stdout.write(payload + "\n")
        sys.stdout.flush()
    else:
        # spec-105 D-105-08: compact output with optional expiring banner +
        # accepted partition. ``format_gate_result_compact`` is a pure helper
        # that consumes the partitioned findings already serialised on the
        # document, so we don't need to re-run the lookup.
        n_findings = len(document.findings)
        n_hits = len(document.cache_hits)
        n_misses = len(document.cache_misses)
        result_label = "FAIL" if failed else "PASS"
        result_header(f"Gate run [{mode_value}]", result_label)
        info(f"findings={n_findings} cache_hits={n_hits} cache_misses={n_misses}")

        # Load the decision-store once for the formatter so the EXPIRING
        # banner can enrich each DEC ID with its rule_id + days remaining.
        decision_store = None
        with contextlib.suppress(Exception):
            decision_store = StateService(root).load_decisions()

        compact = orchestrator_module.format_gate_result_compact(
            list(document.findings),
            list(document.accepted_findings),
            list(document.expiring_soon),
            decision_store=decision_store,
            no_color=no_color,
        )
        print_stdout(compact)

        if verbose:
            for finding in document.findings:
                status_line(
                    "fail" if finding.severity in _FAILURE_SEVERITIES else "ok",
                    f"{finding.check}:{finding.rule_id}",
                    f"{finding.severity.value} {finding.file}:{finding.line}",
                )

    if failed:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# spec-104 D-104-10: gate cache --status / --clear subcommand.
# ---------------------------------------------------------------------------


def _format_size(num_bytes: int) -> str:
    """Return a human-readable size string with B/KB/MB unit."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def _hours_remaining(verified_at: datetime) -> int:
    """Return integer hours remaining in the 24h max-age window.

    Clamped to ``[0, 24]``. Floors fractional remainders so a 12h-old entry
    reports 12 (not 11.97 rounded up to 12 — both are visually right).
    """
    now = datetime.now(UTC)
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)
    elapsed = now - verified_at
    remaining = timedelta(hours=gate_cache_module.MAX_AGE_HOURS) - elapsed
    if remaining < timedelta(0):
        return 0
    hours = int(remaining.total_seconds() // 3600)
    return max(0, min(hours, gate_cache_module.MAX_AGE_HOURS))


def _read_cache_entry_meta(path: Path) -> tuple[datetime | None, int]:
    """Return ``(verified_at, size_bytes)`` for one cache file.

    ``verified_at`` is ``None`` for unparseable entries (size is still
    captured so the operator sees the disk usage).
    """
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, size
    if not isinstance(raw, dict):
        return None, size
    verified_at_str = raw.get("verified_at")
    if not isinstance(verified_at_str, str):
        return None, size
    try:
        verified_at = datetime.fromisoformat(verified_at_str.replace("Z", "+00:00"))
    except ValueError:
        return None, size
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)
    return verified_at, size


def _gate_cache_status(cache_dir: Path) -> None:
    """Print human-readable cache status + total size to stdout."""
    if not cache_dir.exists():
        print_stdout("no cache entries (gate-cache directory absent)")
        return

    entries = sorted(cache_dir.glob("*.json"))
    if not entries:
        print_stdout("no cache entries")
        return

    total_size = 0
    print_stdout("Gate cache entries:")
    for entry_path in entries:
        verified_at, size = _read_cache_entry_meta(entry_path)
        total_size += size
        if verified_at is None:
            print_stdout(f"  {entry_path.stem}  ({_format_size(size)}, unreadable)")
        else:
            remaining = _hours_remaining(verified_at)
            print_stdout(f"  {entry_path.stem}  ({_format_size(size)}, {remaining}h remaining)")
    print_stdout(f"Total: {len(entries)} entries, {_format_size(total_size)}")


def _gate_cache_clear(cache_dir: Path, *, assume_yes: bool) -> None:
    """Wipe all ``*.json`` under ``cache_dir``. Sibling files untouched.

    Without ``--yes`` prompts via ``typer.confirm(..., abort=True)``: a "n"
    response raises ``typer.Abort`` which Typer converts to exit code 1.
    """
    if not cache_dir.exists():
        # Idempotent no-op — empty cache is not an error.
        print_stdout("no cache entries to clear")
        return

    entries = list(cache_dir.glob("*.json"))
    if not entries:
        print_stdout("no cache entries to clear")
        return

    if not assume_yes:
        # ``abort=True`` raises ``typer.Abort`` on decline → exit 1, no wipe.
        typer.confirm(
            f"Delete all {len(entries)} cache entries in {cache_dir}?",
            abort=True,
        )

    deleted = 0
    for entry_path in entries:
        try:
            entry_path.unlink()
            deleted += 1
        except FileNotFoundError:
            continue
    print_stdout(f"cleared {deleted} cache entries from {cache_dir}")


def gate_cache(
    status: Annotated[
        bool,
        typer.Option("--status", help="List cache entries and total size."),
    ] = False,
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Delete all cache entries (with confirmation)."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Skip the interactive confirmation for --clear."),
    ] = False,
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Inspect or clear the gate cache (D-104-10)."""
    if not status and not clear:
        sys.stderr.write(
            "Error: gate cache requires --status or --clear (use --help for details).\n"
        )
        raise typer.Exit(code=2)
    if status and clear:
        sys.stderr.write("Error: --status and --clear are mutually exclusive (pick one).\n")
        raise typer.Exit(code=2)

    root = resolve_project_root(target)
    cache_dir = root / ".ai-engineering" / "state" / "gate-cache"

    if status:
        _gate_cache_status(cache_dir)
    else:
        _gate_cache_clear(cache_dir, assume_yes=yes)
