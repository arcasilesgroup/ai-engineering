"""Governance package.

Policy evaluation runs through the OPA-backed modules in this package. The
legacy in-process mini-Rego interpreter was removed by spec-146; import
`ai_engineering.governance.opa_runner` directly for policy execution.
"""

from __future__ import annotations

__all__: list[str] = []
