#!/usr/bin/env python3
"""Validate bidirectional integrity of selective test scope mapping."""

from __future__ import annotations

import sys
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering.policy.test_scope import ALWAYS_RUN, TEST_SCOPE_RULES  # noqa: E402

EXCLUDED_TEST_FILES: set[str] = set()
EXCLUDED_SOURCE_FILES: set[str] = set()
TIERS: tuple[str, ...] = ("unit", "integration", "e2e")


def _normalize(path: str) -> str:
    return path.strip().replace("\\", "/")


def _matches_glob(path: str, pattern: str) -> bool:
    if fnmatch(path, pattern):
        return True
    return "/**/" in pattern and fnmatch(path, pattern.replace("/**/", "/"))


def _collect_all_tests() -> set[str]:
    return {
        _normalize(str(path.relative_to(ROOT)))
        for path in (ROOT / "tests").rglob("test_*.py")
        if path.is_file()
    }


def _collect_all_sources() -> set[str]:
    return {
        _normalize(str(path.relative_to(ROOT)))
        for path in (ROOT / "src" / "ai_engineering").rglob("*.py")
        if path.is_file()
    }


def _mapped_tests() -> dict[str, dict[str, set[str]]]:
    by_tier: dict[str, dict[str, set[str]]] = {tier: {} for tier in TIERS}
    for rule in TEST_SCOPE_RULES:
        for tier in TIERS:
            for test_path in rule.tiers.get(tier, []):
                path = _normalize(test_path)
                by_tier[tier].setdefault(path, set()).add(rule.name)

    for tier in TIERS:
        for test_path in ALWAYS_RUN.get(tier, []):
            path = _normalize(test_path)
            by_tier[tier].setdefault(path, set()).add("ALWAYS_RUN")

    return by_tier


def _source_coverage_violations(all_sources: set[str]) -> list[str]:
    violations: list[str] = []
    for source in sorted(all_sources):
        if source in EXCLUDED_SOURCE_FILES:
            continue
        covered = False
        for rule in TEST_SCOPE_RULES:
            if any(_matches_glob(source, pattern) for pattern in rule.source_globs):
                covered = True
                break
        if not covered:
            violations.append(f"Unmapped source file: {source}")
    return violations


def _tier_prefix(tier: str) -> str:
    return f"tests/{tier}/"


def main() -> int:
    all_tests = _collect_all_tests()
    all_sources = _collect_all_sources()
    mapped = _mapped_tests()

    failures: list[str] = []

    mapped_test_paths: set[str] = set()
    for tier in TIERS:
        expected_prefix = _tier_prefix(tier)
        tier_entries = mapped[tier]

        for test_path, owners in sorted(tier_entries.items()):
            mapped_test_paths.add(test_path)

            if len(owners) > 1 and "ALWAYS_RUN" not in owners:
                failures.append(
                    "Duplicate mapping in tier "
                    f"'{tier}' for {test_path}: {', '.join(sorted(owners))}"
                )

            if not test_path.startswith(expected_prefix):
                failures.append(
                    f"Tier mismatch for {test_path}: mapped under '{tier}', "
                    f"expected prefix '{expected_prefix}'"
                )

            if not (ROOT / test_path).is_file():
                failures.append(f"Mapped test does not exist: {test_path}")

    unmapped_tests = sorted(all_tests - mapped_test_paths - EXCLUDED_TEST_FILES)
    if unmapped_tests:
        failures.extend(f"Unmapped test file: {path}" for path in unmapped_tests)

    failures.extend(_source_coverage_violations(all_sources))

    if failures:
        print("test mapping integrity failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        "test mapping integrity passed "
        f"({len(mapped_test_paths)} mapped tests, "
        f"{len(all_tests)} total tests, {len(all_sources)} source files)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
