import http.client
import os
from unittest.mock import Mock, patch

from opamp.transport import TCPTransport, UnixTransport, from_env


# Test that the factory picks the right type for every env combination:
# only ODIGOS_OPAMP_UNIX_SOCKET set → UnixTransport
# only ODIGOS_OPAMP_SERVER_HOST set → TCPTransport
# both set → UnixTransport wins (precedence guard)
# neither set → None (fail-fast in mandatory_env_vars_set)
class TestFromEnv:
    """from_env() must pick the right transport for every supported env combination."""

    def test_returns_unix_transport_when_only_unix_socket_set(self):
        with patch.dict(os.environ, {"ODIGOS_OPAMP_UNIX_SOCKET": "/sock"}, clear=True):
            result = from_env()
        assert isinstance(result, UnixTransport)
        assert result._socket_path == "/sock"

    def test_returns_tcp_transport_when_only_server_host_set(self):
        with patch.dict(os.environ, {"ODIGOS_OPAMP_SERVER_HOST": "odigos-server:4318"}, clear=True):
            result = from_env()
        assert isinstance(result, TCPTransport)
        assert result._host == "odigos-server:4318"

    def test_unix_takes_precedence_when_both_set(self):
        env = {
            "ODIGOS_OPAMP_UNIX_SOCKET": "/sock",
            "ODIGOS_OPAMP_SERVER_HOST": "odigos-server:4318",
        }
        with patch.dict(os.environ, env, clear=True):
            result = from_env()
        assert isinstance(result, UnixTransport)

    def test_returns_none_when_no_env_set(self):
        with patch.dict(os.environ, {}, clear=True):
            result = from_env()
        assert result is None


# When from_env() picks a transport, calling .post() on it must talk over the
# matching wire (unix socket OR tcp) and never accidentally use the other one.
# We don't send real traffic - we mock both wires and check which one was hit.
class TestPostRoutesThroughCorrectWire:
    def test_unix_transport_post_uses_unix_socket(self):
        # Env says "use unix". post() should open a unix connection and never a tcp one.
        mock_conn = Mock()
        mock_response = Mock(status=200)
        mock_response.read.return_value = b"unix-response"
        mock_conn.getresponse.return_value = mock_response

        with patch.dict(os.environ, {"ODIGOS_OPAMP_UNIX_SOCKET": "/sock"}, clear=True):
            t = from_env()
        assert isinstance(t, UnixTransport)

        with (
            patch("opamp.transport._UnixHTTPConnection", return_value=mock_conn) as unix_conn_cls,
            patch("opamp.transport.http.client.HTTPConnection") as tcp_conn_cls,
        ):
            data = t.post(b"hello", {"Content-Type": "x"}, timeout=5)

        unix_conn_cls.assert_called_once_with("/sock", timeout=5)
        mock_conn.request.assert_called_once_with("POST", "/v1/opamp", body=b"hello", headers={"Content-Type": "x"})
        tcp_conn_cls.assert_not_called()
        assert data == b"unix-response"

    def test_tcp_transport_post_uses_tcp_connection_and_not_unix_socket(self):
        # Env says "use tcp". post() should open a tcp connection and never a unix one.
        mock_conn = Mock()
        mock_response = Mock(status=200)
        mock_response.read.return_value = b"tcp-response"
        mock_conn.getresponse.return_value = mock_response

        with patch.dict(os.environ, {"ODIGOS_OPAMP_SERVER_HOST": "host:1234"}, clear=True):
            t = from_env()
        assert isinstance(t, TCPTransport)

        with (
            patch("opamp.transport.http.client.HTTPConnection", return_value=mock_conn) as tcp_conn_cls,
            patch("opamp.transport._UnixHTTPConnection") as unix_conn_cls,
        ):
            data = t.post(b"hello", {"Content-Type": "x"}, timeout=5)

        tcp_conn_cls.assert_called_once_with("host:1234", timeout=5)
        mock_conn.request.assert_called_once_with("POST", "/v1/opamp", body=b"hello", headers={"Content-Type": "x"})
        unix_conn_cls.assert_not_called()
        assert data == b"tcp-response"

    # If the server responds with an HTTP error (>=400), post() must raise
    # so the caller's try/except turns it into an empty ServerToAgent.
    def test_transport_raises_on_http_error_status(self):
        mock_conn = Mock()
        mock_response = Mock(status=500)
        mock_response.read.return_value = b""
        mock_conn.getresponse.return_value = mock_response

        t = UnixTransport("/sock")
        with patch("opamp.transport._UnixHTTPConnection", return_value=mock_conn):
            try:
                t.post(b"x", {}, timeout=1)
            except http.client.HTTPException as e:
                assert "500" in str(e)
            else:
                raise AssertionError("expected HTTPException on 500 status")
