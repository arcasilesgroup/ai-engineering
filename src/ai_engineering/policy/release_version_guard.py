"""Guard governed framework version surfaces in pull requests."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from ai_engineering.git.operations import get_changed_files, get_merge_base, run_git

_RELEASE_BRANCH_PREFIX = "release/v"
_CHANGELOG_PATH = "CHANGELOG.md"

_SURFACE_RULES: tuple[tuple[str, str, re.Pattern[str] | None], ...] = (
    (
        "pyproject.version",
        "pyproject.toml",
        re.compile(r'^[+-]version\s*=\s*"', flags=re.MULTILINE),
    ),
    (
        "root-manifest.framework_version",
        ".ai-engineering/manifest.yml",
        re.compile(r"^[+-]framework_version\s*:", flags=re.MULTILINE),
    ),
    (
        "template-manifest.framework_version",
        "src/ai_engineering/templates/.ai-engineering/manifest.yml",
        re.compile(r"^[+-]framework_version\s*:", flags=re.MULTILINE),
    ),
    (
        "version-registry",
        "src/ai_engineering/version/registry.json",
        None,
    ),
)

_REQUIRED_RELEASE_FILES = frozenset(path for _, path, _ in _SURFACE_RULES) | frozenset(
    {_CHANGELOG_PATH}
)


def normalize_paths(paths: list[str]) -> set[str]:
    """Return normalized relative paths for changed-file comparisons."""
    normalized: set[str] = set()
    for path in paths:
        text = path.strip()
        if not text:
            continue
        normalized.add(Path(text).as_posix().removeprefix("./"))
    return normalized


def detect_changed_version_surfaces(diff_by_file: dict[str, str]) -> set[str]:
    """Return the governed release surfaces whose version lines changed."""
    surfaces: set[str] = set()
    for surface_name, file_path, line_pattern in _SURFACE_RULES:
        diff_text = diff_by_file.get(file_path, "")
        if not diff_text:
            continue
        if line_pattern is None:
            if _has_substantive_diff(diff_text):
                surfaces.add(surface_name)
            continue
        if line_pattern.search(diff_text):
            surfaces.add(surface_name)
    return surfaces


def evaluate_release_version_guard(
    changed_files: list[str],
    changed_surfaces: set[str],
    *,
    event_name: str,
    head_ref: str,
) -> tuple[bool, str]:
    """Evaluate whether changed version surfaces are allowed in the current PR context."""
    if event_name != "pull_request":
        return True, "release-version-guard skipped: only enforced on pull_request events"

    if not changed_surfaces:
        return True, "release-version-guard passed: no governed version surfaces changed"

    if not head_ref.startswith(_RELEASE_BRANCH_PREFIX):
        changed = ", ".join(sorted(changed_surfaces))
        return (
            False,
            "release-version-guard failed: governed version surfaces changed "
            f"({changed}) outside a release PR. Use 'ai-eng release <VERSION>' "
            "to create the release/v<version> branch and release commit.",
        )

    normalized_files = normalize_paths(changed_files)
    missing_files = sorted(_REQUIRED_RELEASE_FILES - normalized_files)
    if missing_files:
        missing = ", ".join(missing_files)
        return (
            False,
            "release-version-guard failed: release PRs that change governed version surfaces "
            "must include the full release file set. Missing: "
            f"{missing}.",
        )

    changed = ", ".join(sorted(changed_surfaces))
    return (
        True,
        "release-version-guard passed: release PR updates governed version surfaces "
        f"({changed}) through the expected release branch.",
    )


def collect_release_version_changes(
    project_root: Path, base_ref: str
) -> tuple[list[str], set[str]]:
    """Collect changed files and governed version surfaces relative to ``base_ref``."""
    remote_base = f"origin/{base_ref}"
    changed_files = get_changed_files(project_root, remote_base)
    merge_base = get_merge_base(project_root, remote_base)
    normalized_files = normalize_paths(changed_files)

    diff_by_file: dict[str, str] = {}
    for _, file_path, _ in _SURFACE_RULES:
        if file_path not in normalized_files:
            continue
        diff_by_file[file_path] = _read_diff(project_root, merge_base, file_path)

    changed_surfaces = detect_changed_version_surfaces(diff_by_file)
    return sorted(normalized_files), changed_surfaces


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Block governed version-surface edits outside release pull requests"
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--event-name", default=os.getenv("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--head-ref", default=os.getenv("GITHUB_HEAD_REF", ""))
    parser.add_argument("--base-ref", default=os.getenv("GITHUB_BASE_REF", ""))
    args = parser.parse_args()

    event_name = args.event_name.strip()
    if event_name != "pull_request":
        print("release-version-guard skipped: only enforced on pull_request events")
        return 0

    head_ref = args.head_ref.strip()
    base_ref = args.base_ref.strip()
    if not head_ref or not base_ref:
        print(
            "release-version-guard failed: pull_request context requires both head_ref and base_ref"
        )
        return 1

    project_root = Path(args.project_root).resolve()
    try:
        changed_files, changed_surfaces = collect_release_version_changes(project_root, base_ref)
    except RuntimeError as exc:
        print(f"release-version-guard failed: unable to inspect git diff: {exc}")
        return 1

    passed, message = evaluate_release_version_guard(
        changed_files,
        changed_surfaces,
        event_name=event_name,
        head_ref=head_ref,
    )
    print(message)
    return 0 if passed else 1


def _has_substantive_diff(diff_text: str) -> bool:
    for line in diff_text.splitlines():
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith(("+", "-")):
            return True
    return False


def _read_diff(project_root: Path, merge_base: str, file_path: str) -> str:
    ok, output = run_git(
        ["diff", "--unified=0", f"{merge_base}...HEAD", "--", file_path],
        project_root,
    )
    if not ok:
        raise RuntimeError(f"failed to diff {file_path}: {output}")
    return output


if __name__ == "__main__":
    raise SystemExit(main())
