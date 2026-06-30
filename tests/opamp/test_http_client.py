import http.client
import socket
import pytest
import threading
from unittest.mock import patch

from opamp.http_client import OpAMPHTTPClient
from opamp import opamp_pb2


class MockConnectionEvent:
    """Mock for the opamp_connection_event."""

    def __init__(self):
        self.event = threading.Event()
        self.error = False


@pytest.fixture
def mock_connection_event():
    return MockConnectionEvent()


@pytest.fixture
def mock_condition():
    return threading.Condition()


@pytest.fixture
def test_client(mock_connection_event, mock_condition):
    """Create an OpAMPHTTPClient with mocked dependencies."""
    with patch.dict('os.environ', {'ODIGOS_OPAMP_SERVER_HOST': 'localhost:8080'}):
        return OpAMPHTTPClient(mock_connection_event, mock_condition)


def patch_post(test_client, **kwargs):
    """Patch the transport's post() with the given return_value/side_effect."""
    return patch.object(test_client._transport, 'post', **kwargs)


class TestSendAgentToServerMessage:
    def test_successful_response(self, test_client):
        expected_response = opamp_pb2.ServerToAgent()
        expected_response.instance_uid = b"test-uid"

        with patch_post(test_client, return_value=expected_response.SerializeToString()):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)

            assert result.instance_uid == b"test-uid"

    def test_timeout_returns_empty_response(self, test_client):
        with patch_post(test_client, side_effect=socket.timeout("Connection timed out")):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)

            assert isinstance(result, opamp_pb2.ServerToAgent)
            assert not result.ListFields()

    def test_connection_error_returns_empty_response(self, test_client):
        with patch_post(test_client, side_effect=ConnectionError("Connection refused")):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)

            assert isinstance(result, opamp_pb2.ServerToAgent)
            assert not result.ListFields()

    def test_http_error_returns_empty_response(self, test_client):
        with patch_post(test_client, side_effect=http.client.HTTPException("opamp POST returned status 500")):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)

            assert isinstance(result, opamp_pb2.ServerToAgent)
            assert not result.ListFields()

    def test_unknown_exception_returns_empty_response(self, test_client):
        with patch_post(test_client, side_effect=RuntimeError("Unexpected error")):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)

            assert isinstance(result, opamp_pb2.ServerToAgent)
            assert not result.ListFields()

    def test_invalid_protobuf_response_returns_empty_response(self, test_client):
        with patch_post(test_client, return_value=b"invalid protobuf data"):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)

            assert isinstance(result, opamp_pb2.ServerToAgent)

    def test_sequence_num_increments_on_each_call(self, test_client):
        initial_seq = test_client.next_sequence_num

        with patch_post(test_client, side_effect=socket.timeout("timeout")):
            test_client.send_agent_to_server_message(opamp_pb2.AgentToServer())
            assert test_client.next_sequence_num == initial_seq + 1

            test_client.send_agent_to_server_message(opamp_pb2.AgentToServer())
            assert test_client.next_sequence_num == initial_seq + 2

    def test_does_not_crash_app_on_any_exception(self, test_client):
        exceptions_to_test = [
            socket.timeout("timeout"),
            ConnectionError("connection error"),
            http.client.HTTPException("http error"),
            OSError("os error"),
            RuntimeError("runtime error"),
            ValueError("value error"),
            Exception("generic exception"),
        ]

        for exc in exceptions_to_test:
            with patch_post(test_client, side_effect=exc):
                message = opamp_pb2.AgentToServer()
                result = test_client.send_agent_to_server_message(message)
                assert isinstance(result, opamp_pb2.ServerToAgent), f"Failed for exception: {exc}"
