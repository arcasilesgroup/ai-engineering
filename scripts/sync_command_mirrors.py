#!/usr/bin/env python3
"""Backwards-compat shim for the legacy mirror-sync entry point.

The implementation lives in `scripts/sync_mirrors/` (spec-122-d D-122-24).
This file is preserved so external CI workflows, skills, and scripts
that invoke `python scripts/sync_command_mirrors.py [args]` keep working
unchanged. New code should import from `scripts.sync_mirrors` directly.

Parity is enforced by `tests/integration/sync/test_sync_compat.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing from repo root so `scripts.sync_mirrors` resolves.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts.sync_mirrors.core import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
