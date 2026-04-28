"""Tools phase -- install required CLI tools per spec-101 (D-101-01, D-101-03).

The phase:

1. Calls :func:`ai_engineering.state.manifest.load_required_tools` with the
   resolved stacks from :class:`InstallContext` so the baseline + per-stack
   tool union is enumerated declaratively.
2. For each ``ToolSpec`` returned, looks up the per-OS mechanism list in
   :data:`ai_engineering.installer.tool_registry.TOOL_REGISTRY` and dispatches
   the first mechanism's ``install()`` method.
3. Records the per-tool outcome into ``InstallState.required_tools_state``
   as a :class:`ToolInstallRecord` (state ``installed`` on success,
   ``failed_needs_manual`` on mechanism failure).
4. Aggregates :class:`PhaseResult.failed` whenever ANY required tool fails
   so the EXIT 80 surface (cli_commands/_exit_codes.py) can route correctly.

The legacy ``provider_required_tools`` / ``ensure_tool`` shape is removed --
those helpers were the bug that scoped only ``gh`` / ``az`` and ignored
stacks. Auth check for VCS tools still happens later in
``installer.service._run_operational_phases``; this phase is the spec-101
canonical install surface.

Idempotence (D-101-07, T-2.16)
------------------------------
Before attempting an install, the phase consults the seed
``InstallState.required_tools_state`` for a previous record. The skip
predicate is:

    skip = (record.state == installed)
       AND (run_verify(spec).passed)
       AND (record.os_release == capture_os_release())
       AND (record.python_env_mode_recorded == load_python_env_mode())

Any mismatch -> attempt re-install. ``InstallContext.force = True`` (set
by ``ai-eng install --force``) bypasses the predicate and re-installs
unconditionally. Tools whose previous record is ``failed_needs_manual``
are always retried.
"""

from __future__ import annotations

import logging
import platform
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ai_engineering.installer.tool_registry import TOOL_REGISTRY
from ai_engineering.installer.user_scope_install import (
    _check_simulate_fail,
    _check_simulate_install_ok,
    capture_os_release,
    run_verify,
)
from ai_engineering.state.manifest import load_python_env_mode, load_required_tools
from ai_engineering.state.models import (
    InstallState,
    PythonEnvMode,
    ToolInstallRecord,
    ToolInstallState,
    ToolScope,
    ToolSpec,
)
from ai_engineering.state.service import save_install_state

from . import (
    InstallContext,
    PhasePlan,
    PhaseResult,
    PhaseVerdict,
    PlannedAction,
)

if TYPE_CHECKING:  # pragma: no cover - typing-only
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OS detection -- registry uses ``darwin`` / ``linux`` / ``win32`` keys.
# ---------------------------------------------------------------------------


def _current_os_key() -> str:
    """Return the registry's per-OS key for the current platform.

    Uses :func:`platform.system` (proper-case ``Darwin`` / ``Linux`` /
    ``Windows``) rather than ``sys.platform`` so tests can mock a single
    seam (``platform.system``) and have the result observed by both the
    loader (``state.manifest._normalise_os``) and this phase consistently.
    """
    system_name = (platform.system() or "").lower()
    if system_name.startswith("win"):
        return "win32"
    if system_name == "darwin":
        return "darwin"
    return "linux"


# ---------------------------------------------------------------------------
# spec-101 D-101-01 carve-out: project_local install command per stack
# ---------------------------------------------------------------------------
#
# When a stack contains ONLY ``scope: project_local`` tools, the framework
# performs no install (npm/composer/maven own that). Each stack maps to its
# native install command + the bootstrap file (if any) the user must create
# before that command can run. Per R-3 the typescript/javascript carve-out
# also requires ``package.json`` -- without it, ``npm install`` itself fails,
# so we surface EXIT 80 with the ``npm init -y`` remediation.

_PROJECT_LOCAL_INSTALL_COMMANDS: dict[str, str] = {
    "typescript": "npm install",
    "javascript": "npm install",
    "php": "composer install",
    "java": "./mvnw install (or ./gradlew assemble)",
    "kotlin": "./gradlew assemble",
    "cpp": "cmake -B build",
}


# Stacks whose project_local install path requires ``package.json`` to exist
# at the project root. R-3: missing package.json on a typescript-only project
# is a hard EXIT 80 with the ``npm init -y`` remediation message.
_NODE_STACKS_REQUIRING_PACKAGE_JSON: frozenset[str] = frozenset({"typescript", "javascript"})


# Canonical inverse map: project_local tool name -> originating stack key.
# Kept in sync with ``manifest.yml.required_tools`` so the phase can group
# recorded ``NOT_INSTALLED_PROJECT_LOCAL`` tools back to their stack without
# re-reading the manifest. The stack_runner module carries an analogous map
# for the gate-dispatch path -- both must stay aligned with the manifest.
_CANONICAL_PROJECT_LOCAL_STACK: dict[str, str] = {
    # typescript / javascript share several project_local tools; pick the
    # stack whose presence in ``context.stacks`` matters. We bias toward
    # typescript because typescript projects always also satisfy the
    # javascript invariants. The grouping helper filters by
    # ``context.stacks`` so a javascript-only project still reports under
    # ``javascript``.
    "prettier": "typescript",
    "eslint": "typescript",
    "tsc": "typescript",
    "vitest": "typescript",
    # PHP project_local tools (composer-installed via vendor/bin/).
    "phpstan": "php",
    "php-cs-fixer": "php",
    # Java project_local tools (mvn/gradle-installed).
    "checkstyle": "java",
    "google-java-format": "java",
    # Kotlin project_local tools (gradle-installed).
    "ktlint": "kotlin",
    # CPP project_local tools (cmake-built).
    "clang-tidy": "cpp",
    "clang-format": "cpp",
    "cppcheck": "cpp",
}


# Sibling-stack reroute map. When a project_local tool's canonical stack is
# not in ``context.stacks`` but a listed sibling is, the helper reroutes the
# tool to the sibling. Used so a javascript-only project still gets the
# correct ``javascript`` info message instead of the canonical typescript.
_PROJECT_LOCAL_STACK_SIBLINGS: dict[str, str] = {
    "typescript": "javascript",
    "javascript": "typescript",
}


def _build_record(
    *,
    state: ToolInstallState,
    mechanism: str,
    version: str | None = None,
    os_release: str | None = None,
) -> ToolInstallRecord:
    """Build a :class:`ToolInstallRecord` stamped with current UTC time.

    ``os_release`` defaults to :func:`capture_os_release` -- the major.minor
    capture defined in T-2.12. Callers pass an explicit value to align the
    record with the value they used for the skip-predicate check.
    """
    return ToolInstallRecord(
        state=state,
        mechanism=mechanism,
        version=version,
        verified_at=datetime.now(tz=UTC),
        os_release=os_release if os_release is not None else capture_os_release(),
    )


def _ensure_install_state(context: InstallContext) -> InstallState:
    """Return ``context.existing_state`` or initialise a fresh state."""
    if context.existing_state is None:
        context.existing_state = InstallState()
    return context.existing_state


# ---------------------------------------------------------------------------
# ToolsPhase
# ---------------------------------------------------------------------------


class ToolsPhase:
    """Install required CLI tools (baseline + per-stack) per spec-101.

    spec-109 D-109-03: ``critical = False`` -- a tool install failure is
    recoverable via :func:`installer.auto_remediate.auto_remediate_after_install`
    and does not block subsequent phases (notably ``HooksPhase``). Hooks
    install does NOT depend on tools at install time; the tools are needed
    only at hook *execution* time, which is post-install.
    """

    @property
    def name(self) -> str:
        return "tools"

    @property
    def critical(self) -> bool:
        # spec-109 D-109-03: non-critical so a single missing tool does not
        # cascade-skip HooksPhase. Auto-remediate covers the recovery path.
        return False

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------

    def plan(self, context: InstallContext) -> PhasePlan:
        """Enumerate every required tool the phase will attempt to install."""
        actions: list[PlannedAction] = []
        load_result = load_required_tools(context.stacks, root=context.target)

        for tool in load_result:
            actions.append(
                PlannedAction(
                    action_type="skip",
                    source="",
                    destination="",
                    rationale=f"Install tool: {tool.name}",
                )
            )

        # Stack-level skip markers (e.g. swift on linux) surface as warnings
        # in the plan rationale so dry-runs show what was filtered out.
        for skip in getattr(load_result, "skipped_stacks", []):
            actions.append(
                PlannedAction(
                    action_type="skip",
                    source="",
                    destination="",
                    rationale=f"Skip stack {skip.stack!r}: {skip.reason}",
                )
            )

        return PhasePlan(phase_name=self.name, actions=actions)

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        """Install each required tool and record per-tool outcomes."""
        result = PhaseResult(phase_name=self.name)
        install_state = _ensure_install_state(context)
        load_result = load_required_tools(context.stacks, root=context.target)
        os_key = _current_os_key()

        # Idempotence inputs (D-101-07, T-2.16):
        # * ``current_os_release`` -- captured at major.minor granularity.
        # * ``current_python_env_mode`` -- read from manifest; defaults to
        #   ``UV_TOOL`` when manifest is absent.
        # * ``force`` -- pulled off the context (CLI ``--force`` plumbing
        #   sets it; missing attribute defaults to False).
        current_os_release = capture_os_release()
        current_python_env_mode = load_python_env_mode(context.target)
        force = bool(getattr(context, "force", False))

        # Stamp the python_env_mode_recorded so subsequent runs can detect
        # mode changes (D-101-12). Updated unconditionally each run -- the
        # skip predicate compares the recorded value BEFORE this stamp.
        new_mode_recorded = current_python_env_mode

        for tool in load_result:
            self._install_one(
                tool,
                os_key=os_key,
                result=result,
                state=install_state,
                current_os_release=current_os_release,
                current_python_env_mode=current_python_env_mode,
                force=force,
                tool_spec=TOOL_REGISTRY.get(tool.name) or {},
            )

        # spec-101 T-2.28: project_local-only stacks. When at least one tool
        # was project_local-skipped above, emit a per-stack info message
        # naming the language-native install command. For node-based stacks
        # (typescript/javascript) we also enforce R-3: package.json MUST
        # exist or EXIT 80 with ``npm init -y`` remediation.
        self._emit_project_local_info(
            context=context,
            install_state=install_state,
            result=result,
            current_os_release=current_os_release,
        )

        install_state.python_env_mode_recorded = new_mode_recorded

        # Stack-level skips: enumerate every tool the skipped stack WOULD
        # have contributed and record per-tool ``skipped_platform_unsupported_stack``
        # entries (D-101-13). The loader's ``StackSkip.tool_names`` exposes
        # the original tool list so the installer doesn't re-read the
        # manifest here.
        for skip in getattr(load_result, "skipped_stacks", []):
            result.warnings.append(f"stack {skip.stack!r} skipped on {os_key}: {skip.reason}")
            for tool_name in skip.tool_names:
                if tool_name in install_state.required_tools_state:
                    # Already recorded -- don't double-count if a tool also
                    # appeared in the resolved tool list (defensive).
                    continue
                install_state.required_tools_state[tool_name] = _build_record(
                    state=ToolInstallState.SKIPPED_PLATFORM_UNSUPPORTED_STACK,
                    mechanism="none",
                )
                result.skipped.append(f"tool:{tool_name}:stack-skipped:{skip.stack}")

        # Persist mutated install-state so doctor + downstream consumers see
        # the per-tool records the phase produced. Without this write the
        # records live only in memory and never reach install-state.json.
        self._persist_state(context.target, install_state)

        return result

    @staticmethod
    def _persist_state(project_root: Any, state: InstallState) -> None:
        """Write ``install-state.json`` if the state directory exists.

        ``install-state.json`` is initialised by :class:`StatePhase` earlier
        in the pipeline. The tools phase only updates the per-tool block;
        write the full payload back so the on-disk view stays consistent.
        """
        state_dir = project_root / ".ai-engineering" / "state"
        if not state_dir.is_dir():
            # State phase hasn't run -- skip the write to keep the phase
            # idempotent. The pipeline guarantees state runs before tools
            # in PHASE_ORDER, so this branch is a defensive no-op.
            return
        save_install_state(state_dir, state)

    def _emit_project_local_info(
        self,
        *,
        context: InstallContext,
        install_state: InstallState,
        result: PhaseResult,
        current_os_release: str,
    ) -> None:
        """Emit per-stack info messages + R-3 package.json check.

        Walks ``context.stacks`` and, for any stack whose recorded tools are
        all in :class:`ToolInstallState.NOT_INSTALLED_PROJECT_LOCAL`, emits an
        info-level warning naming the stack and the matching install command.
        For node stacks (typescript/javascript) the missing-``package.json``
        case is escalated to EXIT 80 with the ``npm init -y`` remediation.
        """
        # Build a quick lookup: stack -> [tool_names recorded as project_local].
        tools_by_stack = self._project_local_tools_by_stack(context, install_state)

        for stack_name, tool_names in tools_by_stack.items():
            install_cmd = _PROJECT_LOCAL_INSTALL_COMMANDS.get(stack_name)
            if install_cmd is None:
                # Stack isn't in our project_local install-command map; skip
                # the info message rather than emit a misleading default.
                continue

            # R-3: typescript / javascript MUST have package.json before
            # ``npm install`` can run. Escalate to EXIT 80 with the
            # ``npm init -y`` remediation if the file is absent.
            if stack_name in _NODE_STACKS_REQUIRING_PACKAGE_JSON:
                package_json = context.target / "package.json"
                if not package_json.is_file():
                    # Mark the recorded tools as failures so the verdict fails
                    # and the CLI surface raises Exit(80). Keep the recorded
                    # records as-is (NOT_INSTALLED_PROJECT_LOCAL) -- the
                    # failure is a stack-level prereq, not a per-tool fault.
                    for tool_name in tool_names:
                        result.failed.append(f"tool:{tool_name}:missing-package-json")
                    result.warnings.append(
                        f"stack {stack_name!r}: package.json missing at project root; "
                        "run 'npm init -y' to bootstrap, then re-run 'ai-eng install'"
                    )
                    continue  # skip the info message -- failure already logged

            joined = ", ".join(sorted(tool_names))
            result.warnings.append(
                f"stack {stack_name!r} uses project-local launchers ({joined}); "
                f"ensure '{install_cmd}' has been run to populate the local bin dir"
            )

    @staticmethod
    def _project_local_tools_by_stack(
        context: InstallContext,
        install_state: InstallState,
    ) -> dict[str, list[str]]:
        """Group recorded ``project_local`` tools by their declaring stack.

        Walks ``install_state.required_tools_state`` for tools recorded as
        :class:`ToolInstallState.NOT_INSTALLED_PROJECT_LOCAL` and groups them
        by their canonical originating stack via :data:`_CANONICAL_PROJECT_LOCAL_STACK`.

        For tools shared across stacks (e.g. ``prettier`` in both typescript
        and javascript), the canonical map points at one stack but the helper
        re-routes the entry to whichever sibling stack is actually present
        in ``context.stacks`` -- so a javascript-only project gets the
        ``javascript`` info message, not ``typescript``.
        """
        out: dict[str, list[str]] = {}
        for tool_name, record in install_state.required_tools_state.items():
            if record.state != ToolInstallState.NOT_INSTALLED_PROJECT_LOCAL:
                continue
            stack_name = _CANONICAL_PROJECT_LOCAL_STACK.get(tool_name)
            if stack_name is None:
                continue
            # Sibling-stack rerouting: typescript<->javascript share several
            # project_local tools. When the canonical stack isn't requested
            # but a sibling is, route the tool to the requested sibling.
            if stack_name not in context.stacks:
                sibling = _PROJECT_LOCAL_STACK_SIBLINGS.get(stack_name)
                if sibling and sibling in context.stacks:
                    stack_name = sibling
                else:
                    continue
            out.setdefault(stack_name, []).append(tool_name)
        return out

    def _install_one(
        self,
        tool: ToolSpec,
        *,
        os_key: str,
        result: PhaseResult,
        state: InstallState,
        current_os_release: str = "",
        current_python_env_mode: PythonEnvMode = PythonEnvMode.UV_TOOL,
        force: bool = False,
        tool_spec: dict[str, Any] | None = None,
    ) -> None:
        """Dispatch one tool's first mechanism and record the outcome.

        Wave 23 decomposed: pre-install gating (project_local carve-out,
        registry / platform / stack skips) is delegated to
        :meth:`_resolve_or_skip`, idempotence / re-verify logic to
        :meth:`_should_skip_idempotent`, and the actual mechanism dispatch
        + outcome recording to :meth:`_dispatch_install_for_tool`. The
        glue here just sequences the helpers and short-circuits when any
        of them have already finalised the per-tool state.
        """
        gating = self._resolve_or_skip(
            tool,
            os_key=os_key,
            result=result,
            state=state,
            current_os_release=current_os_release,
        )
        if gating is None:
            return  # tool was already finalised inside the helper.

        registry_entry, mechanism = gating

        # Idempotence path (D-101-07, T-2.16). Skipped when ``--force`` is set
        # so the operator can manually re-install everything.
        if not force and self._should_skip_idempotent(
            tool,
            registry_entry=registry_entry,
            tool_spec=tool_spec,
            state=state,
            result=result,
            current_os_release=current_os_release,
            current_python_env_mode=current_python_env_mode,
        ):
            return

        self._dispatch_install_for_tool(
            tool,
            mechanism=mechanism,
            result=result,
            state=state,
            current_os_release=current_os_release,
        )

    # ------------------------------------------------------------------
    # _install_one helpers (decomposed for cyclomatic-budget compliance)
    # ------------------------------------------------------------------

    def _resolve_or_skip(
        self,
        tool: ToolSpec,
        *,
        os_key: str,
        result: PhaseResult,
        state: InstallState,
        current_os_release: str,
    ) -> tuple[dict[str, Any], Any] | None:
        """Return ``(registry_entry, mechanism)`` or ``None`` after recording a skip.

        Centralises the four pre-install gates in one helper:

        * project_local carve-out (D-101-01): record
          ``NOT_INSTALLED_PROJECT_LOCAL`` and short-circuit.
        * unknown tool: record ``FAILED_NEEDS_MANUAL`` (no registry entry).
        * tool-level platform_unsupported (D-101-03):
          ``SKIPPED_PLATFORM_UNSUPPORTED``.
        * stack-level skip (empty mechanism list):
          ``SKIPPED_PLATFORM_UNSUPPORTED_STACK``.
        """
        if tool.scope == ToolScope.PROJECT_LOCAL:
            state.required_tools_state[tool.name] = _build_record(
                state=ToolInstallState.NOT_INSTALLED_PROJECT_LOCAL,
                mechanism="project_local",
                os_release=current_os_release,
            )
            result.skipped.append(f"tool:{tool.name}:project-local")
            return None

        registry_entry: dict[str, Any] | None = TOOL_REGISTRY.get(tool.name)
        if registry_entry is None:
            state.required_tools_state[tool.name] = _build_record(
                state=ToolInstallState.FAILED_NEEDS_MANUAL,
                mechanism="unknown",
                os_release=current_os_release,
            )
            result.failed.append(f"tool:{tool.name}:no-registry-entry")
            result.warnings.append(
                f"tool {tool.name!r} not registered in TOOL_REGISTRY; install manually"
            )
            return None

        if self._tool_skipped_for_os(tool, os_key):
            state.required_tools_state[tool.name] = _build_record(
                state=ToolInstallState.SKIPPED_PLATFORM_UNSUPPORTED,
                mechanism="none",
                os_release=current_os_release,
            )
            result.skipped.append(f"tool:{tool.name}:platform-unsupported")
            if tool.unsupported_reason:
                result.warnings.append(
                    f"tool {tool.name!r} skipped on {os_key}: {tool.unsupported_reason}"
                )
            return None

        mechanisms: list[Any] = registry_entry.get(os_key, []) or []
        if not mechanisms:
            state.required_tools_state[tool.name] = _build_record(
                state=ToolInstallState.SKIPPED_PLATFORM_UNSUPPORTED_STACK,
                mechanism="none",
                os_release=current_os_release,
            )
            result.skipped.append(f"tool:{tool.name}:no-mechanism")
            return None

        return registry_entry, mechanisms[0]

    @staticmethod
    def _verify_passes(
        spec_for_verify: dict[str, Any],
    ) -> bool:
        """Return True when the offline-safe verify probe passes."""
        try:
            verify_result = run_verify(spec_for_verify)
        except Exception:  # pragma: no cover - run_verify is total
            return False
        return bool(getattr(verify_result, "passed", False))

    @staticmethod
    def _should_skip_idempotent(
        tool: ToolSpec,
        *,
        registry_entry: dict[str, Any],
        tool_spec: dict[str, Any] | None,
        state: InstallState,
        result: PhaseResult,
        current_os_release: str,
        current_python_env_mode: PythonEnvMode,
    ) -> bool:
        """Return True when the verify probe lets us skip the install.

        Updates the recorded state in-place when verify passes (refreshing
        ``verified_at`` and the current-run os_release) so subsequent runs
        see the latest probe timestamp. Returns False when no skip is
        warranted -- the caller continues to mechanism dispatch.
        """
        existing_record = state.required_tools_state.get(tool.name)
        if existing_record is None:
            return False
        if existing_record.state != ToolInstallState.INSTALLED:
            return False

        if not ToolsPhase._verify_passes(tool_spec or registry_entry):
            return False

        # Refresh the record's verified_at + os_release; mechanism + version
        # carry forward unchanged.
        state.required_tools_state[tool.name] = ToolInstallRecord(
            state=ToolInstallState.INSTALLED,
            mechanism=existing_record.mechanism,
            version=existing_record.version,
            verified_at=datetime.now(tz=UTC),
            os_release=current_os_release or existing_record.os_release,
        )

        os_release_matches = (existing_record.os_release or "") == (current_os_release or "")
        mode_matches = state.python_env_mode_recorded == current_python_env_mode
        marker = "already-installed" if (os_release_matches and mode_matches) else "reverified"
        result.skipped.append(f"tool:{tool.name}:{marker}")
        return True

    @staticmethod
    def _dispatch_install_for_tool(
        tool: ToolSpec,
        *,
        mechanism: Any,
        result: PhaseResult,
        state: InstallState,
        current_os_release: str,
    ) -> None:
        """Run the mechanism's ``install()`` and record the outcome.

        Honours the ``AIENG_TEST_SIMULATE_FAIL`` env var (test seam) before
        invoking the real subprocess so EXIT-80 integration tests can drive
        deterministic failure paths. Captures three terminal outcomes:
        installed, simulated-fail, install-failed (incl. exceptions).
        """
        simulated = _check_simulate_fail(tool.name)
        if simulated is not None:
            state.required_tools_state[tool.name] = _build_record(
                state=ToolInstallState.FAILED_NEEDS_MANUAL,
                mechanism=simulated.mechanism or type(mechanism).__name__,
                os_release=current_os_release,
            )
            result.failed.append(f"tool:{tool.name}:simulated-fail")
            result.warnings.append(
                f"tool {tool.name!r} install simulated-failed via AIENG_TEST_SIMULATE_FAIL: "
                f"{simulated.stderr}"
            )
            return

        # Sister hook: ``AIENG_TEST_SIMULATE_INSTALL_OK`` records a synthetic
        # success for the named tool (or ``"*"`` for all). Used by the
        # install-smoke matrix on runners where the real network mechanism
        # is unavailable; the install pipeline still exercises every code
        # path UP TO the mechanism boundary.
        synthetic_ok = _check_simulate_install_ok(tool.name)
        if synthetic_ok is not None:
            state.required_tools_state[tool.name] = _build_record(
                state=ToolInstallState.INSTALLED,
                mechanism=synthetic_ok.mechanism or type(mechanism).__name__,
                version=synthetic_ok.version,
                os_release=current_os_release,
            )
            result.created.append(f"tool:{tool.name}:installed")
            return

        try:
            install_outcome = mechanism.install()
        except Exception as exc:
            logger.warning("install failed for %s: %s", tool.name, exc)
            state.required_tools_state[tool.name] = _build_record(
                state=ToolInstallState.FAILED_NEEDS_MANUAL,
                mechanism=type(mechanism).__name__,
                os_release=current_os_release,
            )
            result.failed.append(f"tool:{tool.name}:exception")
            result.warnings.append(f"tool {tool.name!r} install raised: {exc}")
            return

        mechanism_name = getattr(install_outcome, "mechanism", None) or type(mechanism).__name__

        if getattr(install_outcome, "failed", False):
            state.required_tools_state[tool.name] = _build_record(
                state=ToolInstallState.FAILED_NEEDS_MANUAL,
                mechanism=mechanism_name,
                os_release=current_os_release,
            )
            result.failed.append(f"tool:{tool.name}:install-failed")
            stderr = getattr(install_outcome, "stderr", "")
            result.warnings.append(
                f"tool {tool.name!r} install failed via {mechanism_name}: {stderr}"
            )
            return

        # Success.
        state.required_tools_state[tool.name] = _build_record(
            state=ToolInstallState.INSTALLED,
            mechanism=mechanism_name,
            version=getattr(install_outcome, "version", None),
            os_release=current_os_release,
        )
        result.created.append(f"tool:{tool.name}:installed")

    @staticmethod
    def _tool_skipped_for_os(tool: ToolSpec, os_key: str) -> bool:
        """Return True when ``tool.platform_unsupported`` covers the current OS."""
        unsupported = tool.platform_unsupported
        if not unsupported:
            return False
        # ToolSpec uses ``Platform`` enum (darwin / linux / windows). The
        # registry / sys.platform key is ``darwin`` / ``linux`` / ``win32``.
        os_normalised = "windows" if os_key == "win32" else os_key
        return any(p.value == os_normalised for p in unsupported)

    # ------------------------------------------------------------------
    # verify
    # ------------------------------------------------------------------

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        """Aggregate verdict; ``passed=False`` when any required tool failed."""
        passed = len(result.failed) == 0
        return PhaseVerdict(
            phase_name=self.name,
            passed=passed,
            warnings=list(result.warnings),
            errors=list(result.failed) if not passed else [],
        )
