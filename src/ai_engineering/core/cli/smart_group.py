"""Smart Typer group with cross-subcommand did-you-mean (spec-133).

Extends :class:`typer.core.TyperGroup` so that typos against an unknown
command at the root surface get suggestions from the full command tree
— including nested subcommands. For example, ``ai-eng risk-check``
should now suggest ``gate risk-check`` instead of the wrong
``check``.

The walk is shallow-recursive: every direct child group contributes its
own commands prefixed with the parent name (``gate risk-check``,
``audit verify``, etc.). Hidden groups (``dev``, ``internal``) are
skipped so they never leak into user-facing suggestions.
"""

from __future__ import annotations

from difflib import get_close_matches

import click
import typer.core

__all__ = ("SmartTyperGroup",)


def _enumerate_paths(group: click.Group, prefix: str = "") -> list[str]:
    """Return every reachable command path under ``group`` as space-joined names."""
    paths: list[str] = []
    for name, cmd in group.commands.items():
        if getattr(cmd, "hidden", False):
            continue
        full = f"{prefix} {name}".strip()
        paths.append(full)
        if isinstance(cmd, click.Group):
            paths.extend(_enumerate_paths(cmd, prefix=full))
    return paths


class SmartTyperGroup(typer.core.TyperGroup):
    """TyperGroup that suggests nested subcommand paths on unknown commands.

    Behaviour matches Typer's default ``suggest_commands`` flow at the
    flat level, but extends the candidate pool to every reachable path
    in the command tree. This fixes the case where ``ai-eng risk-check``
    used to suggest ``check`` (closest flat match) when the real path
    is ``ai-eng gate risk-check``.
    """

    def get_help(self, ctx: click.Context) -> str:
        """Render the ROOT help as spec-183 colour-grouped panels.

        Both entry paths converge here: the bare ``ai-eng`` invocation
        (``_app_callback`` echoes ``ctx.get_help()``) and Click's eager
        ``--help`` option. Only the root group is a ``SmartTyperGroup``, so
        subcommand ``--help`` never reaches this override (Non-Goal 1); the
        ``ctx.parent is None`` guard is belt-and-braces. Fail-open: any error
        falls back to Typer's default rendering.
        """
        if ctx.parent is None:
            try:
                from ai_engineering.cli_help_render import render_root_help

                return render_root_help(ctx)
            except Exception:
                return super().get_help(ctx)
        return super().get_help(ctx)

    def resolve_command(
        self,
        ctx: click.Context,
        args: list[str],
    ) -> tuple[str | None, click.Command | None, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as exc:
            if not args or not self.suggest_commands:
                raise
            typo = args[0]
            candidates = _enumerate_paths(self)
            matches = get_close_matches(typo, candidates, n=3, cutoff=0.5)
            if not matches:
                # Fall back to Typer's own suggestion (already attached).
                raise
            suggestion = ", ".join(f"'ai-eng {m}'" for m in matches)
            base = f"No such command {typo!r}.".rstrip(".")
            exc.message = f"{base}. Did you mean {suggestion}?"
            raise
