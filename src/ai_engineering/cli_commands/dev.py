"""Dev CLI namespace (spec-132 D-132-05): source-repo only commands.

The ``dev`` Typer group is hidden by default and houses commands that are
only useful when working inside the ai-engineering source repo (mirror
sync, telemetry replay, etc.). Visibility detection via
``pyproject.toml [tool.aiengineering.source_repo]`` is wired by
``cli_factory.py``.

Currently registered subcommands:

* ``ai-eng dev sync`` -- regenerate IDE-adapted command mirrors.
"""

from __future__ import annotations
