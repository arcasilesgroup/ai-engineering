"""RED tests for feed preflight validation in spec-102."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.doctor.models import DoctorContext
from ai_engineering.doctor.runtime import feeds


def _ctx(target: Path) -> DoctorContext:
    return DoctorContext(target=target)


def test_detect_feeds_from_lockfile_extracts_private_registry(tmp_path: Path) -> None:
    lock_path = tmp_path / "uv.lock"
    lock_path.write_text(
        "\n".join(
            [
                "[[package]]",
                'name = "click"',
                (
                    "source = { registry = "
                    '"https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/" }'
                ),
            ]
        ),
        encoding="utf-8",
    )

    detected = feeds.detect_feeds_from_lockfile(lock_path)

    assert detected == {"https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/"}


def test_validate_feeds_for_install_blocks_when_private_feed_is_unreachable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo"
version = "0.1.0"

[[tool.uv.index]]
name = "corporate"
url = "https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/"
default = true
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text(
        'source = { registry = "https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/" }',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        feeds,
        "_probe_feed",
        lambda feed_url: feeds.FeedProbeResult(reachable=False),
        raising=False,
    )

    result = feeds.validate_feeds_for_install(_ctx(tmp_path), mode="install")

    assert result.status == "blocked"
    assert result.feeds == ["https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/"]
    assert "install" in result.message.lower()


def test_probe_feed_returns_false_for_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        feeds,
        "_http_probe",
        lambda *_args, **_kwargs: feeds._HttpProbeResponse(status=401),
        raising=False,
    )

    result = feeds._probe_feed("https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/")

    assert result.reachable is False
    assert result.auth_required is True


def test_probe_feed_retries_with_get_when_head_is_not_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _fake_probe(_url: str, *, method: str, timeout: float) -> feeds._HttpProbeResponse:
        calls.append(method)
        assert timeout == 5
        return feeds._HttpProbeResponse(status=405 if method == "HEAD" else 204)

    monkeypatch.setattr(feeds, "_http_probe", _fake_probe, raising=False)

    result = feeds._probe_feed("https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/")

    assert calls == ["HEAD", "GET"]
    assert result.reachable is True
    assert result.auth_required is False


class _FakeSocket:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)
        self.sent = bytearray()

    def __enter__(self) -> _FakeSocket:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def recv(self, _size: int) -> bytes:
        if self._chunks:
            return self._chunks.pop(0)
        return b""


def test_http_probe_rejects_embedded_credentials() -> None:
    with pytest.raises(OSError, match="must not embed credentials"):
        feeds._http_probe(
            "https://user:pass@pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/",
            method="HEAD",
            timeout=5,
        )


def test_read_http_status_parses_status_line() -> None:
    sock = _FakeSocket([b"HTTP/1.1 204 No Content\r\nX-Test: 1\r\n\r\n"])

    response = feeds._read_http_status(sock, b"HEAD / HTTP/1.1\r\n\r\n")

    assert response.status == 204
    assert sock.sent.startswith(b"HEAD / HTTP/1.1")


def test_read_http_status_rejects_malformed_status_line() -> None:
    sock = _FakeSocket([b"BROKEN\r\n\r\n"])

    with pytest.raises(OSError, match="Malformed HTTP status line"):
        feeds._read_http_status(sock, b"HEAD / HTTP/1.1\r\n\r\n")


def test_validate_feeds_for_install_allows_auth_gated_private_feed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo"
version = "0.1.0"

[[tool.uv.index]]
name = "corporate"
url = "https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/"
default = true
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        feeds,
        "_probe_feed",
        lambda feed_url: feeds.FeedProbeResult(reachable=False, auth_required=True),
        raising=False,
    )

    result = feeds.validate_feeds_for_install(_ctx(tmp_path), mode="install")

    assert result.status == "ok"
    assert "require package-manager credentials" in result.message
