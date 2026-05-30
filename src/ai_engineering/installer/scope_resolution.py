"""Detection-first scope resolution for scope-aware ``ai-eng`` commands (spec-156).

Every scope-affecting command auto-detects which install scopes are present
(global ``~/.ai-engineering/`` and/or local ``./.ai-engineering/``) and resolves
the one to act on BEFORE doing work (D-156-01). The ``--global``/``--local``
flags are an explicit override only (D-156-02), and the resolved scope is
announced on one human line (D-156-03).

Resolution rules:

- only global present  -> ``global``
- only local present   -> ``local``
- both present         -> ``local`` (local-wins) + announce global also exists
- neither present      -> ``None`` (``install`` runs its wizard; other commands
  fail loud "not installed")
- explicit flag         -> that scope, always (escape hatch for CI / ambiguity)

Detection is marker-presence only (``install-state.json``), mirroring
``doctor.runtime.scope_status``. When the working directory IS the home
directory the two markers are the same file, so it collapses to ``global`` to
avoid double-counting (D-156-17).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_engineering.installer.scope import GLOBAL, LOCAL

_MARKER_REL = Path(".ai-engineering") / "state" / "install-state.json"


def _marker(root: Path) -> bool:
    """Return True when an install marker exists under *root*."""
    return (root / _MARKER_REL).is_file()


def detect_scopes(target: Path) -> set[str]:
    """Return the install scopes present under *target* and the home directory.

    When ``target`` resolves to the home directory the repo and home markers are
    the same file; that case reports ``{"global"}`` only (D-156-17).
    """
    scopes: set[str] = set()
    same_as_home = target.resolve() == Path.home().resolve()
    if _marker(Path.home()):
        scopes.add(GLOBAL)
    if _marker(target) and not same_as_home:
        scopes.add(LOCAL)
    return scopes


@dataclass(frozen=True)
class ResolvedScope:
    """The scope a command should act on, plus the human announce line.

    ``scope`` is ``None`` only when neither install is present (greenfield).
    ``both`` records that both installs exist (the local-wins announcement
    case). ``announce`` is empty when there is nothing to say (greenfield).
    """

    scope: str | None
    both: bool
    announce: str


def resolve_scope(target: Path, explicit: str | None = None) -> ResolvedScope:
    """Resolve the scope to act on for *target* (D-156-01/02).

    *explicit* is the ``--global``/``--local`` override; when set it always
    wins. Otherwise scope is inferred from marker presence, local-wins on both.
    """
    present = detect_scopes(target)
    both = present == {LOCAL, GLOBAL}

    if explicit in (LOCAL, GLOBAL):
        return ResolvedScope(explicit, both, _announce(explicit, both))
    if both:
        return ResolvedScope(LOCAL, True, _announce(LOCAL, True))
    if present == {GLOBAL}:
        return ResolvedScope(GLOBAL, False, _announce(GLOBAL, False))
    if present == {LOCAL}:
        return ResolvedScope(LOCAL, False, _announce(LOCAL, False))
    return ResolvedScope(None, False, "")


def _announce(scope: str, both: bool) -> str:
    """Build the one-line scope announcement (D-156-03)."""
    if scope == GLOBAL:
        return "◈ ai-engineering · acting on global install (~/)"
    if both:
        return (
            "◈ ai-engineering · acting on local install (./) · "
            "global also present — use --global to target it"
        )
    return "◈ ai-engineering · acting on local install (./)"
