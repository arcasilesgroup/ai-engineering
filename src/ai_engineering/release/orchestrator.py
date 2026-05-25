"""Governed release orchestration service."""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from ai_engineering.git.operations import current_branch, run_git
from ai_engineering.release.changelog import promote_unreleased, validate_changelog
from ai_engineering.release.version_bump import (
    _ROOT_MANIFEST_REL,
    _TEMPLATE_MANIFEST_REL,
    bump_python_version,
    compare_versions,
    detect_current_version,
    validate_semver,
)
from ai_engineering.state.audit import emit_deploy_event
from ai_engineering.state.service import load_install_state, save_install_state
from ai_engineering.vcs.protocol import (
    CreateTagContext,
    PipelineStatusContext,
    VcsContext,
    VcsProvider,
)
from ai_engineering.verify.service import verify_release

_RELEASE_PACKET_NAME = "release-packet.json"
_RELEASE_READINESS_NAME = "release-readiness.json"
_CHANGELOG_REL = Path("CHANGELOG.md")
_LOCKFILE_NAME = "uv.lock"
# Editable-root pin in uv.lock: only the project's own `source = { editable = "." }`
# package block is rewritten; dependency pins are left untouched.
_LOCK_EDITABLE_ROOT_RE = re.compile(
    r'(\[\[package\]\]\nname = "[^"]+"\nversion = ")([^"]+)("\nsource = \{ editable = "\." \})'
)


class Clock(Protocol):
    """Clock abstraction for deterministic tests."""

    def utcnow(self) -> datetime: ...


class CommandRunner(Protocol):
    """Command execution abstraction for deterministic tests."""

    def run(self, cmd: list[str], cwd: Path, timeout: int = 60) -> tuple[bool, str]: ...


class SystemClock:
    """Clock implementation backed by system UTC time."""

    def utcnow(self) -> datetime:
        return datetime.now(tz=UTC)


class SubprocessRunner:
    """Command runner implementation backed by subprocess.run."""

    def run(self, cmd: list[str], cwd: Path, timeout: int = 60) -> tuple[bool, str]:
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            output = (proc.stdout + "\n" + proc.stderr).strip()
            return proc.returncode == 0, output
        except FileNotFoundError:
            return False, f"Command not found: {cmd[0]}"
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s: {' '.join(cmd)}"


@dataclass
class ReleaseConfig:
    """Release execution options."""

    version: str
    project_root: Path
    wait: bool = False
    dry_run: bool = False
    skip_bump: bool = False
    wait_timeout: int = 600


@dataclass
class PhaseResult:
    """Result of a single orchestration phase."""

    phase: str
    success: bool
    output: str = ""
    skipped: bool = False
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReleaseDryRunPlan:
    """Structured no-write preview for governed release execution."""

    old_version: str
    target_version: str
    release_branch: str
    tag: str
    governed_changed_files: list[str]
    changelog_promotion: str
    workflow_trigger: str
    testpypi_stage: str
    pypi_stage: str
    readiness_gate: str
    release_packet_outputs: str

    def to_dict(self) -> dict[str, object]:
        return {
            "old_version": self.old_version,
            "target_version": self.target_version,
            "release_branch": self.release_branch,
            "tag": self.tag,
            "governed_changed_files": list(self.governed_changed_files),
            "changelog_promotion": self.changelog_promotion,
            "workflow_trigger": self.workflow_trigger,
            "testpypi_stage": self.testpypi_stage,
            "pypi_stage": self.pypi_stage,
            "readiness_gate": self.readiness_gate,
            "release_packet_outputs": self.release_packet_outputs,
        }


@dataclass
class ReleaseResult:
    """Final result of the release command."""

    success: bool
    phases: list[PhaseResult]
    version: str
    tag_name: str
    pr_url: str = ""
    release_url: str = ""
    pipeline_status: str = ""
    errors: list[str] = field(default_factory=list)
    bump_files: list[str] = field(default_factory=list)
    readiness: dict[str, object] | None = None
    dry_run_plan: dict[str, object] | None = None
    release_packet_url: str = ""
    release_packet_ref: str = ""


@dataclass
class ReleaseState:
    """Detected repository state used for idempotent execution."""

    release_branch: str
    local_branch_exists: bool
    remote_branch_exists: bool
    tag_exists: bool
    current_version: str


def execute_release(
    config: ReleaseConfig,
    provider: VcsProvider,
    clock: Clock | None = None,
    runner: CommandRunner | None = None,
) -> ReleaseResult:
    """Orchestrate full release: validate -> prepare -> PR -> tag -> monitor."""
    clock = clock or SystemClock()
    runner = runner or SubprocessRunner()
    tag_name = f"v{config.version}"
    phases: list[PhaseResult] = []
    result = ReleaseResult(
        success=False,
        phases=phases,
        version=config.version,
        tag_name=tag_name,
    )

    errors = _validate(config, provider)
    if errors:
        phases.append(PhaseResult(phase="validate", success=False, output="; ".join(errors)))
        result.errors.extend(errors)
        return result

    phases.append(PhaseResult(phase="validate", success=True, output="All checks passed"))
    state = _detect_state(config, provider)

    if config.dry_run:
        plan = _build_dry_run_plan(config, state)
        result.dry_run_plan = plan.to_dict()
        phases.append(
            PhaseResult(
                phase="plan",
                success=True,
                output=_format_dry_run_plan(result.dry_run_plan),
                skipped=True,
                details={"dry_run_plan": result.dry_run_plan},
            )
        )
        result.success = True
        return result

    if state.tag_exists:
        phases.append(
            PhaseResult(
                phase="prepare",
                success=True,
                skipped=True,
                output=f"Tag {tag_name} already exists",
            )
        )
        phases.append(
            PhaseResult(
                phase="pr",
                success=True,
                skipped=True,
                output="Release already completed",
            )
        )
        phases.append(
            PhaseResult(
                phase="tag",
                success=True,
                skipped=True,
                output=f"Tag {tag_name} already exists",
            )
        )
        result.success = True
        result.release_url = _release_url_for_tag(config)
        _attach_release_packet(result)
        return result

    if compare_versions(state.current_version, config.version) == 0:
        # Resume path: the bump already merged to the default branch but the tag
        # was never created (e.g. `--wait` was interrupted, or the PR merged out
        # of band). Skip prepare/PR/wait-for-merge and go straight to completion.
        base_branch = _default_branch(config.project_root)
        phases.append(
            PhaseResult(
                phase="prepare",
                success=True,
                skipped=True,
                output=f"Version {config.version} already on {base_branch}",
            )
        )
        phases.append(
            PhaseResult(phase="pr", success=True, skipped=True, output="Release PR already merged")
        )
        phases.append(
            PhaseResult(
                phase="wait-for-merge",
                success=True,
                skipped=True,
                output="Release PR already merged",
            )
        )
        if not _complete_release(config, provider, clock, result, phases):
            return result
    else:
        if not config.skip_bump:
            prepare = _prepare_branch(config, clock)
            phases.append(prepare)
            if not prepare.success:
                result.errors.append(prepare.output)
                return result
            if prepare.output:
                result.bump_files.extend(prepare.output.split("\n"))
        else:
            phases.append(
                PhaseResult(phase="prepare", success=True, skipped=True, output="--skip-bump")
            )

        pr_phase = _create_release_pr(config, provider, runner)
        phases.append(pr_phase)
        if not pr_phase.success:
            result.errors.append(pr_phase.output)
            return result
        if pr_phase.output.startswith("http"):
            result.pr_url = pr_phase.output.splitlines()[0].strip()

        if config.wait:
            wait_phase = _wait_for_merge(config, provider, config.wait_timeout, runner)
            phases.append(wait_phase)
            if not wait_phase.success:
                result.errors.append(wait_phase.output)
                return result
            if not _complete_release(config, provider, clock, result, phases):
                return result
        else:
            skip_msg = "Tag deferred -- run `ai-eng release <version> --wait` after merge"
            phases.append(
                PhaseResult(phase="wait-for-merge", success=True, skipped=True, output="--wait off")
            )
            phases.append(PhaseResult(phase="tag", success=True, skipped=True, output=skip_msg))
            phases.append(
                PhaseResult(phase="manifest", success=True, skipped=True, output="--wait off")
            )
            phases.append(
                PhaseResult(phase="monitor", success=True, skipped=True, output="--wait off")
            )

    result.success = True
    if not result.release_url:
        slug = _repo_slug(config.project_root)
        if slug:
            result.release_url = f"https://github.com/{slug}/releases/tag/{tag_name}"
    return result


def _complete_release(
    config: ReleaseConfig,
    provider: VcsProvider,
    clock: Clock,
    result: ReleaseResult,
    phases: list[PhaseResult],
) -> bool:
    """Run the post-merge completion sequence: readiness -> tag -> manifest -> monitor.

    Shared by the pre-merge ``--wait`` flow and the post-merge resume flow. Appends
    each phase to *phases*, mutates *result*, and returns ``False`` on the first
    failing phase (the caller returns the partially populated result).
    """
    tag_name = f"v{config.version}"

    readiness_phase = _run_release_readiness(config)
    phases.append(readiness_phase)
    result.readiness = _readiness_payload(readiness_phase)
    if not readiness_phase.success:
        result.errors.append(readiness_phase.output)
        return False

    tag_phase = _create_tag(config, provider)
    phases.append(tag_phase)
    if not tag_phase.success:
        result.errors.append(tag_phase.output)
        return False
    raw_sha = tag_phase.details.get("tagged_sha")
    tagged_sha = raw_sha if isinstance(raw_sha, str) else None

    result.release_url = _release_url_for_tag(config)
    _attach_release_packet(result)
    manifest_phase = _update_manifest(config, clock)
    phases.append(manifest_phase)
    if not manifest_phase.success:
        result.errors.append(manifest_phase.output)
        return False

    emit_deploy_event(
        config.project_root,
        environment="production",
        strategy="tag",
        version=config.version,
        result=f"tag={tag_name}",
        release_packet_url=result.release_packet_url,
        release_packet_ref=result.release_packet_ref,
    )

    monitor_phase = _monitor_pipeline(config, provider, config.wait_timeout, tagged_sha=tagged_sha)
    phases.append(monitor_phase)
    if not monitor_phase.success:
        result.errors.append(monitor_phase.output)
        return False
    result.pipeline_status = monitor_phase.output
    if monitor_phase.output.startswith("http"):
        result.release_url = _release_url_from_monitor(config, monitor_phase.output)
        _attach_release_packet(result)
    emit_deploy_event(
        config.project_root,
        environment="production",
        strategy="pipeline",
        version=config.version,
        result=monitor_phase.output,
        release_packet_url=result.release_packet_url,
        release_packet_ref=result.release_packet_ref,
    )
    return True


def _build_dry_run_plan(config: ReleaseConfig, state: ReleaseState) -> ReleaseDryRunPlan:
    tag_name = f"v{config.version}"
    return ReleaseDryRunPlan(
        old_version=state.current_version,
        target_version=config.version,
        release_branch=state.release_branch,
        tag=tag_name,
        governed_changed_files=_governed_changed_files(config.project_root),
        changelog_promotion=(
            f"Promote {_CHANGELOG_REL.as_posix()} [Unreleased] to [{config.version}]"
        ),
        workflow_trigger=f"Push tag {tag_name} to trigger the Release workflow",
        testpypi_stage="TestPyPI publish and install verification before production",
        pypi_stage="PyPI publish only after TestPyPI, readiness, and attestations pass",
        readiness_gate=f"readiness gate: ai-eng verify --release {config.version}",
        release_packet_outputs=(
            f"{_RELEASE_READINESS_NAME}, {_RELEASE_PACKET_NAME}, SBOM, checksums, attestations"
        ),
    )


def _format_dry_run_plan(plan: dict[str, object]) -> str:
    return "\n".join(f"{key}={value}" for key, value in plan.items())


def _governed_changed_files(project_root: Path) -> list[str]:
    files = ["pyproject.toml", _CHANGELOG_REL.as_posix()]
    registry = Path("src") / "ai_engineering" / "version" / "registry.json"
    if (project_root / registry).is_file():
        files.append(registry.as_posix())
    if (project_root / _TEMPLATE_MANIFEST_REL).is_file():
        files.extend([_ROOT_MANIFEST_REL.as_posix(), _TEMPLATE_MANIFEST_REL.as_posix()])
    if (project_root / _LOCKFILE_NAME).is_file():
        files.append(_LOCKFILE_NAME)
    return files


def _run_release_readiness(config: ReleaseConfig) -> PhaseResult:
    report = verify_release(config.project_root, config.version)
    payload = dict(report.to_dict())
    artifact = config.project_root / ".ai-engineering" / "runtime" / "release" / config.version
    payload["artifact_path"] = str(artifact / _RELEASE_READINESS_NAME)
    _write_readiness_payload(Path(str(payload["artifact_path"])), payload)
    return PhaseResult(
        phase="readiness",
        success=bool(report.allows_release),
        output=_readiness_output(payload),
        details={"readiness": payload},
    )


def _write_readiness_payload(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _readiness_output(payload: dict[str, object]) -> str:
    verdict = str(payload.get("verdict", "NO-GO"))
    conditions = payload.get("conditions")
    if isinstance(conditions, list) and conditions:
        return f"{verdict}: {'; '.join(str(condition) for condition in conditions)}"
    return verdict


def _readiness_payload(phase: PhaseResult) -> dict[str, object] | None:
    payload = phase.details.get("readiness")
    if isinstance(payload, dict):
        return cast(dict[str, object], payload)
    return None


def _attach_release_packet(result: ReleaseResult) -> None:
    if not result.release_url:
        return
    result.release_packet_ref = _RELEASE_PACKET_NAME
    result.release_packet_url = _release_packet_url(result.release_url)


def _release_packet_url(release_url: str) -> str:
    if "/releases/tag/" in release_url:
        base = release_url.replace("/releases/tag/", "/releases/download/")
        return f"{base.rstrip('/')}/{_RELEASE_PACKET_NAME}"
    return f"{release_url.rstrip('/')}/{_RELEASE_PACKET_NAME}"


def _release_url_for_tag(config: ReleaseConfig) -> str:
    slug = _repo_slug(config.project_root)
    if not slug:
        return ""
    return f"https://github.com/{slug}/releases/tag/v{config.version}"


def _release_url_from_monitor(config: ReleaseConfig, output: str) -> str:
    url = output.splitlines()[0].strip()
    if "/actions/runs/" not in url:
        return url
    return _release_url_for_tag(config) or url


def _validate(config: ReleaseConfig, provider: VcsProvider) -> list[str]:
    errors: list[str] = []

    if not validate_semver(config.version):
        errors.append(f"Invalid semver version: {config.version}")
        return errors

    tag_name = f"v{config.version}"
    tag_ok, _ = run_git(
        ["rev-parse", "--verify", "--quiet", f"refs/tags/{tag_name}"], config.project_root
    )
    if tag_ok:
        # Idempotent no-op path handled by state detection.
        return errors

    branch = current_branch(config.project_root)
    if branch not in {"main", "master"}:
        errors.append(f"Release must start from main/master branch (current: {branch})")

    ok, output = run_git(["status", "--porcelain"], config.project_root)
    if not ok:
        errors.append(f"Unable to check git status: {output}")
    elif output.strip():
        errors.append("Working tree must be clean")

    resume = False
    try:
        current = detect_current_version(config.project_root)
        comparison = compare_versions(current, config.version)
        if comparison == 0:
            # Bump already landed on the default branch (release PR merged): the
            # version pin already matches and the changelog is already promoted.
            # This is a resume-to-tag run, not a downgrade -- skip the
            # greater-than and changelog gates and let state detection drive the
            # resume flow in execute_release.
            resume = True
        elif comparison > 0:
            errors.append(
                f"New version ({config.version}) must be greater than current ({current})"
            )
    except (ValueError, FileNotFoundError) as exc:
        errors.append(str(exc))

    if not provider.is_available():
        errors.append(f"VCS provider unavailable: {provider.provider_name()}")
    else:
        auth = provider.check_auth(VcsContext(project_root=config.project_root))
        if not auth.success:
            errors.append(f"VCS auth check failed: {auth.output}")

    if not resume:
        changelog_path = config.project_root / _CHANGELOG_REL
        if not changelog_path.exists():
            errors.append(f"{_CHANGELOG_REL.as_posix()} not found")
        else:
            errors.extend(validate_changelog(changelog_path, config.version))

    return errors


def _detect_state(config: ReleaseConfig, provider: VcsProvider) -> ReleaseState:
    del provider
    release_branch = f"release/v{config.version}"
    local_ok, _ = run_git(
        ["show-ref", "--verify", "--quiet", f"refs/heads/{release_branch}"], config.project_root
    )
    remote_ok, _ = run_git(
        ["ls-remote", "--exit-code", "--heads", "origin", release_branch],
        config.project_root,
    )
    tag_name = f"v{config.version}"
    tag_ok, _ = run_git(
        ["rev-parse", "--verify", "--quiet", f"refs/tags/{tag_name}"], config.project_root
    )
    return ReleaseState(
        release_branch=release_branch,
        local_branch_exists=local_ok,
        remote_branch_exists=remote_ok,
        tag_exists=tag_ok,
        current_version=detect_current_version(config.project_root),
    )


def _prepare_branch(config: ReleaseConfig, clock: Clock) -> PhaseResult:
    release_branch = f"release/v{config.version}"
    local_ok, _ = run_git(
        ["show-ref", "--verify", "--quiet", f"refs/heads/{release_branch}"], config.project_root
    )
    if local_ok:
        return PhaseResult(
            phase="prepare", success=True, skipped=True, output="Release branch already exists"
        )

    ok, output = run_git(["checkout", "-b", release_branch], config.project_root)
    if not ok:
        return PhaseResult(
            phase="prepare", success=False, output=f"Failed to create branch: {output}"
        )

    try:
        bump = bump_python_version(config.project_root, config.version)
        lock_path = _update_lockfile_version(config.project_root, config.version)
    except (ValueError, FileNotFoundError) as exc:
        return PhaseResult(phase="prepare", success=False, output=str(exc))

    files_modified = list(bump.files_modified)
    if lock_path is not None:
        files_modified.append(lock_path)

    today = clock.utcnow().strftime("%Y-%m-%d")
    changelog_path = config.project_root / _CHANGELOG_REL
    if not promote_unreleased(changelog_path, config.version, today):
        return PhaseResult(
            phase="prepare",
            success=False,
            output=f"Failed to promote [Unreleased] in {_CHANGELOG_REL.as_posix()}",
        )

    files_to_add = [str(p.relative_to(config.project_root)) for p in files_modified]
    files_to_add.append(_CHANGELOG_REL.as_posix())
    add_ok, add_out = run_git(["add", *files_to_add], config.project_root)
    if not add_ok:
        return PhaseResult(phase="prepare", success=False, output=f"git add failed: {add_out}")

    commit_ok, commit_out = run_git(
        ["commit", "-m", f"chore(release): v{config.version}"],
        config.project_root,
    )
    if not commit_ok:
        return PhaseResult(
            phase="prepare", success=False, output=f"git commit failed: {commit_out}"
        )

    files = [str(path.relative_to(config.project_root)) for path in files_modified]
    return PhaseResult(phase="prepare", success=True, output="\n".join(files))


def _update_lockfile_version(project_root: Path, new_version: str) -> Path | None:
    """Sync the project's own version pin in ``uv.lock`` with the bump.

    Only the editable root package (``source = { editable = "." }``) is rewritten,
    so dependency pins are untouched and the result is byte-identical to what
    ``uv lock`` would emit for a version-only bump. Returns the lockfile path when
    updated, or ``None`` when no ``uv.lock`` is present (e.g. installed consumer
    projects). Raises ``ValueError`` when the lockfile exists but the editable
    root pin cannot be located, so the release fails loud rather than committing a
    desynced lockfile.
    """
    lock_path = project_root / _LOCKFILE_NAME
    if not lock_path.is_file():
        return None

    text = lock_path.read_text(encoding="utf-8")
    updated, count = _LOCK_EDITABLE_ROOT_RE.subn(rf"\g<1>{new_version}\g<3>", text, count=1)
    if count != 1:
        msg = f"Unable to update project version in {_LOCKFILE_NAME}"
        raise ValueError(msg)

    lock_path.write_text(updated, encoding="utf-8")
    return lock_path


def _create_release_pr(
    config: ReleaseConfig,
    provider: VcsProvider,
    runner: CommandRunner,
) -> PhaseResult:
    release_branch = f"release/v{config.version}"
    push_ok, push_out = run_git(["push", "-u", "origin", release_branch], config.project_root)
    if not push_ok:
        return PhaseResult(phase="pr", success=False, output=f"git push failed: {push_out}")

    ctx = VcsContext(
        project_root=config.project_root,
        title=f"chore(release): v{config.version}",
        body=f"## Summary\n- release {config.version}\n- version bump and changelog promotion\n",
        branch=release_branch,
        target_branch=_default_branch(config.project_root),
    )
    pr = provider.create_pr(ctx)
    if not pr.success:
        existing = _find_existing_pr_url(config.project_root, release_branch, provider, runner)
        if existing:
            return PhaseResult(phase="pr", success=True, skipped=True, output=existing)
        return PhaseResult(phase="pr", success=False, output=f"PR creation failed: {pr.output}")

    auto = provider.enable_auto_complete(ctx)
    if not auto.success:
        return PhaseResult(phase="pr", success=False, output=f"Auto-complete failed: {auto.output}")

    return PhaseResult(phase="pr", success=True, output=pr.url or "PR created")


def _wait_for_merge(
    config: ReleaseConfig,
    provider: VcsProvider,
    timeout: int,
    runner: CommandRunner,
) -> PhaseResult:
    release_branch = f"release/v{config.version}"
    deadline = time.time() + timeout

    if provider.provider_name() == "github":
        while time.time() < deadline:
            ok, out = runner.run(
                ["gh", "pr", "view", release_branch, "--json", "state,mergedAt,url"],
                config.project_root,
                timeout=30,
            )
            if ok:
                try:
                    payload = json.loads(out)
                    if payload.get("mergedAt"):
                        return PhaseResult(
                            phase="wait-for-merge",
                            success=True,
                            output=payload.get("url", "merged"),
                        )
                except json.JSONDecodeError:
                    pass
            time.sleep(10)
        return PhaseResult(
            phase="wait-for-merge",
            success=False,
            output=f"Timed out waiting for PR merge after {timeout}s",
        )

    while time.time() < deadline:
        run_git(["fetch", "origin"], config.project_root)
        remote_exists, _ = run_git(
            ["ls-remote", "--exit-code", "--heads", "origin", release_branch],
            config.project_root,
        )
        base_branch = _default_branch(config.project_root)
        main_version = _version_from_git_ref(config.project_root, f"origin/{base_branch}")
        if not remote_exists and main_version == config.version:
            return PhaseResult(phase="wait-for-merge", success=True, output="merged")
        time.sleep(10)

    return PhaseResult(
        phase="wait-for-merge",
        success=False,
        output=f"Timed out waiting for merge after {timeout}s",
    )


def _create_tag(config: ReleaseConfig, provider: VcsProvider) -> PhaseResult:
    tag_name = f"v{config.version}"
    exists, _ = run_git(
        ["rev-parse", "--verify", "--quiet", f"refs/tags/{tag_name}"], config.project_root
    )
    if exists:
        return PhaseResult(
            phase="tag", success=True, skipped=True, output=f"Tag exists: {tag_name}"
        )

    base_branch = _default_branch(config.project_root)
    checkout_ok, checkout_out = run_git(["checkout", base_branch], config.project_root)
    if not checkout_ok:
        return PhaseResult(
            phase="tag", success=False, output=f"Failed checkout {base_branch}: {checkout_out}"
        )

    pull_ok, pull_out = run_git(["pull", "--ff-only"], config.project_root)
    if not pull_ok:
        return PhaseResult(
            phase="tag", success=False, output=f"Failed pull {base_branch}: {pull_out}"
        )

    sha_ok, sha_out = run_git(["rev-parse", "HEAD"], config.project_root)
    if not sha_ok:
        return PhaseResult(phase="tag", success=False, output=f"Failed to read HEAD SHA: {sha_out}")
    sha = sha_out.splitlines()[0].strip()

    tag_result = provider.create_tag(
        CreateTagContext(
            project_root=config.project_root,
            tag_name=tag_name,
            commit_sha=sha,
        )
    )
    if not tag_result.success:
        lowered = tag_result.output.lower()
        if "already exists" in lowered or "reference already exists" in lowered:
            return PhaseResult(
                phase="tag",
                success=True,
                skipped=True,
                output=f"Tag exists: {tag_name}",
                details={"tagged_sha": sha},
            )
        return PhaseResult(
            phase="tag", success=False, output=f"Tag creation failed: {tag_result.output}"
        )

    return PhaseResult(
        phase="tag",
        success=True,
        output=f"{tag_name} created ({sha[:7]})",
        details={"tagged_sha": sha},
    )


def _update_manifest(config: ReleaseConfig, clock: Clock) -> PhaseResult:
    state_dir = config.project_root / ".ai-engineering" / "state"
    state_path = state_dir / "install-state.json"
    if not state_path.exists():
        return PhaseResult(
            phase="manifest",
            success=True,
            skipped=True,
            output="install-state.json not found",
        )

    state = load_install_state(state_dir)
    state.release.last_version = config.version
    state.release.last_released_at = clock.utcnow()
    save_install_state(state_dir, state)
    return PhaseResult(phase="manifest", success=True, output="install-state.json updated")


def _monitor_pipeline(
    config: ReleaseConfig,
    provider: VcsProvider,
    timeout: int,
    tagged_sha: str | None = None,
) -> PhaseResult:
    # The tag ref is created remote-only via the GitHub API (see
    # GitHubProvider.create_tag), so a local ``git rev-parse v<version>`` fails.
    # Prefer the SHA threaded from _create_tag; fall back to a local lookup only
    # for the resume flow, where the tag already exists locally.
    if tagged_sha:
        resolved_sha = tagged_sha
    else:
        sha_ok, sha_out = run_git(
            ["rev-parse", "--verify", "--quiet", f"refs/tags/v{config.version}"],
            config.project_root,
        )
        if not sha_ok:
            return PhaseResult(
                phase="monitor", success=False, output=f"Unable to read tag SHA: {sha_out}"
            )
        resolved_sha = sha_out.splitlines()[0].strip()

    deadline = time.time() + timeout
    while time.time() < deadline:
        status = provider.get_pipeline_status(
            PipelineStatusContext(
                project_root=config.project_root,
                head_sha=resolved_sha,
                workflow_name="Release",
            )
        )
        if not status.success:
            time.sleep(10)
            continue

        runs = _parse_runs(status.output)
        if not runs:
            time.sleep(10)
            continue

        run = runs[0]
        state = str(run.get("status", ""))
        conclusion = str(run.get("conclusion", ""))
        url = str(run.get("url", ""))
        if state == "completed":
            if conclusion == "success":
                return PhaseResult(phase="monitor", success=True, output=url or "completed")
            return PhaseResult(
                phase="monitor",
                success=False,
                output=f"Release pipeline failed: {conclusion} {url}".strip(),
            )

        time.sleep(10)

    return PhaseResult(phase="monitor", success=False, output=f"Timed out after {timeout}s")


def _parse_runs(output: str) -> list[dict[str, object]]:
    text = output.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\])", text, re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
    if not isinstance(parsed, list):
        return []
    return [run for run in parsed if isinstance(run, dict)]


def _version_from_git_ref(project_root: Path, ref: str) -> str | None:
    ok, out = run_git(["show", f"{ref}:pyproject.toml"], project_root)
    if not ok:
        return None
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', out, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def _find_existing_pr_url(
    project_root: Path,
    release_branch: str,
    provider: VcsProvider,
    runner: CommandRunner,
) -> str:
    if provider.provider_name() != "github":
        return ""
    ok, out = runner.run(
        ["gh", "pr", "list", "--head", release_branch, "--json", "url", "--limit", "1"],
        project_root,
        timeout=30,
    )
    if not ok:
        return ""
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, list) or not payload:
        return ""
    first = payload[0]
    if not isinstance(first, dict):
        return ""
    url = first.get("url")
    return str(url) if isinstance(url, str) else ""


def _repo_slug(project_root: Path) -> str:
    ok, out = run_git(["remote", "get-url", "origin"], project_root)
    if not ok:
        return ""
    url = out.strip()
    # git@github.com:owner/repo.git
    ssh_match = re.search(
        r"github\.com[:/](?P<slug>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:\.git)?$", url
    )
    if ssh_match:
        return ssh_match.group("slug").removesuffix(".git")
    return ""


def _default_branch(project_root: Path) -> str:
    main_ok, _ = run_git(["show-ref", "--verify", "--quiet", "refs/heads/main"], project_root)
    if main_ok:
        return "main"
    return "master"
