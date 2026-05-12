"""Category 1: File Existence — verify all internal path references resolve."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.state.control_plane import resolve_state_plane_contract
from ai_engineering.state.work_plane import ActiveWorkPlane, resolve_active_work_plane
from ai_engineering.validator._shared import (
    _KNOWN_OPTIONAL_PATHS,
    _PATH_REF_PATTERN,
    FileCache,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
    _is_source_repo,
)

_SPECS_ROOT_LABEL = "specs/"
_SOURCE_REPO_CONTROL_PLANE_PATHS = [
    "CONSTITUTION.md",
    "src/ai_engineering/templates/project/CONSTITUTION.md",
]


def _is_pristine_install(target: Path) -> bool:
    """True if the consumer project has no user commits yet.

    Detection: either ``.git`` is absent (no repo) or the repo has zero
    refs (no commits). Used to suppress optional-file WARNs on a brand
    new install that has not yet been touched by a developer.
    """
    git_dir = target / ".git"
    if not git_dir.exists():
        return True
    head_file = git_dir / "HEAD" if git_dir.is_dir() else None
    if head_file is None or not head_file.is_file():
        return True
    refs_dir = git_dir / "refs" / "heads"
    if not refs_dir.exists():
        return True
    try:
        has_ref = any(refs_dir.iterdir())
    except OSError:
        has_ref = False
    if has_ref:
        return False
    # No branch refs yet (initial `git init` state).
    packed_refs = git_dir / "packed-refs"
    return not packed_refs.is_file()


def _check_file_existence(
    target: Path, report: IntegrityReport, *, cache: FileCache | None = None
) -> None:
    """Verify all internal path references resolve to existing files."""
    ai_dir = target / ".ai-engineering"
    if not ai_dir.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="governance-directory",
                status=IntegrityStatus.FAIL,
                message=".ai-engineering/ directory not found",
            )
        )
        return

    # Exclude specs/ from reference checking. Spec files contain illustrative
    # paths (e.g., `.claude/skills/ai-X/SKILL.md`) as examples in acceptance
    # criteria and work area descriptions. These are not real file references
    # and trigger false positives in the path reference validator.
    specs_dir = ai_dir / "specs"
    specs_exists = specs_dir.is_dir()

    # Exclude runtime/ from reference checking (spec-123 T-8.x; relocated
    # under ``.ai-engineering/runtime/`` by spec-125 Wave 2). This subtree is
    # gitignored ephemeral state — autopilot wave artifacts, hook
    # checkpoints, tool outputs, etc. — and should never gate CI. Stale
    # references to retired skills/agents inside these artifacts are expected
    # operational debris between cleanup waves.
    runtime_dir = ai_dir / "runtime"

    broken_refs = _collect_broken_references(
        target=target,
        ai_dir=ai_dir,
        specs_dir=specs_dir,
        specs_exists=specs_exists,
        runtime_dir=runtime_dir,
        cache=cache,
    )
    _record_broken_reference_results(report, broken_refs)

    # Verify canonical three-file specs/ contract: spec.md, plan.md, _history.md
    work_plane = resolve_active_work_plane(target)
    if work_plane.specs_dir.is_dir():
        _record_spec_buffer_result(report, work_plane)

    if _is_source_repo(target):
        _record_source_repo_control_plane_paths(report, target)


def _collect_broken_references(
    *,
    target: Path,
    ai_dir: Path,
    specs_dir: Path,
    specs_exists: bool,
    runtime_dir: Path,
    cache: FileCache | None,
) -> list[tuple[str, str, str, str]]:
    broken_refs: list[tuple[str, str, str, str]] = []
    runtime_exists = runtime_dir.is_dir()
    for md_file in _markdown_files(ai_dir, cache):
        if specs_exists and md_file.is_relative_to(specs_dir):
            continue
        if runtime_exists and md_file.is_relative_to(runtime_dir):
            continue
        content = md_file.read_text(encoding="utf-8", errors="replace")
        origin_relative = md_file.relative_to(target).as_posix()
        for match in _PATH_REF_PATTERN.finditer(content):
            ref_path = _normalized_reference_path(match.group(1) or match.group(0))
            if _should_skip_reference_path(ref_path, origin=origin_relative):
                continue
            canonical_ref = _legacy_state_plane_reference(ref_path)
            if canonical_ref is not None:
                broken_refs.append(
                    (
                        md_file.relative_to(target).as_posix(),
                        "legacy-state-plane-reference",
                        (
                            f"Legacy state-plane compatibility reference '{ref_path}' should use "
                            f"'{canonical_ref}'"
                        ),
                        ref_path,
                    )
                )
                continue
            if _reference_exists(target, ai_dir, ref_path):
                continue
            broken_refs.append(
                (
                    md_file.relative_to(target).as_posix(),
                    "broken-reference",
                    f"Reference to '{ref_path}' not found",
                    ref_path,
                )
            )
    return broken_refs


def _markdown_files(ai_dir: Path, cache: FileCache | None) -> list[Path]:
    if cache:
        return [path for path in cache.rglob(ai_dir, "*.md") if path.is_file()]
    return sorted(ai_dir.rglob("*.md"))


def _normalized_reference_path(ref_path: str) -> str:
    normalized = ref_path.strip("`").lstrip(".")
    if normalized.startswith("ai-engineering/"):
        return normalized[len("ai-engineering/") :]
    return normalized


def _should_skip_reference_path(ref_path: str, *, origin: str | None = None) -> bool:
    """Return True when ``ref_path`` should be ignored by the validator.

    spec-132 D-132-09: SKILL.md descriptors in
    ``.claude/`` / ``.codex/`` / ``.gemini/`` / ``.github/`` carry
    implementation notes that reference ``src/ai_engineering/...``
    paths. Those paths never ship to consumers, so we skip them when
    the origin file is a SKILL.md descriptor.

    Args:
        ref_path: Normalised reference path extracted from a markdown
            file.
        origin: Optional origin path (relative to repo root). When the
            origin is a SKILL.md descriptor, source-repo refs under
            ``src/ai_engineering/`` are treated as LLM-only notes and
            skipped.
    """
    if "<" in ref_path and ">" in ref_path:
        return True
    if "{" in ref_path and "}" in ref_path:
        return True
    if "$" in ref_path:
        return True
    if ref_path.startswith(("agents/agents/", "agents/skills/", "codex/agents/", "codex/skills/")):
        return True
    # spec-132 D-132-09: source-repo refs from SKILL.md are LLM notes.
    if (
        origin is not None
        and origin.endswith("SKILL.md")
        and ref_path.startswith("src/ai_engineering/")
    ):
        return True
    return ref_path in _KNOWN_OPTIONAL_PATHS


def _reference_exists(target: Path, ai_dir: Path, ref_path: str) -> bool:
    if (ai_dir / ref_path).exists():
        return True

    fallback_roots = [
        target / ".claude",
        target / ".codex",
        target / ".gemini",
        target / ".github",
    ]
    candidates = [ref_path, _ide_adapted_reference(ref_path)]
    return any((root / candidate).exists() for root in fallback_roots for candidate in candidates)


def _ide_adapted_reference(ref_path: str) -> str:
    if ref_path.startswith("agents/"):
        name = ref_path.removeprefix("agents/")
        return f"agents/ai-{name}"
    if ref_path.startswith("skills/"):
        parts = ref_path.removeprefix("skills/").split("/", 1)
        if len(parts) == 2:
            return f"skills/ai-{parts[0]}/{parts[1]}"
    return ref_path


def _record_broken_reference_results(
    report: IntegrityReport,
    broken_refs: list[tuple[str, str, str, str]],
) -> None:
    if not broken_refs:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="path-references",
                status=IntegrityStatus.OK,
                message="All internal path references resolve",
            )
        )
        return

    for source, check_name, message, _ref in broken_refs:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name=check_name,
                status=IntegrityStatus.FAIL,
                message=message,
                file_path=source,
            )
        )


def _legacy_state_plane_reference(ref_path: str) -> str | None:
    repo_relative = _state_plane_repo_relative_path(ref_path)
    if repo_relative is None:
        return None

    contract = resolve_state_plane_contract()
    canonical_relative = contract.canonical_relative_path(repo_relative)
    if canonical_relative == repo_relative:
        return None
    if contract.compatibility_shim_relative_path(canonical_relative) != repo_relative:
        return None

    if canonical_relative.startswith(".ai-engineering/"):
        return canonical_relative.removeprefix(".ai-engineering/")
    return canonical_relative


def _state_plane_repo_relative_path(ref_path: str) -> str | None:
    normalized = ref_path.strip().replace("\\", "/").lstrip("./")
    if normalized.startswith("ai-engineering/"):
        return f".{normalized}"
    if normalized.startswith(("state/", "specs/")):
        return f".ai-engineering/{normalized}"
    return None


def _record_spec_buffer_result(report: IntegrityReport, work_plane: ActiveWorkPlane) -> None:
    """Verify the canonical three-file specs/ contract: spec.md, plan.md, _history.md.

    spec-132 D-132-09: ``_history.md`` is owned by ``/ai-cleanup`` per
    spec-131 D-131-04 -- the installer does not seed it. When the spec
    buffer is otherwise complete (``spec.md`` + ``plan.md`` both
    present) the missing ``_history.md`` downgrades to WARN so the
    fresh-install validator does not fail. On a pristine install (zero
    commits in the consumer repo) the WARN is suppressed entirely so
    first contact is silent.
    """
    target = work_plane.project_root
    required_spec_files = {
        "spec.md": work_plane.spec_path,
        "plan.md": work_plane.plan_path,
        "_history.md": work_plane.history_path,
    }
    missing_spec = [name for name, path in required_spec_files.items() if not path.exists()]
    if missing_spec:
        spec_plan_present = (
            work_plane.spec_path.exists()
            and work_plane.plan_path.exists()
            and missing_spec == ["_history.md"]
        )
        if spec_plan_present:
            if _is_pristine_install(target):
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.FILE_EXISTENCE,
                        name="spec-buffer",
                        status=IntegrityStatus.OK,
                        message=(
                            "Optional _history.md absent on pristine install; "
                            "/ai-cleanup will create it on first lifecycle close."
                        ),
                        file_path=_SPECS_ROOT_LABEL,
                    )
                )
                return
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="spec-buffer",
                    status=IntegrityStatus.WARN,
                    message=(
                        "Optional _history.md missing; /ai-cleanup will create it on "
                        "first lifecycle close (spec-131 D-131-04)."
                    ),
                    file_path=_SPECS_ROOT_LABEL,
                )
            )
            return
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="spec-buffer",
                status=IntegrityStatus.FAIL,
                message=f"Missing spec files: {', '.join(missing_spec)}",
                file_path=_SPECS_ROOT_LABEL,
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.FILE_EXISTENCE,
            name="spec-buffer",
            status=IntegrityStatus.OK,
            message="Spec buffer files present (spec.md, plan.md, _history.md)",
            file_path=_SPECS_ROOT_LABEL,
        )
    )


def _record_source_repo_control_plane_paths(report: IntegrityReport, target: Path) -> None:
    missing_paths = [
        path for path in _SOURCE_REPO_CONTROL_PLANE_PATHS if not (target / path).exists()
    ]
    if missing_paths:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="control-plane-paths",
                status=IntegrityStatus.FAIL,
                message="Missing normalized control-plane path(s): " + ", ".join(missing_paths),
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.FILE_EXISTENCE,
            name="control-plane-paths",
            status=IntegrityStatus.OK,
            message="Normalized control-plane paths present in source repo and templates",
        )
    )
