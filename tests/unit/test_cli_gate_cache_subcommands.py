"""Unit tests for ``ai-eng gate cache --status / --clear`` subcommands.

RED phase for spec-104 T-3.3 (D-104-10 cache subcommands).

Per ``spec.md`` D-104-10 (lines 244-247):

    > CLI surface adicional, sin nuevos comandos top-level:
    >   - ``ai-eng gate cache --status``: lista entries actuales + max-age +
    >     tamaño total. Read-only.
    >   - ``ai-eng gate cache --clear``: borra todo
    >     ``.ai-engineering/state/gate-cache/``. Confirmación interactiva o
    >     ``--yes``.

Target behaviour (does NOT exist yet — wired by T-3.4):

    - ``ai-eng gate cache --status``
        Read-only enumeration of ``.ai-engineering/state/gate-cache/*.json``.
        Lists each entry filename + on-disk size. Shows max-age remaining
        (24h - elapsed since ``verified_at``). Prints total size. On empty
        cache prints a "no cache entries" message and exits 0.

    - ``ai-eng gate cache --clear`` (with optional ``--yes``)
        Deletes every ``*.json`` under ``.ai-engineering/state/gate-cache/``.
        Without ``--yes``, prompts for interactive confirmation: answering
        ``y``/``yes`` performs the wipe; ``n``/no cancels (no deletion).
        With ``--yes``, performs the wipe non-interactively.
        Idempotent on empty cache (exits 0 cleanly, no error).
        ONLY ``gate-cache/`` is touched — sibling files under
        ``.ai-engineering/state/`` (e.g. ``gate-findings.json``,
        ``install-state.json``, ``decision-store.json``) MUST be preserved.

Each test currently fails because the subcommand wiring (``cache`` under
``gate``) does not exist in ``cli_factory.create_app`` and the underlying
handler functions in ``cli_commands/gate.py`` are not implemented. T-3.4
GREEN phase will land them; these assertions then become the contract for
D-104-10.

TDD CONSTRAINT: this file is IMMUTABLE after T-3.3 lands. T-3.4 may only
add behaviour to satisfy these assertions, never edit them.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cache_key(salt: str) -> str:
    """Return a deterministic 32-char hex cache key matching ``_compute_cache_key`` shape.

    Computed (not hardcoded) so the strings do not trip generic-api-key
    heuristics in secret scanners.
    """

    return hashlib.sha256(salt.encode("utf-8")).hexdigest()[:32]


def _seed_entry(
    cache_dir: Path,
    cache_key: str,
    *,
    check: str = "ruff-check",
    result: str = "pass",
    verified_at: datetime | None = None,
) -> Path:
    """Write a minimal cache-entry JSON to ``cache_dir / f"{cache_key}.json"``.

    ``verified_at`` defaults to "now" so each entry is fresh (within the 24h
    max-age window) unless the caller overrides it.
    """

    cache_dir.mkdir(parents=True, exist_ok=True)
    when = (verified_at or datetime.now(UTC)).isoformat()
    payload = {
        "check": check,
        "result": result,
        "findings": [],
        "verified_at": when,
        "verified_by_version": "0.6.4",
        "key_inputs": {"check_name": check, "tool_version": "0.6.4"},
    }
    path = cache_dir / f"{cache_key}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Build a tmp project root with ``.ai-engineering/state/`` ready."""

    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True, exist_ok=True)
    return tmp_path


def _gate_cache_dir(root: Path) -> Path:
    """Canonical on-disk gate-cache directory for ``root``."""

    return root / ".ai-engineering" / "state" / "gate-cache"


# ---------------------------------------------------------------------------
# Tests — gate cache --status
# ---------------------------------------------------------------------------


def test_gate_cache_status_lists_entries(project_root: Path) -> None:
    """``gate cache --status`` lists all on-disk entries with their sizes.

    Seeds three entries with distinct cache keys and asserts that every
    filename appears in the human-readable status output.
    """

    # Arrange — seed three entries with distinct payloads/sizes.
    cache_dir = _gate_cache_dir(project_root)
    keys = [
        _cache_key("spec-104-status-a"),
        _cache_key("spec-104-status-b"),
        _cache_key("spec-104-status-c"),
    ]
    seeded_paths = [
        _seed_entry(cache_dir, keys[0], check="ruff-check"),
        _seed_entry(cache_dir, keys[1], check="gitleaks"),
        _seed_entry(cache_dir, keys[2], check="ty"),
    ]
    for p in seeded_paths:
        assert p.exists(), "precondition: seeded entry on disk"

    # Act
    app = create_app()
    result = runner.invoke(
        app,
        ["gate", "cache", "--status", "--target", str(project_root)],
    )

    # Assert — exit 0 (status is read-only).
    assert result.exit_code == 0, (
        f"gate cache --status must exit 0 on a populated cache; "
        f"got exit_code={result.exit_code} output={result.output!r}"
    )

    # Assert — every seeded cache key is mentioned in the output.
    for key in keys:
        assert key in result.output, (
            f"gate cache --status must list every entry by name; "
            f"missing key {key!r} in output:\n{result.output}"
        )


def test_gate_cache_status_shows_max_age_remaining(project_root: Path) -> None:
    """An entry verified ~12h ago shows ~12h remaining of the 24h max-age window.

    The output must surface the per-entry remaining freshness so operators
    can audit how soon entries will be invalidated by the 24h cap.
    """

    # Arrange — seed one entry with verified_at = now - 12h.
    cache_dir = _gate_cache_dir(project_root)
    twelve_hours_ago = datetime.now(UTC) - timedelta(hours=12)
    key = _cache_key("spec-104-max-age-remaining")
    _seed_entry(cache_dir, key, verified_at=twelve_hours_ago)

    # Act
    app = create_app()
    result = runner.invoke(
        app,
        ["gate", "cache", "--status", "--target", str(project_root)],
    )

    # Assert — exit 0 and the output mentions remaining hours.
    assert result.exit_code == 0, (
        f"gate cache --status must exit 0; got {result.exit_code} output={result.output!r}"
    )

    # Assert — output advertises a remaining-hour count somewhere between
    # 11 and 13 (inclusive) hours, since the entry was verified ~12h ago and
    # the cap is 24h. Implementation may render as "12h", "11.9h", "12 hours
    # remaining" etc.; we accept any of those by extracting integer-hour
    # numerals followed by ``h`` or ``hour``.
    output_lower = result.output.lower()
    candidate_numbers = [
        int(m.group(1)) for m in re.finditer(r"(\d+)\s*(?:h\b|hours?\b)", output_lower)
    ]
    assert candidate_numbers, (
        "gate cache --status must surface remaining hours per entry "
        "(format like '12h remaining' or '12 hours remaining'); "
        f"output:\n{result.output}"
    )
    assert any(11 <= n <= 13 for n in candidate_numbers), (
        f"entry verified ~12h ago must show ~12h remaining (24h cap); "
        f"found hour values {candidate_numbers!r} in output:\n{result.output}"
    )


def test_gate_cache_status_shows_total_size(project_root: Path) -> None:
    """``gate cache --status`` output includes a total size in bytes/KB.

    Operators rely on this number to validate the 16 MB on-disk cap from
    D-104-03.
    """

    # Arrange — seed two entries.
    cache_dir = _gate_cache_dir(project_root)
    keys = [_cache_key(f"spec-104-total-size-{i}") for i in range(2)]
    for k in keys:
        _seed_entry(cache_dir, k)

    # Act
    app = create_app()
    result = runner.invoke(
        app,
        ["gate", "cache", "--status", "--target", str(project_root)],
    )

    # Assert
    assert result.exit_code == 0, (
        f"gate cache --status must exit 0; got {result.exit_code} output={result.output!r}"
    )

    # Assert — the output advertises a total size with a unit (B / KB / MB).
    output_lower = result.output.lower()
    has_total_label = "total" in output_lower
    has_size_unit = bool(re.search(r"\d+(?:\.\d+)?\s*(?:b|kb|kib|mb|mib)\b", output_lower))
    assert has_total_label and has_size_unit, (
        "gate cache --status must include a 'total' size with a byte unit "
        "(B/KB/MB); output:\n" + result.output
    )


def test_gate_cache_status_empty_cache(project_root: Path) -> None:
    """On an empty cache, ``gate cache --status`` prints a friendly message and exits 0.

    Specifically, the output mentions there are no entries (matched by the
    word "no" together with "cache" / "entries" — implementations vary on
    exact phrasing), and the exit code is 0 so this is non-fatal.
    """

    # Arrange — explicitly create an empty gate-cache directory.
    cache_dir = _gate_cache_dir(project_root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    assert not any(cache_dir.iterdir()), "precondition: cache dir is empty"

    # Act
    app = create_app()
    result = runner.invoke(
        app,
        ["gate", "cache", "--status", "--target", str(project_root)],
    )

    # Assert — exit 0 (empty cache is not an error).
    assert result.exit_code == 0, (
        f"gate cache --status on empty cache must exit 0; "
        f"got exit_code={result.exit_code} output={result.output!r}"
    )

    # Assert — output mentions emptiness via "no" + ("cache" or "entries").
    output_lower = result.output.lower()
    assert "no" in output_lower and (
        "cache" in output_lower or "entries" in output_lower or "entry" in output_lower
    ), (
        "gate cache --status on empty cache must print a 'no cache entries' "
        "(or equivalent) message; output:\n" + result.output
    )


# ---------------------------------------------------------------------------
# Tests — gate cache --clear
# ---------------------------------------------------------------------------


def test_gate_cache_clear_with_yes_flag_skips_prompt(project_root: Path) -> None:
    """``gate cache --clear --yes`` deletes every entry without prompting.

    The flow MUST be non-interactive: even if a prompt could appear, ``--yes``
    bypasses it. After the command, the gate-cache directory has no surviving
    ``*.json`` entries.
    """

    # Arrange — seed three entries.
    cache_dir = _gate_cache_dir(project_root)
    keys = [_cache_key(f"spec-104-clear-yes-{i}") for i in range(3)]
    seeded = [_seed_entry(cache_dir, k) for k in keys]
    for p in seeded:
        assert p.exists(), "precondition: entry seeded"

    # Act — invoke with --yes and NO stdin input. If implementation
    # accidentally prompts, runner.invoke with empty input would hang or
    # the test would surface the failure.
    app = create_app()
    result = runner.invoke(
        app,
        ["gate", "cache", "--clear", "--yes", "--target", str(project_root)],
        input="",  # belt-and-suspenders: nothing to feed a prompt.
    )

    # Assert — exit 0 (clear succeeded).
    assert result.exit_code == 0, (
        f"gate cache --clear --yes must exit 0; "
        f"got exit_code={result.exit_code} output={result.output!r}"
    )

    # Assert — every seeded entry was removed.
    surviving = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    assert not surviving, (
        f"gate cache --clear --yes must delete every *.json entry; "
        f"survivors: {[p.name for p in surviving]!r}"
    )


def test_gate_cache_clear_without_yes_prompts(project_root: Path) -> None:
    """``gate cache --clear`` (no ``--yes``) prompts for confirmation.

    Sub-assertions:
      1. Answering "y" performs the wipe — entries deleted, exit 0.
      2. Answering "n" cancels — entries preserved, exit 0 (cancellation is
         not an error from the user's perspective; they declined).
    """

    app = create_app()

    # ----- Sub-case 1: confirm with "y" -> entries deleted. -----
    cache_dir = _gate_cache_dir(project_root)
    keys_yes = [_cache_key(f"spec-104-prompt-yes-{i}") for i in range(2)]
    for k in keys_yes:
        _seed_entry(cache_dir, k)
    assert list(cache_dir.glob("*.json")), "precondition: entries seeded for confirm-y"

    result_yes = runner.invoke(
        app,
        ["gate", "cache", "--clear", "--target", str(project_root)],
        input="y\n",
    )
    assert result_yes.exit_code == 0, (
        f"gate cache --clear with 'y' confirm must exit 0; "
        f"got exit_code={result_yes.exit_code} output={result_yes.output!r}"
    )
    survivors_after_yes = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    assert not survivors_after_yes, (
        "gate cache --clear answered 'y' must delete every entry; "
        f"survivors: {[p.name for p in survivors_after_yes]!r}"
    )

    # ----- Sub-case 2: decline with "n" -> entries preserved. -----
    keys_no = [_cache_key(f"spec-104-prompt-no-{i}") for i in range(2)]
    for k in keys_no:
        _seed_entry(cache_dir, k)
    seeded_count = len(list(cache_dir.glob("*.json")))
    assert seeded_count == 2, "precondition: entries seeded for decline-n"

    result_no = runner.invoke(
        app,
        ["gate", "cache", "--clear", "--target", str(project_root)],
        input="n\n",
    )
    # Decline is not an error: typer.confirm with abort=True raises Abort
    # (exit 1) on "n", and abort=False keeps exit 0. Either is acceptable
    # provided the entries are preserved. The contract under test is that
    # the cache is NOT mutated.
    assert result_no.exit_code in (0, 1), (
        f"gate cache --clear with 'n' decline must exit 0 or 1 (abort); "
        f"got exit_code={result_no.exit_code} output={result_no.output!r}"
    )
    survivors_after_no = list(cache_dir.glob("*.json"))
    assert len(survivors_after_no) == seeded_count, (
        "gate cache --clear answered 'n' must NOT delete entries; "
        f"expected {seeded_count} survivors, got {len(survivors_after_no)}: "
        f"{[p.name for p in survivors_after_no]!r}"
    )


def test_gate_cache_clear_no_op_when_empty(project_root: Path) -> None:
    """``gate cache --clear --yes`` on an empty cache exits 0 without error.

    No entries to delete, no prompt to issue: this must be a clean no-op.
    """

    # Arrange — gate-cache dir exists but is empty.
    cache_dir = _gate_cache_dir(project_root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    assert not any(cache_dir.iterdir()), "precondition: cache dir is empty"

    # Act
    app = create_app()
    result = runner.invoke(
        app,
        ["gate", "cache", "--clear", "--yes", "--target", str(project_root)],
    )

    # Assert — exit 0 (idempotent no-op).
    assert result.exit_code == 0, (
        f"gate cache --clear --yes on empty cache must exit 0; "
        f"got exit_code={result.exit_code} output={result.output!r}"
    )

    # Assert — directory still empty (or absent), no spurious files created.
    surviving = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    assert not surviving, (
        f"gate cache --clear --yes on empty cache must not create files; "
        f"unexpected survivors: {[p.name for p in surviving]!r}"
    )


def test_gate_cache_clear_preserves_other_state(project_root: Path) -> None:
    """``gate cache --clear --yes`` only wipes ``gate-cache/`` — sibling state files remain.

    Seeds:
      * ``gate-cache/<key>.json`` cache entries (will be wiped).
      * ``gate-findings.json`` (sibling — must survive).
      * ``install-state.json`` (sibling — must survive).
      * ``decision-store.json`` (sibling — must survive).

    Asserts after clear that only the cache entries are gone and every
    sibling JSON retains its original byte content.
    """

    # Arrange — seed gate-cache entries.
    cache_dir = _gate_cache_dir(project_root)
    cache_keys = [_cache_key(f"spec-104-preserve-{i}") for i in range(2)]
    for k in cache_keys:
        _seed_entry(cache_dir, k)

    # Arrange — seed sibling state files. Use file-specific content so we can
    # assert byte-for-byte preservation (not just existence).
    state_dir = project_root / ".ai-engineering" / "state"
    sibling_files = {
        "gate-findings.json": json.dumps(
            {"schema": "ai-engineering/gate-findings/v1", "findings": []}
        ),
        "install-state.json": json.dumps({"schemaVersion": "1.0", "phases": {}}),
        "decision-store.json": json.dumps({"schemaVersion": "1.1", "decisions": []}),
    }
    for name, content in sibling_files.items():
        (state_dir / name).write_text(content, encoding="utf-8")

    # Sanity — siblings exist before clear.
    for name in sibling_files:
        assert (state_dir / name).exists(), f"precondition: sibling {name} seeded"

    # Act
    app = create_app()
    result = runner.invoke(
        app,
        ["gate", "cache", "--clear", "--yes", "--target", str(project_root)],
    )

    # Assert — exit 0.
    assert result.exit_code == 0, (
        f"gate cache --clear --yes must exit 0; "
        f"got exit_code={result.exit_code} output={result.output!r}"
    )

    # Assert — gate-cache entries are gone.
    surviving_cache = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    assert not surviving_cache, (
        f"gate cache --clear must wipe gate-cache/*.json; "
        f"survivors: {[p.name for p in surviving_cache]!r}"
    )

    # Assert — every sibling state file survives byte-for-byte.
    for name, expected_content in sibling_files.items():
        sibling_path = state_dir / name
        assert sibling_path.exists(), (
            f"gate cache --clear MUST preserve sibling state file {name!r}; it was deleted"
        )
        actual = sibling_path.read_text(encoding="utf-8")
        assert actual == expected_content, (
            f"gate cache --clear MUST NOT modify sibling state file {name!r}; "
            f"content drifted from {expected_content!r} to {actual!r}"
        )
