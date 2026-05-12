"""Tests for the universal `@no_args_help` decorator (spec-132 D-132-11).

Walks every public Typer command in :func:`ai_engineering.cli_factory.create_app`
and asserts that invoking it with NO arguments prints the help text and exits
with status 0 instead of raising ``MissingParameter``.

The opt-out is enforced for the internal ``internal`` group (sub-004 will rename
this group to ``dev``; until that rename lands the test skips the dev-named
assertion and verifies via the canonical ``internal`` name).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
import typer
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app


def _has_required_argument(callback: object) -> bool:
    """Return True when the Typer callback has a positional required argument."""
    import inspect

    if callback is None or not callable(callback):
        return False
    sig = inspect.signature(callback)
    for param in sig.parameters.values():
        default = param.default
        # Typer marks Argument required when default has no fallback. Annotated
        # arguments arrive via ``typer.Argument(...)`` either positionally
        # (default=ellipsis) or as the ``Annotated[..., typer.Argument(...)]``
        # form (the default is ``inspect.Parameter.empty`` until Typer resolves
        # the metadata).
        if default is inspect.Parameter.empty:
            return True
        # Direct ``typer.Argument(...)`` default.
        if hasattr(default, "param_decls") and getattr(default, "default", ...) is ...:
            return True
    return False


def _walk_commands(
    app: typer.Typer, prefix: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], typer.models.CommandInfo, bool]]:
    """Yield ``(verb_path, command_info, opted_out)`` tuples.

    ``opted_out`` is True when any segment along the path is an opt-out group
    (currently the hidden ``internal`` group; sub-004 introduces ``dev``).
    """
    opt_out_groups = {"internal", "dev"}
    is_in_opt_out = any(seg in opt_out_groups for seg in prefix)
    for cmd in app.registered_commands:
        if cmd.name is None:
            continue
        yield (*prefix, cmd.name), cmd, is_in_opt_out
    for group in app.registered_groups:
        if group.name is None or group.typer_instance is None:
            continue
        next_prefix = (*prefix, group.name)
        next_opt_out = is_in_opt_out or group.name in opt_out_groups
        for cmd in group.typer_instance.registered_commands:
            if cmd.name is None:
                continue
            yield (*next_prefix, cmd.name), cmd, next_opt_out
        # Nested sub-groups (audit -> retention).
        for nested in group.typer_instance.registered_groups:
            if nested.name is None or nested.typer_instance is None:
                continue
            deeper_prefix = (*next_prefix, nested.name)
            for cmd in nested.typer_instance.registered_commands:
                if cmd.name is None:
                    continue
                yield (*deeper_prefix, cmd.name), cmd, next_opt_out


def _public_required_arg_cases() -> list[tuple[str, ...]]:
    """Discover public commands with required positional arguments."""
    app = create_app()
    cases: list[tuple[str, ...]] = []
    for verb_path, cmd, opted_out in _walk_commands(app):
        if opted_out:
            continue
        if not _has_required_argument(cmd.callback):
            continue
        cases.append(verb_path)
    return cases


REQUIRED_ARG_CASES = _public_required_arg_cases()


@pytest.mark.parametrize(
    "verb_path",
    REQUIRED_ARG_CASES,
    ids=lambda path: " ".join(path),
)
def test_public_command_with_required_arg_prints_help_on_no_args(
    verb_path: tuple[str, ...],
) -> None:
    """Each public command with required args prints help on bare invocation."""
    app = create_app()
    runner = CliRunner()
    result = runner.invoke(app, list(verb_path), catch_exceptions=False)

    assert result.exit_code == 0, (
        f"`ai-eng {' '.join(verb_path)}` exited {result.exit_code} (expected 0). "
        f"Output:\n{result.output}"
    )
    assert "Usage:" in result.output, (
        f"`ai-eng {' '.join(verb_path)}` did not print help text. Output:\n{result.output}"
    )
    assert "Missing argument" not in result.output, (
        f"`ai-eng {' '.join(verb_path)}` still raises MissingParameter. Output:\n{result.output}"
    )


def test_brief_problem_commands_are_covered() -> None:
    """Spec brief lists these specific commands as MissingParameter offenders.

    Acts as a tripwire: if any of these is no longer registered, this test
    fails loudly so the maintainer revisits coverage.

    Spec-132 sub-004 collapsed the legacy ``stack``/``ide``/``provider``
    mutator verbs (``add`` / ``remove``) into the interactive
    ``ai-eng config`` flow, so they are no longer part of the required-
    arg surface.

    Spec-133 simplified ``ai-eng verify`` (no MODE — runs all
    specialists) and ``ai-eng spec start`` (positional path, optional)
    so neither has required positional arguments now; both are removed
    from the tripwire.

    The remaining tripwires are commands that still take a required
    positional argument and would otherwise trip Click's
    ``MissingParameter`` UX.
    """
    expected_subset = {
        ("release",),
        ("commit",),
        ("pr",),
        ("gate", "commit-msg"),
        ("risk", "accept"),
        ("risk", "renew"),
        ("risk", "resolve"),
        ("risk", "revoke"),
        ("risk", "show"),
    }
    discovered = set(REQUIRED_ARG_CASES)
    missing = expected_subset - discovered
    assert not missing, (
        f"Brief problem commands not discovered as required-arg cases: {missing}. "
        f"Discovered: {sorted(discovered)}"
    )


def test_opt_out_internal_group_still_strict() -> None:
    """The hidden ``internal`` group keeps strict argument behaviour.

    Internal commands have no human users; they MUST fail loudly when
    invoked incorrectly so test harnesses do not silently get help text.
    """
    app = create_app()
    # The ``internal python`` command takes positional script args via
    # ``allow_extra_args=True``; it does not raise MissingParameter, so the
    # invariant we test is "no help-on-no-args wrapper applied". We do that
    # by inspecting the Typer command's ``cls`` registration.
    internal_group = next(g for g in app.registered_groups if g.name == "internal")
    for cmd in internal_group.typer_instance.registered_commands:
        # The opt-out commands should NOT carry our custom Click command class.
        from ai_engineering.core.cli.decorators import HelpOnNoArgsCommand

        assert not (cmd.cls is not None and issubclass(cmd.cls, HelpOnNoArgsCommand)), (
            f"internal {cmd.name} was wrapped with help-on-no-args; internal commands must opt out"
        )

    # spec-132 sub-004: dev group now registered; assert opt-out parity with internal.
    from ai_engineering.core.cli.decorators import HelpOnNoArgsCommand

    dev_group = next((g for g in app.registered_groups if g.name == "dev"), None)
    assert dev_group is not None, "dev group must exist after spec-132 sub-004"
    for cmd in dev_group.typer_instance.registered_commands:
        assert not (cmd.cls is not None and issubclass(cmd.cls, HelpOnNoArgsCommand)), (
            f"dev {cmd.name} was wrapped with help-on-no-args; dev commands must opt out"
        )


def test_decorator_only_triggers_when_required_args_unset() -> None:
    """Help-on-no-args wrapper is a no-op for commands with only optional args."""
    from ai_engineering.core.cli.decorators import HelpOnNoArgsCommand

    sub_app = typer.Typer()

    def options_only(target: str = typer.Option("default", "--target")) -> None:
        typer.echo(f"ran:{target}")

    sub_app.command(cls=HelpOnNoArgsCommand)(options_only)
    runner = CliRunner()
    result = runner.invoke(sub_app, [], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "ran:default" in result.output, result.output
    assert "Usage:" not in result.output, result.output


def test_decorator_does_not_swallow_help_flag_behaviour() -> None:
    """`--help` still prints help and exits 0 (no behavioural regression)."""
    from ai_engineering.core.cli.decorators import HelpOnNoArgsCommand

    sub_app = typer.Typer()

    def needs_name(name: str = typer.Argument(...)) -> None:
        typer.echo(f"hi {name}")

    sub_app.command(cls=HelpOnNoArgsCommand)(needs_name)
    runner = CliRunner()
    result = runner.invoke(sub_app, ["--help"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_decorator_lets_valid_invocations_through() -> None:
    """Wrapper does not interfere with successful argumented invocations."""
    from ai_engineering.core.cli.decorators import HelpOnNoArgsCommand

    sub_app = typer.Typer()

    def needs_name(name: str = typer.Argument(...)) -> None:
        typer.echo(f"hi {name}")

    sub_app.command(cls=HelpOnNoArgsCommand)(needs_name)
    runner = CliRunner()
    result = runner.invoke(sub_app, ["alice"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "hi alice" in result.output


def test_at_least_one_public_required_arg_case_discovered() -> None:
    """Sanity: discovery must find the brief's offending commands."""
    # Tripwire: if discovery breaks we don't want a vacuously-passing matrix.
    assert REQUIRED_ARG_CASES, (
        "No public commands with required arguments discovered. "
        "Check _has_required_argument and _walk_commands."
    )
    # Sanity-check one offender end-to-end at the Click layer.
    app = create_app()
    runner = CliRunner()
    result = runner.invoke(app, ["verify", "--help"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Usage:" in result.output
    # The matrix above already proves the discovered cases survive Click's
    # parameter-required check (otherwise they would not have printed help on
    # bare invocation). No need to peek through Typer internals here.
