"""Verify service -- aggregates tool outputs into scored reports."""

from __future__ import annotations

import ast
import json
import subprocess
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from ai_engineering.state.models import GateFinding, GateFindingsDocument
from ai_engineering.state.work_plane import resolve_active_work_plane
from ai_engineering.validator._shared import IntegrityStatus
from ai_engineering.validator.service import validate_content_integrity
from ai_engineering.verify.scoring import (
    FindingSeverity,
    SpecialistResult,
    VerifyScore,
)
from ai_engineering.verify.taxonomy import classify_check_name
from ai_engineering.verify.tls_pip_audit import pip_audit_command

SPECIALIST_ORDER = (
    "governance",
    "security",
    "architecture",
    "quality",
    "feature",
)

SPECIALIST_LABELS = {
    "governance": "Governance",
    "security": "Security",
    "architecture": "Architecture",
    "quality": "Quality",
    "feature": "Feature",
}

_NORMAL_RUNNERS = {
    "macro-agent-1": ("governance", "security", "architecture"),
    "macro-agent-2": ("quality", "feature"),
}

_GATE_FINDINGS_RELATIVE_PATH = Path(".ai-engineering") / "state" / "gate-findings.json"
_SECURITY_CHECK_CATEGORIES = {
    "gitleaks": "secrets",
    "pip-audit": "dependency",
    "semgrep": "security",
}


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def _runner_for(specialist: str, profile: str) -> str:
    if profile == "full":
        return specialist
    for runner, specialists in _NORMAL_RUNNERS.items():
        if specialist in specialists:
            return runner
    return specialist


def _start_specialist(name: str, profile: str) -> tuple[VerifyScore, SpecialistResult]:
    result = VerifyScore(mode=name, profile=profile)
    specialist = SpecialistResult(
        name=name,
        label=SPECIALIST_LABELS[name],
        runner=_runner_for(name, profile),
    )
    result.specialists.append(specialist)
    return result, specialist


def _finalize_specialist(result: VerifyScore, specialist: SpecialistResult) -> VerifyScore:
    result.findings.extend(specialist.findings)
    return result


def _not_applicable(name: str, profile: str, rationale: str) -> VerifyScore:
    result, specialist = _start_specialist(name, profile)
    specialist.applicable = False
    specialist.rationale = rationale
    return _finalize_specialist(result, specialist)


def _load_gate_findings_document(project_root: Path) -> GateFindingsDocument | None:
    path = project_root / _GATE_FINDINGS_RELATIVE_PATH
    if not path.is_file():
        return None
    try:
        return GateFindingsDocument.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _quality_category_for_gate_check(check_name: str) -> str | None:
    if check_name.startswith("ruff"):
        return "lint"
    if check_name == "ty":
        return "type"
    if check_name.startswith("pytest"):
        return "tests"
    return None


def _verify_severity_from_gate_finding(finding: GateFinding) -> FindingSeverity:
    if finding.severity.value == "critical":
        return FindingSeverity.CRITICAL
    if finding.severity.value in {"high", "medium"}:
        return FindingSeverity.MAJOR
    if finding.severity.value == "low":
        return FindingSeverity.MINOR
    return FindingSeverity.INFO


def _taxonomy_kwargs(name: str) -> dict[str, str]:
    classification = classify_check_name(name)
    if classification is None:
        return {}
    return {
        "stable_id": classification.stable_id,
        "primary_plane": classification.primary_plane.value,
    }


def _record_quality_gate_findings(
    specialist: SpecialistResult,
    document: GateFindingsDocument,
) -> None:
    for finding in document.findings:
        category = _quality_category_for_gate_check(finding.check)
        if category is None:
            continue
        specialist.add(
            _verify_severity_from_gate_finding(finding),
            category,
            finding.message,
            file=finding.file,
            line=finding.line,
            **_taxonomy_kwargs(finding.check),
        )

    for finding in document.accepted_findings:
        category = _quality_category_for_gate_check(finding.check)
        if category is None:
            continue
        specialist.add(
            FindingSeverity.INFO,
            category,
            f"{finding.message} (accepted via {finding.dec_id})",
            file=finding.file,
            line=finding.line,
            **_taxonomy_kwargs(finding.check),
        )


def _record_security_gate_findings(
    specialist: SpecialistResult,
    document: GateFindingsDocument,
) -> None:
    for finding in document.findings:
        category = _SECURITY_CHECK_CATEGORIES.get(finding.check)
        if category is None:
            continue
        severity = _security_gate_severity(category, finding)
        specialist.add(
            severity,
            category,
            finding.message,
            file=finding.file,
            line=finding.line,
            **_taxonomy_kwargs(finding.check),
        )

    for finding in document.accepted_findings:
        category = _SECURITY_CHECK_CATEGORIES.get(finding.check)
        if category is None:
            continue
        specialist.add(
            FindingSeverity.INFO,
            category,
            f"{finding.message} (accepted via {finding.dec_id})",
            file=finding.file,
            line=finding.line,
            **_taxonomy_kwargs(finding.check),
        )


def _security_gate_severity(category: str, finding: GateFinding) -> FindingSeverity:
    if category == "secrets":
        return FindingSeverity.BLOCKER
    if category == "dependency":
        return FindingSeverity.CRITICAL
    return _verify_severity_from_gate_finding(finding)


def verify_quality(project_root: Path, *, profile: str = "normal") -> VerifyScore:
    """Run quality checks and produce a scored report."""
    report, specialist = _start_specialist("quality", profile)

    document = _load_gate_findings_document(project_root)
    if document is not None:
        _record_quality_gate_findings(specialist, document)
    else:
        tool_result = _run(
            ["uv", "run", "ruff", "check", "src/", "--output-format", "json"],
            project_root,
        )
        if tool_result.returncode != 0 and tool_result.stdout:
            try:
                findings = json.loads(tool_result.stdout)
                for finding in findings:
                    specialist.add(
                        FindingSeverity.MAJOR,
                        "lint",
                        finding.get("message", "lint violation"),
                        file=finding.get("filename"),
                        line=finding.get("location", {}).get("row"),
                    )
            except json.JSONDecodeError:
                specialist.add(
                    FindingSeverity.MAJOR,
                    "lint",
                    "ruff check failed (non-JSON output)",
                )

    try:
        from ai_engineering.policy.duplication import _duplication_ratio

        ratio, _total, _dup = _duplication_ratio(project_root / "src" / "ai_engineering")
        if ratio > 3.0:
            specialist.add(
                FindingSeverity.MAJOR,
                "duplication",
                f"Duplication ratio {ratio:.1f}% exceeds 3%",
            )
    except Exception:
        pass

    return _finalize_specialist(report, specialist)


def verify_security(project_root: Path, *, profile: str = "normal") -> VerifyScore:
    """Run security checks and produce a scored report."""
    report, specialist = _start_specialist("security", profile)

    document = _load_gate_findings_document(project_root)
    if document is not None:
        _record_security_gate_findings(specialist, document)
    else:
        _record_gitleaks_findings(specialist, project_root)
        _record_pip_audit_findings(specialist, project_root)

    return _finalize_specialist(report, specialist)


def _record_gitleaks_findings(specialist: SpecialistResult, project_root: Path) -> None:
    """Add secret-scan findings to the security specialist."""
    tool_result = _run(
        [
            "gitleaks",
            "detect",
            "--source",
            ".",
            "--no-banner",
            "--report-format",
            "json",
            "--report-path",
            "/dev/stdout",
        ],
        project_root,
    )
    if tool_result.returncode == 0 or not tool_result.stdout:
        return

    try:
        leaks = json.loads(tool_result.stdout)
    except json.JSONDecodeError:
        return

    for leak in leaks:
        specialist.add(
            FindingSeverity.BLOCKER,
            "secrets",
            f"Secret detected: {leak.get('Description', 'unknown')}",
            file=leak.get("File"),
            line=leak.get("StartLine"),
        )


def _record_pip_audit_findings(specialist: SpecialistResult, project_root: Path) -> None:
    """Add dependency-audit findings to the security specialist."""
    tool_result = _run(pip_audit_command("--format", "json"), project_root)
    if tool_result.returncode == 0:
        return
    if not tool_result.stdout:
        _add_dependency_audit_failure(specialist, "pip-audit failed without producing output")
        return

    try:
        audit = json.loads(tool_result.stdout)
    except json.JSONDecodeError:
        _add_dependency_audit_failure(specialist, "pip-audit failed without valid JSON output")
        return

    for dependency in audit.get("dependencies", []):
        _record_dependency_vulnerabilities(specialist, dependency)


def _record_dependency_vulnerabilities(
    specialist: SpecialistResult, dependency: dict[str, object]
) -> None:
    """Record vulnerabilities for a single dependency entry."""
    dependency_name = str(dependency.get("name", "unknown"))
    for vulnerability in dependency.get("vulns", []):
        vulnerability_id = "unknown vulnerability"
        if isinstance(vulnerability, dict):
            vulnerability_id = str(vulnerability.get("id", vulnerability_id))
        specialist.add(
            FindingSeverity.CRITICAL,
            "dependency",
            f"{dependency_name}: {vulnerability_id}",
        )


def _add_dependency_audit_failure(specialist: SpecialistResult, message: str) -> None:
    """Record a dependency audit tool failure."""
    specialist.add(
        FindingSeverity.CRITICAL,
        "dependency-audit",
        message,
    )


def verify_governance(project_root: Path, *, profile: str = "normal") -> VerifyScore:
    """Run governance checks and produce a scored report."""
    result, specialist = _start_specialist("governance", profile)
    report = validate_content_integrity(project_root)
    for check in report.checks:
        if check.status == IntegrityStatus.FAIL:
            specialist.add(
                FindingSeverity.CRITICAL,
                check.category.value,
                check.message,
                file=check.file_path,
                **_taxonomy_kwargs(check.category.value),
            )
        elif check.status == IntegrityStatus.WARN:
            specialist.add(
                FindingSeverity.MINOR,
                check.category.value,
                check.message,
                file=check.file_path,
                **_taxonomy_kwargs(check.category.value),
            )
    return _finalize_specialist(result, specialist)


def verify_architecture(project_root: Path, *, profile: str = "normal") -> VerifyScore:
    """Check for structural drift such as internal import cycles."""
    result, specialist = _start_specialist("architecture", profile)
    cycles = _detect_import_cycles(project_root)
    for cycle in cycles:
        specialist.add(
            FindingSeverity.CRITICAL,
            "cycle",
            f"Internal import cycle detected: {' -> '.join(cycle)}",
        )
    return _finalize_specialist(result, specialist)


def verify_feature(project_root: Path, *, profile: str = "normal") -> VerifyScore:
    """Assess whether the active spec/plan handoff surface is coherent."""
    work_plane = resolve_active_work_plane(project_root)
    spec_path = work_plane.spec_path
    plan_path = work_plane.plan_path
    spec_file = _project_relative_path(project_root, spec_path)
    plan_file = _project_relative_path(project_root, plan_path)
    if not spec_path.exists():
        return _not_applicable(
            "feature",
            profile,
            f"No active spec was found under {spec_file}.",
        )

    result, specialist = _start_specialist("feature", profile)
    spec_text = spec_path.read_text(encoding="utf-8")
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""

    status = _frontmatter_value(spec_text, "status")
    approval = _frontmatter_value(spec_text, "approval")
    if status and status != "approved":
        specialist.add(
            FindingSeverity.MAJOR,
            "spec-status",
            f"Active spec status is '{status}', not 'approved'.",
            file=spec_file,
        )
    if approval and approval != "approved":
        specialist.add(
            FindingSeverity.MAJOR,
            "spec-approval",
            f"Active spec approval is '{approval}', not 'approved'.",
            file=spec_file,
        )
    if not plan_path.exists() or "No active plan" in plan_text:
        specialist.add(
            FindingSeverity.MAJOR,
            "plan-status",
            "Active spec exists without an actionable plan.",
            file=plan_file,
        )

    return _finalize_specialist(result, specialist)


def _project_relative_path(project_root: Path, path: Path) -> str:
    """Return a stable project-relative path for findings and rationale."""
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def verify_platform(project_root: Path, *, profile: str = "normal") -> VerifyScore:
    """Aggregate all specialists into a platform score."""
    combined = VerifyScore(mode="platform", profile=profile)
    for specialist_name in SPECIALIST_ORDER:
        report = SPECIALIST_MODES[specialist_name](project_root, profile=profile)
        combined.findings.extend(report.findings)
        combined.specialists.extend(report.specialists)
    return combined


def _frontmatter_value(content: str, key: str) -> str | None:
    marker = f"{key}:"
    in_frontmatter = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter and stripped.startswith(marker):
            return stripped.split(":", 1)[1].strip().strip("'\"")
    return None


def _detect_import_cycles(project_root: Path) -> list[list[str]]:
    package_root = project_root / "src" / "ai_engineering"
    if not package_root.is_dir():
        return []

    graph, modules = _build_internal_import_graph(package_root)
    cycles: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    visited: set[str] = set()

    for module in sorted(modules):
        if module not in visited:
            _walk_import_graph(module, graph, modules, visited, [], seen, cycles)
    return cycles


def _build_internal_import_graph(package_root: Path) -> tuple[dict[str, set[str]], set[str]]:
    """Build a module import graph for the ai_engineering package."""
    graph: dict[str, set[str]] = defaultdict(set)
    modules: set[str] = set()
    for file_path in package_root.rglob("*.py"):
        module = _module_name(package_root, file_path)
        modules.add(module)
        graph.setdefault(module, set())
        for import_name in _parsed_internal_imports(file_path, module):
            graph[module].add(import_name)
            modules.add(import_name)
            graph.setdefault(import_name, set())
    return graph, modules


def _parsed_internal_imports(file_path: Path, module: str) -> Iterable[str]:
    """Parse a module file and yield its internal imports."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return ()
    return _internal_imports(module, tree)


def _walk_import_graph(
    node: str,
    graph: dict[str, set[str]],
    modules: set[str],
    visited: set[str],
    visiting: list[str],
    seen: set[tuple[str, ...]],
    cycles: list[list[str]],
) -> None:
    """Depth-first search over the import graph, recording cycles once."""
    visiting.append(node)
    for neighbor in graph.get(node, ()):
        if neighbor not in modules:
            continue
        if neighbor in visiting:
            _record_cycle(neighbor, visiting, seen, cycles)
            continue
        if neighbor in visited:
            continue
        _walk_import_graph(neighbor, graph, modules, visited, visiting, seen, cycles)
    visiting.pop()
    visited.add(node)


def _record_cycle(
    neighbor: str,
    visiting: list[str],
    seen: set[tuple[str, ...]],
    cycles: list[list[str]],
) -> None:
    """Record a discovered cycle if it has not been seen yet."""
    start = visiting.index(neighbor)
    cycle = [*visiting[start:], neighbor]
    key = tuple(cycle)
    if key in seen:
        return
    seen.add(key)
    cycles.append(cycle)


def _module_name(package_root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(package_root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    base = ["ai_engineering", *parts]
    return ".".join(base)


def _internal_imports(module_name: str, tree: ast.AST) -> Iterable[str]:
    package_parts = module_name.split(".")
    parent_parts = package_parts[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from _import_targets(node)
            continue
        if isinstance(node, ast.ImportFrom):
            yield from _import_from_targets(node, parent_parts)


def _import_targets(node: ast.Import) -> Iterable[str]:
    """Yield internal absolute imports from an ``import`` statement."""
    for alias in node.names:
        if alias.name.startswith("ai_engineering"):
            yield alias.name


def _import_from_targets(node: ast.ImportFrom, parent_parts: list[str]) -> Iterable[str]:
    """Yield internal imports from a ``from ... import ...`` statement."""
    if node.level > 0:
        yield from _relative_import_targets(node, parent_parts)
        return
    if node.module and node.module.startswith("ai_engineering"):
        yield from _module_and_alias_targets(node.module, node)


def _relative_import_targets(node: ast.ImportFrom, parent_parts: list[str]) -> Iterable[str]:
    """Resolve a relative import into internal module targets."""
    base_parts = parent_parts[: len(parent_parts) - node.level + 1]
    module_parts = node.module.split(".") if node.module else []
    candidate_parts = [*base_parts, *module_parts]
    if not candidate_parts or candidate_parts[0] != "ai_engineering":
        return ()
    base_module = ".".join(candidate_parts)
    return _module_and_alias_targets(base_module, node)


def _module_and_alias_targets(base_module: str, node: ast.ImportFrom) -> Iterable[str]:
    """Yield a base module plus its imported aliases."""
    yield base_module
    for alias in node.names:
        yield f"{base_module}.{alias.name}"


SPECIALIST_MODES = {
    "quality": verify_quality,
    "security": verify_security,
    "governance": verify_governance,
    "architecture": verify_architecture,
    "feature": verify_feature,
}


MODES = {
    **SPECIALIST_MODES,
    "platform": verify_platform,
}
