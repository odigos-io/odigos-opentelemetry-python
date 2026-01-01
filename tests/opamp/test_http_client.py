import pytest
import threading
from unittest.mock import Mock, patch, MagicMock

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


class TestSendAgentToServerMessage:

    def test_successful_response(self, test_client):
        expected_response = opamp_pb2.ServerToAgent()
        expected_response.instance_uid = b"test-uid"
        
        mock_response = Mock()
        mock_response.content = expected_response.SerializeToString()
        mock_response.raise_for_status = Mock()

        with patch('opamp.http_client.requests_odigos.post', return_value=mock_response):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)
            
            assert result.instance_uid == b"test-uid"

    def test_timeout_returns_empty_response(self, test_client):
        import requests_odigos
        
        with patch('opamp.http_client.requests_odigos.post', side_effect=requests_odigos.Timeout("Connection timed out")):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)
            
            assert isinstance(result, opamp_pb2.ServerToAgent)
            assert not result.ListFields()

    def test_connection_error_returns_empty_response(self, test_client):
        import requests_odigos
        
        with patch('opamp.http_client.requests_odigos.post', side_effect=requests_odigos.ConnectionError("Connection refused")):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)
            
            assert isinstance(result, opamp_pb2.ServerToAgent)
            assert not result.ListFields()

    def test_http_error_403_returns_empty_response(self, test_client):
        import requests_odigos
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests_odigos.HTTPError("403 Forbidden")
        
        with patch('opamp.http_client.requests_odigos.post', return_value=mock_response):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)
            
            assert isinstance(result, opamp_pb2.ServerToAgent)
            assert not result.ListFields()

    def test_http_error_500_returns_empty_response(self, test_client):
        import requests_odigos
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests_odigos.HTTPError("500 Internal Server Error")
        
        with patch('opamp.http_client.requests_odigos.post', return_value=mock_response):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)
            
            assert isinstance(result, opamp_pb2.ServerToAgent)
            assert not result.ListFields()

    def test_request_exception_returns_empty_response(self, test_client):
        import requests_odigos
        
        with patch('opamp.http_client.requests_odigos.post', side_effect=requests_odigos.RequestException("Some request error")):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)
            
            assert isinstance(result, opamp_pb2.ServerToAgent)
            assert not result.ListFields()

    def test_unknown_exception_returns_empty_response(self, test_client):
        with patch('opamp.http_client.requests_odigos.post', side_effect=RuntimeError("Unexpected error")):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)
            
            assert isinstance(result, opamp_pb2.ServerToAgent)
            assert not result.ListFields()

    def test_invalid_protobuf_response_returns_empty_response(self, test_client):
        mock_response = Mock()
        mock_response.content = b"invalid protobuf data"
        mock_response.raise_for_status = Mock()

        with patch('opamp.http_client.requests_odigos.post', return_value=mock_response):
            message = opamp_pb2.AgentToServer()
            result = test_client.send_agent_to_server_message(message)
            
            assert isinstance(result, opamp_pb2.ServerToAgent)

    def test_sequence_num_increments_on_each_call(self, test_client):
        import requests_odigos
        
        initial_seq = test_client.next_sequence_num
        
        with patch('opamp.http_client.requests_odigos.post', side_effect=requests_odigos.Timeout("timeout")):
            test_client.send_agent_to_server_message(opamp_pb2.AgentToServer())
            assert test_client.next_sequence_num == initial_seq + 1
            
            test_client.send_agent_to_server_message(opamp_pb2.AgentToServer())
            assert test_client.next_sequence_num == initial_seq + 2

    def test_does_not_crash_app_on_any_exception(self, test_client):
        import requests_odigos
        
        exceptions_to_test = [
            requests_odigos.Timeout("timeout"),
            requests_odigos.ConnectionError("connection error"),
            requests_odigos.HTTPError("http error"),
            requests_odigos.RequestException("request error"),
            RuntimeError("runtime error"),
            ValueError("value error"),
            Exception("generic exception"),
        ]
        
        for exc in exceptions_to_test:
            with patch('opamp.http_client.requests_odigos.post', side_effect=exc):
                message = opamp_pb2.AgentToServer()
                result = test_client.send_agent_to_server_message(message)
                assert isinstance(result, opamp_pb2.ServerToAgent), f"Failed for exception: {exc}"
