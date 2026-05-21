"""Ownership map CLI commands.

Imports ``.github/CODEOWNERS`` (or an operator-provided override path)
into the canonical ``ownership-map.json`` (spec-148 P3 files-only;
originally spec-138 M3.T5 against ``state.db.ownership_map``).

CODEOWNERS grammar (per `GitHub docs <https://docs.github.com/en/
repositories/managing-your-repositorys-settings-and-features/
customizing-your-repository/about-code-owners>`_): one rule per line,
``<path-pattern>  @owner1 [@owner2 ...]``. Blank lines and lines
beginning with ``#`` are ignored. Patterns are space-separated tokens;
escaped spaces (``\\ ``) are not supported by this importer.

Idempotent: re-running on the same ``CODEOWNERS`` file produces the
same row set (UPSERT clause keeps the latest ``updated_at``).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_ui import error, header, info, status_line, success
from ai_engineering.paths import find_project_root
from ai_engineering.state.models import (
    FrameworkUpdatePolicy,
    OwnershipEntry,
    OwnershipLevel,
    OwnershipMap,
)
from ai_engineering.state.observability import emit_control_outcome
from ai_engineering.state.repository import DurableStateRepository

__all__ = [
    "ownership_import",
    "parse_codeowners",
]

# Owner tokens always start with ``@`` and may carry an org/team form
# (``@org/team``) or a single user (``@user``). Email-form owners are
# also valid CODEOWNERS entries (RFC 5322); we accept anything that
# matches the GitHub grammar.
_OWNER_TOKEN_RE = re.compile(r"^(?:@[\w\-./]+|[^\s@]+@[\w\-.]+)$")


def _ownership_level(value: str | None) -> OwnershipLevel:
    """Coerce a CODEOWNERS owner token into a valid ``OwnershipLevel``.

    Non-enum owners (``@team`` / email forms) are conservatively treated
    as team-managed, preserving the prior state.db import semantics.
    """
    try:
        return OwnershipLevel(value or "")
    except ValueError:
        return OwnershipLevel.TEAM_MANAGED


def _framework_update_policy(value: str | None) -> FrameworkUpdatePolicy:
    """Coerce a row severity into a valid ``FrameworkUpdatePolicy``.

    Absent severity → ``DENY`` so update never overwrites operator-owned
    paths by surprise, preserving the prior state.db import semantics.
    """
    try:
        return FrameworkUpdatePolicy(value or "")
    except ValueError:
        return FrameworkUpdatePolicy.DENY


def parse_codeowners(content: str) -> list[dict[str, object | None]]:
    """Parse the textual contents of a CODEOWNERS file.

    Args:
        content: Full file contents as a string. Trailing newlines are
            tolerated; CRLF line endings are normalised.

    Returns:
        List of row dicts with keys ``path_pattern`` (str) and
        ``owners`` (list[str]). Empty list when the file has no rules.
    """
    rows: list[dict[str, object | None]] = []
    for raw_line in content.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Split on whitespace; first token is the path pattern, the
        # rest are owner tokens. CODEOWNERS allows trailing comments
        # but not inline ones (per GitHub docs), so we keep the parse
        # strict.
        tokens = line.split()
        if len(tokens) < 2:
            continue
        path_pattern = tokens[0]
        owners = [tok for tok in tokens[1:] if _OWNER_TOKEN_RE.match(tok)]
        if not owners:
            continue
        rows.append(
            {
                "path_pattern": path_pattern,
                "owners": owners,
                "severity": None,
                "reviewers": [],
            }
        )
    return rows


def ownership_import(
    source: Annotated[
        str | None,
        typer.Option(
            "--source",
            help="Path to CODEOWNERS (default: .github/CODEOWNERS in repo root).",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="List parsed rules without writing."),
    ] = False,
) -> None:
    """Import CODEOWNERS into ``state.db.ownership_map``.

    Spec-138 M3.T5. Reads ``.github/CODEOWNERS`` (or ``--source``),
    parses every ``<pattern> @owner...`` rule, and UPSERTs into the
    canonical ``ownership_map`` table. Idempotent.

    Exits 0 on success even when CODEOWNERS is missing (the table just
    stays at its previous state). Prints a one-line summary on success.
    """
    root = find_project_root()
    if source:
        codeowners_path = Path(source)
        if not codeowners_path.is_absolute():
            codeowners_path = root / codeowners_path
    else:
        codeowners_path = root / ".github" / "CODEOWNERS"

    if not codeowners_path.is_file():
        info(f"No CODEOWNERS file at {codeowners_path}; nothing to import.")
        return

    try:
        content = codeowners_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        error(f"Failed to read {codeowners_path}: {exc}")
        raise typer.Exit(code=1) from None

    rows = parse_codeowners(content)
    if not rows:
        info(f"{codeowners_path} contains no parseable ownership rules.")
        return

    header(f"Ownership rules ({len(rows)} total)")
    for row in rows:
        pattern = str(row.get("path_pattern") or "?")
        owners = row.get("owners") or []
        owners_str = ", ".join(str(o) for o in owners) if isinstance(owners, list) else str(owners)
        pattern_short = pattern[:60] + ("…" if len(pattern) > 60 else "")
        status_line("ok", pattern_short, owners_str)

    if dry_run:
        info("Dry run: no rows written.")
        return

    # spec-148 P3 (files-only): collapse CODEOWNERS rows into the
    # OwnershipEntry model (the only shape consumers read) and merge by
    # pattern into the canonical ownership-map.json via the durable repo.
    # Start from the persisted file when present; an absent file is an
    # empty base (the framework defaults are the installer's job, not the
    # importer's — load_ownership() would otherwise synthesise them).
    repo = DurableStateRepository(root)
    store = repo.load_ownership() if repo.ownership_map_path.exists() else OwnershipMap()
    by_pattern: dict[str, OwnershipEntry] = {entry.pattern: entry for entry in store.paths}
    attempted = 0
    for row in rows:
        pattern = row.get("path_pattern")
        if not isinstance(pattern, str) or not pattern:
            continue
        owners = row.get("owners")
        first_owner = (
            owners[0]
            if isinstance(owners, list) and owners and isinstance(owners[0], str)
            else None
        )
        severity = row.get("severity")
        by_pattern[pattern] = OwnershipEntry.model_validate(
            {
                "pattern": pattern,
                "owner": _ownership_level(first_owner),
                "framework_update": _framework_update_policy(
                    severity if isinstance(severity, str) else None
                ),
            }
        )
        attempted += 1
    store.paths = list(by_pattern.values())
    repo.save_ownership(store)

    emit_control_outcome(
        root,
        category="governance",
        control="ownership-import",
        component="ownership-map",
        outcome="success",
        source="cli",
        metadata={
            "count": attempted,
            "source": str(codeowners_path),
            "store_path": str(repo.ownership_map_path),
        },
    )

    success(f"Imported {attempted} ownership rules -> ownership-map.json.")
