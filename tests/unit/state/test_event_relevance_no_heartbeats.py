"""Guard the two retired heartbeat emitters (spec-137 D-137-01).

The brief survey on 2026-05-15 found that 1,230 of 1,335 NDJSON rows
(92.1%) in a single working day came from just two unconditional
polling emitters:

1. ``ai-eng spec verify`` emitted ``spec_verified`` on every invocation
   (848 rows/day) regardless of drift.
2. ``install_simulate_hook`` emitted one row per tool per synthetic
   install (382 rows/day) regardless of outcome.

This test locks the post-migration shape: both emit sites must wrap
the emit in a conditional so emit-on-change semantics replace the
heartbeat. If a future PR reverts one of these wrappers, the test
fails loud.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

SPEC_CMD = REPO_ROOT / "src" / "ai_engineering" / "cli_commands" / "spec_cmd.py"
USER_SCOPE_INSTALL = REPO_ROOT / "src" / "ai_engineering" / "installer" / "user_scope_install.py"


def _find_call_under_if_branch(tree: ast.Module, callee_name: str, signature_literal: str) -> bool:
    """Return True iff a call to ``callee_name`` whose first stringy
    argument matches ``signature_literal`` is nested inside an ``ast.If``
    statement (the conditional that turns a heartbeat into a state-change
    emit)."""
    for parent in ast.walk(tree):
        if not isinstance(parent, ast.If):
            continue
        for descendant in ast.walk(parent):
            if not isinstance(descendant, ast.Call):
                continue
            callee = descendant.func
            name: str | None = None
            if isinstance(callee, ast.Name):
                name = callee.id
            elif isinstance(callee, ast.Attribute):
                name = callee.attr
            if name != callee_name:
                continue
            for arg in descendant.args:
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and arg.value == signature_literal
                ):
                    return True
            for kw in descendant.keywords:
                v = kw.value
                if (
                    isinstance(v, ast.Constant)
                    and isinstance(v.value, str)
                    and v.value == signature_literal
                ):
                    return True
    return False


def test_spec_verified_is_emit_on_change_only() -> None:
    """`_emit_signal(..., 'spec_verified', ...)` must be inside an `if` block."""
    tree = ast.parse(SPEC_CMD.read_text(encoding="utf-8"))
    assert _find_call_under_if_branch(tree, "_emit_signal", "spec_verified"), (
        "spec_verified emit must be inside an `if drift_detected:` (or "
        "equivalent) conditional per spec-137 D-137-01. Found an "
        "unconditional emit -- the heartbeat tail will regress."
    )


def test_install_simulate_hook_short_circuits_on_success() -> None:
    """`_emit_simulate_event` must early-return when outcome=='success'."""
    source = USER_SCOPE_INSTALL.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_emit_simulate_event":
            # First statement after docstring should be a conditional return-on-success
            # (or any pattern that drops the success-case rows).
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                statements = body[1:]
            else:
                statements = body
            for stmt in statements[:3]:
                # Look for `outcome == "success"` test followed by a `return`.
                if isinstance(stmt, ast.If) and _is_success_guard(stmt):
                    return
            raise AssertionError(
                "install_simulate_hook must short-circuit on outcome=='success' "
                "(spec-137 D-137-01). No success-guard found in the first three "
                "statements of _emit_simulate_event."
            )
    raise AssertionError("Function _emit_simulate_event not found.")


def _is_success_guard(node: ast.If) -> bool:
    """Return True iff the `if` tests for outcome == 'success' and returns inside."""
    if not isinstance(node.test, ast.Compare):
        return False
    left = node.test.left
    if not isinstance(left, ast.Name) or left.id != "outcome":
        return False
    if not node.test.ops or not isinstance(node.test.ops[0], ast.Eq):
        return False
    comparator = node.test.comparators[0]
    if not isinstance(comparator, ast.Constant) or comparator.value != "success":
        return False
    return any(isinstance(stmt, ast.Return) for stmt in node.body)
