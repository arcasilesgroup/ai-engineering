"""Mirror sync package.

Splits the legacy `scripts/sync_command_mirrors.py` monolith (~82 KB,
~50 top-level callables) into a small package with one logic module
(`core`) plus thin per-concern facades (`frontmatter`, `manifest_sync`,
`claude_target`, `codex_target`, `gemini_target`, `copilot_target`).

The original entry point at `scripts/sync_command_mirrors.py` is now a
backwards-compat shim (<= 2 KB) that delegates to `__main__:main`.

Per spec-122-d D-122-24. Splitting concerns this way preserves
byte-for-byte parity (verified by `tests/integration/sync/test_sync_compat.py`)
while giving downstream readers a navigable surface.
"""

from __future__ import annotations

from scripts.sync_mirrors.core import main, sync_all

__all__ = ["main", "sync_all"]
