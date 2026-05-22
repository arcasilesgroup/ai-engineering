"""Workflow policy sanity checks for GitHub Actions files.

Current enforced policies:
- No use of `pull_request_target` trigger (parsed via `workflow_triggers`, which
  normalizes PyYAML's boolean `on:` key so a bare `on:` block cannot fail open).
- Top-level `permissions` key must be present.
- Every job must have `timeout-minutes`.
- Workflows with `pull_request` trigger must have `concurrency` key, unless the
  filename is in the reviewed `_CONCURRENCY_ALLOWLIST`.
- Every non-local action `uses:` (workflows AND composite actions) must SHA-pin.
- No unpinned runtime install in a step `run:` block — `curl|bash` bootstraps,
  `npm install -g <pkg>` without `@<version>`, `uv run --with <pkg>` /
  `uv pip install <pkg>` without `==` — unless allowlisted (spec-152 D-152-12).
- No `actions/cache`(`/restore`,`/save`), and no `setup-*` composite with
  `enable-cache: true`, inside a privileged/untrusted job (pull_request_target,
  untrusted workflow_run checkout, or `id-token: write`) unless a reviewed
  `_CACHE_EXCEPTIONS` entry names it (spec-152 D-152-11).
- `release.yml` must preserve the governed tag-triggered publish path.

The script also exposes an opt-in `--check-reachability` mode (off the PR hot
path) that resolves each pinned SHA via `git ls-remote` to catch refs that are
shaped-but-unreachable (spec-152 D-152-06).
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

# spec-152 D-152-05: no org prefix is exempt from SHA pinning. Every external
# action `uses:` — first-party (`actions/`, `github/`, ...) included — must pin
# to a 40-char commit SHA. A retag of even a first-party action is a supply-chain
# risk, so the exemption is removed entirely. Keep this tuple empty; if a future
# reviewed exception is ever needed, add it WITH an inline rationale and a
# `# expires: <date>` comment so it is auditable.
_FIRST_PARTY_PREFIXES: tuple[str, ...] = ()

# Workflows permitted to omit a top-level `concurrency:` block. Empty by default
# (spec-152 D-152-21): PR workflows declare `concurrency` directly (T-4a) rather
# than being allowlisted. Each entry maps `<workflow filename>` -> rationale and
# MUST carry a `# expires: <date>` token in its value when added.
_CONCURRENCY_ALLOWLIST: dict[str, str] = {}

# spec-152 D-152-12: workflows permitted to keep an UNPINNED runtime install in a
# step `run:` block. Empty by default — every runtime tool the repo installs
# (actionlint, gitleaks, snyk, cyclonedx-bom) is pinnable and is pinned in T-22,
# so no entry is warranted. If a genuinely unpinnable case ever appears, add it
# WITH an inline rationale and a `# expires: <date>` token in its value.
_INSTALL_ALLOWLIST: dict[str, str] = {}

# spec-152 D-152-11: workflows permitted to run an `actions/cache`(`/restore`,
# `/save`) — or a composite `enable-cache: true` — inside a privileged or
# untrusted-input job (pull_request_target, untrusted workflow_run checkout, or
# an `id-token: write` / release-OIDC job). Empty by default: ci-check caches run
# under plain `push`/`pull_request` non-OIDC jobs and release caches are disabled
# (T-17), so no trust boundary is crossed. Each entry maps `<workflow filename>`
# -> rationale and MUST carry a `# expires: <date>` token when added.
_CACHE_EXCEPTIONS: dict[str, str] = {}

# Pattern: owner/action@<40-hex-char SHA>
_SHA_PIN_RE = re.compile(r"^[^/]+/[^@]+@[0-9a-f]{40}$")

_CANONICAL_REPOSITORY = "arcasilesgroup/ai-engineering"
_RELEASE_WORKFLOW = Path(".github/workflows/release.yml")
_RELEASE_JOB_ORDER = (
    "resolve-version",
    "release-readiness",
    "release-build",
    "attest-and-verify",
    "publish-testpypi",
    "verify-testpypi-install",
    "publish-pypi",
    "finalize-release-packet",
)
_PRIVILEGED_RELEASE_JOBS = (
    "publish-testpypi",
    "publish-pypi",
    "finalize-release-packet",
)


def workflow_triggers(data: dict[str, Any]) -> dict[str, Any]:
    """Return the workflow trigger mapping, handling PyYAML's boolean `on` key."""
    triggers = data.get("on", data.get(True, {}))
    if triggers is None:
        return {}
    if isinstance(triggers, str):
        return {triggers: None}
    if isinstance(triggers, list):
        return {str(item): None for item in triggers}
    if isinstance(triggers, dict):
        return {str(key): value for key, value in triggers.items()}
    return {}


def _steps_text(job: dict[str, Any]) -> str:
    """Serialize a job's steps for narrow textual policy checks."""
    steps = job.get("steps", [])
    return yaml.safe_dump(steps, sort_keys=False)


def _workflow_text(data: dict[str, Any]) -> str:
    """Serialize a workflow for narrow textual policy checks."""
    return yaml.safe_dump(data, sort_keys=False)


def _needs_set(job: dict[str, Any]) -> set[str]:
    """Normalize a job's `needs` declaration to a set."""
    needs = job.get("needs", [])
    if isinstance(needs, str):
        return {needs}
    if isinstance(needs, list):
        return {str(item) for item in needs}
    return set()


def _required_input_present(inputs: dict[str, Any], name: str) -> bool:
    """Return whether a workflow_dispatch input is required."""
    config = inputs.get(name)
    return isinstance(config, dict) and config.get("required") is True


def _has_privileged_context_guard(job: dict[str, Any]) -> bool:
    """Check a privileged publish/finalize job is restricted to trusted release events."""
    guard = str(job.get("if", ""))
    has_repository_guard = f"github.repository == '{_CANONICAL_REPOSITORY}'" in guard
    has_tag_guard = (
        "github.event_name == 'push'" in guard and "startsWith(github.ref, 'refs/tags/v')" in guard
    )
    has_dispatch_guard = "github.event_name == 'workflow_dispatch'" in guard
    return (
        has_repository_guard
        and has_tag_guard
        and has_dispatch_guard
        and "pull_request" not in guard
    )


def _expect_text(text: str, required: tuple[str, ...], label: str) -> list[str]:
    """Return missing text fragments as policy failure messages."""
    return [f"{label}: missing {needle!r}" for needle in required if needle not in text]


def check_release_workflow_policy(workflow: Path, data: dict[str, Any]) -> list[str]:
    """Check the spec-143 release workflow supply-chain contract.

    The helper is deliberately narrow: it only validates the live Release
    workflow, leaving generic workflow checks reusable for the rest of CI.
    """
    failures: list[str] = []

    triggers = workflow_triggers(data)
    push_tags = (triggers.get("push") or {}).get("tags", [])
    if "v*" not in push_tags:
        failures.append(f"{workflow}: release workflow must trigger on push tags ['v*']")
    if "workflow_dispatch" not in triggers:
        failures.append(f"{workflow}: release workflow must keep protected workflow_dispatch")
    if "release" in triggers or "workflow_run" in triggers:
        failures.append(f"{workflow}: release workflow must not use release/workflow_run triggers")

    dispatch = triggers.get("workflow_dispatch") or {}
    dispatch_inputs = dispatch.get("inputs", {}) if isinstance(dispatch, dict) else {}
    if not isinstance(dispatch_inputs, dict):
        dispatch_inputs = {}
    for input_name in ("version", "recovery_reason"):
        if not _required_input_present(dispatch_inputs, input_name):
            failures.append(f"{workflow}: workflow_dispatch input {input_name!r} must be required")

    top_permissions = data.get("permissions", {})
    if isinstance(top_permissions, dict):
        for permission in ("id-token", "attestations", "contents"):
            if top_permissions.get(permission) == "write":
                failures.append(
                    f"{workflow}: top-level permissions must not grant {permission}: write"
                )

    concurrency_text = yaml.safe_dump(data.get("concurrency"), sort_keys=False)
    if "github.ref_name" not in concurrency_text and "version" not in concurrency_text:
        failures.append(f"{workflow}: concurrency must be keyed by tag/version")

    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return [*failures, f"{workflow}: jobs must be a mapping"]

    if tuple(jobs.keys()) != _RELEASE_JOB_ORDER:
        failures.append(
            f"{workflow}: release jobs must appear in order {_RELEASE_JOB_ORDER}; "
            f"got {tuple(jobs.keys())}"
        )

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if "timeout-minutes" not in job:
            failures.append(f"{workflow}: job {job_name!r} missing timeout-minutes")
    readiness_timeout = (jobs.get("release-readiness") or {}).get("timeout-minutes")
    if not isinstance(readiness_timeout, int) or readiness_timeout < 30:
        failures.append(f"{workflow}: release-readiness timeout-minutes must be at least 30")

    expected_needs: dict[str, set[str]] = {
        "release-readiness": {"resolve-version"},
        "release-build": {"resolve-version", "release-readiness"},
        "attest-and-verify": {"resolve-version", "release-build"},
        "publish-testpypi": {
            "resolve-version",
            "release-readiness",
            "release-build",
            "attest-and-verify",
        },
        "verify-testpypi-install": {"resolve-version", "publish-testpypi"},
    }
    for job_name, expected in expected_needs.items():
        job = jobs.get(job_name)
        if isinstance(job, dict) and _needs_set(job) != expected:
            failures.append(f"{workflow}: job {job_name!r} needs {sorted(expected)}")

    publish_pypi = jobs.get("publish-pypi", {})
    if isinstance(publish_pypi, dict) and "verify-testpypi-install" not in _needs_set(publish_pypi):
        failures.append(f"{workflow}: publish-pypi must need verify-testpypi-install")
    finalize = jobs.get("finalize-release-packet", {})
    if isinstance(finalize, dict) and "publish-pypi" not in _needs_set(finalize):
        failures.append(f"{workflow}: finalize-release-packet must need publish-pypi")

    workflow_text = _workflow_text(data)
    forbidden_fragments = (
        "ci-build.yml",
        "gh run list",
        "github.event.workflow_run",
        "github.event.pull_request",
        "pull_request_target",
        "run-id:",
        "workflow_run:",
        "username:",
        "password:",
        "PYPI_TOKEN",
    )
    for fragment in forbidden_fragments:
        if fragment in workflow_text:
            failures.append(f"{workflow}: forbidden release workflow fragment {fragment!r}")

    release_build = jobs.get("release-build", {})
    if isinstance(release_build, dict):
        failures.extend(
            _expect_text(
                _steps_text(release_build),
                (
                    "uv build",
                    "METADATA",
                    "PKG-INFO",
                    "Version",
                    "ai-engineering==${VERSION}",
                    "cyclonedx-py",
                    "sbom.cdx.json",
                    "sha256sum dist/* sbom.cdx.json",
                    "CHECKSUMS-SHA256.txt",
                    "release-dists",
                    "release-supply-chain",
                ),
                f"{workflow}: release-build",
            )
        )

    attest = jobs.get("attest-and-verify", {})
    if isinstance(attest, dict):
        if attest.get("permissions") != {
            "contents": "read",
            "attestations": "write",
            "id-token": "write",
        }:
            failures.append(f"{workflow}: attest-and-verify permissions are not job-scoped")
        failures.extend(
            _expect_text(
                _steps_text(attest),
                (
                    "actions/attest-build-provenance",
                    "subject-path: dist/*",
                    "gh attestation verify",
                    "github-attestation-verify.log",
                    "Result: PASS (exit 0)",
                ),
                f"{workflow}: attest-and-verify",
            )
        )

    for job_name, environment_name in (
        ("publish-testpypi", "testpypi"),
        ("publish-pypi", "pypi"),
    ):
        job = jobs.get(job_name, {})
        if not isinstance(job, dict):
            continue
        if job.get("permissions") != {"contents": "read", "id-token": "write"}:
            failures.append(f"{workflow}: {job_name} permissions must only grant OIDC")
        environment = job.get("environment", {})
        if not isinstance(environment, dict) or environment.get("name") != environment_name:
            failures.append(f"{workflow}: {job_name} must use environment {environment_name!r}")
        if not _has_privileged_context_guard(job):
            failures.append(f"{workflow}: {job_name} missing tag/recovery repository guard")

    testpypi = jobs.get("publish-testpypi", {})
    if isinstance(testpypi, dict):
        failures.extend(
            _expect_text(
                _steps_text(testpypi),
                (
                    "pypa/gh-action-pypi-publish",
                    "repository-url: https://test.pypi.org/legacy/",
                    "testpypi-proof.txt",
                ),
                f"{workflow}: publish-testpypi",
            )
        )

    verify_testpypi = jobs.get("verify-testpypi-install", {})
    if isinstance(verify_testpypi, dict):
        failures.extend(
            _expect_text(
                _steps_text(verify_testpypi),
                (
                    "--index-url",
                    "https://test.pypi.org/simple/",
                    "--extra-index-url",
                    "https://pypi.org/simple/",
                    "testpypi-install-proof.txt",
                ),
                f"{workflow}: verify-testpypi-install",
            )
        )

    pypi = jobs.get("publish-pypi", {})
    if isinstance(pypi, dict):
        failures.extend(
            _expect_text(
                _steps_text(pypi),
                ("pypa/gh-action-pypi-publish", "release-dists", "pypi-proof.txt"),
                f"{workflow}: publish-pypi",
            )
        )

    if isinstance(finalize, dict):
        if finalize.get("permissions") != {"contents": "write"}:
            failures.append(f"{workflow}: finalize-release-packet must only grant contents write")
        if not _has_privileged_context_guard(finalize):
            failures.append(
                f"{workflow}: finalize-release-packet missing tag/recovery repository guard"
            )
        failures.extend(
            _expect_text(
                _steps_text(finalize),
                (
                    "gh release create",
                    "gh release edit",
                    "gh release upload",
                    "--clobber",
                    "release-packet.json",
                    "release-notes.md",
                    "release-notes-full.md",
                    "GITHUB_RELEASE_BODY_LIMIT",
                    "release-readiness.json",
                    "github-attestation-verify.log",
                    "testpypi-proof.txt",
                    "testpypi-install-proof.txt",
                    "pypi-proof.txt",
                    "ci_run_url",
                    "recovery",
                ),
                f"{workflow}: finalize-release-packet",
            )
        )

    readiness = jobs.get("release-readiness", {})
    if isinstance(readiness, dict):
        failures.extend(
            _expect_text(
                _steps_text(readiness),
                (
                    "ai-eng --json verify --release",
                    "--target release-source",
                    "Checkout workflow tooling",
                    "Checkout release tag source",
                    "path: release-source",
                    "Install gitleaks",
                    "GITLEAKS_VERSION",
                    "gitleaks version",
                    "release-readiness-envelope.json",
                    "release-readiness.json",
                    "find_readiness",
                    "release_readiness",
                    ".ai-engineering",
                    "runtime",
                    "always()",
                    "if-no-files-found",
                    "CONDITIONAL GO",
                    "NO-GO",
                ),
                f"{workflow}: release-readiness",
            )
        )

    return failures


def _clean_uses(uses: str) -> str:
    """Strip an inline trailing comment from a `uses:` value (``a/b@sha # v1``)."""
    return uses.split("#")[0].strip()


def _is_unpinnable_use(uses_clean: str) -> bool:
    """Return whether a `uses:` reference has no upstream tag/SHA to pin.

    Local composite (``./``) and docker-image (``docker://``) references are
    pinned by the repo commit itself or carry their own digest scheme.
    """
    return uses_clean.startswith("docker://") or uses_clean.startswith("./")


def _check_steps_sha_pinning(label: str, steps: Any) -> list[str]:
    """Check every actionable `uses:` in a step list is SHA-pinned.

    Pure over the parsed step list so it serves both workflow jobs
    (``jobs.<id>.steps``) and composite actions (``runs.steps``).
    """
    failures: list[str] = []
    if not isinstance(steps, list):
        return failures
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        uses = step.get("uses", "")
        if not isinstance(uses, str) or not uses:
            continue
        uses_clean = _clean_uses(uses)
        if any(uses_clean.startswith(prefix) for prefix in _FIRST_PARTY_PREFIXES):
            continue
        if _is_unpinnable_use(uses_clean):
            continue
        if not _SHA_PIN_RE.match(uses_clean):
            step_name = step.get("name", f"step {i}")
            failures.append(
                f"{label}, {step_name}: action '{uses_clean}' must use SHA pinning "
                f"(owner/action@<sha> # vN.M.P)"
            )
    return failures


def _check_sha_pinning(workflow: Path, data: dict) -> list[str]:
    """Check that every workflow job's actions use SHA pinning."""
    failures: list[str] = []
    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return failures
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        failures.extend(
            _check_steps_sha_pinning(f"{workflow}: job '{job_name}'", job.get("steps", []))
        )
    return failures


# --- spec-152 D-152-12: unpinned-runtime-install detection (pure core) -------

# A shell bootstrap that pipes a freshly-downloaded script straight into an
# interpreter (`curl ... | bash`, `wget ... | sh`) or runs it via process
# substitution (`bash <(curl ...)`). The fetched bytes are whatever the
# upstream serves at run time, so the install is unpinned by construction.
_CURL_PIPE_SHELL_RE = re.compile(r"(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba)?sh\b")
_SHELL_PROCESS_SUB_RE = re.compile(r"\b(?:ba)?sh\s+<\(\s*(?:curl|wget)\b")

# `npm install -g <pkg>` / `npm i -g <pkg>`. The package token is captured so a
# missing `@<version>` (anything other than a leading-scope `@`) can be flagged.
_NPM_GLOBAL_RE = re.compile(r"\bnpm\s+(?:install|i)\s+(?:--global|-g)\s+(?P<pkg>[^\s;&|]+)")

# `uv run --with <pkg>` and `uv pip install <pkg>`. Surrounding quotes are
# stripped by the caller before the `==` pin check.
_UV_RUN_WITH_RE = re.compile(r"\buv\s+run\b[^\n]*?--with[=\s]+(?P<pkg>[^\s;&|]+)")
_UV_PIP_INSTALL_RE = re.compile(r"\buv\s+pip\s+install\s+(?P<pkg>[^\s;&|]+)")


def _unquote(token: str) -> str:
    """Strip a single layer of matching surrounding quotes from a shell token."""
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
        return token[1:-1]
    return token


def _npm_pkg_is_pinned(pkg: str) -> bool:
    """Return whether an ``npm install -g`` package token carries an ``@version``.

    ``snyk@1.1305.0`` → pinned. ``snyk`` → not. ``@scope/name@1.2.3`` → pinned
    (the leading scope ``@`` is ignored; a *second* ``@`` carries the version).
    ``@scope/name`` → not pinned.
    """
    pkg = _unquote(pkg)
    body = pkg[1:] if pkg.startswith("@") else pkg
    return "@" in body


def scan_install_pins(text: str) -> list[str]:
    """Return a failure message for every unpinned runtime install in ``text``.

    Pure predicate over a step's ``run:`` text (spec-152 D-152-12, §10.8
    Hexagonal core). Detects four ingress shapes:

    * ``curl ... | bash`` / ``bash <(curl ...)`` script bootstrap;
    * ``npm install -g <pkg>`` without ``@<version>``;
    * ``uv run --with <pkg>`` without ``==``;
    * ``uv pip install <pkg>`` without ``==``.

    Each detected offender yields one message; an empty list means every install
    in the text is pinned (or there is no install at all).
    """
    failures: list[str] = []
    if not isinstance(text, str) or not text:
        return failures

    if _CURL_PIPE_SHELL_RE.search(text) or _SHELL_PROCESS_SUB_RE.search(text):
        failures.append(
            "unpinned install: `curl|bash`/`bash <(curl ...)` bootstrap fetches "
            "unpinned bytes at run time; download a pinned release and verify its "
            "sha256 instead"
        )

    for match in _NPM_GLOBAL_RE.finditer(text):
        pkg = match.group("pkg")
        if not _npm_pkg_is_pinned(pkg):
            failures.append(
                f"unpinned install: `npm install -g {pkg}` must pin a version "
                f"(`{_unquote(pkg)}@<version>`)"
            )

    for label, pattern in (
        ("uv run --with", _UV_RUN_WITH_RE),
        ("uv pip install", _UV_PIP_INSTALL_RE),
    ):
        for match in pattern.finditer(text):
            pkg = _unquote(match.group("pkg"))
            # Only python distribution specs are pinnable here; a bare flag or a
            # local path (`.`, `-r`, `requirements.txt`) is not a named package.
            if pkg.startswith("-") or pkg in {".", ".."} or "/" in pkg:
                continue
            if "==" not in pkg:
                failures.append(
                    f"unpinned install: `{label} {pkg}` must pin a version (`{pkg}==<version>`)"
                )

    return failures


def _job_run_text(job: dict[str, Any]) -> str:
    """Concatenate every step ``run:`` block in a job for textual scanning."""
    steps = job.get("steps", [])
    if not isinstance(steps, list):
        return ""
    parts: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        run = step.get("run")
        if isinstance(run, str):
            parts.append(run)
    return "\n".join(parts)


def _check_install_pins(workflow: Path, data: dict[str, Any]) -> list[str]:
    """Flag unpinned runtime installs across a workflow's job ``run:`` steps."""
    if workflow.name in _INSTALL_ALLOWLIST:
        return []
    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return []
    failures: list[str] = []
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        for message in scan_install_pins(_job_run_text(job)):
            failures.append(f"{workflow}: job '{job_name}': {message}")
    return failures


# --- spec-152 D-152-11: cache trust-boundary classification (pure core) ------

_CACHE_USES_PREFIXES = (
    "actions/cache@",
    "actions/cache/restore@",
    "actions/cache/save@",
)
# Composite setup actions whose `enable-cache: true` input turns on a uv/tool
# cache inside the composite. Consuming one of these in a privileged job is the
# same trust-boundary crossing as a direct `actions/cache` step.
_CACHE_ENABLING_COMPOSITE_PREFIX = "./.github/actions/setup-"


def _job_uses_cache(job: dict[str, Any]) -> bool:
    """Return whether any step invokes an ``actions/cache`` action."""
    steps = job.get("steps", [])
    if not isinstance(steps, list):
        return False
    for step in steps:
        if not isinstance(step, dict):
            continue
        uses = step.get("uses", "")
        if isinstance(uses, str) and any(
            _clean_uses(uses).startswith(prefix) for prefix in _CACHE_USES_PREFIXES
        ):
            return True
    return False


def _job_enables_composite_cache(job: dict[str, Any]) -> bool:
    """Return whether a step consumes a ``setup-*`` composite with cache enabled."""
    steps = job.get("steps", [])
    if not isinstance(steps, list):
        return False
    for step in steps:
        if not isinstance(step, dict):
            continue
        uses = step.get("uses", "")
        if not isinstance(uses, str):
            continue
        if not _clean_uses(uses).startswith(_CACHE_ENABLING_COMPOSITE_PREFIX):
            continue
        with_block = step.get("with", {})
        enable = with_block.get("enable-cache") if isinstance(with_block, dict) else None
        # The composite default is cache-on (setup-env action.yml default "true"),
        # so an absent or empty input is also the on-state; only an explicit
        # "false" turns the cache off.
        normalized = "true" if enable is None else str(enable).strip().lower()
        return normalized in {"true", ""}
    return False


def _job_has_oidc(job: dict[str, Any]) -> bool:
    """Return whether a job grants ``id-token: write`` (release/OIDC context)."""
    permissions = job.get("permissions")
    return isinstance(permissions, dict) and permissions.get("id-token") == "write"


def _job_checks_out_untrusted_workflow_run(job: dict[str, Any]) -> bool:
    """Return whether a job checks out the untrusted head ref of a ``workflow_run``."""
    text = _steps_text(job)
    return "github.event.workflow_run" in text


def classify_cache_usage(workflow: Path, data: dict[str, Any]) -> list[str]:
    """Flag cache usage that crosses a trust boundary (spec-152 D-152-11).

    Pure predicate (§10.8 Hexagonal core, §10.3 SOLID). A cache step — direct
    ``actions/cache``(`/restore`,`/save`) or a ``setup-*`` composite with
    ``enable-cache: true`` — is rejected when its job runs in any of:

    * a ``pull_request_target`` workflow (fork code, repo-write token);
    * a job that checks out an untrusted ``workflow_run`` head ref; or
    * a job granting ``id-token: write`` (release/OIDC publish context).

    A reviewed ``_CACHE_EXCEPTIONS`` entry naming the workflow file suppresses
    every flag for that workflow. Plain ``push``/``pull_request`` caches in
    non-OIDC jobs are allowed (their isolation is the trust-tier key prefix, not
    removal).
    """
    if workflow.name in _CACHE_EXCEPTIONS:
        return []

    triggers = workflow_triggers(data)
    workflow_is_pr_target = "pull_request_target" in triggers

    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return []

    failures: list[str] = []
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        uses_cache = _job_uses_cache(job)
        enables_composite = _job_enables_composite_cache(job)
        if not (uses_cache or enables_composite):
            continue

        reasons: list[str] = []
        if workflow_is_pr_target:
            reasons.append("pull_request_target (untrusted fork code with write token)")
        if _job_checks_out_untrusted_workflow_run(job):
            reasons.append("untrusted workflow_run head-ref checkout")
        if _job_has_oidc(job):
            reasons.append("id-token: write (release/OIDC publish context)")

        if not reasons:
            continue

        surface = "composite enable-cache:true" if enables_composite and not uses_cache else "cache"
        failures.append(
            f"{workflow}: job '{job_name}': {surface} is not allowed in a "
            f"privileged/untrusted context [{', '.join(reasons)}]; remove the "
            f"cache, run cold, or add a reviewed _CACHE_EXCEPTIONS entry"
        )
    return failures


def check_composite_action_policy(action: Path, data: dict[str, Any]) -> list[str]:
    """Check a composite ``action.yml``: its ``runs.steps`` must SHA-pin actions.

    Composites have no ``jobs:`` — their steps live under ``runs.steps`` — so the
    workflow scanner misses them. This routes those steps through the shared
    SHA-pin predicate (spec-152 D-152-04).
    """
    runs = data.get("runs", {})
    if not isinstance(runs, dict):
        return []
    return _check_steps_sha_pinning(f"{action}: composite", runs.get("steps", []))


def extract_pinned_refs(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return every SHA-pinned ``(owner/repo, sha)`` pair in a parsed YAML tree.

    Pure ref-extraction core for the reachability check: walks workflow jobs and
    composite ``runs.steps``, ignoring local (``./``) and ``docker://`` refs that
    carry no upstream SHA. Comments are stripped before matching.
    """
    refs: list[tuple[str, str]] = []
    step_lists: list[Any] = []
    jobs = data.get("jobs", {})
    if isinstance(jobs, dict):
        step_lists.extend(job.get("steps") for job in jobs.values() if isinstance(job, dict))
    runs = data.get("runs", {})
    if isinstance(runs, dict):
        step_lists.append(runs.get("steps"))

    for steps in step_lists:
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses", "")
            if not isinstance(uses, str) or not uses:
                continue
            uses_clean = _clean_uses(uses)
            if _is_unpinnable_use(uses_clean) or "@" not in uses_clean:
                continue
            repo, _, sha = uses_clean.rpartition("@")
            if repo and _SHA_PIN_RE.match(uses_clean):
                refs.append((repo, sha))
    return refs


def _ref_is_reachable(repo: str, sha: str) -> bool:
    """Return whether ``sha`` is a published ref tip of ``https://github.com/<repo>``.

    Edge adapter — the only side-effecting boundary of the reachability check, so
    the core stays pure and testable by monkeypatching this function.

    Lists every advertised ref with ``git ls-remote <url>`` (no ref argument: a
    full SHA passed as a ref *pattern* matches nothing, so the spec's literal
    ``git ls-remote <repo> <sha>`` form is a no-op and is deliberately not used)
    and reports whether ``sha`` appears in the object column of any line. That
    column covers both lightweight tags / branch heads (which point straight at a
    commit) and the peeled ``^{}`` line of an annotated tag (its target commit).
    A SHA that is a valid historical commit but never a published ref tip reads
    as unreachable here — that is the intended signal: a pin should resolve to a
    ref the upstream still advertises.
    """
    url = f"https://github.com/{repo}"
    # Fixed argv (no shell), so untrusted `repo` text cannot inject a command.
    argv = ["git", "ls-remote", url]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if result.returncode != 0:
        return False
    return any(line.split("\t", 1)[0] == sha for line in result.stdout.splitlines())


def check_reachability(refs: list[tuple[str, str]]) -> list[str]:
    """Return a failure message for every pinned ``(repo, sha)`` that is unreachable.

    Off the PR hot path — only invoked under ``--check-reachability``. Pure over
    the ref list; the network call is isolated in ``_ref_is_reachable``.
    """
    failures: list[str] = []
    for repo, sha in refs:
        if not _ref_is_reachable(repo, sha):
            failures.append(
                f"{repo}@{sha}: pinned SHA is not a published ref tip on the upstream remote"
            )
    return failures


def check_generic_workflow_policy(workflow: Path, data: dict[str, Any]) -> list[str]:
    """Run the generic (non-release) policy checks for a single workflow.

    Extracted from ``main()`` (spec-152 T-1, §10.3 SOLID) so each fixture can be
    asserted directly. Trigger inspection routes through ``workflow_triggers()``
    so PyYAML's boolean ``on:`` key (a bare ``on:`` block) cannot fail open.
    """
    failures: list[str] = []

    triggers = workflow_triggers(data)
    if "pull_request_target" in triggers:
        failures.append(f"{workflow}: 'pull_request_target' is not allowed")

    if "permissions" not in data:
        failures.append(f"{workflow}: missing top-level permissions block")

    # workflow_triggers() always returns a normalized dict.
    has_pr_trigger = "pull_request" in triggers
    if has_pr_trigger and "concurrency" not in data and workflow.name not in _CONCURRENCY_ALLOWLIST:
        failures.append(
            f"{workflow}: missing 'concurrency' key "
            f"(required for workflows with pull_request trigger)"
        )

    jobs = data.get("jobs", {})
    if isinstance(jobs, dict):
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            if "timeout-minutes" not in job:
                failures.append(f"{workflow}: job '{job_name}' missing 'timeout-minutes'")

    failures.extend(_check_sha_pinning(workflow, data))
    failures.extend(_check_install_pins(workflow, data))
    failures.extend(classify_cache_usage(workflow, data))
    return failures


def _load_workflow(path: Path) -> dict[str, Any] | None:
    """Parse a workflow/action YAML file, returning ``None`` if the root is not a mapping."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else None


def _collect_failures() -> list[str]:
    """Run every policy check across workflows and composite actions (regex-only)."""
    workflows = sorted(Path(".github/workflows").glob("*.yml"))
    composites = sorted(Path(".github/actions").glob("*/action.yml"))
    failures: list[str] = []

    for workflow in workflows:
        data = _load_workflow(workflow)
        if data is None:
            failures.append(f"{workflow}: workflow root must be a mapping")
            continue
        failures.extend(check_generic_workflow_policy(workflow, data))
        if workflow == _RELEASE_WORKFLOW:
            failures.extend(check_release_workflow_policy(workflow, data))

    for action in composites:
        data = _load_workflow(action)
        if data is None:
            failures.append(f"{action}: composite action root must be a mapping")
            continue
        failures.extend(check_composite_action_policy(action, data))

    return failures


def _collect_pinned_refs() -> list[tuple[str, str]]:
    """Gather every SHA-pinned ref across workflows and composite actions."""
    refs: list[tuple[str, str]] = []
    for path in [
        *sorted(Path(".github/workflows").glob("*.yml")),
        *sorted(Path(".github/actions").glob("*/action.yml")),
    ]:
        data = _load_workflow(path)
        if data is not None:
            refs.extend(extract_pinned_refs(data))
    return refs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GitHub Actions workflow policy checks.")
    parser.add_argument(
        "--check-reachability",
        action="store_true",
        help=(
            "Resolve every pinned SHA via `git ls-remote` and fail on an unreachable "
            "ref. Off the PR hot path (network-bound); default runs are regex-only."
        ),
    )
    args = parser.parse_args(argv)

    failures = _collect_failures()

    workflow_count = len(sorted(Path(".github/workflows").glob("*.yml")))
    composite_count = len(sorted(Path(".github/actions").glob("*/action.yml")))

    if args.check_reachability:
        failures.extend(check_reachability(_collect_pinned_refs()))

    if failures:
        print("workflow policy check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        f"workflow policy check passed ({workflow_count} workflow files, "
        f"{composite_count} composite actions)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
