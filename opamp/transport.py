import os
import socket
import http.client

import requests_odigos


class TCPTransport:
    """HTTP/1.1 over TCP. Talks to ODIGOS_OPAMP_SERVER_HOST."""

    def __init__(self, host: str):
        self._url = f"http://{host}/v1/opamp"

    def post(self, body: bytes, headers: dict, timeout: float) -> bytes:
        response = requests_odigos.post(self._url, data=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.content


class UnixTransport:
    """HTTP/1.1 over an AF_UNIX stream socket. Talks to ODIGOS_OPAMP_UNIX_SOCKET."""

    def __init__(self, socket_path: str):
        self._socket_path = socket_path

    def post(self, body: bytes, headers: dict, timeout: float) -> bytes:
        conn = _UnixHTTPConnection(self._socket_path, timeout=timeout)
        try:
            conn.request("POST", "/v1/opamp", body=body, headers=headers)
            response = conn.getresponse()
            if response.status >= 400:
                raise RuntimeError(f"opamp unix POST returned status {response.status}")
            return response.read()
        finally:
            conn.close()


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
