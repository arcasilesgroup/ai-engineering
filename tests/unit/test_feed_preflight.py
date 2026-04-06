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
    from urllib.error import HTTPError

    def _raise_http_error(*args: object, **kwargs: object) -> object:
        raise HTTPError(
            url="https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(feeds, "urlopen", _raise_http_error, raising=False)

    result = feeds._probe_feed("https://pkgs.dev.azure.com/acme/_packaging/core/pypi/simple/")

    assert result.reachable is False
    assert result.auth_required is True


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
