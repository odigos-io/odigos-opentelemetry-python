import os
import socket
import http.client

_OPAMP_PATH = "/v1/opamp"


def _post(conn: http.client.HTTPConnection, body: bytes, headers: dict) -> bytes:
    try:
        conn.request("POST", _OPAMP_PATH, body=body, headers=headers)
        response = conn.getresponse()
        status = response.status
        data = response.read()
        if status >= 400:
            raise http.client.HTTPException(f"opamp POST returned status {status}")
        return data
    finally:
        conn.close()


class TCPTransport:
    """HTTP/1.1 over TCP. Talks to ODIGOS_OPAMP_SERVER_HOST."""

    def __init__(self, host: str):
        self._host = host

    def post(self, body: bytes, headers: dict, timeout: float) -> bytes:
        conn = http.client.HTTPConnection(self._host, timeout=timeout)
        return _post(conn, body, headers)


class UnixTransport:
    """HTTP/1.1 over an AF_UNIX stream socket. Talks to ODIGOS_OPAMP_UNIX_SOCKET."""

    def __init__(self, socket_path: str):
        self._socket_path = socket_path

    def post(self, body: bytes, headers: dict, timeout: float) -> bytes:
        conn = _UnixHTTPConnection(self._socket_path, timeout=timeout)
        return _post(conn, body, headers)


class _UnixHTTPConnection(http.client.HTTPConnection):
    """http.client.HTTPConnection that talks over a unix domain socket."""

    def __init__(self, socket_path: str, timeout: float):
        super().__init__("localhost", timeout=timeout)
        self._socket_path = socket_path

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self._socket_path)
        self.sock = sock


def from_env():
    """Pick an OpAMP transport from env vars. ODIGOS_OPAMP_UNIX_SOCKET wins if both are set.
    Returns None if neither is set so the client can fail fast on missing config.
    """
    socket_path = os.getenv("ODIGOS_OPAMP_UNIX_SOCKET")
    if socket_path:
        return UnixTransport(socket_path)

    host = os.getenv("ODIGOS_OPAMP_SERVER_HOST")
    if host:
        return TCPTransport(host)

    return None
