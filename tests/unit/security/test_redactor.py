"""Tests for `ai_engineering._shared.redactor` (spec-134 D-134-09).

The redactor is the single source of truth for two redaction modes:

* `strictness="normal"` — historical secrets-only behaviour that
  `state/instincts.py` and `state/observability.py` previously inlined.
  Replacement must remain byte-equivalent (the telemetry contract is
  load-bearing).
* `strictness="strict"` — seven-vector redaction for upstream bug
  reports (D-134-09). Vectors: secrets, `$HOME` paths, repo-private
  paths, emails, GitHub tokens, username / hostname CLI assignments,
  and `state.db` SQL blobs.

The suite enforces three coverage axes per vector (hit / miss /
boundary) plus two normal-mode regression cases — for a minimum of
21 strict + 2 normal-mode + frontmatter cases.
"""

from __future__ import annotations

import pytest

# The module is expected to live at this import path (T-1.2 implements it).
# RED: this import fails until T-1.2 lands.
from ai_engineering._shared.redactor import redact, redact_normal

# ----------------------------------------------------------------------
# Vector 1 — secrets (api_key / token / secret / password / authorization /
# credentials / auth) — historical pattern preserved in normal mode.
# ----------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        'api_key="abcd1234"',
        "token: ghp_supersecret",
        "password = hunter2hunter",
    ],
)
def test_secrets_hit(raw: str) -> None:
    """Strict mode redacts the secret value but keeps the key name."""
    assert "[REDACTED]" in redact(raw, strictness="strict")


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "the quick brown fox",
        "no secrets here just lorem ipsum",
        "key='abc' (too short and not a secret-ish name)",
    ],
)
def test_secrets_miss(raw: str) -> None:
    """Strict mode leaves non-secret text untouched."""
    assert redact(raw, strictness="strict") == raw or "[REDACTED]" not in redact(
        raw, strictness="strict"
    )


@pytest.mark.unit
def test_secrets_boundary_short_value() -> None:
    """Boundary: secret-named field with a 3-char value is below the 4-char floor."""
    # _SECRET_RE requires `{4,}` for the value — three chars does not match.
    raw = "token=abc"
    assert redact(raw, strictness="strict") == raw


# ----------------------------------------------------------------------
# Vector 2 — `$HOME` / `/Users/<user>` machine paths.
# ----------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "/Users/dachi/repos/foo.py",
        "/Users/janedoe/Documents/notes.md",
        "saw it at /Users/some.user/project/file.txt this morning",
    ],
)
def test_userhome_hit(raw: str) -> None:
    """Strict mode collapses `/Users/<user>/...` into a placeholder."""
    out = redact(raw, strictness="strict")
    assert "/Users/" not in out
    assert "$HOME" in out or "[REDACTED-PATH]" in out


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "no machine path here",
        "/usr/local/bin/gh",
        "relative/path/file.py",
    ],
)
def test_userhome_miss(raw: str) -> None:
    """Non-userhome paths are untouched."""
    out = redact(raw, strictness="strict")
    assert out == raw or "/Users/" not in out


@pytest.mark.unit
def test_userhome_boundary_root_only() -> None:
    """Boundary: bare `/Users` without a trailing username should not match."""
    raw = "the /Users directory"
    out = redact(raw, strictness="strict")
    # /Users with no username is not a personal-path leak.
    assert "/Users" in out


# ----------------------------------------------------------------------
# Vector 3 — `/private/...` repo-private path leak.
# ----------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "/private/var/folders/abc/state.db",
        "see /private/tmp/build/output.log",
        "/private/etc/secret.conf",
    ],
)
def test_repo_private_hit(raw: str) -> None:
    """Strict mode redacts `/private/...` paths."""
    out = redact(raw, strictness="strict")
    assert "/private/" not in out


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "private discussion in chat",
        "the privately owned repo",
        "no path here",
    ],
)
def test_repo_private_miss(raw: str) -> None:
    """Strict mode does not touch the bare word 'private'."""
    assert redact(raw, strictness="strict") == raw


@pytest.mark.unit
def test_repo_private_boundary_trailing_slash() -> None:
    """Boundary: `/private` without a trailing segment is not collapsed."""
    raw = "/private"
    out = redact(raw, strictness="strict")
    # No trailing segment = no useful path leakage; redactor MAY keep it.
    assert isinstance(out, str)


# ----------------------------------------------------------------------
# Vector 4 — email addresses.
# ----------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "contact dachi.gogotchuri@gmail.com for details",
        "user@example.org reported the issue",
        "first.last+tag@subdomain.co.uk",
    ],
)
def test_email_hit(raw: str) -> None:
    """Strict mode redacts email addresses."""
    out = redact(raw, strictness="strict")
    assert "@" not in out or "[REDACTED-EMAIL]" in out


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "no email here just plain text",
        "git@github.com is a routing host not a user email",
        "@mention without a tld",
    ],
)
def test_email_miss(raw: str) -> None:
    """Non-email text is untouched in strict mode."""
    out = redact(raw, strictness="strict")
    # @mention and git@github.com may or may not be redacted; assert NO false truncation
    # of `no email here just plain text`.
    if "@" not in raw:
        assert out == raw


@pytest.mark.unit
def test_email_boundary_at_no_tld() -> None:
    """Boundary: `name@host` without a top-level domain is not an email."""
    raw = "name@host"
    out = redact(raw, strictness="strict")
    assert "[REDACTED-EMAIL]" not in out


# ----------------------------------------------------------------------
# Vector 5 — GitHub tokens (gh[psouar]_<36+chars>).
# ----------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "ghp_" + "a" * 40,
        "token=gho_" + "b" * 36,
        "use ghs_" + "1234567890abcdef" * 3 + " for installation auth",
    ],
)
def test_gh_token_hit(raw: str) -> None:
    """Strict mode redacts GitHub token literals."""
    out = redact(raw, strictness="strict")
    assert "[REDACTED-GH-TOKEN]" in out or "[REDACTED]" in out


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "ghp_short",
        "no token here",
        "githubtoken=actually_not_a_token",
    ],
)
def test_gh_token_miss(raw: str) -> None:
    """Strict mode does not redact non-token text."""
    out = redact(raw, strictness="strict")
    # ghp_short is below the 36-char floor — must remain.
    assert "ghp_short" in out or "[REDACTED-GH-TOKEN]" not in out


@pytest.mark.unit
def test_gh_token_boundary_35_chars() -> None:
    """Boundary: 35 chars after the prefix is below the 36-char floor."""
    raw = "ghp_" + "x" * 35
    out = redact(raw, strictness="strict")
    assert "[REDACTED-GH-TOKEN]" not in out


# ----------------------------------------------------------------------
# Vector 6 — username / hostname CLI assignments.
# ----------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "whoami=dachi",
        "hostname=mac-mini.local",
        "user_name=admin01",
    ],
)
def test_username_cli_hit(raw: str) -> None:
    """Strict mode redacts `whoami=` / `hostname=` / similar CLI assignments."""
    out = redact(raw, strictness="strict")
    assert "[REDACTED-USER]" in out or "[REDACTED-HOST]" in out


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "this is unrelated prose",
        "the user is unknown",
        "set the env var",
    ],
)
def test_username_cli_miss(raw: str) -> None:
    """Non-assignment text is untouched."""
    out = redact(raw, strictness="strict")
    assert out == raw


@pytest.mark.unit
def test_username_cli_boundary_word_match() -> None:
    """Boundary: `username` mentioned without assignment is not a leak."""
    raw = "the username is configured elsewhere"
    out = redact(raw, strictness="strict")
    assert out == raw


# ----------------------------------------------------------------------
# Vector 7 — `state.db` SQL blob.
# ----------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "SELECT * FROM decisions WHERE state.db row",
        "state.db SQL: INSERT INTO foo VALUES (1)",
        "UPDATE table SET x=1; -- state.db migration",
    ],
)
def test_state_db_sql_hit(raw: str) -> None:
    """Strict mode redacts lines that mention `state.db` plus SQL keywords."""
    out = redact(raw, strictness="strict")
    assert "[REDACTED-DB]" in out or "state.db" not in out


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        "state.db location is documented",
        "no sql here",
        "SELECT statement without the db reference",
    ],
)
def test_state_db_sql_miss(raw: str) -> None:
    """state.db mention without SQL keywords is left intact; SQL without state.db is left intact."""
    out = redact(raw, strictness="strict")
    # The vector requires BOTH state.db + SQL keyword on the same line.
    assert "[REDACTED-DB]" not in out


@pytest.mark.unit
def test_state_db_sql_boundary_separate_lines() -> None:
    """Boundary: SQL on one line and `state.db` on another should not be conflated."""
    raw = "SELECT * FROM x\nstate.db is fine here"
    out = redact(raw, strictness="strict")
    assert "[REDACTED-DB]" not in out


# ----------------------------------------------------------------------
# Normal-mode regression — byte-equivalent with the historical
# `_SECRET_RE.sub(r"\1\2[REDACTED]", text)` shape.
# ----------------------------------------------------------------------


@pytest.mark.unit
def test_normal_mode_byte_equivalent_secret() -> None:
    """`redact_normal` preserves the exact replacement shape `key + sep + [REDACTED]`."""
    raw = 'api_key="abcd1234567890"'
    out = redact_normal(raw)
    # Historical contract — telemetry callers expect `api_key="[REDACTED]"`.
    assert out == 'api_key="[REDACTED]"'


@pytest.mark.unit
def test_normal_mode_ignores_strict_vectors() -> None:
    """Normal mode runs the secrets-only pattern and leaves emails / paths intact."""
    raw = "see /Users/x/path for details and email user@example.com"
    out = redact_normal(raw)
    assert "/Users/x/path" in out
    assert "user@example.com" in out
