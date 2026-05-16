"""Strict and normal-mode text redaction (spec-134 D-134-09).

Two modes:

* ``redact_normal(text)`` — historical secrets-only behaviour preserved
  byte-equivalent (the replacement shape ``r"\\1\\2[REDACTED]"`` is
  load-bearing for telemetry callers in
  :mod:`ai_engineering.state.instincts` and
  :mod:`ai_engineering.state.observability`).
* ``redact(text, strictness="strict")`` — full seven-vector redaction
  for upstream bug reports (`/ai-engineering-issue`). Vectors:

    1. Secrets — `api_key|token|secret|password|authorization|...`
       assignments with values ≥4 chars.
    2. User-home paths — ``/Users/<name>/...`` collapsed to ``$HOME/...``.
    3. Repo-private paths — ``/private/<segment>/...`` redacted.
    4. Email addresses (RFC 5322 simplified — local@host.tld).
    5. GitHub tokens — ``gh[psouar]_`` + ≥36 base62 chars.
    6. Username / hostname CLI assignments — ``whoami=``, ``hostname=``,
       ``user_name=``.
    7. ``state.db`` SQL blobs — lines containing both ``state.db`` and a
       SQL keyword (``SELECT``, ``INSERT``, ``UPDATE``, ``DELETE``).

This module is **pure stdlib**: it must not import from
``ai_engineering.*`` to keep the package self-contained and importable
from any surface (including hook scripts that ship with the framework
template).
"""

from __future__ import annotations

import re
from typing import Literal

# ---------------------------------------------------------------------------
# Vector 1 — secrets (historical pattern, preserved byte-equivalent).
# ---------------------------------------------------------------------------

_SECRET_RE = re.compile(
    r"(?i)(api_key|token|secret|password|authorization|credentials|auth)"
    r"([\"'\s:=]+)"
    r"[^\s\"',;]{4,}",
)

# ---------------------------------------------------------------------------
# Vector 2 — `/Users/<user>/...` user-home paths.
# Match the literal `/Users/` prefix followed by at least one
# non-whitespace character (the username segment). `\b` would not work
# because forward slash is not a word boundary; instead we anchor on the
# trailing slash that separates user from sub-path.
# ---------------------------------------------------------------------------

_USERHOME_RE = re.compile(r"/Users/[^/\s]+(?=/|\s|$)")

# ---------------------------------------------------------------------------
# Vector 3 — `/private/<segment>/...` repo-private paths. Requires a
# trailing path segment so bare `/private` doesn't trigger.
# ---------------------------------------------------------------------------

_REPO_PRIVATE_RE = re.compile(r"/private/[^\s]+")

# ---------------------------------------------------------------------------
# Vector 4 — email addresses. Simplified RFC 5322:
# local-part ([A-Za-z0-9._%+-]+) @ host with TLD ≥ 2 chars.
# Excludes `git@github.com` style routing hosts because the TLD is
# required (`.com` matches) — we accept this is a false positive and
# strict mode redacts it anyway.
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,253}\.[A-Za-z]{2,63}")

# ---------------------------------------------------------------------------
# Vector 5 — GitHub tokens. `gh[psouar]_` prefix + 36-255 base62 chars.
# Per GitHub: prefixes `ghp_` (personal), `gho_` (oauth), `ghu_` (user),
# `ghs_` (server-to-server), `ghr_` (refresh).
# ---------------------------------------------------------------------------

_GH_TOKEN_RE = re.compile(r"\bgh[psouar]_[A-Za-z0-9_]{36,255}\b")

# ---------------------------------------------------------------------------
# Vector 6 — username / hostname CLI assignments.
# Match `key=value` where key is one of `whoami`, `hostname`, `user`,
# `user_name`, `username`, and value is at least 1 non-whitespace char.
# Anchor on the assignment operator so bare prose ("the username") does
# not match.
# ---------------------------------------------------------------------------

_USERNAME_CLI_RE = re.compile(
    r"\b(whoami|hostname|user|user_name|username)\s*=\s*(\S+)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Vector 7 — `state.db` SQL blob. Match a line containing both `state.db`
# (case-insensitive) AND a SQL keyword (`SELECT|INSERT|UPDATE|DELETE`).
# Implemented as a per-line scan so multi-line input with SQL on one
# line and state.db on another does NOT trigger.
# ---------------------------------------------------------------------------

_SQL_KEYWORDS_RE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
_STATE_DB_RE = re.compile(r"state\.db", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def redact_normal(text: str) -> str:
    """Apply the historical secrets-only redaction.

    Byte-equivalent with the legacy ``_SECRET_RE.sub(r"\\1\\2[REDACTED]", text)``
    pattern used by :mod:`ai_engineering.state.instincts` and
    :mod:`ai_engineering.state.observability`. Telemetry callers must
    see identical replacement output to preserve their wire contracts.

    Args:
        text: Source text. May be empty; ``""`` is returned unchanged.

    Returns:
        Text with secret values replaced by ``[REDACTED]``. The matched
        key + separator are preserved so downstream callers retain
        structural context.
    """
    if not text:
        return text
    return _SECRET_RE.sub(r"\1\2[REDACTED]", text)


def redact(
    text: str,
    *,
    strictness: Literal["normal", "strict"] = "strict",
) -> str:
    """Redact sensitive content.

    Strict mode runs all 7 vectors; normal mode runs only the historical
    secrets pattern (delegates to :func:`redact_normal`).

    Args:
        text: Source text. ``""`` returns ``""`` unchanged.
        strictness: ``"normal"`` for telemetry (secrets only) or
            ``"strict"`` for upstream bug reports (all 7 vectors).
            Defaults to ``"strict"`` because the dominant new caller is
            ``/ai-engineering-issue``.

    Returns:
        Redacted text. The shape of redaction tokens varies by vector:

        * secrets — ``key + sep + [REDACTED]`` (preserves structure).
        * user-home paths — ``$HOME``.
        * repo-private paths — ``[REDACTED-PATH]``.
        * emails — ``[REDACTED-EMAIL]``.
        * GitHub tokens — ``[REDACTED-GH-TOKEN]``.
        * username / hostname CLI — ``key=[REDACTED-USER]`` or
          ``key=[REDACTED-HOST]``.
        * state.db SQL — ``[REDACTED-DB]``.
    """
    if not text:
        return text

    if strictness == "normal":
        return redact_normal(text)

    # Strict mode applies all 7 vectors. Order matters: redact tokens
    # before emails so `ghp_xxx@host.tld` is caught by the token pattern
    # first (avoids a partial email replacement that leaves the token
    # half-redacted).
    out = text
    out = _GH_TOKEN_RE.sub("[REDACTED-GH-TOKEN]", out)
    out = _SECRET_RE.sub(r"\1\2[REDACTED]", out)
    out = _USERHOME_RE.sub("$HOME", out)
    out = _REPO_PRIVATE_RE.sub("[REDACTED-PATH]", out)
    out = _EMAIL_RE.sub("[REDACTED-EMAIL]", out)
    out = _redact_username_cli(out)
    out = _redact_state_db_sql(out)
    return out


def _redact_username_cli(text: str) -> str:
    """Apply vector 6 — keep the key, redact the value with a typed token."""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        token = "[REDACTED-HOST]" if key.lower() == "hostname" else "[REDACTED-USER]"
        return f"{key}={token}"

    return _USERNAME_CLI_RE.sub(_replace, text)


def _redact_state_db_sql(text: str) -> str:
    """Apply vector 7 — replace lines containing BOTH state.db AND SQL."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    for line in lines:
        if _STATE_DB_RE.search(line) and _SQL_KEYWORDS_RE.search(line):
            # Preserve the trailing newline so the joined output keeps
            # the original line count.
            trailing = "\n" if line.endswith("\n") else ""
            out.append("[REDACTED-DB]" + trailing)
        else:
            out.append(line)
    return "".join(out)


__all__ = ["redact", "redact_normal"]
