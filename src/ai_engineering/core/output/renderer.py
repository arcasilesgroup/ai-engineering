"""Single source of truth for command output (spec-132 D-132-12).

Wraps the legacy four output modules (``cli_envelope``, ``cli_ui``,
``cli_progress``, ``cli_output``) behind one stable contract. After
spec-132 sub-004, every command under ``cli_commands/`` reaches output
exclusively through this module; direct legacy imports are banned by
the conformance gate ``test_renderer_banned_imports``.

Three modes:

* ``human`` (default) — Rich-coloured narrative on stderr.
* ``json`` — accumulate state in-memory and emit ONE envelope on
  ``ok()`` / ``error()``; stderr is silent.
* ``quiet`` — suppress narrative; only ``ok`` / ``error`` produce output.

The closed Verb taxonomy (``Installing`` / ``Updating`` / ``Removing`` /
``Moving`` / ``Creating`` / ``Verifying`` / ``Skipping`` / ``Restoring``)
is enforced both at type-check time via ``Literal`` and at runtime via
``typing.get_args`` so callers that bypass type checking still surface
errors loud and early.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from typing import (
    Any,
    Literal,
    NamedTuple,
    NoReturn,
    get_args,
)

from ai_engineering import cli_envelope, cli_progress, cli_ui

# Strip Rich markup tags (``[bold]x[/bold]`` -> ``x``) for plain-text fallback.
_MARKUP_RE = re.compile(r"\[/?[^\]]*\]")

Verb = Literal[
    "Installing",
    "Updating",
    "Removing",
    "Moving",
    "Creating",
    "Verifying",
    "Skipping",
    "Restoring",
]
"""Closed Verb taxonomy for ``action()``. Other verbs raise ``TypeError``."""

ChangeKind = Literal["created", "updated", "removed", "moved", "skipped", "restored"]
"""Closed change-kind taxonomy for ``record()`` / ``diff_summary()``."""


class NextAction(NamedTuple):
    """A suggested follow-up command for narrative + JSON consumption."""

    label: str
    command: str


def _emit_styled(markup: str) -> None:
    """Write Rich-markup line to stderr; fall back to plain text if Rich fails.

    Mirrors ``cli_ui``'s Rich-fallback contract without reaching for its
    private helper. Tests rely on ``capsys`` capturing the resulting bytes
    on ``sys.stderr``; the Rich console writes to ``sys.stderr`` after the
    autouse cache-clear fixture in the renderer test suite.
    """
    try:
        cli_ui.get_console().print(markup)
    except (ImportError, ModuleNotFoundError):
        plain = _MARKUP_RE.sub("", markup)
        sys.stderr.write(plain + "\n")
        sys.stderr.flush()


# Map each Verb to its semantic Rich theme key. Lookup is total over Verb.
_VERB_STYLE: dict[str, str] = {
    "Installing": "info",
    "Updating": "info",
    "Removing": "error",
    "Moving": "warning",
    "Creating": "success",
    "Verifying": "brand",
    "Skipping": "muted",
    "Restoring": "warning",
}


class _NoopTracker:
    """Drop-in replacement for ``cli_progress.StepTracker`` in json/quiet modes.

    The ``description`` argument is intentionally accepted and discarded so
    callers can use the same call shape regardless of mode.
    """

    def step(self, description: str) -> None:
        del description  # silent contract in non-human modes

    def substep(self, description: str) -> None:
        del description  # silent contract in non-human modes


class Renderer:
    """Command-scoped output coordinator.

    One ``Renderer`` instance per command invocation. The ``command`` argument
    is the canonical CLI verb (``install`` / ``update`` / ``check`` / ...)
    and is used as the JSON envelope's ``command`` field.

    Mode selection (mutually exclusive in practice; JSON wins on collision):
        - ``json=True``  -> emit one envelope on ``ok()``/``error()``; stderr silent.
        - ``quiet=True`` -> suppress narrative; ``ok``/``error`` write minimal line.
        - neither       -> default human Rich narrative on stderr.
    """

    def __init__(
        self,
        command: str,
        *,
        json: bool = False,
        quiet: bool = False,
    ) -> None:
        self.command = command
        self._json = bool(json)
        # JSON mode is structured; it implicitly silences quiet output too.
        self._quiet = bool(quiet) and not self._json
        self._changes: list[dict[str, Any]] = []
        self._next_actions: list[NextAction] = []
        self._fields: dict[str, str] = {}

    # ---------- mode accessors ----------------------------------------

    @property
    def is_human(self) -> bool:
        return not self._json and not self._quiet

    @property
    def is_json(self) -> bool:
        return self._json

    @property
    def is_quiet(self) -> bool:
        return self._quiet

    # ---------- alternate construction --------------------------------

    @classmethod
    def from_app(cls, command: str) -> Renderer:
        """Build a Renderer reading the global ``cli_output.is_json_mode()`` flag.

        Quiet mode has no global flag today; commands wire it explicitly when
        needed.
        """
        from ai_engineering.cli_output import is_json_mode

        return cls(command, json=is_json_mode())

    # ---------- narrative API -----------------------------------------

    def header(self, title: str | None = None) -> None:
        """Print the command header. Suppressed in json/quiet modes."""
        if not self.is_human:
            return
        cli_ui.header(title or self.command)

    def step(self, description: str) -> None:
        """Print a single narrative step. Suppressed in json/quiet modes."""
        if not self.is_human:
            return
        cli_ui.info(description)

    def action(
        self,
        verb: Verb,
        object_: str,
        detail: str | None = None,
    ) -> None:
        """Print a verb/object/detail line. Verb taxonomy enforced at runtime."""
        if verb not in get_args(Verb):
            allowed = ", ".join(get_args(Verb))
            raise TypeError(f"verb {verb!r} is not in the closed Verb taxonomy: {allowed}")
        if not self.is_human:
            return
        style = _VERB_STYLE[verb]
        suffix = f" [muted]{detail}[/muted]" if detail else ""
        _emit_styled(f"  [{style}]{verb}[/{style}] [path]{object_}[/path]{suffix}")

    @contextmanager
    def progress(
        self,
        total: int,
        desc: str,
    ) -> Generator[cli_progress.StepTracker | _NoopTracker, None, None]:
        """Multi-step progress spinner.

        In ``json``/``quiet`` modes yields a no-op tracker so callers don't
        have to branch on output mode.
        """
        if not self.is_human:
            yield _NoopTracker()
            return
        with cli_progress.step_progress(total, desc) as tracker:
            yield tracker

    # ---------- structured records ------------------------------------

    def record(
        self,
        kind: ChangeKind,
        path: str,
        *,
        from_: str | None = None,
    ) -> None:
        """Record a single change.

        - Human: emits an inline status line.
        - JSON: accumulates in the envelope (emitted on ``ok()``/``error()``).
        - Quiet: no-op (the bottom-line ``ok``/``error`` carries the summary).
        """
        if kind not in get_args(ChangeKind):
            allowed = ", ".join(get_args(ChangeKind))
            raise TypeError(f"kind {kind!r} is not in the ChangeKind taxonomy: {allowed}")
        # Always accumulate so ok() in json mode has the full picture.
        self._changes.append({"kind": kind, "path": path, "from": from_})
        if self.is_human:
            label = kind.upper()
            arrow = f" [muted](from {from_})[/muted]" if from_ else ""
            _emit_styled(f"  [key]{label}[/key] [path]{path}[/path]{arrow}")

    def check_result(
        self,
        name: str,
        passed: bool,
        *,
        detail: str | None = None,
        skipped: bool = False,
        warn: bool = False,
    ) -> None:
        """Record a pass/fail/skip/warn outcome for a named check or workflow step.

        Distinct from :meth:`record` (which is for ``ChangeKind`` file events).
        Use this for: integrity-check categories, commit/PR workflow steps,
        verify specialists, doctor probes.

        States: ``passed=True`` -> PASS (green); ``passed=False`` -> FAIL (red);
        ``warn=True`` overrides to WARN (yellow); ``skipped=True`` -> SKIP (muted).
        """
        self._changes.append(
            {
                "kind": "check",
                "name": name,
                "passed": passed and not warn,
                "skipped": skipped,
                "warn": warn,
                "detail": detail,
            }
        )
        if not self.is_human:
            return
        if skipped:
            marker = "[muted]○ SKIP[/muted]"
        elif warn:
            marker = "[warning]⚠ WARN[/warning]"
        elif passed:
            marker = "[success]✓ PASS[/success]"
        else:
            marker = "[error]✗ FAIL[/error]"
        suffix = f" [muted]({detail})[/muted]" if detail else ""
        _emit_styled(f"  {marker} [key]{name}[/key]{suffix}")

    def kv(self, key: str, value: object) -> None:
        """Print a key/value pair (e.g. ``VCS         github``).

        - Human: aligned key/value line via ``cli_ui.kv``.
        - JSON: accumulates into a ``fields`` map on the envelope.
        - Quiet: no-op.
        """
        rendered = str(value)
        self._fields[key] = rendered
        if self.is_human:
            cli_ui.kv(key, rendered)

    def section(self, title: str) -> None:
        """Print a section header (mid-output divider). Human-only."""
        if not self.is_human:
            return
        _emit_styled(f"\n  [bold]{title}[/bold]")

    def diff_summary(
        self,
        created: Iterable[str] = (),
        updated: Iterable[str] = (),
        removed: Iterable[str] = (),
        moved: Iterable[str] = (),
        skipped: Iterable[str] = (),
        restored: Iterable[str] = (),
    ) -> None:
        """Render an accumulated diff tree.

        - Human: prints a labelled tree of file changes.
        - JSON: no-op (records already accumulated via ``record()`` or here).
        - Quiet: single-line count summary.
        """
        buckets: dict[str, list[str]] = {
            "created": list(created),
            "updated": list(updated),
            "removed": list(removed),
            "moved": list(moved),
            "skipped": list(skipped),
            "restored": list(restored),
        }
        # Mirror into accumulated changes so JSON ok() carries them too.
        for kind_str, paths in buckets.items():
            for path in paths:
                self._changes.append({"kind": kind_str, "path": path, "from": None})

        if self.is_json:
            return
        if self.is_quiet:
            counts = ", ".join(
                f"{kind_str}={len(paths)}" for kind_str, paths in buckets.items() if paths
            )
            if counts:
                sys.stderr.write(f"{counts}\n")
                sys.stderr.flush()
            return
        # Human: simple labelled list per bucket.
        for kind_str, paths in buckets.items():
            if not paths:
                continue
            _emit_styled(f"  [key]{kind_str}[/key]")
            for path in paths:
                _emit_styled(f"    [path]{path}[/path]")

    # ---------- next actions ------------------------------------------

    def next(self, actions: list[NextAction]) -> None:
        """Print or accumulate the next-step block."""
        # Always accumulate for json ok()/error() to consume.
        self._next_actions.extend(actions)
        if not self.is_human:
            return
        cli_ui.suggest_next([(action.command, action.label) for action in actions])

    # ---------- terminal emissions ------------------------------------

    def ok(
        self,
        summary: str,
        *,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Emit the success bottom-line.

        - Human: green success message.
        - JSON: assembles + emits exactly one ``SuccessEnvelope``.
        - Quiet: minimal stderr success line.
        """
        if self.is_json:
            payload: dict[str, Any] = dict(result or {})
            payload.setdefault("summary", summary)
            if self._changes:
                payload.setdefault("changes", list(self._changes))
            if self._fields:
                payload.setdefault("fields", dict(self._fields))
            envelope_next = [
                cli_envelope.NextAction(command=action.command, description=action.label)
                for action in self._next_actions
            ]
            cli_envelope.emit_success(self.command, payload, envelope_next)
            return None
        if self.is_quiet:
            sys.stderr.write(f"{summary}\n")
            sys.stderr.flush()
            return None
        cli_ui.success(summary)
        return None

    def error(
        self,
        msg: str,
        *,
        code: str = "ERROR",
        fix: str | None = None,
        next_actions: list[NextAction] | None = None,
    ) -> NoReturn:
        """Emit the failure bottom-line and exit nonzero.

        - Human: red error + fix hint + arrow block; ``SystemExit(1)``.
        - JSON: ``ErrorEnvelope`` to stdout; ``SystemExit(1)``.
        - Quiet: red error line to stderr; ``SystemExit(1)``.
        """
        actions: list[NextAction] = list(self._next_actions)
        if next_actions:
            actions.extend(next_actions)
        if self.is_json:
            envelope_next = [
                cli_envelope.NextAction(command=action.command, description=action.label)
                for action in actions
            ]
            cli_envelope.emit_error(
                self.command,
                msg,
                code,
                fix or "",
                envelope_next,
            )
            sys.exit(1)
        if self.is_quiet:
            sys.stderr.write(f"{msg}\n")
            sys.stderr.flush()
            sys.exit(1)
        cli_ui.error(msg)
        if fix:
            cli_ui.warning(f"fix: {fix}")
        if actions:
            cli_ui.suggest_next([(action.command, action.label) for action in actions])
        sys.exit(1)

    # ---------- introspection (for tests / debugging) -----------------

    def accumulated_changes(self) -> list[dict[str, Any]]:
        """Snapshot of accumulated ``record()`` entries (defensive copy)."""
        return list(self._changes)

    def accumulated_next_actions(self) -> list[NextAction]:
        """Snapshot of accumulated next-action entries (defensive copy)."""
        return list(self._next_actions)
