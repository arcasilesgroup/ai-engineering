"""Tests for socket-based HTTP helpers in feeds module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.doctor.runtime.feeds import (
    FeedProbeResult,
    _http_probe,
    _HttpProbeResponse,
    _probe_feed,
    _read_http_status,
)

# -- _read_http_status --------------------------------------------------------


class TestReadHttpStatus:
    def test_parses_200_ok(self) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [
            b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n",
            b"",
        ]
        req = b"HEAD / HTTP/1.1\r\nHost: h\r\n\r\n"
        result = _read_http_status(sock, req)
        assert result == _HttpProbeResponse(status=200)
        sock.sendall.assert_called_once_with(req)

    def test_parses_401_unauthorized(self) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [
            b"HTTP/1.1 401 Unauthorized\r\n\r\n",
            b"",
        ]
        result = _read_http_status(sock, b"HEAD / HTTP/1.1\r\n\r\n")
        assert result.status == 401

    def test_parses_405_method_not_allowed(self) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [
            b"HTTP/1.1 405 Method Not Allowed\r\n\r\n",
            b"",
        ]
        result = _read_http_status(sock, b"HEAD / HTTP/1.1\r\n\r\n")
        assert result.status == 405

    def test_raises_on_malformed_status_line(self) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [b"GARBAGE\r\n\r\n", b""]
        with pytest.raises(OSError, match="Malformed"):
            _read_http_status(sock, b"HEAD / HTTP/1.1\r\n\r\n")

    def test_raises_on_non_numeric_status(self) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [b"HTTP/1.1 ABC OK\r\n\r\n", b""]
        with pytest.raises(OSError, match="Malformed"):
            _read_http_status(sock, b"HEAD / HTTP/1.1\r\n\r\n")

    def test_handles_chunked_recv(self) -> None:
        """Headers arrive in multiple recv calls."""
        sock = MagicMock()
        sock.recv.side_effect = [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Type: text/plain\r\n\r\n",
            b"",
        ]
        result = _read_http_status(sock, b"HEAD / HTTP/1.1\r\n\r\n")
        assert result.status == 200

    def test_handles_empty_recv(self) -> None:
        """Connection closed before full headers received."""
        sock = MagicMock()
        sock.recv.side_effect = [b"HTTP/1.1 200 OK\r\n\r\n", b""]
        result = _read_http_status(sock, b"HEAD / HTTP/1.1\r\n\r\n")
        assert result.status == 200


# -- _http_probe validation ---------------------------------------------------


class TestHttpProbeValidation:
    def test_rejects_ftp_scheme(self) -> None:
        with pytest.raises(OSError, match="Unsupported"):
            _http_probe("ftp://example.com", method="HEAD", timeout=5)

    def test_rejects_file_scheme(self) -> None:
        with pytest.raises(OSError, match="Unsupported"):
            _http_probe("file:///etc/passwd", method="HEAD", timeout=5)

    def test_rejects_missing_hostname(self) -> None:
        with pytest.raises(OSError, match="missing hostname"):
            _http_probe("https://", method="HEAD", timeout=5)

    def test_rejects_embedded_username(self) -> None:
        with pytest.raises(OSError, match="must not embed credentials"):
            _http_probe("https://user@example.com/path", method="HEAD", timeout=5)

    def test_rejects_embedded_credentials(self) -> None:
        with pytest.raises(OSError, match="must not embed credentials"):
            _http_probe("https://user:pass@example.com/path", method="HEAD", timeout=5)

    @patch("ai_engineering.doctor.runtime.feeds.socket.create_connection")
    def test_uses_port_443_for_https(self, mock_conn: MagicMock) -> None:
        sock = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=sock)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        tls_sock = MagicMock()
        tls_sock.recv.side_effect = [b"HTTP/1.1 200 OK\r\n\r\n", b""]

        with patch("ai_engineering.doctor.runtime.feeds.ssl.create_default_context") as mock_ctx:
            mock_ctx.return_value.wrap_socket.return_value.__enter__ = MagicMock(
                return_value=tls_sock
            )
            mock_ctx.return_value.wrap_socket.return_value.__exit__ = MagicMock(return_value=False)
            result = _http_probe("https://example.com/feed", method="HEAD", timeout=5)

        mock_conn.assert_called_once_with(("example.com", 443), timeout=5)
        assert result.status == 200

    @patch("ai_engineering.doctor.runtime.feeds.socket.create_connection")
    def test_uses_port_80_for_http(self, mock_conn: MagicMock) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [b"HTTP/1.1 200 OK\r\n\r\n", b""]
        mock_conn.return_value.__enter__ = MagicMock(return_value=sock)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        result = _http_probe("http://example.com/feed", method="HEAD", timeout=5)

        mock_conn.assert_called_once_with(("example.com", 80), timeout=5)
        assert result.status == 200

    @patch("ai_engineering.doctor.runtime.feeds.socket.create_connection")
    def test_includes_query_in_path(self, mock_conn: MagicMock) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [b"HTTP/1.1 200 OK\r\n\r\n", b""]
        mock_conn.return_value.__enter__ = MagicMock(return_value=sock)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        _http_probe("http://example.com/api?q=1", method="GET", timeout=5)

        sent = sock.sendall.call_args[0][0]
        assert b"GET /api?q=1 HTTP/1.1" in sent


# -- _probe_feed integration --------------------------------------------------


class TestProbeFeed:
    @patch("ai_engineering.doctor.runtime.feeds._http_probe")
    def test_returns_reachable_for_200(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _HttpProbeResponse(status=200)
        result = _probe_feed("https://example.com/feed")
        assert result == FeedProbeResult(reachable=True)

    @patch("ai_engineering.doctor.runtime.feeds._http_probe")
    def test_returns_auth_required_for_401(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _HttpProbeResponse(status=401)
        result = _probe_feed("https://example.com/feed")
        assert result == FeedProbeResult(reachable=False, auth_required=True)

    @patch("ai_engineering.doctor.runtime.feeds._http_probe")
    def test_returns_auth_required_for_403(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _HttpProbeResponse(status=403)
        result = _probe_feed("https://example.com/feed")
        assert result == FeedProbeResult(reachable=False, auth_required=True)

    @patch("ai_engineering.doctor.runtime.feeds._http_probe")
    def test_retries_with_get_on_405(self, mock_probe: MagicMock) -> None:
        mock_probe.side_effect = [
            _HttpProbeResponse(status=405),
            _HttpProbeResponse(status=200),
        ]
        result = _probe_feed("https://example.com/feed")
        assert result == FeedProbeResult(reachable=True)
        assert mock_probe.call_count == 2

    @patch("ai_engineering.doctor.runtime.feeds._http_probe")
    def test_returns_unreachable_on_os_error(self, mock_probe: MagicMock) -> None:
        mock_probe.side_effect = OSError("connection refused")
        result = _probe_feed("https://example.com/feed")
        assert result == FeedProbeResult(reachable=False)

    @patch("ai_engineering.doctor.runtime.feeds._http_probe")
    def test_returns_not_reachable_for_500(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _HttpProbeResponse(status=500)
        result = _probe_feed("https://example.com/feed")
        assert result == FeedProbeResult(reachable=False)
