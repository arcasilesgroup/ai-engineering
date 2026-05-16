#!/usr/bin/env python3
"""Backwards-compat shim for the legacy mirror-sync entry point.

The implementation lives in `scripts/sync_mirrors/` (spec-122-d D-122-24).
This file is preserved so external CI workflows, skills, scripts, and
unit tests that invoke `python scripts/sync_command_mirrors.py [args]`
or import names directly from this module keep working unchanged.
New code should import from `scripts.sync_mirrors.core` directly.

Parity is enforced by `tests/integration/sync/test_sync_compat.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing from repo root so `scripts.sync_mirrors` resolves.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

# Re-export the full public surface from `scripts.sync_mirrors.core` so
# legacy imports of `from scripts.sync_command_mirrors import <X>` keep
# resolving to the new canonical implementation.
from scripts.sync_mirrors import core as _core  # noqa: E402
from scripts.sync_mirrors.core import *  # noqa: E402, F403
from scripts.sync_mirrors.core import main  # noqa: E402

# Re-export underscore-prefixed helpers that `*` does not export.
# Tests use these as documented internal entry points.
_check_or_write = _core._check_or_write
_format_yaml_field = _core._format_yaml_field
_resolve_cross_reference_files = _core._resolve_cross_reference_files
_serialize_frontmatter = _core._serialize_frontmatter
_specialist_agent_output_paths = _core._specialist_agent_output_paths

if __name__ == "__main__":
    sys.exit(main())
