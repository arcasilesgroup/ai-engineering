"""Backwards-compatible shim over :mod:`opa_runner` (spec-122 Phase E, T-3.16).

The legacy custom mini-Rego interpreter that used to live here was unable to
parse ``import rego.v1`` and the OPA proper grammar (``deny contains "msg"
if { ... }``), which is why the policy bundle migrated to OPA in spec-122-c
(T-3.5). This module retains the public ``evaluate(policy_path, input) ->
Decision`` API for any straggling caller and translates each call into a
single ``opa eval`` invocation against a one-file bundle.

There are zero production callers — only the defensive test surface in
:mod:`tests.unit.governance.test_opa_runner` exercises this path. The shim
exists as an insurance policy for downstream forks that imported the
spec-110 API directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import opa_runner

__all__ = ["Decision", "PolicyError", "evaluate"]

_PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z_][\w.]*)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Decision:
    """Result of a policy evaluation. Mirrors the spec-110 dataclass shape."""

    allow: bool
    reason: str | None = None


class PolicyError(ValueError):
    """Raised when the .rego file is missing a ``package`` declaration."""


def evaluate(policy_path: Path | str, input_data: dict[str, Any]) -> Decision:
    """Evaluate ``policy_path`` against ``input_data`` via the OPA CLI.

    The shim infers the policy's package name from its ``package <name>``
    line, queries ``data.<pkg>.deny`` against a one-file bundle rooted at
    the policy's parent directory, and translates the OPA result back to a
    :class:`Decision`.
    """
    path = Path(policy_path)
    source = path.read_text(encoding="utf-8")
    match = _PACKAGE_RE.search(source)
    if match is None:
        raise PolicyError(f"{path} is missing a `package` declaration")
    package = match.group(1)

    result = opa_runner.evaluate(
        f"data.{package}.deny",
        input_data,
        bundle_path=path.parent,
    )
    if result.deny_messages:
        return Decision(allow=False, reason=result.deny_messages[0])
    return Decision(allow=True)
