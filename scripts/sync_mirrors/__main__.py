"""CLI entry point for the mirror sync package.

Invoked as `python -m scripts.sync_mirrors [args]`. The legacy
`scripts/sync_command_mirrors.py` shim delegates here so external CI
and skill invocations keep working unchanged.
"""

from __future__ import annotations

import sys

from scripts.sync_mirrors.core import main

if __name__ == "__main__":
    sys.exit(main())
