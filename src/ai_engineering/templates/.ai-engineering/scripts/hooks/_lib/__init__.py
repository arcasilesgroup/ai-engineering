"""Shared hook libraries (sealed: stdlib-only).

The spec-mandated `_lib/hook-common.py` filename uses a hyphen, which is
not directly importable. We re-export the module here as the underscored
name `hook_common` so hooks can `from _lib.hook_common import ...`.
"""

from __future__ import annotations

import importlib.util as _importlib_util
import sys as _sys
from pathlib import Path as _Path

_HOOK_COMMON_PATH = _Path(__file__).parent / "hook-common.py"
_spec = _importlib_util.spec_from_file_location("_lib.hook_common", _HOOK_COMMON_PATH)
if _spec is not None and _spec.loader is not None:
    hook_common = _importlib_util.module_from_spec(_spec)
    _sys.modules["_lib.hook_common"] = hook_common
    _spec.loader.exec_module(hook_common)
