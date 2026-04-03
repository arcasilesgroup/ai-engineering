"""Hidden internal CLI commands for framework-managed automation."""

from __future__ import annotations

import subprocess
import sys

import typer


def internal_python(ctx: typer.Context) -> None:
    """Run Python with the framework interpreter and forward stdio/exit code."""
    args = list(ctx.args)
    if not args:
        raise typer.BadParameter("Provide Python arguments or a script path.")

    completed = subprocess.run(
        [sys.executable, *args],
        stdin=sys.stdin.buffer,
        stdout=sys.stdout.buffer,
        stderr=sys.stderr.buffer,
        check=False,
    )
    if completed.returncode != 0:
        raise typer.Exit(code=completed.returncode)
