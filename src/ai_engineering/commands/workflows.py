"""Governed workflows for commit, pr, and acho command contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal, Mapping

from ai_engineering.paths import repo_root, state_dir
from ai_engineering.policy.gates import (
    PROTECTED_BRANCHES,
    current_branch,
    run_pre_commit,
    run_pre_push,
)
from ai_engineering.state.decision_logic import append_decision, context_hash, find_valid_decision
from ai_engineering.state.io import append_ndjson, load_model
from ai_engineering.state.models import DecisionStore


PrOnlyMode = Literal["auto-push", "defer-pr", "attempt-pr-anyway", "export-pr-payload"]


def _run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def _repo_name(root: Path) -> str:
    return root.name


def _audit(root: Path, event: str, details: Mapping[str, object]) -> None:
    append_ndjson(
        state_dir(root) / "audit-log.ndjson",
        {"event": event, "actor": "command-runner", "details": dict(details)},
    )


def ensure_not_protected(root: Path) -> tuple[bool, str]:
    branch = current_branch(root)
    if branch in PROTECTED_BRANCHES:
        return False, f"blocked: command is not allowed on protected branch '{branch}'"
    return True, "ok"


def stage_all(root: Path) -> None:
    _run(["git", "add", "-A"], cwd=root)


def has_staged_changes(root: Path) -> bool:
    proc = _run(["git", "diff", "--cached", "--quiet"], cwd=root)
    return proc.returncode != 0


def has_remote_upstream(root: Path) -> bool:
    proc = _run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=root)
    return proc.returncode == 0


def push_current_branch(root: Path) -> tuple[bool, str]:
    branch = current_branch(root)
    proc = _run(["git", "push", "-u", "origin", branch], cwd=root)
    if proc.returncode != 0:
        return False, proc.stderr.strip() or proc.stdout.strip() or "push failed"
    return True, proc.stdout.strip() or "push succeeded"


def create_commit(root: Path, message: str) -> tuple[bool, str]:
    proc = _run(["git", "commit", "-m", message], cwd=root)
    if proc.returncode != 0:
        return False, proc.stderr.strip() or proc.stdout.strip() or "commit failed"
    return True, proc.stdout.strip() or "commit created"


def create_pr(root: Path, title: str, body: str) -> tuple[bool, str]:
    proc = _run(["gh", "pr", "create", "--title", title, "--body", body], cwd=root)
    if proc.returncode != 0:
        return False, proc.stderr.strip() or proc.stdout.strip() or "pr creation failed"
    return True, proc.stdout.strip() or "pr created"


def run_commit_workflow(*, message: str, push: bool) -> tuple[bool, list[str]]:
    root = repo_root()
    messages: list[str] = []

    ok, protection_msg = ensure_not_protected(root)
    if not ok:
        _audit(root, "command_blocked", {"command": "commit", "reason": protection_msg})
        return False, [protection_msg]

    gate_ok, gate_messages = run_pre_commit()
    if not gate_ok:
        return False, gate_messages

    stage_all(root)
    if not has_staged_changes(root):
        return False, ["no staged changes to commit"]

    commit_ok, commit_msg = create_commit(root, message)
    messages.append(commit_msg)
    if not commit_ok:
        return False, messages

    _audit(root, "command_commit_created", {"message": message})
    if not push:
        return True, messages

    push_gate_ok, push_gate_messages = run_pre_push()
    if not push_gate_ok:
        return False, push_gate_messages

    push_ok, push_msg = push_current_branch(root)
    messages.append(push_msg)
    if push_ok:
        _audit(root, "command_branch_pushed", {"branch": current_branch(root)})
    return push_ok, messages


def _resolve_pr_only_mode(root: Path, requested_mode: PrOnlyMode) -> PrOnlyMode:
    policy_id = "PR_ONLY_UNPUSHED_BRANCH_MODE"
    context = context_hash({"branch": current_branch(root), "policyId": policy_id})
    try:
        store = load_model(state_dir(root) / "decision-store.json", DecisionStore)
    except Exception:
        return requested_mode
    prior = find_valid_decision(
        store,
        policy_id=policy_id,
        repo_name=_repo_name(root),
        context_hash_value=context,
    )
    if prior is not None and prior.decision in {
        "auto-push",
        "defer-pr",
        "attempt-pr-anyway",
        "export-pr-payload",
    }:
        return prior.decision  # type: ignore[return-value]
    return requested_mode


def run_pr_only_workflow(
    *,
    title: str,
    body: str,
    mode: PrOnlyMode,
    record_decision: bool,
) -> tuple[bool, list[str]]:
    root = repo_root()
    notes: list[str] = []

    effective_mode = mode
    if not has_remote_upstream(root):
        notes.append("warning: branch has no upstream. auto-push is recommended.")
        effective_mode = _resolve_pr_only_mode(root, mode)

    if not has_remote_upstream(root) and effective_mode == "auto-push":
        gate_ok, gate_messages = run_pre_push()
        if not gate_ok:
            return False, gate_messages
        push_ok, push_msg = push_current_branch(root)
        notes.append(push_msg)
        if not push_ok:
            return False, notes

    if not has_remote_upstream(root) and effective_mode == "defer-pr":
        notes.append("defer-pr selected: PR not created yet")
        if record_decision:
            c_hash = context_hash(
                {"branch": current_branch(root), "policyId": "PR_ONLY_UNPUSHED_BRANCH_MODE"}
            )
            try:
                append_decision(
                    state_dir(root) / "decision-store.json",
                    policy_id="PR_ONLY_UNPUSHED_BRANCH_MODE",
                    repo_name=_repo_name(root),
                    decision="defer-pr",
                    rationale="user declined auto-push for PR-only flow",
                    context_hash_value=c_hash,
                )
            except Exception:
                notes.append("warning: could not persist decision-store record")
        _audit(root, "pr_only_deferred", {"mode": "defer-pr", "branch": current_branch(root)})
        return True, notes

    if not has_remote_upstream(root) and effective_mode == "export-pr-payload":
        payload = {
            "title": title,
            "body": body,
            "base": "main",
            "head": current_branch(root),
        }
        notes.append(f"export-pr-payload: {payload}")
        _audit(root, "pr_only_export_payload", payload)
        return True, notes

    pr_ok, pr_msg = create_pr(root, title, body)
    notes.append(pr_msg)
    if not pr_ok and effective_mode == "attempt-pr-anyway":
        notes.append("warning: attempt-pr-anyway failed but flow continued by policy")
        _audit(root, "pr_only_attempt_failed", {"message": pr_msg})
        return True, notes
    if pr_ok:
        _audit(root, "pr_created", {"title": title, "mode": effective_mode})
    return pr_ok, notes


def run_pr_workflow(*, message: str, title: str, body: str) -> tuple[bool, list[str]]:
    commit_ok, commit_notes = run_commit_workflow(message=message, push=True)
    if not commit_ok:
        return False, commit_notes
    pr_ok, pr_message = create_pr(repo_root(), title, body)
    notes = [*commit_notes, pr_message]
    return pr_ok, notes
