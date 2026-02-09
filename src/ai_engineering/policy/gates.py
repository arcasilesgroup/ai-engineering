"""Governance gate enforcement for hooks and guarded workflows."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from ai_engineering.paths import repo_root, state_dir
from ai_engineering.state.io import append_ndjson


PROTECTED_BRANCHES = {"main", "master"}


class GateCheck(NamedTuple):
    """Single mandatory check definition."""

    tool: str
    args: list[str]
    remediation: str


PRE_COMMIT_CHECKS = [
    GateCheck(
        "ruff", ["format", "--check", "src", "tests"], "run '.venv/bin/ruff format src tests'"
    ),
    GateCheck("ruff", ["check", "src", "tests"], "run '.venv/bin/ruff check src tests'"),
    GateCheck(
        "gitleaks",
        ["protect", "--staged", "--redact"],
        "review staged content and remove secrets before retrying",
    ),
    GateCheck(
        "docs-contract",
        [],
        "ensure active backlog/delivery docs include required metadata and checklist contract",
    ),
]


PRE_PUSH_CHECKS = [
    GateCheck("semgrep", ["--config", "auto"], "address findings or tune local code before push"),
    GateCheck("pip-audit", [], "upgrade vulnerable dependencies and regenerate lockfiles"),
    GateCheck("pytest", [], "fix failing tests and rerun '.venv/bin/python -m pytest'"),
    GateCheck("ty", ["check", "src"], "fix type diagnostics and rerun '.venv/bin/ty check src'"),
]


DOC_CONTRACT_FILES: tuple[str, ...] = (
    ".ai-engineering/context/backlog/epics.md",
    ".ai-engineering/context/backlog/features.md",
    ".ai-engineering/context/backlog/user-stories.md",
    ".ai-engineering/context/backlog/tasks.md",
    ".ai-engineering/context/backlog/index.md",
    ".ai-engineering/context/backlog/status.md",
    ".ai-engineering/context/backlog/traceability-matrix.md",
    ".ai-engineering/context/delivery/discovery.md",
    ".ai-engineering/context/delivery/architecture.md",
    ".ai-engineering/context/delivery/planning.md",
    ".ai-engineering/context/delivery/implementation.md",
    ".ai-engineering/context/delivery/review.md",
    ".ai-engineering/context/delivery/verification.md",
    ".ai-engineering/context/delivery/testing.md",
    ".ai-engineering/context/delivery/iteration.md",
    ".ai-engineering/context/delivery/index.md",
    ".ai-engineering/context/delivery/evidence/validation-runs.md",
    ".ai-engineering/context/delivery/evidence/execution-history.md",
)

DOC_CONTRACT_REVIEW_FILE = ".ai-engineering/context/delivery/review.md"

DOC_CONTRACT_REQUIRED_GATES = (
    "unit",
    "integration",
    "e2e",
    "ruff",
    "ty",
    "gitleaks",
    "semgrep",
    "pip-audit",
)


def _metadata_block(content: str) -> str | None:
    marker = "## Document Metadata"
    start = content.find(marker)
    if start == -1:
        return None
    block_start = start + len(marker)
    next_heading = content.find("\n## ", block_start)
    if next_heading == -1:
        return content[block_start:]
    return content[block_start:next_heading]


def _run_docs_contract_check(root: Path) -> tuple[bool, str]:
    errors: list[str] = []
    required_metadata_fields = (
        "- Doc ID:",
        "- Owner:",
        "- Status:",
        "- Last reviewed:",
        "- Source of truth:",
    )

    for relative in DOC_CONTRACT_FILES:
        path = root / relative
        if not path.exists():
            errors.append(f"missing required doc: {relative}")
            continue
        content = path.read_text(encoding="utf-8")
        metadata = _metadata_block(content)
        if metadata is None:
            errors.append(f"{relative}: missing '## Document Metadata' section")
            continue
        for field in required_metadata_fields:
            if field not in metadata:
                errors.append(f"{relative}: missing metadata field '{field}'")
        expected_source = f"`{relative}`"
        if expected_source not in metadata:
            errors.append(
                f"{relative}: source of truth must reference its own path as {expected_source}"
            )

    review_path = root / DOC_CONTRACT_REVIEW_FILE
    if review_path.exists():
        review = review_path.read_text(encoding="utf-8")
        checklist_title = "## Backlog and Delivery Docs Pre-Merge Checklist"
        if checklist_title not in review:
            errors.append(f"{DOC_CONTRACT_REVIEW_FILE}: missing pre-merge checklist section")
        for gate in DOC_CONTRACT_REQUIRED_GATES:
            if f"`{gate}`" not in review:
                errors.append(
                    f"{DOC_CONTRACT_REVIEW_FILE}: pre-merge checklist missing required gate `{gate}`"
                )
    else:
        errors.append(f"missing required doc: {DOC_CONTRACT_REVIEW_FILE}")

    if errors:
        return False, "\n".join(errors)
    return True, "docs contract checks passed"


def current_branch(root: Path) -> str:
    """Return current git branch name."""
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.strip()


def _tool_path(root: Path, tool: str) -> str | None:
    """Resolve tool path preferring project-local .venv binaries."""
    venv_unix = root / ".venv" / "bin" / tool
    if venv_unix.exists():
        return str(venv_unix)
    venv_windows = root / ".venv" / "Scripts" / f"{tool}.exe"
    if venv_windows.exists():
        return str(venv_windows)
    return shutil.which(tool)


def _venv_python(root: Path) -> str | None:
    """Resolve python executable from local venv if present."""
    unix = root / ".venv" / "bin" / "python"
    if unix.exists():
        return str(unix)
    windows = root / ".venv" / "Scripts" / "python.exe"
    if windows.exists():
        return str(windows)
    return None


def _run_raw(root: Path, command: list[str]) -> tuple[bool, str]:
    """Execute command and return success/output without tool resolution."""
    proc = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return True, proc.stdout.strip() or "ok"
    output = (proc.stdout + proc.stderr).strip()
    return False, output or "command failed"


def _attempt_python_tool_install(root: Path, package: str) -> tuple[bool, str]:
    """Attempt installing a Python-based tool into local .venv."""
    python_exec = _venv_python(root)
    if python_exec is None:
        return False, "missing local .venv python runtime"
    return _run_raw(
        root,
        [
            python_exec,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            package,
        ],
    )


def _attempt_gitleaks_install(root: Path) -> tuple[bool, str]:
    """Attempt installing gitleaks using available platform package managers."""
    installers: list[list[str]] = []
    if shutil.which("brew"):
        installers.append(["brew", "install", "gitleaks"])
    if shutil.which("winget"):
        installers.append(
            [
                "winget",
                "install",
                "--exact",
                "--id",
                "Gitleaks.Gitleaks",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        )
    if shutil.which("choco"):
        installers.append(["choco", "install", "gitleaks", "-y"])
    if shutil.which("apt-get") and sys.platform.startswith("linux"):
        installers.append(["apt-get", "install", "-y", "gitleaks"])

    if not installers:
        return False, "no supported package manager available to auto-install gitleaks"

    failures: list[str] = []
    for command in installers:
        ok, output = _run_raw(root, command)
        if ok and shutil.which("gitleaks"):
            return True, output
        failures.append(output)
    return False, "; ".join(failures)


def _attempt_tool_remediation(root: Path, tool: str) -> tuple[bool, str]:
    """Attempt repairing missing mandatory tooling before failing a gate."""
    if tool in {"ruff", "pip-audit", "pytest", "semgrep", "ty"}:
        package_map = {
            "ruff": "ruff",
            "pip-audit": "pip-audit",
            "pytest": "pytest",
            "semgrep": "semgrep",
            "ty": "ty",
        }
        ok, output = _attempt_python_tool_install(root, package_map[tool])
        if ok and _tool_path(root, tool) is not None:
            return True, f"auto-remediation installed {tool}"
        return False, f"auto-remediation failed for {tool}: {output}"

    if tool == "gitleaks":
        ok, output = _attempt_gitleaks_install(root)
        if ok and _tool_path(root, tool) is not None:
            return True, "auto-remediation installed gitleaks"
        return False, f"auto-remediation failed for gitleaks: {output}"

    return False, f"no auto-remediation strategy for required tool: {tool}"


def _github_repo_slug_from_origin(root: Path) -> tuple[str, str] | None:
    """Parse owner/repo from origin URL if it is a GitHub remote."""
    proc = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    url = proc.stdout.strip()
    if "github.com" not in url:
        return None

    normalized = url
    if normalized.startswith("git@github.com:"):
        normalized = normalized.replace("git@github.com:", "")
    elif normalized.startswith("https://github.com/"):
        normalized = normalized.replace("https://github.com/", "")
    else:
        return None

    normalized = normalized.removesuffix(".git")
    parts = normalized.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def discover_protected_branches(root: Path) -> set[str]:
    """Discover protected branches from GitHub, with safe fallback."""
    branches = set(PROTECTED_BRANCHES)
    slug = _github_repo_slug_from_origin(root)
    if slug is None:
        return branches

    owner, repo = slug
    proc = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo}/branches?protected=true",
            "--jq",
            ".[].name",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return branches
    discovered = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if discovered:
        branches.update(discovered)
    return branches


def gate_requirements(root: Path) -> dict[str, object]:
    """Return machine-readable gate requirements for current repository."""
    return {
        "protectedBranches": sorted(discover_protected_branches(root)),
        "stages": {
            "pre-commit": [
                {"tool": check.tool, "args": check.args, "remediation": check.remediation}
                for check in PRE_COMMIT_CHECKS
            ],
            "pre-push": [
                {"tool": check.tool, "args": check.args, "remediation": check.remediation}
                for check in PRE_PUSH_CHECKS
            ],
            "commit-msg": [
                {
                    "tool": "commit-message",
                    "args": [],
                    "remediation": "provide a non-empty commit message",
                }
            ],
        },
    }


def _run_tool(root: Path, tool: str, args: list[str]) -> tuple[bool, str]:
    """Run required tool and return success plus message."""
    executable = _tool_path(root, tool)
    if executable is None:
        repaired, details = _attempt_tool_remediation(root, tool)
        if not repaired:
            return False, f"missing required tool: {tool}; {details}"
        executable = _tool_path(root, tool)
        if executable is None:
            return False, f"missing required tool after auto-remediation: {tool}"

    proc = subprocess.run(
        [executable, *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return True, "ok"
    output = proc.stdout + proc.stderr
    return False, output.strip() or f"{tool} failed"


def _audit(event: str, details: dict[str, object]) -> None:
    """Append governance event to audit log."""
    try:
        root = repo_root()
        append_ndjson(
            state_dir(root) / "audit-log.ndjson",
            {"event": event, "actor": "gate-engine", "details": details},
        )
    except Exception:
        return


def _block_if_protected(root: Path, stage: str) -> tuple[bool, str]:
    protected_branches = discover_protected_branches(root)
    branch = current_branch(root)
    if branch in protected_branches:
        msg = f"blocked: direct {stage} is not allowed on protected branch '{branch}'"
        _audit(
            "gate_blocked_protected_branch",
            {"stage": stage, "branch": branch, "protectedBranches": sorted(protected_branches)},
        )
        return False, msg
    return True, "ok"


def _run_gate_checks(root: Path, stage: str, checks: list[GateCheck]) -> tuple[bool, list[str]]:
    """Run mandatory gate checks and include remediation in failures."""
    failures: list[str] = []
    for check in checks:
        if check.tool == "docs-contract":
            check_ok, output = _run_docs_contract_check(root)
        else:
            check_ok, output = _run_tool(root, check.tool, check.args)
        if check_ok:
            continue
        failures.append(f"{check.tool}: {output}\nremediation: {check.remediation}")

    if failures:
        _audit("gate_failed", {"stage": stage, "failures": failures})
        return False, failures
    _audit("gate_passed", {"stage": stage})
    return True, [f"{stage} checks passed"]


def run_pre_commit() -> tuple[bool, list[str]]:
    """Run pre-commit mandatory checks."""
    root = repo_root()
    ok, msg = _block_if_protected(root, "commit")
    if not ok:
        return False, [msg]

    return _run_gate_checks(root, "pre-commit", PRE_COMMIT_CHECKS)


def run_commit_msg(commit_msg_file: Path) -> tuple[bool, list[str]]:
    """Run commit-msg mandatory checks."""
    root = repo_root()
    ok, msg = _block_if_protected(root, "commit")
    if not ok:
        return False, [msg]

    message = commit_msg_file.read_text(encoding="utf-8").strip()
    if not message:
        failure = "commit message cannot be empty"
        _audit("gate_failed", {"stage": "commit-msg", "failures": [failure]})
        return False, [failure]
    _audit("gate_passed", {"stage": "commit-msg"})
    return True, ["commit-msg checks passed"]


def run_pre_push() -> tuple[bool, list[str]]:
    """Run pre-push mandatory checks."""
    root = repo_root()
    ok, msg = _block_if_protected(root, "push")
    if not ok:
        return False, [msg]

    return _run_gate_checks(root, "pre-push", PRE_PUSH_CHECKS)


def run_docs_contract() -> tuple[bool, list[str]]:
    """Run documentation contract checks for backlog and delivery artifacts."""
    root = repo_root()
    ok, output = _run_docs_contract_check(root)
    if ok:
        return True, [output]
    return False, [output]
