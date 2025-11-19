from enum import Enum

class AgentHealthStatus(str, Enum):
    HEALTHY = "Healthy"
    STARTING = "Starting"
    UNSUPPORTED_RUNTIME_VERSION = "UnsupportedRuntimeVersion"
    TERMINATED = "ProcessTerminated"
    AGENT_FAILURE = "AgentFailure"
    NO_CONNECTION_TO_OPAMP_SERVER = "NoConnectionToOpAMPServer"
