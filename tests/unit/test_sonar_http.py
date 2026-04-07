"""Tests for socket-based HTTP helpers in sonar policy module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.policy.checks.sonar import (
    _build_sonar_url,
    _read_http_response,
    _sonar_api_get,
)

# -- _read_http_response ------------------------------------------------------


class TestReadHttpResponse:
    def test_parses_200_with_json_body(self) -> None:
        sock = MagicMock()
        body = b'{"status": "OK"}'
        raw = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + body
        sock.recv.side_effect = [raw, b""]
        status, returned_body = _read_http_response(sock, b"GET / HTTP/1.1\r\n\r\n")
        assert status == 200
        assert returned_body == body

    def test_parses_401(self) -> None:
        sock = MagicMock()
        raw = b"HTTP/1.1 401 Unauthorized\r\n\r\n"
        sock.recv.side_effect = [raw, b""]
        status, body = _read_http_response(sock, b"GET / HTTP/1.1\r\n\r\n")
        assert status == 401
        assert body == b""

    def test_parses_500(self) -> None:
        sock = MagicMock()
        raw = b"HTTP/1.1 500 Internal Server Error\r\n\r\nerror detail"
        sock.recv.side_effect = [raw, b""]
        status, body = _read_http_response(sock, b"GET / HTTP/1.1\r\n\r\n")
        assert status == 500
        assert body == b"error detail"

    def test_raises_on_malformed_status_line(self) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [b"GARBAGE\r\n\r\n", b""]
        with pytest.raises(ValueError, match="Malformed"):
            _read_http_response(sock, b"GET / HTTP/1.1\r\n\r\n")

    def test_raises_on_non_numeric_status(self) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [b"HTTP/1.1 XYZ Bad\r\n\r\n", b""]
        with pytest.raises(ValueError, match="Malformed"):
            _read_http_response(sock, b"GET / HTTP/1.1\r\n\r\n")

    def test_handles_chunked_recv(self) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Length: 2\r\n\r\n",
            b"OK",
            b"",
        ]
        status, _body = _read_http_response(sock, b"GET / HTTP/1.1\r\n\r\n")
        assert status == 200

    def test_sends_request_bytes(self) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [b"HTTP/1.1 200 OK\r\n\r\n", b""]
        req = b"GET /api HTTP/1.1\r\nHost: h\r\n\r\n"
        _read_http_response(sock, req)
        sock.sendall.assert_called_once_with(req)


# -- _sonar_api_get -----------------------------------------------------------


class TestSonarApiGet:
    def test_returns_none_for_missing_hostname(self) -> None:
        assert _sonar_api_get("https://", "tok") is None

    def test_returns_none_for_embedded_credentials(self) -> None:
        assert _sonar_api_get("https://user:pass@host.com/api", "tok") is None

    def test_returns_none_for_embedded_username(self) -> None:
        assert _sonar_api_get("https://user@host.com/api", "tok") is None

    @patch("ai_engineering.policy.checks.sonar.socket.create_connection")
    @patch("ai_engineering.policy.checks.sonar.ssl.create_default_context")
    def test_returns_parsed_json_on_200(self, mock_ssl: MagicMock, mock_conn: MagicMock) -> None:
        body = b'{"projectStatus":{"status":"OK"}}'
        raw = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + body

        tls_sock = MagicMock()
        tls_sock.recv.side_effect = [raw, b""]

        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_ssl.return_value.wrap_socket.return_value.__enter__ = MagicMock(return_value=tls_sock)
        mock_ssl.return_value.wrap_socket.return_value.__exit__ = MagicMock(return_value=False)

        result = _sonar_api_get("https://sonarcloud.io/api/check?k=x", "mytoken")

        assert result == {"projectStatus": {"status": "OK"}}

    @patch("ai_engineering.policy.checks.sonar.socket.create_connection")
    @patch("ai_engineering.policy.checks.sonar.ssl.create_default_context")
    def test_returns_none_on_non_200(self, mock_ssl: MagicMock, mock_conn: MagicMock) -> None:
        raw = b"HTTP/1.1 403 Forbidden\r\n\r\n"

        tls_sock = MagicMock()
        tls_sock.recv.side_effect = [raw, b""]

        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_ssl.return_value.wrap_socket.return_value.__enter__ = MagicMock(return_value=tls_sock)
        mock_ssl.return_value.wrap_socket.return_value.__exit__ = MagicMock(return_value=False)

        result = _sonar_api_get("https://sonarcloud.io/api/check?k=x", "tok")

        assert result is None

    @patch("ai_engineering.policy.checks.sonar.socket.create_connection")
    def test_returns_none_on_connection_error(self, mock_conn: MagicMock) -> None:
        mock_conn.side_effect = OSError("connection refused")
        result = _sonar_api_get("https://sonarcloud.io/api/check", "tok")
        assert result is None

    @patch("ai_engineering.policy.checks.sonar.socket.create_connection")
    def test_http_scheme_uses_port_80(self, mock_conn: MagicMock) -> None:
        sock = MagicMock()
        sock.recv.side_effect = [b"HTTP/1.1 200 OK\r\n\r\n{}", b""]
        mock_conn.return_value.__enter__ = MagicMock(return_value=sock)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        _sonar_api_get("http://localhost/api/check", "tok")

        mock_conn.assert_called_once_with(("localhost", 80), timeout=15)


# -- _build_sonar_url ---------------------------------------------------------


class TestBuildSonarUrl:
    def test_builds_url_with_params(self) -> None:
        url = _build_sonar_url(
            "https://sonarcloud.io",
            "/api/qualitygates/project_status",
            {"projectKey": "mykey"},
        )
        assert url == ("https://sonarcloud.io/api/qualitygates/project_status?projectKey=mykey")

    def test_returns_none_for_non_https_host(self) -> None:
        result = _build_sonar_url(
            "ftp://evil.com",
            "/api/check",
            {"projectKey": "x"},
        )
        assert result is None
