"""Assert the canonical manifests carry the spec-137 audit_policy block."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

ROOT_MANIFEST = REPO_ROOT / ".ai-engineering" / "manifest.yml"
TEMPLATE_MANIFEST = (
    REPO_ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "manifest.yml"
)

EXPECTED_KINDS = {
    "skill_invoked",
    "agent_dispatched",
    "context_load",
    "ide_hook",
    "framework_error",
    "framework_operation",
    "git_hook",
    "control_outcome",
    "task_trace",
    "memory_event",
    "eval_run",
    "retention_applied",
    "policy_decision",
}


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _assert_block(manifest: dict, source: str) -> None:
    block = manifest.get("audit_policy")
    assert isinstance(block, dict), f"{source}: audit_policy block missing or malformed."

    allowlist = block.get("kind_allowlist", [])
    assert isinstance(allowlist, list), f"{source}: kind_allowlist must be a list."
    assert set(allowlist) == EXPECTED_KINDS, (
        f"{source}: kind_allowlist drifted from the 13 declared kinds: "
        f"missing={EXPECTED_KINDS - set(allowlist)}, "
        f"extra={set(allowlist) - EXPECTED_KINDS}"
    )

    floor = block.get("severity_floor", {})
    assert isinstance(floor, dict), f"{source}: severity_floor must be a mapping."
    for kind, severity in floor.items():
        assert severity in {"S0", "S1", "S2", "S3"}, (
            f"{source}: invalid severity '{severity}' for kind '{kind}'."
        )
    assert floor.get("default") in {"S0", "S1", "S2", "S3"}, (
        f"{source}: severity_floor must declare a 'default' tier."
    )

    failure_emission = block.get("failure_emission")
    assert failure_emission in {"always", "never"}, (
        f"{source}: failure_emission must be 'always' or 'never', got {failure_emission!r}."
    )


def test_root_manifest_declares_audit_policy() -> None:
    _assert_block(_load_yaml(ROOT_MANIFEST), "root manifest.yml")


def test_template_manifest_declares_audit_policy() -> None:
    _assert_block(_load_yaml(TEMPLATE_MANIFEST), "templates/.ai-engineering/manifest.yml")
