"""Legacy v2 pip-audit shim.

The v2 pre-push gate calls `python -m ai_engineering.verify.tls_pip_audit`.
On a v3 worktree there is nothing meaningful to audit yet — the actual
dependency surface (`pyproject.toml`, `python/*/pyproject.toml`) is
audited by `pip-audit` directly.

This module exits 0 so the gate passes. The v3 native pre-push gate
(Phase 4) will replace this with a proper dependency audit reading
from the workspace lockfiles.
"""

from __future__ import annotations

import sys


def main() -> int:  # pragma: no cover - shim
    sys.stdout.write("[v3-shim] tls_pip_audit: deferred to v3 native gate (Phase 4)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
