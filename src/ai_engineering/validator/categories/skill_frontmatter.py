"""Category 7: Skill Frontmatter — required YAML metadata and requirement schema validity."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

from ai_engineering.validator._shared import (
    _FRONTMATTER_RE,
    _KEBAB_RE,
    _SEMVER_RE,
    _SUPPORTED_OSES,
    FileCache,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
)


def _as_string_list(value: object) -> list[str] | None:
    """Return *value* as list[str] when valid, else None."""
    if not isinstance(value, list):
        return None
    if any(not isinstance(item, str) for item in value):
        return None
    return [item for item in value if isinstance(item, str)]


def _validate_skill_identity(
    frontmatter: dict[str, object],
    file_stem: str,
    rel: str,
    report: IntegrityReport,
) -> int:
    """Validate name and version fields. Returns failure count."""
    failures = 0
    name = frontmatter.get("name")
    version = frontmatter.get("version")
    if version is None:
        metadata = frontmatter.get("metadata")
        if isinstance(metadata, dict):
            metadata_dict = cast(dict[str, object], metadata)
            if "version" in metadata_dict:
                version = metadata_dict["version"]

    if not isinstance(name, str) or not _KEBAB_RE.fullmatch(name) or name != file_stem:
        failures += 1
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.SKILL_FRONTMATTER,
                name="invalid-name",
                status=IntegrityStatus.FAIL,
                message=f"Frontmatter 'name' must be kebab-case and match filename ('{file_stem}')",
                file_path=rel,
            )
        )

    if not isinstance(version, str) or not _SEMVER_RE.fullmatch(version):
        failures += 1
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.SKILL_FRONTMATTER,
                name="invalid-version",
                status=IntegrityStatus.FAIL,
                message="Frontmatter 'version' must be semver (e.g. 1.0.0)",
                file_path=rel,
            )
        )

    return failures


def _validate_skill_requires(
    frontmatter: dict[str, object],
    rel: str,
    report: IntegrityReport,
) -> int:
    """Validate requires and os fields. Returns failure count."""
    failures = 0

    requires = frontmatter.get("requires")
    if requires is not None:
        if not isinstance(requires, dict):
            failures += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.SKILL_FRONTMATTER,
                    name="invalid-requires",
                    status=IntegrityStatus.FAIL,
                    message="Frontmatter 'requires' must be an object",
                    file_path=rel,
                )
            )
        else:
            req_dict: dict[str, object] = requires  # type: ignore[assignment]
            for req_key in ("bins", "anyBins", "env", "config"):
                if req_key in req_dict and _as_string_list(req_dict[req_key]) is None:
                    failures += 1
                    report.checks.append(
                        IntegrityCheckResult(
                            category=IntegrityCategory.SKILL_FRONTMATTER,
                            name=f"invalid-requires-{req_key}",
                            status=IntegrityStatus.FAIL,
                            message=f"Frontmatter requires.{req_key} must be a list of strings",
                            file_path=rel,
                        )
                    )

    os_list = frontmatter.get("os")
    if os_list is not None:
        os_values = _as_string_list(os_list)
        if os_values is None:
            failures += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.SKILL_FRONTMATTER,
                    name="invalid-os",
                    status=IntegrityStatus.FAIL,
                    message="Frontmatter 'os' must be a list of strings",
                    file_path=rel,
                )
            )
        else:
            invalid = [platform for platform in os_values if platform not in _SUPPORTED_OSES]
            if invalid:
                failures += 1
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.SKILL_FRONTMATTER,
                        name="invalid-os-values",
                        status=IntegrityStatus.FAIL,
                        message=f"Frontmatter 'os' has unsupported values: {', '.join(invalid)}",
                        file_path=rel,
                    )
                )

    return failures


def _parse_skill_frontmatter(
    text: str,
    rel: str,
    report: IntegrityReport,
) -> dict[str, object] | None:
    """Extract and parse YAML frontmatter. Returns dict or None on failure."""
    fm_match = _FRONTMATTER_RE.match(text)
    if not fm_match:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.SKILL_FRONTMATTER,
                name="missing-frontmatter",
                status=IntegrityStatus.FAIL,
                message="Missing YAML frontmatter block",
                file_path=rel,
            )
        )
        return None

    try:
        frontmatter = yaml.safe_load(fm_match.group(1)) or {}
    except yaml.YAMLError as exc:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.SKILL_FRONTMATTER,
                name="invalid-frontmatter-yaml",
                status=IntegrityStatus.FAIL,
                message=f"Invalid frontmatter YAML: {exc}",
                file_path=rel,
            )
        )
        return None

    if not isinstance(frontmatter, dict):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.SKILL_FRONTMATTER,
                name="invalid-frontmatter-type",
                status=IntegrityStatus.FAIL,
                message="Frontmatter must parse to a YAML mapping/object",
                file_path=rel,
            )
        )
        return None

    return frontmatter


def _check_skill_frontmatter(
    target: Path, report: IntegrityReport, *, cache: FileCache | None = None
) -> None:
    """Validate YAML frontmatter in all skill files."""
    # Skills now live in IDE-specific directories, not .ai-engineering/skills/
    ide_skill_dirs = [
        target / ".claude" / "skills",
        target / ".agents" / "skills",
    ]
    skills_roots = [d for d in ide_skill_dirs if d.is_dir()]
    if not skills_roots:
        # Neither IDE skill directory exists — return empty results, not an error
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.SKILL_FRONTMATTER,
                name="skill-frontmatter",
                status=IntegrityStatus.OK,
                message="No IDE skill directories found; skipping frontmatter validation",
            )
        )
        return

    checked = 0
    failures = 0
    skill_files: list[Path] = []
    for skills_root in skills_roots:
        if cache:
            skill_files.extend(p for p in cache.rglob(skills_root, "SKILL.md") if p.is_file())
        else:
            skill_files.extend(sorted(skills_root.rglob("SKILL.md")))
    for skill_file in skill_files:
        checked += 1
        rel = skill_file.relative_to(target).as_posix()
        text = skill_file.read_text(encoding="utf-8", errors="replace")

        frontmatter = _parse_skill_frontmatter(text, rel, report)
        if frontmatter is None:
            failures += 1
            continue

        # Directory layout: skills/<name>/SKILL.md (flat, no categories)
        # name = parent directory (e.g. "debug")
        skill_name = skill_file.parent.name
        failures += _validate_skill_identity(frontmatter, skill_name, rel, report)
        failures += _validate_skill_requires(frontmatter, rel, report)

    if failures == 0:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.SKILL_FRONTMATTER,
                name="skill-frontmatter",
                status=IntegrityStatus.OK,
                message=f"Validated frontmatter in {checked} skills",
            )
        )
