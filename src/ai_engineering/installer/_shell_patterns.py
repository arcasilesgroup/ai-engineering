"""Compound-shell exfiltration regex blocklist.

Per spec D-101-02 Hardening 3, the user-scope guard (``_safe_run`` in
``user_scope_install``) inspects the FULL argv whenever ``argv[0]`` resolves
to an allowlisted shell or interpreter driver (``bash``/``sh``/``zsh``/
``fish``/``pwsh``). The patterns published here are the single source of
truth for compound-shell rejection so the runtime guard and any future
static-analysis lint share the same regex set.

Each pattern targets ONE exfiltration class with conservative wording:

* ``r"\\|\\s*(bash|sh|zsh|fish)\\b"`` — pipe-to-shell sink (``curl X | bash``,
  ``base64 -d <<< xxx | sh``).
* ``r"\\bnc\\s+-[A-Za-z]*e[A-Za-z]*\\b"`` — netcat invoked with the ``-e``
  flag (reverse-shell primitive).
* ``r">\\s*&?\\s*/dev/tcp/"`` — bash-internal TCP redirect
  (``bash -i >& /dev/tcp/...``).
* ``r"\\beval\\s*\\$\\("`` — ``eval $(...)`` command-substitution sink.
* ``r"\\bbase64\\s+-d\\b"`` — base64 decode (almost always paired with a
  shell sink in attack chains).
* ``r"<\\s*<\\("`` — process substitution (``< <(curl ...)``).
* ``r"(?i)\\biwr\\b[^|]*\\|\\s*\\biex\\b"`` — PowerShell
  ``Invoke-WebRequest`` piped into ``Invoke-Expression``.
* ``r"(?i)\\binvoke-expression\\b"`` — explicit PowerShell ``iex`` alias.

The patterns are intentionally narrow: they do not match ``bash -c "echo
ok"``, ``python -c "print('hi')"``, ``bash -c "ls -la"``, or ``sh -c "test
-f file.txt"``. Adding new patterns MUST preserve that property — a guard
that silently rejects benign argv would block legitimate installer flows.

This module ONLY publishes the blocklist; integration into ``_safe_run``
is owned by spec-101 task T-1.6.
"""

from __future__ import annotations

import re

__all__ = ("BLOCK_PATTERNS", "matches_any_block_pattern")


# Frozen tuple so consumers cannot mutate the source of truth in place.
BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Pipe-to-shell: ``curl X | bash``, ``wget -O- X | bash``, ``... | sh``.
    re.compile(r"\|\s*(bash|sh|zsh|fish)\b"),
    # Netcat with -e flag (reverse-shell primitive).
    #
    # Wave 23 broaden: the original ``\bnc\s+-[A-Za-z]*e[A-Za-z]*\b`` only
    # matched when ``-e`` was the *first* flag after ``nc`` -- real-world
    # exploit invocations interleave other flags AND positional args first
    # (``nc -nlvp 4444 -e /bin/sh``, ``nc -lvp 4444 -e bash``,
    # ``nc -nv -e /bin/sh``). The relaxed pattern walks any number of
    # whitespace-separated tokens between ``nc`` and a short-flag bundle
    # containing ``e`` (e.g. ``-e``, ``-ne``, ``-Ee``) OR the long flag
    # ``--exec``. The trailing word boundary plus the explicit ``-{1,2}``
    # alternation keep ``nc --version`` / ``nc --verbose`` /
    # ``nc -h``-style benign argv from matching: ``--version`` lacks the
    # ``[A-Za-z]*e[A-Za-z]*`` short-flag shape because it has too many
    # post-prefix characters that don't form a valid short-flag bundle.
    re.compile(r"\bnc\s+(?:\S+\s+)*-(?:[A-Za-z]*e[A-Za-z]*|-exec)\b"),
    # Bash-internal TCP redirect: ``>& /dev/tcp/host/port``.
    re.compile(r">\s*&?\s*/dev/tcp/"),
    # Eval-on-network-fetch: ``eval $(curl ...)``.
    re.compile(r"\beval\s*\$\("),
    # base64 decode (paired with a shell sink in known exfiltration chains).
    re.compile(r"\bbase64\s+-d\b"),
    # Process substitution: ``< <(curl evil.sh)``.
    re.compile(r"<\s*<\("),
    # PowerShell: ``iwr ... | iex`` (Invoke-WebRequest piped to Invoke-Expression).
    re.compile(r"(?i)\biwr\b[^|]*\|\s*\biex\b"),
    # PowerShell: explicit Invoke-Expression alias call.
    re.compile(r"(?i)\binvoke-expression\b"),
)


def matches_any_block_pattern(text: str) -> tuple[re.Pattern[str], str] | None:
    """Return the first matching pattern + matched substring, or ``None``.

    Used by ``_safe_run`` to surface a precise diagnostic when a compound
    shell chain is rejected. Returning the matched substring (rather than
    just a boolean) lets the caller include the offending fragment in the
    ``UserScopeViolation`` message without echoing the entire argv.

    Args:
        text: The string to scan (typically ``" ".join(argv[1:])``).

    Returns:
        ``(pattern, matched_substring)`` for the first hit, or ``None``
        when no pattern matches.
    """
    for pattern in BLOCK_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            return pattern, match.group(0)
    return None
