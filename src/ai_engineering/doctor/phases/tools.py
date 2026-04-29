"""Doctor phase: tool availability and venv health validation (spec-101).

The phase is a free-function module (matches ``state/service.py:66/86``
convention surfaced in phase-0-notes finding #3). It provides four checks
and a fix entry point:

* ``tools-required`` -- manifest-driven; reads
  :func:`ai_engineering.state.manifest.load_required_tools` for the union
  of baseline + per-stack tools and probes each via
  :func:`ai_engineering.installer.user_scope_install.run_verify` (the
  offline-safe, D-101-04-compliant verify wrapper). The legacy hardcoded
  ``_REQUIRED_TOOLS = ["ruff", ...]`` literal is removed (D-101-08).
* ``tools-vcs`` -- VCS-tool probe (gh / az). Unchanged from the prior
  doctor phase; ``installer.tools.provider_required_tools`` is no longer
  consulted here -- the VCS provider name flows directly from
  ``InstallState``.
* ``venv-health`` -- branches on ``python_env.mode`` (D-101-12). In
  ``uv-tool`` mode the probe returns OK / not-applicable so worktrees
  are not nudged toward a redundant ``uv venv`` re-install. In ``venv``
  mode the legacy probe runs unchanged. ``shared-parent`` mode resolves
  the venv root from the git common-dir and probes that instead.
* ``venv-python`` -- python version cross-check; gated on
  ``python_env.mode != uv-tool`` so the same uv-tool skip applies.

The ``fix`` entry point dispatches per-tool through
:data:`ai_engineering.installer.tool_registry.TOOL_REGISTRY` -- the same
registry that drives the installer phase. This is D-101-08's "one
mechanism path, two callers" guarantee.
"""

from __future__ import annotations

import logging
import platform as platform_module
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.detector.readiness import is_tool_available
from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.installer.tool_registry import TOOL_REGISTRY
from ai_engineering.installer.tools import can_auto_install_tool, manual_install_step
from ai_engineering.installer.user_scope_install import (
    _check_simulate_fail,
    _check_simulate_install_ok,
    capture_os_release,
    run_verify,
)
from ai_engineering.state.manifest import load_python_env_mode, load_required_tools
from ai_engineering.state.models import (
    PythonEnvMode,
    ToolInstallRecord,
    ToolInstallState,
    ToolScope,
    ToolSpec,
)
from ai_engineering.state.service import save_install_state

logger = logging.getLogger(__name__)

__all__ = (
    "check",
    "fix",
)


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------


_VCS_TOOL_MAP: dict[str, str] = {
    "github": "gh",
    "azure_devops": "az",
}


def _current_os_key() -> str:
    """Return the registry per-OS key for the current platform.

    Matches ``installer/phases/tools.py::_current_os_key`` so the doctor
    phase resolves mechanisms via the same lookup as the installer.
    """
    system_name = (platform_module.system() or "").lower()
    if system_name.startswith("win"):
        return "win32"
    if system_name == "darwin":
        return "darwin"
    return "linux"


# ---------------------------------------------------------------------------
# Stack resolution -- the manifest's providers.stacks is the source of truth
# ---------------------------------------------------------------------------


def _resolve_stacks(ctx: DoctorContext) -> list[str]:
    """Return the project's declared stacks from the manifest.

    Re-reads manifest at call time (rather than relying on
    ``ctx.manifest_config``) so unit tests that drop a manifest into a
    tmp project root pick up the change without rebuilding the context.
    Falls back to the cached manifest_config when the file read fails.
    """
    try:
        config = load_manifest_config(ctx.target)
    except Exception:
        config = ctx.manifest_config
    if config is None:
        return ["python"]
    stacks = list(getattr(getattr(config, "providers", None), "stacks", []) or [])
    return stacks or ["python"]


# ---------------------------------------------------------------------------
# tools-required (manifest-driven, D-101-08)
# ---------------------------------------------------------------------------


# Baseline tools probed when the manifest is absent. Mirrors the canonical
# baseline in ``manifest.yml.required_tools.baseline`` so a fresh checkout
# without ``.ai-engineering/manifest.yml`` still gets actionable diagnostics.
_BASELINE_PATH_TOOLS: tuple[str, ...] = ("gitleaks", "ruff", "ty", "pip-audit")


def _probe_one_required_tool(tool: ToolSpec) -> bool:
    """Return True when *tool* probes as available via PATH + verify.

    Mirrors the per-tool decision tree previously embedded in
    :func:`_check_required_tools`. Extracting the helper drops the parent
    cyclomatic complexity below the spec-101 threshold (≤10) and gives
    tests a finer-grained patch surface if needed.
    """
    if tool.scope == ToolScope.PROJECT_LOCAL:
        # D-101-15: project_local tools resolve via launcher, not PATH.
        # The installer skips them; the doctor mirrors that decision.
        return True

    registry_entry = TOOL_REGISTRY.get(tool.name)
    if registry_entry is None:
        return False
    if not is_tool_available(tool.name):
        return False
    try:
        verify_result = run_verify(registry_entry)
    except Exception:
        # Fail closed: any verify-time exception counts as missing so
        # the operator gets a fix hint rather than silent success.
        return False
    return bool(getattr(verify_result, "passed", False))


def _externally_installed_record(*, version: str | None) -> ToolInstallRecord:
    """Build a :class:`ToolInstallRecord` for spec-113 G-12 external recovery.

    spec-113 G-12 / D-113-10: when the doctor finds a tool present on PATH
    that the install state had recorded as ``failed_needs_manual``, the
    record is updated to ``INSTALLED`` with ``mechanism="external"`` so
    subsequent runs do NOT re-attempt the failed download path.
    """
    return ToolInstallRecord(
        state=ToolInstallState.INSTALLED,
        mechanism="external",
        version=version,
        verified_at=datetime.now(tz=UTC),
        os_release=capture_os_release() or None,
    )


def _recover_externally_installed_tools(
    ctx: DoctorContext,
    recovered: list[str],
) -> None:
    """Persist install-state record updates for tools recovered from PATH.

    Only fires when *recovered* is non-empty. Failures to save are logged
    but never raised -- the doctor must remain advisory.
    """
    if not recovered:
        return
    state = ctx.install_state
    if state is None:
        return
    state_dir = ctx.target / ".ai-engineering" / "state"
    try:
        save_install_state(state_dir, state)
    except OSError as exc:  # pragma: no cover - defensive fail-open
        logger.debug("doctor: could not persist external-recovery records: %s", exc)


def _probe_with_external_recovery(
    tool: ToolSpec,
    install_state: object | None,
) -> tuple[bool, bool]:
    """Probe *tool* and surface whether external recovery happened (G-12).

    Returns ``(probe_ok, recovered)``:

    * ``probe_ok``: True when ``is_tool_available`` + ``run_verify`` both
      pass, mirroring :func:`_probe_one_required_tool`.
    * ``recovered``: True when the install-state record had been
      ``failed_needs_manual`` AND the probe now passes, which means the
      operator installed the tool externally (e.g. ``apk add jq``). The
      caller persists the upgraded record via
      :func:`_recover_externally_installed_tools`.
    """
    probe_ok = _probe_one_required_tool(tool)
    if not probe_ok or install_state is None:
        return probe_ok, False

    state_dict = getattr(install_state, "required_tools_state", None)
    if not isinstance(state_dict, dict):
        return probe_ok, False

    record = state_dict.get(tool.name)
    if record is None:
        return probe_ok, False

    record_state = getattr(record, "state", None)
    if record_state != ToolInstallState.FAILED_NEEDS_MANUAL:
        return probe_ok, False

    # External recovery path: the record was failed_needs_manual but the
    # tool now verifies. Update in place; caller persists.
    state_dict[tool.name] = _externally_installed_record(version=None)
    return probe_ok, True


def _check_required_tools(ctx: DoctorContext) -> CheckResult:
    """Verify every required tool via the spec-101 offline-safe probe.

    Reads :func:`load_required_tools` for the manifest's resolved stacks,
    skips ``project_local`` tools (D-101-15: those resolve through their
    language launcher, not via PATH), and runs ``run_verify`` against the
    registry's verify block for each remaining tool. A quick
    :func:`is_tool_available` PATH probe runs first as a fast pre-check --
    when the binary is absent from PATH the probe short-circuits, the tool
    is recorded missing, and the heavier verify subprocess is skipped.

    When the manifest is absent (``load_required_tools`` returns empty),
    the helper falls back to :data:`_BASELINE_PATH_TOOLS` so the doctor
    still surfaces actionable diagnostics on a fresh checkout.
    """
    stacks = _resolve_stacks(ctx)
    try:
        load_result = load_required_tools(stacks, root=ctx.target)
    except Exception as exc:
        return CheckResult(
            name="tools-required",
            status=CheckStatus.WARN,
            message=(
                f"could not load required_tools from manifest: {exc}; "
                "run 'ai-eng doctor --fix --phase tools' to repair"
            ),
            fixable=True,
        )

    missing: list[str] = []
    recovered: list[str] = []
    seen_user_global = 0
    for tool in load_result:
        if tool.scope == ToolScope.PROJECT_LOCAL:
            continue
        seen_user_global += 1
        probe_ok, was_recovered = _probe_with_external_recovery(tool, ctx.install_state)
        if not probe_ok:
            missing.append(tool.name)
            continue
        if was_recovered:
            recovered.append(tool.name)

    # Persist external-recovery state updates back to install-state.json so
    # subsequent doctor runs see the upgraded record.
    _recover_externally_installed_tools(ctx, recovered)

    if seen_user_global == 0:
        # No manifest yet (fresh checkout): probe the canonical baseline so
        # ``ai-eng doctor`` still gives the user something to act on.
        missing.extend(name for name in _BASELINE_PATH_TOOLS if not is_tool_available(name))

    if missing:
        return CheckResult(
            name="tools-required",
            status=CheckStatus.WARN,
            message=(
                f"missing tools: {', '.join(missing)}; "
                "run 'ai-eng doctor --fix --phase tools' to install"
            ),
            fixable=True,
        )

    return CheckResult(
        name="tools-required",
        status=CheckStatus.OK,
        message="all required tools available",
    )


# ---------------------------------------------------------------------------
# tools-vcs (unchanged from spec-071; preserved verbatim)
# ---------------------------------------------------------------------------


def _check_tools_vcs(ctx: DoctorContext) -> CheckResult:
    """Check VCS-specific tool based on install state provider."""
    if ctx.install_state is None:
        return CheckResult(
            name="tools-vcs",
            status=CheckStatus.OK,
            message="no install state; skipping VCS tool check",
        )

    vcs_provider = ctx.install_state.vcs_provider
    if vcs_provider is None:
        return CheckResult(
            name="tools-vcs",
            status=CheckStatus.OK,
            message="no VCS provider configured; skipping",
        )

    tool = _VCS_TOOL_MAP.get(vcs_provider)
    if tool is None:
        return CheckResult(
            name="tools-vcs",
            status=CheckStatus.OK,
            message=f"unknown VCS provider '{vcs_provider}'; skipping",
        )

    if not is_tool_available(tool):
        return CheckResult(
            name="tools-vcs",
            status=CheckStatus.WARN,
            message=f"VCS tool '{tool}' not found (provider: {vcs_provider})",
        )

    return CheckResult(
        name="tools-vcs",
        status=CheckStatus.OK,
        message=f"VCS tool '{tool}' available",
    )


# ---------------------------------------------------------------------------
# pyvenv.cfg parser (preserved from spec-071)
# ---------------------------------------------------------------------------


def _parse_pyvenv_cfg(cfg_path: Path) -> dict[str, str]:
    """Parse a pyvenv.cfg file into key-value pairs."""
    result: dict[str, str] = {}
    if not cfg_path.is_file():
        return result
    try:
        for raw_line in cfg_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if "=" in line:
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()
    except OSError:
        pass
    return result


def _resolve_shared_parent_venv(ctx: DoctorContext) -> Path | None:
    """Resolve the shared-parent venv root (D-101-12).

    Returns ``$(git rev-parse --git-common-dir)/../.venv`` when the project
    is inside a git checkout, else ``None``. Tests patch this helper to
    inject a synthetic shared-parent path.
    """
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(ctx.target),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    common_dir = (proc.stdout or "").strip()
    if not common_dir:
        return None
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = (ctx.target / common_path).resolve()
    return common_path.parent / ".venv"


# ---------------------------------------------------------------------------
# venv-health (D-101-12 mode-aware)
# ---------------------------------------------------------------------------


def _venv_health_message_uv_tool() -> CheckResult:
    """Return the canonical 'not applicable' result for uv-tool mode."""
    return CheckResult(
        name="venv-health",
        status=CheckStatus.OK,
        message=(
            "venv probe not applicable in python_env.mode=uv-tool "
            "(skipped by D-101-12; tools resolve via ~/.local/share/uv/tools/)"
        ),
        fixable=False,
    )


def _check_venv_health_for_path(venv_path: Path) -> CheckResult:
    """Run the legacy venv-health probe against a specific ``.venv`` path.

    Extracted so ``mode=venv`` and ``mode=shared-parent`` can share the
    same probe logic against different roots.
    """
    cfg_path = venv_path / "pyvenv.cfg"
    if not cfg_path.is_file():
        return CheckResult(
            name="venv-health",
            status=CheckStatus.WARN,
            message=f"no {cfg_path} found; virtual environment may not exist",
            fixable=True,
        )

    cfg = _parse_pyvenv_cfg(cfg_path)
    home = cfg.get("home")
    if home is None:
        return CheckResult(
            name="venv-health",
            status=CheckStatus.FAIL,
            message="pyvenv.cfg missing 'home' key",
            fixable=True,
        )

    if not Path(home).is_dir():
        return CheckResult(
            name="venv-health",
            status=CheckStatus.FAIL,
            message=f"pyvenv.cfg home path does not exist: {home}",
            fixable=True,
        )

    return CheckResult(
        name="venv-health",
        status=CheckStatus.OK,
        message="virtual environment healthy",
    )


def _check_venv_health(ctx: DoctorContext, mode: PythonEnvMode) -> CheckResult:
    """Branch on python_env.mode per D-101-12.

    * ``uv-tool``      -> not applicable (skip).
    * ``venv``         -> probe ``ctx.target/.venv``.
    * ``shared-parent``-> probe the resolved shared-parent venv.
    """
    if mode == PythonEnvMode.UV_TOOL:
        return _venv_health_message_uv_tool()
    if mode == PythonEnvMode.SHARED_PARENT:
        venv = _resolve_shared_parent_venv(ctx)
        if venv is None:
            return CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message=(
                    "python_env.mode=shared-parent set but no git common-dir "
                    "found; run 'git init' or change mode to 'venv'"
                ),
                fixable=False,
            )
        return _check_venv_health_for_path(venv)
    # mode == venv
    return _check_venv_health_for_path(ctx.target / ".venv")


# ---------------------------------------------------------------------------
# venv-python (preserved; gated on mode != uv-tool)
# ---------------------------------------------------------------------------


def _check_venv_python(ctx: DoctorContext, mode: PythonEnvMode) -> CheckResult:
    """Cross-check venv Python version against ``.python-version``.

    Skipped when ``python_env.mode=uv-tool`` -- there is no project venv
    to probe in that mode. Returns OK with a not-applicable message.
    """
    if mode == PythonEnvMode.UV_TOOL:
        return CheckResult(
            name="venv-python",
            status=CheckStatus.OK,
            message="venv-python probe not applicable in python_env.mode=uv-tool",
        )

    pyver_path = ctx.target / ".python-version"
    if not pyver_path.is_file():
        return CheckResult(
            name="venv-python",
            status=CheckStatus.OK,
            message="no .python-version file; skipping version check",
        )

    try:
        expected = pyver_path.read_text(encoding="utf-8").strip()
    except OSError:
        return CheckResult(
            name="venv-python",
            status=CheckStatus.WARN,
            message="could not read .python-version",
        )

    cfg_path = ctx.target / ".venv" / "pyvenv.cfg"
    cfg = _parse_pyvenv_cfg(cfg_path)
    version = cfg.get("version")

    if version is None:
        return CheckResult(
            name="venv-python",
            status=CheckStatus.WARN,
            message="pyvenv.cfg missing 'version' key; cannot verify Python version",
        )

    if not version.startswith(expected):
        return CheckResult(
            name="venv-python",
            status=CheckStatus.WARN,
            message=f"venv Python {version} does not match .python-version {expected}",
        )

    return CheckResult(
        name="venv-python",
        status=CheckStatus.OK,
        message=f"venv Python {version} matches .python-version",
    )


# ---------------------------------------------------------------------------
# Public API: check / fix
# ---------------------------------------------------------------------------


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all four tools-phase checks in canonical order."""
    mode = load_python_env_mode(ctx.target)
    return [
        _check_required_tools(ctx),
        _check_tools_vcs(ctx),
        _check_venv_health(ctx, mode),
        _check_venv_python(ctx, mode),
    ]


def fix(
    ctx: DoctorContext,
    failed: list[CheckResult],
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """Attempt to repair fixable failures (D-101-08 mechanism dispatch).

    Fixable:
    * ``tools-required`` -- dispatch the registry's first per-OS mechanism
      for each missing tool.
    * ``venv-health``    -- recreate ``.venv`` via ``uv venv`` (only when
      mode is venv / shared-parent).
    """
    results: list[CheckResult] = []
    for cr in failed:
        if cr.name == "tools-required":
            results.append(_fix_tools_required(ctx, cr, dry_run=dry_run))
        elif cr.name == "venv-health":
            results.append(_fix_venv_health(ctx, cr, dry_run=dry_run))
        else:
            results.append(cr)
    return results


def _missing_tool_specs(ctx: DoctorContext) -> list[ToolSpec]:
    """Return the tool specs whose verify probe currently fails.

    When the manifest is absent (loader returns an empty list), falls back
    to synthesising :class:`ToolSpec` placeholders for
    :data:`_BASELINE_PATH_TOOLS` whose PATH probe fails. This mirrors the
    fallback in :func:`_check_required_tools` so the fix path has
    something to act on for fresh checkouts.
    """
    stacks = _resolve_stacks(ctx)
    try:
        load_result = load_required_tools(stacks, root=ctx.target)
    except Exception:
        return _baseline_missing_specs()

    missing: list[ToolSpec] = []
    seen_tools = 0
    for tool in load_result:
        if tool.scope == ToolScope.PROJECT_LOCAL:
            # Mechanism dispatch on project_local tools is delegated to the
            # language's package manager; the framework does not install
            # them. We still add them to the missing list so the registry
            # can decide whether a project_local mechanism (NpmDevMechanism)
            # is wired -- some test fixtures register them deliberately.
            seen_tools += 1
            registry_entry = TOOL_REGISTRY.get(tool.name)
            if registry_entry is not None:
                missing.append(tool)
            continue
        seen_tools += 1
        registry_entry = TOOL_REGISTRY.get(tool.name)
        if registry_entry is None:
            missing.append(tool)
            continue
        if not is_tool_available(tool.name):
            missing.append(tool)
            continue
        try:
            verify_result = run_verify(registry_entry)
        except Exception:
            missing.append(tool)
            continue
        if not getattr(verify_result, "passed", False):
            missing.append(tool)

    if seen_tools == 0:
        # No manifest yet: probe the canonical baseline.
        return _baseline_missing_specs()

    return missing


def _baseline_missing_specs() -> list[ToolSpec]:
    """Build :class:`ToolSpec` placeholders for absent baseline tools."""
    out: list[ToolSpec] = []
    for name in _BASELINE_PATH_TOOLS:
        if not is_tool_available(name):
            out.append(ToolSpec(name=name, scope=ToolScope.USER_GLOBAL))
    return out


def _attempt_install_one(
    tool_name: str,
    *,
    os_key: str,
) -> str:
    """Try installing one tool; return the outcome bucket name.

    Outcome buckets:
      * ``"manual"`` -- registry has no mechanism for this OS, OR the
        legacy ``can_auto_install_tool`` returns False (test seam).
      * ``"installed"`` -- mechanism's ``install()`` returned a non-failed
        result.
      * ``"failed"`` -- mechanism raised or returned ``failed=True``.

    Extracting this helper drops :func:`_fix_tools_required` complexity
    below the spec-101 cyclomatic threshold (≤10).
    """
    # spec-113: when AIENG_TEST=1 the simulate hooks are the load-bearing
    # contract for the test surface — they must run BEFORE the legacy
    # capability gate so a per-OS exclusion (e.g. semgrep on Windows) or a
    # registry without WINGET id (e.g. jq) does not divert the synthetic
    # install attempt to the ``manual`` bucket. The helpers themselves
    # gate on AIENG_TEST and refuse on production builds, so calling them
    # unconditionally here remains safe.
    simulated_fail = _check_simulate_fail(tool_name)
    if simulated_fail is not None:
        return "failed"
    simulated_ok = _check_simulate_install_ok(tool_name)
    if simulated_ok is not None:
        return "installed"

    # Legacy capability check -- tests patch this seam to drive the
    # manual-step path without spinning up a real subprocess.
    if not can_auto_install_tool(tool_name):
        return "manual"

    registry_entry = TOOL_REGISTRY.get(tool_name)
    if registry_entry is None:
        return "manual"
    mechanisms = registry_entry.get(os_key) or []
    if not mechanisms:
        return "manual"

    mechanism = mechanisms[0]
    try:
        outcome = mechanism.install()
    except Exception:
        return "failed"
    return "failed" if getattr(outcome, "failed", False) else "installed"


def _build_fix_warn_message(
    *,
    repaired: list[str],
    failed_to_install: list[str],
    manual: list[str],
    fallback: str,
) -> str:
    """Assemble the WARN message for partially-failed fix attempts."""
    parts: list[str] = []
    if repaired:
        parts.append(f"installed: {', '.join(repaired)}")
    if failed_to_install:
        parts.append(f"install failed: {', '.join(failed_to_install)}")
    if manual:
        manual_steps = "; ".join(manual_install_step(name) for name in manual)
        parts.append(f"manual follow-up required: {', '.join(manual)} ({manual_steps})")
    return "; ".join(parts) if parts else fallback


def _fix_tools_required(
    ctx: DoctorContext,
    cr: CheckResult,
    *,
    dry_run: bool = False,
) -> CheckResult:
    """Dispatch the first registry mechanism for each missing tool (D-101-08).

    Decomposed (T-Wave23) into :func:`_attempt_install_one` + outcome
    aggregation so the cyclomatic complexity stays ≤10. Honours the
    legacy capability seams (``can_auto_install_tool``,
    ``manual_install_step``) so the doctor's existing test contract
    keeps driving the auto-install / manual-step branches.
    """
    missing = _missing_tool_specs(ctx)
    if not missing:
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FIXED,
            message="all tools now available",
        )

    if dry_run:
        names = ", ".join(t.name for t in missing)
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FIXED,
            message=f"would attempt to install missing tools: {names}",
        )

    os_key = _current_os_key()
    repaired: list[str] = []
    failed_to_install: list[str] = []
    manual: list[str] = []

    for tool in missing:
        bucket = _attempt_install_one(tool.name, os_key=os_key)
        if bucket == "installed":
            repaired.append(tool.name)
        elif bucket == "failed":
            failed_to_install.append(tool.name)
        else:  # bucket == "manual"
            manual.append(tool.name)

    if failed_to_install or manual:
        return CheckResult(
            name=cr.name,
            status=CheckStatus.WARN,
            message=_build_fix_warn_message(
                repaired=repaired,
                failed_to_install=failed_to_install,
                manual=manual,
                fallback=cr.message,
            ),
            fixable=True,
        )

    return CheckResult(
        name=cr.name,
        status=CheckStatus.FIXED,
        message=(f"installed: {', '.join(repaired)}" if repaired else "all tools now available"),
    )


def _fix_venv_health(
    ctx: DoctorContext,
    cr: CheckResult,
    *,
    dry_run: bool = False,
) -> CheckResult:
    """Recreate the project venv via ``uv venv`` (mode=venv only)."""
    mode = load_python_env_mode(ctx.target)
    if mode == PythonEnvMode.UV_TOOL:
        # Should not happen -- the check returns OK in uv-tool mode and is
        # never marked fixable. Defensive return so a stray failed entry
        # doesn't trigger a redundant uv venv invocation.
        return CheckResult(
            name=cr.name,
            status=CheckStatus.OK,
            message="venv repair not applicable in python_env.mode=uv-tool",
        )

    if dry_run:
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FIXED,
            message="would recreate .venv via uv venv",
        )

    cmd: list[str] = ["uv", "venv", ".venv"]
    pyver_path = ctx.target / ".python-version"
    if pyver_path.is_file():
        try:
            version = pyver_path.read_text(encoding="utf-8").strip()
            if version:
                cmd = ["uv", "venv", "--python", version, ".venv"]
        except OSError:
            pass

    try:
        subprocess.run(
            cmd,
            cwd=str(ctx.target),
            check=True,
            capture_output=True,
            timeout=120,
        )
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FIXED,
            message="recreated .venv via uv venv",
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FAIL,
            message=f"failed to recreate .venv: {exc}",
            fixable=True,
        )
