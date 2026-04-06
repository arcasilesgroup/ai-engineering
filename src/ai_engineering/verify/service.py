"""Verify service -- aggregates tool outputs into scored reports."""

from __future__ import annotations

import ast
import json
import subprocess
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from ai_engineering.validator._shared import IntegrityStatus
from ai_engineering.validator.service import validate_content_integrity
from ai_engineering.verify.scoring import (
    FindingSeverity,
    SpecialistResult,
    VerifyScore,
)
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


def verify_quality(project_root: Path, *, profile: str = "normal") -> VerifyScore:
    """Run quality checks and produce a scored report."""
    report, specialist = _start_specialist("quality", profile)

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
    if tool_result.returncode != 0 and tool_result.stdout:
        try:
            leaks = json.loads(tool_result.stdout)
            for leak in leaks:
                specialist.add(
                    FindingSeverity.BLOCKER,
                    "secrets",
                    f"Secret detected: {leak.get('Description', 'unknown')}",
                    file=leak.get("File"),
                    line=leak.get("StartLine"),
                )
        except json.JSONDecodeError:
            pass

    tool_result = _run(pip_audit_command("--format", "json"), project_root)
    if tool_result.returncode != 0:
        if tool_result.stdout:
            try:
                audit = json.loads(tool_result.stdout)
                for dependency in audit.get("dependencies", []):
                    for vulnerability in dependency.get("vulns", []):
                        vulnerability_id = vulnerability.get(
                            "id",
                            "unknown vulnerability",
                        )
                        specialist.add(
                            FindingSeverity.CRITICAL,
                            "dependency",
                            f"{dependency['name']}: {vulnerability_id}",
                        )
            except json.JSONDecodeError:
                specialist.add(
                    FindingSeverity.CRITICAL,
                    "dependency-audit",
                    "pip-audit failed without valid JSON output",
                )
        else:
            specialist.add(
                FindingSeverity.CRITICAL,
                "dependency-audit",
                "pip-audit failed without producing output",
            )

    return _finalize_specialist(report, specialist)


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
            )
        elif check.status == IntegrityStatus.WARN:
            specialist.add(
                FindingSeverity.MINOR,
                check.category.value,
                check.message,
                file=check.file_path,
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
    spec_path = project_root / ".ai-engineering" / "specs" / "spec.md"
    plan_path = project_root / ".ai-engineering" / "specs" / "plan.md"
    if not spec_path.exists():
        return _not_applicable(
            "feature",
            profile,
            "No active spec was found under .ai-engineering/specs/spec.md.",
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
            file=".ai-engineering/specs/spec.md",
        )
    if approval and approval != "approved":
        specialist.add(
            FindingSeverity.MAJOR,
            "spec-approval",
            f"Active spec approval is '{approval}', not 'approved'.",
            file=".ai-engineering/specs/spec.md",
        )
    if not plan_path.exists() or "No active plan" in plan_text:
        specialist.add(
            FindingSeverity.MAJOR,
            "plan-status",
            "Active spec exists without an actionable plan.",
            file=".ai-engineering/specs/plan.md",
        )

    return _finalize_specialist(result, specialist)


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

    graph: dict[str, set[str]] = defaultdict(set)
    modules: set[str] = set()
    for file_path in package_root.rglob("*.py"):
        module = _module_name(package_root, file_path)
        modules.add(module)
        graph.setdefault(module, set())
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for import_name in _internal_imports(module, tree):
            graph[module].add(import_name)
            modules.add(import_name)
            graph.setdefault(import_name, set())

    cycles: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    visiting: list[str] = []
    visited: set[str] = set()

    def dfs(node: str) -> None:
        visiting.append(node)
        for neighbor in graph.get(node, ()):
            if neighbor not in modules:
                continue
            if neighbor in visiting:
                start = visiting.index(neighbor)
                cycle = [*visiting[start:], neighbor]
                key = tuple(cycle)
                if key not in seen:
                    seen.add(key)
                    cycles.append(cycle)
                continue
            if neighbor in visited:
                continue
            dfs(neighbor)
        visiting.pop()
        visited.add(node)

    for module in sorted(modules):
        if module not in visited:
            dfs(module)
    return cycles


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
            for alias in node.names:
                if alias.name.startswith("ai_engineering"):
                    yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                base_parts = parent_parts[: len(parent_parts) - node.level + 1]
                module_parts = node.module.split(".") if node.module else []
                candidate_parts = [*base_parts, *module_parts]
                if candidate_parts and candidate_parts[0] == "ai_engineering":
                    base_module = ".".join(candidate_parts)
                    yield base_module
                    for alias in node.names:
                        yield f"{base_module}.{alias.name}"
            elif node.module and node.module.startswith("ai_engineering"):
                yield node.module
                for alias in node.names:
                    yield f"{node.module}.{alias.name}"


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
