"""CLI-layer pure helpers for ``ai-eng`` (spec-132 D-132-11).

Currently exports the :class:`HelpOnNoArgsCommand` Click command class and the
:func:`apply_no_args_help` registration helper. Both belong to ``core`` because
they encode UX policy that adapters consume but never define.
"""

from ai_engineering.core.cli.decorators import (
    HelpOnNoArgsCommand,
    apply_no_args_help,
    no_args_help,
)
from ai_engineering.core.cli.smart_group import SmartTyperGroup

__all__ = [
    "HelpOnNoArgsCommand",
    "SmartTyperGroup",
    "apply_no_args_help",
    "no_args_help",
]
