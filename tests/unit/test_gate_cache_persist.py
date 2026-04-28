"""Unit tests for ``ai_engineering.policy.gate_cache`` atomic persistence.

RED phase for spec-104 T-1.1 (D-104-03 robustness invariants):

    > Robustez: write atómico via `tempfile + os.rename`; lectura corrupta →
    > log warn, treat as miss, regenera.

Target functions (do not exist yet — created in T-1.2):

    - ``_atomic_write(path: Path, data: dict) -> None``
        Atomically write ``data`` (JSON-serialisable) to ``path``. Implementation
        must write to a sibling ``*.tmp`` file in the same directory and then
        publish via ``os.replace`` (NOT ``os.rename``) for cross-platform
        atomicity per phase-0-notes.md Risk-C. Parent directories are created
        ``parents=True, exist_ok=True``.

    - ``_read_safe(path: Path) -> dict | None``
        Return parsed JSON dict on success. Return ``None`` (no exception) when
        the file is missing, empty (zero bytes), partially-written/truncated,
        or otherwise unparseable JSON. A warning is logged on corruption.

Each test currently fails with ``ImportError`` because neither function is
implemented yet. T-1.2 GREEN phase will implement both and these tests become
the contract for D-104-03 robustness.

TDD CONSTRAINT: this file is IMMUTABLE after T-1.1 lands.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Tests — _atomic_write
# ---------------------------------------------------------------------------


def test_atomic_write_creates_file(tmp_path: Path) -> None:
    """Writing via ``_atomic_write`` produces a file with the exact JSON content."""
    # Arrange
    from ai_engineering.policy.gate_cache import _atomic_write

    target = tmp_path / "cache-entry.json"
    payload = {"check": "ruff-check", "result": "pass", "verified_at": "2026-04-26T00:00:00Z"}

    # Act
    _atomic_write(target, payload)

    # Assert
    assert target.exists(), "atomic write must produce the target file"
    on_disk = json.loads(target.read_text(encoding="utf-8"))
    assert on_disk == payload, "round-trip JSON must equal the input payload"


def test_atomic_write_overwrites_existing(tmp_path: Path) -> None:
    """A second ``_atomic_write`` call replaces the first file's content."""
    # Arrange
    from ai_engineering.policy.gate_cache import _atomic_write

    target = tmp_path / "cache-entry.json"
    first = {"version": 1, "result": "pass"}
    second = {"version": 2, "result": "fail"}

    # Act
    _atomic_write(target, first)
    _atomic_write(target, second)

    # Assert
    on_disk = json.loads(target.read_text(encoding="utf-8"))
    assert on_disk == second, "second write must overwrite the first"
    assert on_disk != first


def test_atomic_write_uses_tempfile(tmp_path: Path) -> None:
    """A sibling ``*.tmp`` file is created in the same directory before publish.

    We patch ``os.replace`` to capture the source path and assert that:
      * The source path is a sibling of the target (same parent dir — required
        for atomicity, see phase-0-notes.md Risk-C).
      * The source filename ends with ``.tmp`` (or starts with ``.`` for hidden
        tempfiles) — i.e., a temp file was actually created, not the target
        directly.
    """
    # Arrange
    from ai_engineering.policy import gate_cache
    from ai_engineering.policy.gate_cache import _atomic_write

    target = tmp_path / "entry.json"
    payload = {"k": "v"}

    captured: dict[str, Path] = {}
    real_replace = gate_cache.os.replace if hasattr(gate_cache, "os") else None

    import os as _os

    def fake_replace(src: str | Path, dst: str | Path) -> None:
        captured["src"] = Path(src)
        captured["dst"] = Path(dst)
        # Honour the real semantics so subsequent reads still work.
        _os.replace(src, dst)

    # Patch wherever gate_cache references os.replace.
    with mock.patch("ai_engineering.policy.gate_cache.os.replace", side_effect=fake_replace):
        # Act
        _atomic_write(target, payload)

    # Assert — replace was called with a sibling tempfile.
    assert "src" in captured, "_atomic_write must call os.replace exactly once"
    assert captured["dst"] == target, "destination must be the requested target"
    assert captured["src"].parent == target.parent, (
        "tempfile MUST be a sibling of the target (same directory) for atomicity; "
        f"got src parent {captured['src'].parent}, target parent {target.parent}"
    )
    src_name = captured["src"].name
    assert src_name != target.name, "tempfile name must differ from the final filename"
    assert src_name.endswith(".tmp") or src_name.startswith("."), (
        f"tempfile must be marked as a tempfile (suffix .tmp or hidden dotfile); got {src_name!r}"
    )

    # Real_replace consumption guard (silences unused-var lint; does not assert).
    _ = real_replace


def test_atomic_write_atomic_under_concurrent_writes(tmp_path: Path) -> None:
    """Concurrent ``_atomic_write`` calls produce a valid file (no corruption).

    Last-writer-wins is the contract; we don't care which writer's payload
    survives, only that the resulting file parses to one of the inputs and
    is not a half-written hybrid.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import _atomic_write

    target = tmp_path / "concurrent.json"
    writers = 8
    payloads = [{"writer": i, "value": "x" * (64 * (i + 1))} for i in range(writers)]
    barrier = threading.Barrier(writers)
    errors: list[BaseException] = []

    def worker(payload: dict[str, object]) -> None:
        try:
            barrier.wait(timeout=10)
            _atomic_write(target, payload)
        except BaseException as exc:  # pragma: no cover — captured in assertion
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(p,)) for p in payloads]

    # Act
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # Assert — no thread crashed.
    assert not errors, f"concurrent writers raised: {errors!r}"
    assert target.exists(), "target must exist after concurrent writes"

    # Assert — the surviving file parses cleanly to exactly one of the payloads.
    on_disk = json.loads(target.read_text(encoding="utf-8"))
    assert on_disk in payloads, (
        "Concurrent write produced a corrupted/half-written file. "
        f"Got {on_disk!r}, expected one of the input payloads."
    )


def test_atomic_write_creates_parent_dir(tmp_path: Path) -> None:
    """Parent directory is created ``parents=True, exist_ok=True``."""
    # Arrange
    from ai_engineering.policy.gate_cache import _atomic_write

    nested_target = tmp_path / "a" / "b" / "c" / "entry.json"
    payload = {"nested": True}

    assert not nested_target.parent.exists(), "precondition: parent dir does not yet exist"

    # Act
    _atomic_write(nested_target, payload)

    # Assert
    assert nested_target.exists(), "atomic write must create the file"
    assert nested_target.parent.is_dir(), "parents must be created with parents=True"
    assert json.loads(nested_target.read_text(encoding="utf-8")) == payload


def test_atomic_write_uses_os_replace_for_windows_compat(tmp_path: Path) -> None:
    """Implementation MUST call ``os.replace`` (not ``os.rename``).

    Per phase-0-notes.md Risk-C: ``os.rename`` raises ``FileExistsError`` on
    Windows when the destination exists; ``os.replace`` is atomic on both POSIX
    and Windows. We assert by patching both and verifying which one is invoked.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import _atomic_write

    target = tmp_path / "win-compat.json"
    payload = {"compat": "windows"}

    import os as _os

    real_replace = _os.replace
    replace_calls: list[tuple[Path, Path]] = []
    rename_calls: list[tuple[Path, Path]] = []

    def tracking_replace(src: str | Path, dst: str | Path) -> None:
        replace_calls.append((Path(src), Path(dst)))
        real_replace(src, dst)

    def tracking_rename(src: str | Path, dst: str | Path) -> None:
        rename_calls.append((Path(src), Path(dst)))
        # Do NOT actually call os.rename — we want to fail fast if the
        # implementation reaches for it.
        raise AssertionError(
            f"_atomic_write must use os.replace, not os.rename (src={src!r}, dst={dst!r})"
        )

    # Act
    with (
        mock.patch("ai_engineering.policy.gate_cache.os.replace", side_effect=tracking_replace),
        mock.patch("ai_engineering.policy.gate_cache.os.rename", side_effect=tracking_rename),
    ):
        _atomic_write(target, payload)

    # Assert
    assert len(replace_calls) == 1, (
        f"os.replace must be called exactly once; got {len(replace_calls)}"
    )
    assert not rename_calls, (
        "os.rename must NEVER be called — Windows atomicity requires os.replace"
    )


def test_atomic_write_unicode_safe(tmp_path: Path) -> None:
    """Non-ASCII content (emoji, accented chars, CJK) round-trips cleanly."""
    # Arrange
    from ai_engineering.policy.gate_cache import _atomic_write

    target = tmp_path / "unicode.json"
    payload = {
        "message": "Café — naïve coöperation 🚀 ❤️ ✅",
        "rule_id": "S5852",
        "details": {"path": "src/módulo/файл.py", "annotation": "東京"},
    }

    # Act
    _atomic_write(target, payload)

    # Assert — bytes were written as UTF-8 and parse back identical.
    raw = target.read_bytes()
    assert raw, "file must be non-empty"
    decoded = json.loads(raw.decode("utf-8"))
    assert decoded == payload, "unicode payload must round-trip byte-for-byte"


# ---------------------------------------------------------------------------
# Tests — _read_safe
# ---------------------------------------------------------------------------


def test_read_safe_returns_none_when_file_missing(tmp_path: Path) -> None:
    """Reading a non-existent file returns ``None`` — no exception leaks."""
    # Arrange
    from ai_engineering.policy.gate_cache import _read_safe

    missing = tmp_path / "does-not-exist.json"
    assert not missing.exists(), "precondition: file does not exist"

    # Act
    result = _read_safe(missing)

    # Assert
    assert result is None, f"missing file must yield None; got {result!r}"


def test_read_safe_returns_none_when_corrupted(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Invalid JSON returns ``None`` (no exception) and a warning is logged."""
    # Arrange
    from ai_engineering.policy.gate_cache import _read_safe

    corrupted = tmp_path / "bad.json"
    corrupted.write_text("{this is not valid json,,,", encoding="utf-8")

    # Act
    with caplog.at_level(logging.WARNING, logger="ai_engineering.policy.gate_cache"):
        result = _read_safe(corrupted)

    # Assert — no exception leaked, returns None.
    assert result is None, f"corrupted JSON must yield None; got {result!r}"

    # Assert — a warning was logged about the corruption.
    warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warning_records, (
        "corrupted read must emit a WARNING-level log record so operators see drift"
    )
    combined = " ".join(r.getMessage() for r in warning_records).lower()
    assert any(token in combined for token in ("corrupt", "invalid", "decode", "parse")), (
        "warning message must reference corruption/invalid/decode/parse; "
        f"got {[r.getMessage() for r in warning_records]!r}"
    )


def test_read_safe_returns_dict_when_valid(tmp_path: Path) -> None:
    """Valid JSON dict on disk is returned verbatim."""
    # Arrange
    from ai_engineering.policy.gate_cache import _read_safe

    target = tmp_path / "good.json"
    payload = {
        "result": "pass",
        "findings": [],
        "verified_at": "2026-04-26T12:34:56Z",
        "key_inputs": {"tool_version": "0.6.4"},
    }
    target.write_text(json.dumps(payload), encoding="utf-8")

    # Act
    result = _read_safe(target)

    # Assert
    assert result == payload, f"valid JSON must round-trip; got {result!r}"
    assert isinstance(result, dict), "return type must be dict for valid input"


def test_read_safe_returns_none_when_empty_file(tmp_path: Path) -> None:
    """A zero-byte file is treated as a cache miss (returns ``None``)."""
    # Arrange
    from ai_engineering.policy.gate_cache import _read_safe

    empty = tmp_path / "empty.json"
    empty.touch()
    assert empty.exists()
    assert empty.stat().st_size == 0, "precondition: file is zero bytes"

    # Act
    result = _read_safe(empty)

    # Assert
    assert result is None, f"empty file must yield None (cache miss); got {result!r}"


def test_read_safe_handles_truncated_file(tmp_path: Path) -> None:
    """Partially-written JSON (truncated mid-write) returns ``None``, no exception.

    Simulates a process killed mid-write before ``os.replace`` published the
    final file. The on-disk content is a prefix of valid JSON but not parseable.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import _read_safe

    truncated = tmp_path / "truncated.json"
    # A plausible prefix: opening brace + key + start of value, no close.
    truncated.write_text('{"result": "pass", "findings": [{"check":', encoding="utf-8")

    # Act / Assert — no exception leaks.
    try:
        result = _read_safe(truncated)
    except Exception as exc:  # pragma: no cover — failure path
        pytest.fail(
            f"_read_safe must NOT raise on truncated input — caller treats as miss. "
            f"Got: {type(exc).__name__}: {exc}"
        )

    # Assert — returns None per the corruption-detection contract.
    assert result is None, f"truncated JSON must yield None; got {result!r}"
