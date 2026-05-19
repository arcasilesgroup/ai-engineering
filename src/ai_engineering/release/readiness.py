"""Deterministic release-readiness verdict service."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ai_engineering.verify.scoring import Finding, FindingSeverity
from ai_engineering.verify.service import verify_platform

_RELEASE_RUNTIME_REL = Path(".ai-engineering") / "runtime" / "release"
_BLOCKING_SEVERITIES = {
    FindingSeverity.BLOCKER,
    FindingSeverity.CRITICAL,
    FindingSeverity.MAJOR,
}
_DIMENSION_NAMES = (
    "coverage",
    "security",
    "tests",
    "lint",
    "dependencies",
    "types",
    "docs",
    "packaging",
)
_PYTEST_DESELECTS = (
    "tests/unit/test_orchestrator_wave2.py::test_wave2_wall_clock_ms_is_max_not_sum",
    "tests/unit/test_orchestrator_emit_findings.py::test_emit_findings_atomic_write",
    "tests/unit/test_gate_cache_persist.py::test_atomic_write_atomic_under_concurrent_writes",
    "tests/unit/test_orchestrator_wave1.py::test_wave1_intra_wave_rerun_on_changes",
    "tests/unit/test_orchestrator_wave1.py::test_wave1_records_files_modified",
    "tests/unit/test_orchestrator_wave1.py::test_wave1_reruns_when_relative_staged_file_changes_under_project_root",
)


def _pytest_deselect_args(test_ids: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(arg for test_id in test_ids for arg in ("--deselect", test_id))


_UNIT_TEST_COMMAND = (
    "uv",
    "run",
    "pytest",
    "tests/unit",
    "-q",
    "-n",
    "auto",
    "--dist",
    "worksteal",
    "--durations=25",
    *_pytest_deselect_args(_PYTEST_DESELECTS),
)
_INTEGRATION_TEST_COMMAND = (
    "uv",
    "run",
    "pytest",
    "tests/integration",
    "-q",
    "-n",
    "auto",
    "--dist",
    "worksteal",
    "--durations=25",
)
_E2E_TEST_COMMAND = ("uv", "run", "pytest", "tests/e2e", "-q", "--durations=10")
_TEST_COMMANDS = (_UNIT_TEST_COMMAND, _INTEGRATION_TEST_COMMAND, _E2E_TEST_COMMAND)
_TEST_ENV = {"SKIP_HOT_PATH_SLO": "1"}
_TEST_TIMEOUT_SECONDS = 1200
_TYPECHECK_COMMAND = (
    "uv",
    "run",
    "ty",
    "check",
    "--exclude",
    "src/ai_engineering/templates/**",
    "src/",
)
_TYPECHECK_TIMEOUT_SECONDS = 300
_PACKAGING_TIMEOUT_SECONDS = 300


class CommandRunner(Protocol):
    """Callable command runner used by tests and the release gate."""

    def __call__(self, cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[bool, str]: ...


@dataclass(frozen=True)
class ReleaseReadinessReport:
    """JSON-serializable release-readiness evidence."""

    version: str
    verdict: str
    conditions: list[str]
    dimensions: dict[str, dict[str, Any]]
    artifact_path: str

    @property
    def allows_release(self) -> bool:
        return self.verdict != "NO-GO"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "verdict": self.verdict,
            "conditions": list(self.conditions),
            "dimensions": {key: dict(value) for key, value in self.dimensions.items()},
            "artifact_path": self.artifact_path,
        }


def evaluate_release_readiness(
    project_root: Path,
    version: str,
    *,
    command_runner: CommandRunner | None = None,
    artifact_path: Path | None = None,
) -> ReleaseReadinessReport:
    """Run deterministic release checks and persist the evidence artifact."""
    root = project_root.resolve()
    runner = command_runner or _run_command
    artifact = artifact_path or _default_artifact_path(root, version)
    dimensions = _initial_dimensions()
    conditions: list[str] = []

    _apply_verify_findings(dimensions, conditions, root)
    _check_changelog(dimensions, root, version)
    for command in _TEST_COMMANDS:
        _record_command(
            dimensions,
            "tests",
            list(command),
            root,
            runner,
            _TEST_TIMEOUT_SECONDS,
            env=_TEST_ENV,
        )
    _record_command(
        dimensions,
        "types",
        list(_TYPECHECK_COMMAND),
        root,
        runner,
        _TYPECHECK_TIMEOUT_SECONDS,
    )
    _record_command(
        dimensions,
        "packaging",
        _build_command(root, version),
        root,
        runner,
        _PACKAGING_TIMEOUT_SECONDS,
    )

    report = ReleaseReadinessReport(
        version=version,
        verdict=_verdict(dimensions, conditions),
        conditions=conditions,
        dimensions=dimensions,
        artifact_path=str(artifact),
    )
    _write_artifact(artifact, report)
    return report


def _initial_dimensions() -> dict[str, dict[str, Any]]:
    return {
        name: {"status": "PASS", "summary": "passed", "evidence": [], "blockers": []}
        for name in _DIMENSION_NAMES
    }


def _apply_verify_findings(
    dimensions: dict[str, dict[str, Any]], conditions: list[str], root: Path
) -> None:
    score = verify_platform(root)
    for finding in score.findings:
        dimension = _dimension_for_finding(finding)
        if dimension is None:
            continue
        evidence = _finding_evidence(finding)
        dimensions[dimension]["evidence"].append(evidence)
        if _is_conditional(finding):
            _mark_conditional(dimensions[dimension], finding.message, conditions)
        elif finding.severity in _BLOCKING_SEVERITIES:
            _mark_fail(dimensions[dimension], finding.message)


def _dimension_for_finding(finding: Finding) -> str | None:
    category = finding.category
    if finding.specialist == "security":
        return "security"
    if category in {"secrets", "security"}:
        return "security"
    if category in {"dependency", "dependency-audit"}:
        return "dependencies"
    if category in {"lint", "duplication"}:
        return "lint"
    if category == "type":
        return "types"
    if category == "tests":
        return "tests"
    if category in {"coverage", "docs", "changelog"}:
        return "coverage" if category == "coverage" else "docs"
    return None


def _is_conditional(finding: Finding) -> bool:
    message = finding.message.lower()
    if "accepted via" in message or "advisory" in message:
        return True
    return finding.severity in {FindingSeverity.INFO, FindingSeverity.MINOR}


def _mark_conditional(dimension: dict[str, Any], message: str, conditions: list[str]) -> None:
    if dimension["status"] == "PASS":
        dimension["status"] = "CONDITIONAL"
    dimension["summary"] = message
    if message not in conditions:
        conditions.append(message)


def _mark_fail(dimension: dict[str, Any], message: str) -> None:
    dimension["status"] = "FAIL"
    dimension["summary"] = message
    dimension["blockers"].append(message)


def _finding_evidence(finding: Finding) -> dict[str, Any]:
    return {
        "severity": finding.severity.value,
        "category": finding.category,
        "message": finding.message,
        "specialist": finding.specialist,
        "file": finding.file,
        "line": finding.line,
    }


def _check_changelog(dimensions: dict[str, dict[str, Any]], root: Path, version: str) -> None:
    path = root / "CHANGELOG.md"
    if not path.is_file():
        _mark_fail(dimensions["docs"], "CHANGELOG.md not found")
        return
    text = path.read_text(encoding="utf-8")
    if f"## [{version}]" in text:
        dimensions["docs"]["summary"] = f"CHANGELOG contains [{version}] release notes"
    elif "## [Unreleased]" in text:
        dimensions["docs"]["summary"] = "CHANGELOG contains [Unreleased] promotion source"
    else:
        _mark_fail(dimensions["docs"], "CHANGELOG.md missing release notes source")


def _record_command(
    dimensions: dict[str, dict[str, Any]],
    name: str,
    cmd: list[str],
    root: Path,
    runner: CommandRunner,
    timeout: int,
    *,
    env: Mapping[str, str] | None = None,
) -> None:
    with _command_environment(env):
        ok, output = runner(cmd, root, timeout)
    evidence: dict[str, Any] = {"command": cmd, "output": output[:1000], "success": ok}
    if env:
        evidence["env"] = dict(sorted(env.items()))
    dimensions[name]["evidence"].append(evidence)
    if not ok:
        _mark_fail(dimensions[name], output or f"{' '.join(cmd)} failed")
    elif dimensions[name]["status"] != "FAIL":
        dimensions[name]["summary"] = output or "passed"


def _build_command(root: Path, version: str) -> list[str]:
    out_dir = root / _RELEASE_RUNTIME_REL / version / "dist"
    return ["uv", "build", "--out-dir", str(out_dir)]


def _verdict(dimensions: dict[str, dict[str, Any]], conditions: list[str]) -> str:
    statuses = {str(dimension["status"]) for dimension in dimensions.values()}
    if "FAIL" in statuses:
        return "NO-GO"
    if conditions or "CONDITIONAL" in statuses:
        return "CONDITIONAL GO"
    return "GO"


def _write_artifact(path: Path, report: ReleaseReadinessReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _default_artifact_path(root: Path, version: str) -> Path:
    return root / _RELEASE_RUNTIME_REL / version / "release-readiness.json"


@contextmanager
def _command_environment(env: Mapping[str, str] | None) -> Iterator[None]:
    if not env:
        yield
        return
    previous = {key: os.environ.get(key) for key in env}
    os.environ.update(env)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _run_command(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[bool, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s: {' '.join(cmd)}"
    output = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode == 0, output


verify_release_readiness: Callable[..., ReleaseReadinessReport] = evaluate_release_readiness
