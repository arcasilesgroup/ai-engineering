"""The installed-version rule, spec 033 / B-033-4.

A finding that contradicts the installed bytes is mismatch; a matching claim passes; an
unresolvable package is unverified — never a guess from memory (graph-engineering's
installed-version rule: the installed source is the truth).
"""

from __future__ import annotations

from importlib import metadata


def verify_against_installed(package: str, claim: str) -> str:
    """Verify `claim` against the installed distribution of `package`.

    Returns "match", "mismatch" or "unverified". A package that cannot be resolved on this
    machine is unverified, not a guess — a finding that trusted a version nobody can check
    is exactly the noise the rule exists to drop.
    """
    try:
        installed = metadata.version(package)
    except metadata.PackageNotFoundError:
        return "unverified"
    if installed == claim:
        return "match"
    return "mismatch"