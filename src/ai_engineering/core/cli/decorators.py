"""Universal help-on-no-args support for Typer commands (spec-132 D-132-11).

Click raises :class:`click.exceptions.MissingParameter` during parameter
processing — that is, *before* the Typer command callback runs. A callback
decorator alone therefore cannot intercept the missing-argument condition.

This module exports two collaborators that together implement the brief's
"universal" requirement:

* :class:`HelpOnNoArgsCommand` — a :class:`typer.core.TyperCommand` subclass
  whose ``parse_args`` short-circuits when (a) the raw arg list is empty
  AND (b) the command has at least one required positional argument. The
  short-circuit prints ``ctx.get_help()`` and exits 0.
* :func:`apply_no_args_help` — a registration-time helper that wires
  :class:`HelpOnNoArgsCommand` as the Typer ``cls=`` on each registered
  command of a Typer app, recursing into nested groups. Opt-out groups can
  be passed via the ``opt_out_groups`` argument.
* :func:`no_args_help` — a thin compatibility alias that wraps a callback
  with no behavioural change beyond keeping ``functools.wraps`` metadata.
  Kept so call-sites that already imported a callback decorator do not
  need to learn the new registration shape.

Per CANONICAL.md §10.4 (DRY) and §10.5 (TDD), behaviour is exercised by
``tests/unit/cli/test_no_args_help.py``.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterable
from typing import TypeVar, cast

import click
import typer

F = TypeVar("F", bound=Callable[..., object])


class HelpOnNoArgsCommand(typer.core.TyperCommand):
    """Print help and exit 0 when invoked without args and a required param exists.

    Stock Typer / Click semantics raise ``MissingParameter`` with exit code 2
    and a red error panel. Per D-132-11 we treat "no args provided" as an
    implicit help request whenever the command has at least one required
    parameter — positional :class:`click.Argument` or required
    :class:`click.Option` (e.g. ``--specs-dir`` on ``spec activate``) — with
    no default value.

    The short-circuit applies *only* to the bare-no-args case. Any other
    parser path (partial args, ``--help``, ``--option=value``) flows through
    Click's normal handling.
    """

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        """Intercept the no-args path before Click raises MissingParameter."""
        if not args and self._has_required_user_param():
            click.echo(self.get_help(ctx))
            ctx.exit(0)
        return super().parse_args(ctx, args)

    def _has_required_user_param(self) -> bool:
        """Return True when at least one user-supplied required param exists.

        Excludes Click's auto-injected ``--help`` Option (which is ``required``
        only in the sense of its declaration, but never user-required).
        """
        for param in self.params:
            if not param.required:
                continue
            if isinstance(param, click.Argument):
                return True
            if isinstance(param, click.Option) and not param.is_flag:
                # Skip the auto-injected `--help` option.
                if "--help" in (param.opts or ()):
                    continue
                return True
        return False


def no_args_help(func: F) -> F:
    """Compatibility callback decorator.

    The real enforcement lives in :class:`HelpOnNoArgsCommand` (parameter
    parsing happens before any callback runs). This decorator is kept so the
    public API in :mod:`ai_engineering.core.cli` can expose a uniform name
    matching the spec wording; it does not modify call behaviour.
    """

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        return func(*args, **kwargs)

    return cast(F, wrapper)


def apply_no_args_help(
    app: typer.Typer,
    *,
    opt_out_groups: Iterable[str] = (),
) -> None:
    """Apply :class:`HelpOnNoArgsCommand` to every command in ``app`` recursively.

    Mutates each :class:`typer.models.CommandInfo` so its ``cls`` is the help-
    on-no-args command class. Skips any command nested under a group whose
    name is in ``opt_out_groups``.

    Idempotent: running twice is a no-op because each call replaces ``cls``
    with the same class.

    Args:
        app: The Typer application to decorate.
        opt_out_groups: Iterable of group names whose nested commands keep
            stock Typer behaviour (e.g. internal-only ``internal`` / ``dev``).
    """
    opt_out = frozenset(opt_out_groups)
    _apply_to_typer(app, opt_out=opt_out, in_opt_out=False)


def _apply_to_typer(
    app: typer.Typer,
    *,
    opt_out: frozenset[str],
    in_opt_out: bool,
) -> None:
    """Recursive worker — walks ``registered_commands`` and ``registered_groups``."""
    if not in_opt_out:
        for cmd in app.registered_commands:
            # Preserve any caller-supplied ``cls`` override that already extends
            # our help-on-no-args class. Otherwise replace with our subclass.
            existing = cmd.cls
            if existing is None or not issubclass(existing, HelpOnNoArgsCommand):
                cmd.cls = HelpOnNoArgsCommand
    for group in app.registered_groups:
        if group.typer_instance is None:
            continue
        nested_in_opt_out = in_opt_out or (group.name in opt_out)
        _apply_to_typer(
            group.typer_instance,
            opt_out=opt_out,
            in_opt_out=nested_in_opt_out,
        )
