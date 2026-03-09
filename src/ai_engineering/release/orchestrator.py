"""Governed release orchestration service."""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from ai_engineering.git.operations import current_branch, run_git
from ai_engineering.release.changelog import promote_unreleased, validate_changelog
from ai_engineering.release.version_bump import (
    bump_python_version,
    compare_versions,
    detect_current_version,
    validate_semver,
)
from ai_engineering.state.audit import emit_deploy_event
from ai_engineering.state.io import read_json_model, write_json_model
from ai_engineering.state.models import InstallManifest
from ai_engineering.vcs.protocol import (
    CreateTagContext,
    PipelineStatusContext,
    VcsContext,
    VcsProvider,
)


class Clock(Protocol):
    """Clock abstraction for deterministic tests."""

    def utcnow(self) -> datetime: ...


class CommandRunner(Protocol):
    """Command execution abstraction for deterministic tests."""

    def run(
        self, cmd: list[str], cwd: Path, timeout: int = 60
    ) -> tuple[bool, str]: ...  # pragma: no cover


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
    draft: bool = False
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
        dry_output = (
            f"release_branch={state.release_branch} "
            f"local_branch_exists={state.local_branch_exists} "
            f"remote_branch_exists={state.remote_branch_exists} tag_exists={state.tag_exists}"
        )
        phases.append(PhaseResult(phase="plan", success=True, output=dry_output, skipped=True))
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
        result.release_url = (
            f"https://github.com/{_repo_slug(config.project_root)}/releases/tag/{tag_name}"
        )
        return result

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
    else:
        phases.append(
            PhaseResult(phase="wait-for-merge", success=True, skipped=True, output="--wait off")
        )

    tag_phase = _create_tag(config, provider)
    phases.append(tag_phase)
    if not tag_phase.success:
        result.errors.append(tag_phase.output)
        return result

    manifest_phase = _update_manifest(config, clock)
    phases.append(manifest_phase)
    if not manifest_phase.success:
        result.errors.append(manifest_phase.output)
        return result

    emit_deploy_event(
        config.project_root,
        environment="production",
        strategy="tag",
        version=config.version,
        result=f"tag={tag_name}",
    )

    if config.wait:
        monitor_phase = _monitor_pipeline(config, provider, config.wait_timeout)
        phases.append(monitor_phase)
        if not monitor_phase.success:
            result.errors.append(monitor_phase.output)
            return result
        result.pipeline_status = monitor_phase.output
        if monitor_phase.output.startswith("http"):
            result.release_url = monitor_phase.output.splitlines()[0]
        emit_deploy_event(
            config.project_root,
            environment="production",
            strategy="pipeline",
            version=config.version,
            result=monitor_phase.output,
        )
    else:
        phases.append(PhaseResult(phase="monitor", success=True, skipped=True, output="--wait off"))

    result.success = True
    if not result.release_url:
        slug = _repo_slug(config.project_root)
        if slug:
            result.release_url = f"https://github.com/{slug}/releases/tag/{tag_name}"
    return result


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

    try:
        current = detect_current_version(config.project_root)
        if compare_versions(current, config.version) >= 0:
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

    changelog_path = config.project_root / "CHANGELOG.md"
    if not changelog_path.exists():
        errors.append("CHANGELOG.md not found")
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
    except (ValueError, FileNotFoundError) as exc:
        return PhaseResult(phase="prepare", success=False, output=str(exc))

    today = clock.utcnow().strftime("%Y-%m-%d")
    changelog_path = config.project_root / "CHANGELOG.md"
    if not promote_unreleased(changelog_path, config.version, today):
        return PhaseResult(
            phase="prepare",
            success=False,
            output="Failed to promote [Unreleased] in CHANGELOG.md",
        )

    add_ok, add_out = run_git(
        ["add", "pyproject.toml", str(bump.files_modified[1]), "CHANGELOG.md"], config.project_root
    )
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

    files = [str(path.relative_to(config.project_root)) for path in bump.files_modified]
    return PhaseResult(phase="prepare", success=True, output="\n".join(files))


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
                phase="tag", success=True, skipped=True, output=f"Tag exists: {tag_name}"
            )
        return PhaseResult(
            phase="tag", success=False, output=f"Tag creation failed: {tag_result.output}"
        )

    return PhaseResult(phase="tag", success=True, output=f"{tag_name} created ({sha[:7]})")


def _update_manifest(config: ReleaseConfig, clock: Clock) -> PhaseResult:
    manifest_path = config.project_root / ".ai-engineering" / "state" / "install-manifest.json"
    if not manifest_path.exists():
        return PhaseResult(
            phase="manifest",
            success=True,
            skipped=True,
            output="install-manifest.json not found",
        )

    manifest = read_json_model(manifest_path, InstallManifest)
    manifest.release.last_version = config.version
    manifest.release.last_released_at = clock.utcnow()
    write_json_model(manifest_path, manifest)
    return PhaseResult(phase="manifest", success=True, output="install-manifest.json updated")


def _monitor_pipeline(config: ReleaseConfig, provider: VcsProvider, timeout: int) -> PhaseResult:
    sha_ok, sha_out = run_git(["rev-parse", f"v{config.version}"], config.project_root)
    if not sha_ok:
        return PhaseResult(
            phase="monitor", success=False, output=f"Unable to read tag SHA: {sha_out}"
        )
    tagged_sha = sha_out.splitlines()[0].strip()

    deadline = time.time() + timeout
    while time.time() < deadline:
        status = provider.get_pipeline_status(
            PipelineStatusContext(
                project_root=config.project_root,
                head_sha=tagged_sha,
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
