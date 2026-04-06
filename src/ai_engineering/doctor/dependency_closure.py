"""Framework runtime dependency-closure validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import metadata


@dataclass(frozen=True)
class ClosureViolation:
    """A framework runtime dependency that does not satisfy its declared constraint."""

    package: str
    dependency: str
    required_specifier: str
    actual_version: str


def validate_framework_dependency_closure() -> list[ClosureViolation]:
    """Return framework runtime dependency violations that can break CLI import."""
    violations: list[ClosureViolation] = []
    specifier = _required_specifier(_required_dependencies("typer"), "click")
    if specifier is None:
        return violations

    actual_version = _installed_version("click")
    if not _satisfies_specifier(actual_version, specifier):
        violations.append(
            ClosureViolation(
                package="typer",
                dependency="click",
                required_specifier=specifier,
                actual_version=actual_version,
            )
        )
    return violations


def _installed_version(name: str) -> str:
    return metadata.version(name)


def _required_dependencies(name: str) -> list[str]:
    requirements = metadata.requires(name)
    return list(requirements or [])


def _required_specifier(requirements: list[str], dependency: str) -> str | None:
    dependency_prefix = dependency.lower()
    for requirement in requirements:
        normalized = requirement.split(";", 1)[0].strip()
        if not normalized.lower().startswith(dependency_prefix):
            continue
        specifier = normalized[len(dependency) :].strip()
        return specifier or None
    return None


def _satisfies_specifier(version: str, specifier: str) -> bool:
    parts = [part.strip() for part in specifier.split(",") if part.strip()]
    return all(_matches_single_specifier(version, part) for part in parts)


def _matches_single_specifier(version: str, specifier: str) -> bool:
    for operator in (">=", "<=", "==", "!=", ">", "<"):
        if specifier.startswith(operator):
            expected = specifier[len(operator) :].strip()
            return _compare_versions(version, expected, operator)
    return True


def _compare_versions(left: str, right: str, operator: str) -> bool:
    left_tuple = _version_tuple(left)
    right_tuple = _version_tuple(right)
    if operator == ">=":
        return left_tuple >= right_tuple
    if operator == "<=":
        return left_tuple <= right_tuple
    if operator == "==":
        return left_tuple == right_tuple
    if operator == "!=":
        return left_tuple != right_tuple
    if operator == ">":
        return left_tuple > right_tuple
    if operator == "<":
        return left_tuple < right_tuple
    return True


def _version_tuple(version: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", version)
    return tuple(int(number) for number in numbers)
