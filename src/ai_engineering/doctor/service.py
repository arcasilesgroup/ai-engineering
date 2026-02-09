"""Doctor service for readiness checks."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.detector.readiness import detect_az, detect_gh, detect_python_tools
from ai_engineering.hooks.manager import detect_hook_readiness, install_placeholder_hooks
from ai_engineering.paths import ai_engineering_root, repo_root
from ai_engineering.policy.gates import (
    _attempt_tool_remediation,
    current_branch,
    discover_protected_branches,
)
from ai_engineering.state.io import load_model
from ai_engineering.state.models import (
    DecisionStore,
    InstallManifest,
    OwnershipMap,
    SourcesLock,
)


def _validate_state_files(ae_root: Path) -> dict[str, bool]:
    state_root = ae_root / "state"
    checks = {
        "install-manifest.json": InstallManifest,
        "ownership-map.json": OwnershipMap,
        "sources.lock.json": SourcesLock,
        "decision-store.json": DecisionStore,
    }
    result: dict[str, bool] = {}
    for file_name, model in checks.items():
        try:
            load_model(state_root / file_name, model)
            result[file_name] = True
        except Exception:
            result[file_name] = False
    result["audit-log.ndjson"] = (state_root / "audit-log.ndjson").exists()
    return result


def _remediate_python_tools(root: Path) -> dict[str, dict[str, object]]:
    """Attempt auto-remediation for missing Python tools and return results."""
    tool_map = {"uv": "uv", "ruff": "ruff", "ty": "ty", "pipAudit": "pip-audit"}
    results: dict[str, dict[str, object]] = {}
    current = detect_python_tools()
    for key, tool_name in tool_map.items():
        if current[key]["ready"]:
            results[key] = {"ready": True, "remediated": False}
            continue
        ok, detail = _attempt_tool_remediation(root, tool_name)
        results[key] = {"ready": ok, "remediated": ok, "detail": detail}
    return results


def run_doctor(*, fix_hooks: bool = False, fix_tools: bool = False) -> dict[str, object]:
    """Run readiness checks and return machine-readable status."""
    root = repo_root()
    if fix_hooks:
        install_placeholder_hooks(root)
    ae_root = ai_engineering_root(root)
    state_checks = _validate_state_files(ae_root)
    hook_checks = detect_hook_readiness(root)
    branch = current_branch(root)
    protected = sorted(discover_protected_branches(root))

    remediation: dict[str, dict[str, object]] | None = None
    if fix_tools:
        remediation = _remediate_python_tools(root)

    python_readiness = detect_python_tools()

    return {
        "repo": str(root),
        "governanceRootExists": ae_root.exists(),
        "branchPolicy": {
            "currentBranch": branch,
            "protectedBranches": protected,
            "currentBranchProtected": branch in protected,
        },
        "stateFiles": state_checks,
        "toolingReadiness": {
            "gh": detect_gh(),
            "az": detect_az(),
            "python": python_readiness,
            "gitHooks": hook_checks,
        },
        **({"toolRemediation": remediation} if remediation is not None else {}),
    }
