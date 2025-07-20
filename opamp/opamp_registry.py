import os

from opamp.http_client import OpAMPHTTPClient


_client = None
_client_pid = None

def set_client(client) -> None:
    global _client, _client_pid
    _client = client
    _client_pid = os.getpid()

def get_client() -> OpAMPHTTPClient:
    if _client_pid != os.getpid():
        return None  # Defensive: ensure we don't return a client from a different process
    return _client
