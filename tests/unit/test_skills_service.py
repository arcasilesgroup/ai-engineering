"""Unit tests for remote skills lock/cache services."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.skills import service
from ai_engineering.state.defaults import sources_lock_default
from ai_engineering.state.io import write_json


def test_sync_sources_updates_checksum_and_cache(temp_repo: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    (temp_repo / ".git").mkdir()
    state_root = temp_repo / ".ai-engineering" / "state"
    state_root.mkdir(parents=True)
    write_json(state_root / "sources.lock.json", sources_lock_default())
    cache_root = temp_repo / ".ai-engineering" / ".cache" / "skills"
    cache_root.mkdir(parents=True)

    monkeypatch.setattr(service, "repo_root", lambda: temp_repo)
    monkeypatch.setattr(service, "_fetch_url", lambda _url: b"skill-content")

    result = service.sync_sources(offline=False)

    assert result["summary"]["synced"] >= 1
    assert any(item["status"] == "synced" for item in result["results"])


def test_sync_sources_offline_uses_cache(temp_repo: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    (temp_repo / ".git").mkdir()
    state_root = temp_repo / ".ai-engineering" / "state"
    state_root.mkdir(parents=True)
    write_json(state_root / "sources.lock.json", sources_lock_default())
    monkeypatch.setattr(service, "repo_root", lambda: temp_repo)

    # First sync online to seed cache.
    monkeypatch.setattr(service, "_fetch_url", lambda _url: b"seed")
    service.sync_sources(offline=False)

    # Then force offline mode.
    result = service.sync_sources(offline=True)

    assert result["offline"] is True
    assert result["summary"]["offlineCache"] >= 1


def test_sync_sources_rejects_non_allowlisted_url(temp_repo: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    (temp_repo / ".git").mkdir()
    state_root = temp_repo / ".ai-engineering" / "state"
    state_root.mkdir(parents=True)
    lock = sources_lock_default()
    lock["sources"][0]["url"] = "https://evil.example/skills"
    write_json(state_root / "sources.lock.json", lock)
    monkeypatch.setattr(service, "repo_root", lambda: temp_repo)

    result = service.sync_sources(offline=False)

    assert result["summary"]["failed"] >= 1
    assert any(item["status"] == "allowlist-rejected" for item in result["results"])


def test_sync_sources_detects_checksum_mismatch(temp_repo: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    (temp_repo / ".git").mkdir()
    state_root = temp_repo / ".ai-engineering" / "state"
    state_root.mkdir(parents=True)
    lock = sources_lock_default()
    lock["sources"][0]["checksum"] = "sha256:deadbeef"
    write_json(state_root / "sources.lock.json", lock)
    monkeypatch.setattr(service, "repo_root", lambda: temp_repo)
    monkeypatch.setattr(service, "_fetch_url", lambda _url: b"different-content")

    result = service.sync_sources(offline=False)

    assert result["summary"]["failed"] >= 1
    assert any(item["status"] == "checksum-mismatch" for item in result["results"])
