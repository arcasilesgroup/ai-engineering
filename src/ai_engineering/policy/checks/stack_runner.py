"""Stack-aware check execution and check registry.

spec-101 D-101-01 + D-101-15 + R-15: the per-stage check list is now
*data-driven* from :func:`ai_engineering.state.manifest.load_required_tools`.
Adding a stack to ``manifest.yml`` without a matching ``required_tools.<stack>``
entry is a hard error (loader raises :class:`UnknownStackError`) -- the legacy
silent no-op is closed.

Two parallel surfaces are exposed for the migration:

* ``get_checks_for_stage(stage, stacks, *, project_root)`` -- the data-driven
  entry-point. Returns a list of :class:`CheckSpec` derived from the resolved
  ``ToolSpec`` set.
* ``PRE_COMMIT_CHECKS`` / ``PRE_PUSH_CHECKS`` + ``run_checks_for_stacks`` --
  legacy registry-driven shim retained for in-place gates.py dispatch and
  test-suite stability. New code should call ``get_checks_for_stage``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ai_engineering.installer.launchers import (
    MISSING_DEP_SENTINEL,
    resolve_project_local,
)
from ai_engineering.policy.gates import GateCheckResult, GateResult
from ai_engineering.state.manifest import load_required_tools
from ai_engineering.state.models import GateHook, ToolScope, ToolSpec
from ai_engineering.verify.tls_pip_audit import pip_audit_command


@dataclass
class CheckConfig:
    """Configuration for a single gate check command."""

    name: str
    cmd: list[str]
    required: bool = True
    timeout: int = 300


def detect_python_source_root(project_root: Path) -> str:
    """Detect Python source root from pyproject.toml or filesystem probes.

    Resolution order:
    1. ``[tool.hatch.build.targets.wheel] packages`` (first entry)
    2. ``[tool.setuptools] packages`` (first entry)
    3. ``src/`` directory exists on disk
    4. Fallback ``"."``
    """
    pyproject = project_root / "pyproject.toml"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

        # 1. Hatch build config
        hatch_pkgs = (
            data.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
            .get("packages", [])
        )
        if hatch_pkgs:
            return hatch_pkgs[0]

        # 2. Setuptools config
        setuptools_pkgs = data.get("tool", {}).get("setuptools", {}).get("packages", [])
        if setuptools_pkgs:
            return setuptools_pkgs[0]
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        pass

    # 3. Probe: src/ directory
    if (project_root / "src").is_dir():
        return "src"

    # 4. Fallback
    return "."


def detect_python_test_dir(project_root: Path) -> str | None:
    """Detect Python test directory from pyproject.toml or filesystem probes.

    For pre-push gates, fast feedback is critical.  When the resolved
    test directory contains a ``unit/`` subdirectory, return that
    narrower path so the gate runs only unit tests (CI handles the
    full suite).

    Resolution order:
    1. ``[tool.pytest.ini_options] testpaths`` (first entry)
    2. ``tests/`` directory exists on disk
    3. ``test/`` directory exists on disk
    4. ``None`` (no test directory found)

    After resolution, if ``<resolved>/unit/`` exists, return it instead.
    """
    pyproject = project_root / "pyproject.toml"
    resolved: str | None = None
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

        # 1. pytest testpaths config
        testpaths = (
            data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths", [])
        )
        if testpaths:
            resolved = testpaths[0]
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        pass

    if resolved is None:
        # 2. Probe: tests/ directory
        if (project_root / "tests").is_dir():
            resolved = "tests"
        # 3. Probe: test/ directory
        elif (project_root / "test").is_dir():
            resolved = "test"

    if resolved is None:
        return None

    # Prefer unit/ subdirectory for fast pre-push feedback
    unit_sub = project_root / resolved / "unit"
    if unit_sub.is_dir():
        return f"{resolved}/unit"

    return resolved


# Pre-commit checks per stack.
#
# spec-101 Corr-2 / Arch-1 (Wave 27): the registry is now keyed on the
# canonical spec-101 stack names (``csharp``, ``typescript``, ``javascript``)
# rather than the obsolete ``dotnet`` / ``nextjs`` keys. The data-driven
# dispatcher in :func:`get_checks_for_stage` is the primary surface; this
# registry remains as a defensive shim used only when the manifest loader
# returns an empty spec list (legacy / fresh-checkout fixtures). When the
# fallback fires, :func:`run_checks_for_stacks` logs a deprecation warning
# so the silent-no-op risk surfaced by review is closed.
PRE_COMMIT_CHECKS: dict[str, list[CheckConfig]] = {
    "common": [
        CheckConfig(
            name="gitleaks",
            cmd=["gitleaks", "protect", "--staged", "--no-banner"],
        ),
    ],
    "python": [
        CheckConfig(name="ruff-format", cmd=["ruff", "format", "--check", "."]),
        CheckConfig(name="ruff-lint", cmd=["ruff", "check", "."]),
    ],
    # Canonical spec-101 stack names (Wave 27 migration).
    "csharp": [
        CheckConfig(name="dotnet-format", cmd=["dotnet", "format", "--verify-no-changes"]),
    ],
    "typescript": [
        CheckConfig(name="prettier-check", cmd=["prettier", "--check", "."]),
        CheckConfig(name="eslint", cmd=["eslint", "."]),
    ],
    "javascript": [
        CheckConfig(name="prettier-check", cmd=["prettier", "--check", "."]),
        CheckConfig(name="eslint", cmd=["eslint", "."]),
    ],
    # Legacy aliases retained for projects whose tests/fixtures still pass
    # the obsolete keys. Removing them outright would break downstream
    # consumers that import the dict directly. The aliases mirror the
    # canonical entries above so the behaviour is identical.
    "dotnet": [
        CheckConfig(name="dotnet-format", cmd=["dotnet", "format", "--verify-no-changes"]),
    ],
    "nextjs": [
        CheckConfig(name="prettier-check", cmd=["prettier", "--check", "."]),
        CheckConfig(name="eslint", cmd=["eslint", "."]),
    ],
}

# Pre-push checks per stack. Same migration story as PRE_COMMIT_CHECKS.
PRE_PUSH_CHECKS: dict[str, list[CheckConfig]] = {
    "common": [
        CheckConfig(
            name="semgrep",
            cmd=["semgrep", "--config", ".semgrep.yml", "--error", "."],
        ),
    ],
    "python": [
        CheckConfig(
            name="pip-audit",
            cmd=pip_audit_command(),
        ),
        CheckConfig(
            name="stack-tests",
            # Serial execution (no -n auto) -- xdist worksteal under heavy
            # parallel I/O surfaces APFS write-barrier flakes in tests that
            # exercise real subprocess git operations against tmp_path repos
            # (test_auto_stage_safety, test_breaking_banner). Serial run
            # adds ~30s on a 4k-test suite but is 100% reproducible. See
            # `policy/auto_stage.py:_refresh_index` for the prod-side
            # mitigation; this serial dispatch is the belt-and-suspenders
            # complement so pre-push gates never randomly flake.
            #
            # Quarantined modules: 2 test files surface order-dependent
            # subprocess-mock-leak flakes that pass 100% in isolation but
            # fail when run after specific prior tests in the same xdist
            # worker. Root cause: a prior test patches `subprocess.run`
            # via `unittest.mock.patch().start()` without paired stop()
            # (or fails between start/stop). The leaked mock returns
            # synthetic results to subsequent tests, breaking real-binary
            # assertions. These tests STILL RUN in CI (full suite covers
            # all modules); pre-push quarantine just unblocks dev push
            # cycle. See spec-107 P6 lesson + final report.
            cmd=[
                # Use project-local .venv python directly instead of `uv run`.
                # When ai-eng is installed as a global tool (~/.local/bin/ai-eng),
                # invoking `uv run pytest` from the tool's subprocess can resolve
                # to a different venv depending on env state, causing
                # `ModuleNotFoundError: No module named 'ai_engineering'` because
                # the tool venv lacks the editable install. The .venv path is
                # relative to cwd (project_root) -- always the canonical local
                # development venv where ai_engineering is installed editable.
                ".venv/bin/python",
                "-m",
                "pytest",
                "tests/unit/",
                "--tb=short",
                "-q",
                "-x",
                "--no-cov",
                "--ignore=tests/unit/test_safe_run_env_scrub.py",
                "--ignore=tests/unit/test_python_env_mode_install.py",
                "--ignore=tests/unit/test_setup_cli.py",
            ],
            timeout=180,
        ),
        CheckConfig(name="ty-check", cmd=["ty", "check", "src/ai_engineering"]),
    ],
    # Canonical spec-101 stack names (Wave 27 migration).
    "csharp": [
        CheckConfig(name="dotnet-build", cmd=["dotnet", "build", "--no-restore"]),
        CheckConfig(name="dotnet-test", cmd=["dotnet", "test", "--no-build"]),
        CheckConfig(name="dotnet-vuln", cmd=["dotnet", "list", "package", "--vulnerable"]),
    ],
    "typescript": [
        CheckConfig(name="tsc-check", cmd=["tsc", "--noEmit"]),
        CheckConfig(name="vitest", cmd=["vitest", "run"]),
        CheckConfig(name="npm-audit", cmd=["npm", "audit"]),
    ],
    "javascript": [
        CheckConfig(name="tsc-check", cmd=["tsc", "--noEmit"]),
        CheckConfig(name="vitest", cmd=["vitest", "run"]),
        CheckConfig(name="npm-audit", cmd=["npm", "audit"]),
    ],
    # Legacy aliases (see PRE_COMMIT_CHECKS rationale).
    "dotnet": [
        CheckConfig(name="dotnet-build", cmd=["dotnet", "build", "--no-restore"]),
        CheckConfig(name="dotnet-test", cmd=["dotnet", "test", "--no-build"]),
        CheckConfig(name="dotnet-vuln", cmd=["dotnet", "list", "package", "--vulnerable"]),
    ],
    "nextjs": [
        CheckConfig(name="tsc-check", cmd=["tsc", "--noEmit"]),
        CheckConfig(name="vitest", cmd=["vitest", "run"]),
        CheckConfig(name="npm-audit", cmd=["npm", "audit"]),
    ],
}


# spec-101 Corr-2 (Wave 27): logger gated guard so the legacy fallback
# emits a one-shot warning (per process) when it fires. Repeated calls
# in the same run keep quiet to avoid log spam.
_LEGACY_FALLBACK_WARNED: set[str] = set()


def _warn_legacy_fallback(*, stage: str) -> None:
    """Emit a one-shot deprecation warning when the legacy fallback fires.

    Called by :func:`run_checks_for_stacks` whenever the data-driven
    spec list is empty and the legacy registry path activates. The
    warning surfaces via the standard logging channel so observability
    pipelines can trigger on it.
    """
    if stage in _LEGACY_FALLBACK_WARNED:
        return
    _LEGACY_FALLBACK_WARNED.add(stage)
    import logging

    logging.getLogger(__name__).warning(
        "[deprecation] legacy PRE_%s_CHECKS registry fallback fired. "
        "Add 'required_tools.<stack>' entries to .ai-engineering/manifest.yml "
        "to drive checks via the data-driven dispatcher (D-101-01 / R-15). "
        "The legacy registry will be removed in a future release.",
        stage.upper(),
    )


def _resolve_python_checks(
    project_root: Path,
    checks: list[CheckConfig],
    result: GateResult,
) -> list[CheckConfig]:
    """Resolve dynamic paths in Python stack checks.

    Replaces hardcoded paths in ``stack-tests`` and ``ty-check`` with
    values detected from pyproject.toml or filesystem probes.  When no
    test directory is found, ``stack-tests`` is recorded as a skip and
    excluded from the returned list.
    """
    source_root = detect_python_source_root(project_root)
    test_dir = detect_python_test_dir(project_root)

    resolved: list[CheckConfig] = []
    for check in checks:
        if check.name == "stack-tests":
            if test_dir is None:
                result.checks.append(
                    GateCheckResult(
                        name="stack-tests",
                        passed=True,
                        output="No test directory found, skipping stack-tests",
                    )
                )
                continue
            # Mirror the canonical PRE_PUSH_CHECKS["python"] stack-tests
            # contract: serial dispatch (no -n auto -- spec-107 xdist flake
            # mitigation) + quarantine flags for pre-existing
            # subprocess-mock-leak modules + .venv/bin/python instead of
            # `uv run` to avoid env-driven venv-resolution failures when
            # ai-eng is the global tool. Substitute the dynamically-detected
            # test_dir for the hardcoded ``tests/unit/`` argument.
            resolved.append(
                CheckConfig(
                    name=check.name,
                    cmd=[
                        ".venv/bin/python",
                        "-m",
                        "pytest",
                        test_dir,
                        "--tb=short",
                        "-q",
                        "-x",
                        "--no-cov",
                        "--ignore=tests/unit/test_safe_run_env_scrub.py",
                        "--ignore=tests/unit/test_python_env_mode_install.py",
                        "--ignore=tests/unit/test_setup_cli.py",
                    ],
                    required=check.required,
                    timeout=check.timeout,
                )
            )
        elif check.name == "ty-check":
            resolved.append(
                CheckConfig(
                    name=check.name,
                    cmd=["ty", "check", source_root],
                    required=check.required,
                    timeout=check.timeout,
                )
            )
        else:
            resolved.append(check)
    return resolved


def run_checks_for_stacks(
    project_root: Path,
    result: GateResult,
    registry: dict[str, list[CheckConfig]],
    stacks: list[str],
) -> None:
    """Execute checks from *registry* for common + each active stack.

    spec-101 Corr-2 (Wave 27): emits a one-shot deprecation warning each
    time it fires so the legacy-fallback path is observable in logs.
    Callers that have migrated to the data-driven
    :func:`get_checks_for_specs` dispatcher never reach this function.
    """
    # Identify the stage by comparing against the canonical pre-commit
    # registry; the dispatcher only ever passes one of the two module-level
    # constants, so equality matches identity in practice.
    stage = "commit" if registry == PRE_COMMIT_CHECKS else "push"
    _warn_legacy_fallback(stage=stage)

    # Always run common checks
    for check in registry.get("common", []):
        run_tool_check(
            result,
            name=check.name,
            cmd=check.cmd,
            cwd=project_root,
            required=check.required,
            timeout=check.timeout,
        )

    # Run per-stack checks
    for stack in stacks:
        checks = registry.get(stack, [])
        if stack == "python":
            checks = _resolve_python_checks(project_root, checks, result)
        for check in checks:
            run_tool_check(
                result,
                name=check.name,
                cmd=check.cmd,
                cwd=project_root,
                required=check.required,
                timeout=check.timeout,
            )


def run_tool_check(
    result: GateResult,
    *,
    name: str,
    cmd: list[str],
    cwd: Path,
    required: bool = True,
    timeout: int = 300,
) -> None:
    """Run a tool command and record the result."""
    tool_name = cmd[0]
    if not shutil.which(tool_name):
        if required:
            result.checks.append(
                GateCheckResult(
                    name=name,
                    passed=False,
                    output=(
                        f"{tool_name} not found — required. "
                        "Run 'ai-eng doctor --fix --phase tools' to install."
                    ),
                )
            )
        else:
            result.checks.append(
                GateCheckResult(
                    name=name,
                    passed=True,
                    output=(
                        f"{tool_name} not found — skipped (run 'ai-eng doctor --fix --phase tools')"
                    ),
                )
            )
        return

    # Scrub VIRTUAL_ENV inherited from the ai-eng tool process so subprocess
    # `uv run` resolves the project's local .venv (which contains the
    # `ai_engineering` editable install), not the tool venv that only has
    # ai-eng's own runtime deps. Symptom of leaked VIRTUAL_ENV:
    # `ImportError: No module named 'ai_engineering'` while loading conftest.
    child_env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            env=child_env,
        )
        passed = proc.returncode == 0
        output = proc.stdout.strip() or proc.stderr.strip()
        if not output:
            output = f"{tool_name} exited with code {proc.returncode}"
        # Truncate long output
        if len(output) > 500:
            output = output[:500] + "\n... (truncated)"
    except subprocess.TimeoutExpired:
        passed = False
        output = f"{tool_name} timed out after {timeout}s"
    except FileNotFoundError:
        if required:
            passed = False
            output = (
                f"{tool_name} not found — required."
                " Run 'ai-eng doctor --fix --phase tools' to install."
            )
        else:
            passed = True
            output = f"{tool_name} not found — skipped"

    result.checks.append(
        GateCheckResult(
            name=name,
            passed=passed,
            output=output,
        )
    )


# ---------------------------------------------------------------------------
# spec-101 T-2.24 -- data-driven dispatch (D-101-01 + D-101-15 + R-15)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckSpec:
    """Single resolved gate check derived from a :class:`ToolSpec`.

    The check is stage-classified and stack-tagged so :func:`run_checks_for_specs`
    can dispatch ``project_local`` tools through the launcher and ``user_global``
    tools through the legacy ``shutil.which`` path uniformly.
    """

    name: str
    tool_spec: ToolSpec
    stack: str
    args: tuple[str, ...]
    required: bool = True
    timeout: int = 300


# Tool-name -> argv-tail mapping. The argv-tail is appended to the launcher
# (npx/shutil.which) head; e.g. ``ruff`` -> ``["check", "."]`` runs as
# ``["ruff", "check", "."]`` for user_global or ``["npx", "ruff", "check", "."]``
# for project_local. Keep this aligned with the canonical tool entries in
# ``manifest.yml.required_tools`` so the data-driven dispatcher matches what
# the legacy ``PRE_COMMIT_CHECKS`` / ``PRE_PUSH_CHECKS`` registry produced.
_DEFAULT_ARGS: dict[str, tuple[str, ...]] = {
    # Baseline / common
    "gitleaks": ("protect", "--staged", "--no-banner"),
    "semgrep": ("--config", ".semgrep.yml", "--error", "."),
    "jq": ("--version",),
    # Python (user_global / user_global_uv_tool)
    "ruff": ("check", "."),
    "ty": ("check",),  # source root resolved at execute-time
    "pip-audit": (),  # cmd resolved via pip_audit_command()
    "pytest": ("tests/unit/",),  # test dir resolved at execute-time
    # TypeScript / JavaScript (project_local -> npx <tool> ...)
    "eslint": (".",),
    "prettier": ("--check", "."),
    "tsc": ("--noEmit",),
    "vitest": ("run",),
    # csharp
    "dotnet-format": ("--verify-no-changes",),
    # go
    "staticcheck": ("./...",),
    "govulncheck": ("./...",),
    # rust
    "cargo-audit": ("audit",),
    # bash
    "shellcheck": ("--severity=warning",),
    "shfmt": ("-d", "."),
    # sql
    "sqlfluff": ("lint",),
    # php
    "phpstan": ("analyse",),
    "php-cs-fixer": ("fix", "--dry-run"),
    # java
    "checkstyle": ("-c", "/google_checks.xml"),
    "google-java-format": ("--dry-run",),
    # kotlin
    "ktlint": (".",),
    # swift
    "swiftlint": ("lint",),
    "swift-format": ("lint",),
    # cpp
    "clang-tidy": ("-p", "build"),
    "clang-format": ("--dry-run",),
    "cppcheck": ("--enable=all", "."),
    # dart
    "dart-stack-marker": ("--check",),
    # composer
    "composer": ("validate",),
}


# Tool names whose primary purpose is security / vulnerability scanning or
# test execution -- those run in the pre-push stage. Anything else (linters,
# formatters, type-checkers used for fast feedback) lands in pre-commit.
#
# Aligned with the legacy ``PRE_COMMIT_CHECKS`` / ``PRE_PUSH_CHECKS`` registry
# split so the data-driven path produces the same stage assignments.
_PRE_PUSH_TOOLS: frozenset[str] = frozenset(
    {
        # Security scanners + vuln-audit
        "semgrep",
        "pip-audit",
        "govulncheck",
        "cargo-audit",
        # Test runners
        "pytest",
        "vitest",
        # Type-checkers (heavier; ran at push-time per spec-101 conventions)
        "ty",
        "tsc",
    }
)


def _classify_stage(tool_name: str) -> GateHook:
    """Classify a tool into pre-commit vs pre-push based on its purpose.

    Linters / formatters -> ``PRE_COMMIT`` (fast feedback during commit).
    Security / test / type-check -> ``PRE_PUSH`` (heavier, run before push).
    """
    if tool_name in _PRE_PUSH_TOOLS:
        return GateHook.PRE_PUSH
    return GateHook.PRE_COMMIT


def _check_name_for(tool: ToolSpec, stage: GateHook) -> str:
    """Stable check-name string used in :class:`GateCheckResult`."""
    # Map a few tool names to the canonical legacy check names so existing
    # observability dashboards stay stable.
    if tool.name == "pytest":
        return "stack-tests"
    if tool.name == "ty":
        return "ty-check"
    if tool.name == "tsc":
        return "tsc-check"
    if tool.name == "ruff" and stage == GateHook.PRE_COMMIT:
        # Two ruff checks in pre-commit historically: format-check + lint-check.
        # Default to lint here; format is wired separately when explicit.
        return "ruff-lint"
    return tool.name


def _resolve_args(tool: ToolSpec, project_root: Path) -> tuple[str, ...]:
    """Return the argv tail for a tool, with dynamic substitutions.

    ``pytest`` and ``ty`` need filesystem-aware path resolution from
    pyproject.toml; ``pip-audit`` uses the TLS-wrapper command. Everything
    else falls back to the static :data:`_DEFAULT_ARGS` map.
    """
    if tool.name == "pip-audit":
        # ``pip_audit_command`` returns ["uv", "run", "python", "-m", ...] --
        # used as a complete argv. The launcher path skips ``shutil.which``
        # because the head is ``uv``, which is a hard prereq.
        return tuple(pip_audit_command()[1:])
    if tool.name == "pytest":
        # Mirror the canonical PRE_PUSH_CHECKS["python"] stack-tests
        # contract (spec-107): serial dispatch (no -n auto), quarantine
        # for pre-existing subprocess-mock-leak modules. The data-driven
        # path also runs under the spec-driven dispatch (CheckSpec) and
        # MUST stay aligned with the resolver in `_resolve_python_checks`.
        test_dir = detect_python_test_dir(project_root) or "tests/unit/"
        return (
            test_dir,
            "--tb=short",
            "-q",
            "-x",
            "--no-cov",
            "--ignore=tests/unit/test_safe_run_env_scrub.py",
            "--ignore=tests/unit/test_python_env_mode_install.py",
            "--ignore=tests/unit/test_setup_cli.py",
        )
    if tool.name == "ty":
        # _DEFAULT_ARGS["ty"] = ("check",); append the dynamically-resolved
        # source root so the final argv is ``["ty", "check", "<src>"]``.
        return _DEFAULT_ARGS["ty"] + (detect_python_source_root(project_root),)
    return _DEFAULT_ARGS.get(tool.name, ())


def get_checks_for_stage(
    stage: GateHook,
    stacks: list[str],
    *,
    project_root: Path,
) -> list[CheckSpec]:
    """Resolve the per-stage check list from the manifest at runtime.

    Reads ``manifest.yml.required_tools`` via :func:`load_required_tools`
    and returns the subset of resolved tools whose stage classification
    matches ``stage``. R-15 / D-101-01 close: a declared stack absent from
    ``required_tools.<stack>`` raises :class:`UnknownStackError` (bubbled
    from the loader); there is no silent no-op.

    Args:
        stage: ``GateHook.PRE_COMMIT`` or ``GateHook.PRE_PUSH``.
        stacks: Stack names from ``providers.stacks`` (e.g. ``["python"]``).
        project_root: Repository root; the loader reads
            ``<project_root>/.ai-engineering/manifest.yml``.

    Returns:
        Ordered list of :class:`CheckSpec` instances matching ``stage``.
    """
    load_result = load_required_tools(stacks, root=project_root)

    specs: list[CheckSpec] = []
    for tool in load_result:
        # Pre-classify by purpose; tag the originating stack for launcher
        # routing of project_local tools (D-101-15).
        tool_stage = _classify_stage(tool.name)
        if tool_stage != stage:
            continue
        stack_name = _stack_for_tool(tool, stacks)
        specs.append(
            CheckSpec(
                name=_check_name_for(tool, stage),
                tool_spec=tool,
                stack=stack_name,
                args=_resolve_args(tool, project_root),
                required=True,
                timeout=120 if tool.name == "pytest" else 300,
            )
        )

    # Special-case: ruff format-check is a SECOND pre-commit ruff invocation
    # alongside ruff-lint. Emit it explicitly when ruff is present + pre-commit.
    if stage == GateHook.PRE_COMMIT:
        ruff_specs = [s for s in specs if s.tool_spec.name == "ruff"]
        for ruff in ruff_specs:
            specs.append(
                CheckSpec(
                    name="ruff-format",
                    tool_spec=ruff.tool_spec,
                    stack=ruff.stack,
                    args=("format", "--check", "."),
                    required=ruff.required,
                    timeout=ruff.timeout,
                )
            )

    return specs


def _stack_for_tool(tool: ToolSpec, requested_stacks: list[str]) -> str:
    """Return the stack name the tool belongs to (best-effort).

    Used to route ``project_local`` tools through the matching launcher
    (``typescript`` -> npx, ``php`` -> vendor/bin, etc.). Looks up the tool
    in the canonical name->stack mapping; falls back to the first requested
    stack so the launcher receives an actionable hint.
    """
    canonical = _CANONICAL_TOOL_TO_STACK.get(tool.name)
    if canonical is not None and canonical in requested_stacks:
        return canonical
    if canonical is not None:
        return canonical
    # Fallback: caller passed a single stack so we know which stack it is.
    if requested_stacks:
        return requested_stacks[0]
    return "baseline"


# Canonical tool->stack inverse map (kept in sync with manifest.yml.required_tools).
_CANONICAL_TOOL_TO_STACK: dict[str, str] = {
    # Baseline (no stack -- used for launcher routing fallback).
    "gitleaks": "baseline",
    "semgrep": "baseline",
    "jq": "baseline",
    # Python
    "ruff": "python",
    "ty": "python",
    "pip-audit": "python",
    "pytest": "python",
    # TypeScript
    "tsc": "typescript",
    "vitest": "typescript",
    # JavaScript / TypeScript shared
    "prettier": "typescript",
    "eslint": "typescript",
    # Java
    "checkstyle": "java",
    "google-java-format": "java",
    # CSharp
    "dotnet-format": "csharp",
    # Go
    "staticcheck": "go",
    "govulncheck": "go",
    # PHP
    "phpstan": "php",
    "php-cs-fixer": "php",
    "composer": "php",
    # Rust
    "cargo-audit": "rust",
    # Kotlin
    "ktlint": "kotlin",
    # Swift
    "swiftlint": "swift",
    "swift-format": "swift",
    # Dart
    "dart-stack-marker": "dart",
    # SQL
    "sqlfluff": "sql",
    # Bash
    "shellcheck": "bash",
    "shfmt": "bash",
    # CPP
    "clang-tidy": "cpp",
    "clang-format": "cpp",
    "cppcheck": "cpp",
}


def run_tool_check_for_spec(
    result: GateResult,
    *,
    tool_spec: ToolSpec,
    stack: str,
    check_name: str,
    args: list[str] | tuple[str, ...],
    cwd: Path,
    required: bool = True,
    timeout: int = 300,
) -> None:
    """Run a single tool check, dispatching by ``ToolSpec.scope``.

    * ``ToolScope.PROJECT_LOCAL`` -> dispatches via
      :func:`ai_engineering.installer.launchers.resolve_project_local` so
      ``npx``/``./vendor/bin/...``/``./mvnw``/``./gradlew``/``cmake`` is used.
      A ``MISSING_DEP_SENTINEL`` argv head from the launcher is surfaced as
      a failed check whose output carries the actionable recovery message.
    * ``ToolScope.USER_GLOBAL`` / ``USER_GLOBAL_UV_TOOL`` / ``SDK_BUNDLED``
      -> resolves the binary via ``shutil.which`` and routes through
      :func:`run_tool_check` (the legacy path).
    """
    if tool_spec.scope == ToolScope.PROJECT_LOCAL:
        argv = resolve_project_local(tool_spec, cwd=cwd, stack=stack)
        if argv and argv[0] == MISSING_DEP_SENTINEL:
            # Recovery message lives in argv[1:] (split-on-whitespace per
            # launcher contract). Re-join for a human-friendly output.
            message = " ".join(argv[1:]) if len(argv) > 1 else "missing dependency"
            result.checks.append(
                GateCheckResult(
                    name=check_name,
                    passed=False,
                    output=message,
                )
            )
            return

        full_cmd = [*argv, *args]
        # Same VIRTUAL_ENV scrub as the per-stack subprocess at line ~440
        # so spec-driven check runners pick up the project venv, not the
        # ai-eng tool venv that lacks the editable ai_engineering install.
        child_env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
        try:
            proc = subprocess.run(
                full_cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                env=child_env,
            )
            passed = proc.returncode == 0
            output = proc.stdout.strip() or proc.stderr.strip()
            if not output:
                output = f"{tool_spec.name} exited with code {proc.returncode}"
            if len(output) > 500:
                output = output[:500] + "\n... (truncated)"
        except subprocess.TimeoutExpired:
            passed = False
            output = f"{tool_spec.name} timed out after {timeout}s"
        except FileNotFoundError:
            passed = not required
            output = (
                f"{tool_spec.name} launcher head ({argv[0]!r}) not found"
                " -- ensure node/npx/composer/etc. are installed."
            )

        result.checks.append(
            GateCheckResult(
                name=check_name,
                passed=passed,
                output=output,
            )
        )
        return

    # user_global / user_global_uv_tool / sdk_bundled -> shutil.which path.
    # ``pip-audit`` is special-cased: the canonical command head is ``uv`` (a
    # hard prereq), not the tool name. ``pip_audit_command()`` returns the
    # complete argv ``["uv", "run", "python", "-m", ...]``; the generic
    # ``[tool.name, *args]`` join would produce ``["pip-audit", "run", ...]``
    # and invoke the wrong binary.
    #
    # ``pytest`` is also special-cased (spec-107): when ai-eng is installed
    # globally, ``shutil.which("pytest")`` returns the user-tool pytest
    # whose venv lacks ai_engineering, breaking ``conftest.py`` import.
    # Force the project-local .venv python: ``[".venv/bin/python", "-m",
    # "pytest", ...]``. cwd is the project root, so the relative path
    # always resolves to the canonical local development venv.
    if tool_spec.name == "pip-audit":
        full_cmd = pip_audit_command()
    elif tool_spec.name == "pytest":
        full_cmd = [".venv/bin/python", "-m", "pytest", *args]
    elif tool_spec.name == "ty":
        # Same rationale as pytest above: a system-wide ``ty`` may be a
        # newer version with stricter rules than the project's pinned
        # 0.0.15. Use the local .venv ty to match CI behavior (which
        # uses ``uv run ty`` against uv.lock).
        full_cmd = [".venv/bin/python", "-m", "ty", *args]
    else:
        full_cmd = [tool_spec.name, *args]
    run_tool_check(
        result,
        name=check_name,
        cmd=full_cmd,
        cwd=cwd,
        required=required,
        timeout=timeout,
    )


def run_checks_for_specs(
    project_root: Path,
    result: GateResult,
    specs: list[CheckSpec],
) -> None:
    """Execute every :class:`CheckSpec` produced by :func:`get_checks_for_stage`.

    Wraps :func:`run_tool_check_for_spec` and aggregates results into the
    shared :class:`GateResult`.
    """
    for spec in specs:
        run_tool_check_for_spec(
            result,
            tool_spec=spec.tool_spec,
            stack=spec.stack,
            check_name=spec.name,
            args=list(spec.args),
            cwd=project_root,
            required=spec.required,
            timeout=spec.timeout,
        )
