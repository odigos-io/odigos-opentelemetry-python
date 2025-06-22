import os
import sys
import json
import time
import base64
import threading
import requests_odigos
import logging

from uuid_extensions import uuid7
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.context import (
    _SUPPRESS_HTTP_INSTRUMENTATION_KEY,
    attach,
    detach,
    set_value,
)

from opamp import opamp_pb2, anyvalue_pb2, utils
from opamp.health_status import AgentHealthStatus
from initializer.process_resource import PROCESS_VPID

from google.protobuf.json_format import MessageToDict

from opamp.config import from_dict, Config

# Setup the logger
opamp_logger = logging.getLogger('odigos')

_debugger_instance = None

env_var_mappings = {
    "ODIGOS_WORKLOAD_NAMESPACE": ResourceAttributes.K8S_NAMESPACE_NAME,
    "ODIGOS_CONTAINER_NAME": ResourceAttributes.K8S_CONTAINER_NAME,
    "ODIGOS_POD_NAME": ResourceAttributes.K8S_POD_NAME
}

class OpAMPHTTPClient:
    def __init__(self, opamp_connection_event, condition: threading.Condition):
        self.server_host = os.getenv('ODIGOS_OPAMP_SERVER_HOST')
        self.server_url = f"http://{self.server_host}/v1/opamp"
        self.signals = {}
        self.running = True
        self.condition = condition
        self.opamp_connection_event = opamp_connection_event
        self.next_sequence_num = 0
        self.instance_uid = uuid7().__str__()
        self.remote_config_status = None
        self.sampler = None # OdigosSampler instance
        self.pid = os.getpid()
        self.update_conf_cb = None # Callback for configuration updates in the processor


    def start(self, python_version_supported: bool = None):
        if not python_version_supported:

            python_version = f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'
            error_message = f"Opentelemetry SDK require Python in version 3.8 or higher [{python_version} is not supported]"

            # opamp_logger.warning(f"{error_message}, sending disconnect message to OpAMP server...")
            self.send_unsupported_version_disconnect_message(error_message=error_message)
            self.opamp_connection_event.event.set()
            return

        self.client_thread = threading.Thread(target=self.run, name="OpAMPClientThread", daemon=True)
        self.client_thread.start()

    def run(self):
        try:
            if not self.mandatory_env_vars_set():
                self.opamp_connection_event.error = True
                self.opamp_connection_event.event.set()
                return

            self.send_first_message_with_retry()
            self.opamp_connection_event.event.set()

            if self.opamp_connection_event.error:
                # if the first message failed, we will not start the worker thread
                return

            self.worker()

        except Exception as e:
            # opamp_logger.error(f"Error running OpAMP client: {e}")
            failure_message = self.get_agent_failure_disconnect_message(error_message=str(e))
            self.send_agent_to_server_message(failure_message)

            # Exiting the opamp thread and set the event to notify the main thread
            self.opamp_connection_event.error = True
            self.opamp_connection_event.event.set()
            sys.exit()

    def get_agent_failure_disconnect_message(self, error_message: str, component_health: bool = False) -> None:
        agent_failure_message = opamp_pb2.AgentToServer()

        agent_disconnect = self.get_agent_disconnect()
        agent_failure_message.agent_disconnect.CopyFrom(agent_disconnect)

        agent_health = self.get_agent_health(component_health=component_health, last_error=error_message, status=AgentHealthStatus.AGENT_FAILURE.value)
        agent_failure_message.health.CopyFrom(agent_health)

        return agent_failure_message

    def send_unsupported_version_disconnect_message(self, error_message: str) -> None:
        first_disconnect_message = opamp_pb2.AgentToServer()

        agent_description = self.get_agent_description()

        first_disconnect_message.agent_description.CopyFrom(agent_description)

        agent_disconnect = self.get_agent_disconnect()
        first_disconnect_message.agent_disconnect.CopyFrom(agent_disconnect)

        agent_health = self.get_agent_health(component_health=False, last_error=error_message, status=AgentHealthStatus.UNSUPPORTED_RUNTIME_VERSION.value)
        first_disconnect_message.health.CopyFrom(agent_health)

        self.send_agent_to_server_message(first_disconnect_message)

    def send_first_message_with_retry(self) -> None:
        max_retries = 5
        delay = 2
        for attempt in range(1, max_retries + 1):
            try:
                # Send first message to OpAMP server, Health is false as the component is not initialized
                agent_health = self.get_agent_health(component_health=False, last_error="Python OpenTelemetry agent is starting", status=AgentHealthStatus.STARTING.value)
                agent_description = self.get_agent_description()
                first_message_server_to_agent = self.send_agent_to_server_message(opamp_pb2.AgentToServer(agent_description=agent_description, health=agent_health))

                # Check if the response of the first message is empty
                # It may happen if OpAMPServer is not available
                if first_message_server_to_agent.ListFields():
                    if self.update_remote_config_status(first_message_server_to_agent):
                        if first_message_server_to_agent.HasField("remote_config") and self.update_conf_cb:
                            try:
                                remote_config = self.get_remote_config(first_message_server_to_agent)
                                self.update_conf_cb(remote_config)
                            except Exception:
                                # Catch exception and don't update the config
                                # The default config is preloaded when the EBPFSpanProcessor is initialized
                                pass

                    sdk_config = utils.get_sdk_config(first_message_server_to_agent.remote_config.config.config_map)
                    self.signals = utils.parse_first_message_signals(sdk_config)

                    # Send healthy message to OpAMP server
                    # opamp_logger.info("Reporting healthy to OpAMP server...")
                    agent_health = self.get_agent_health(component_health=True, status=AgentHealthStatus.HEALTHY.value)
                    self.send_agent_to_server_message(opamp_pb2.AgentToServer(health=agent_health))

                    # Return if the first message was successfully sent
                    return

            except Exception as e:
                # opamp_logger.error(f"Attempt {attempt}/{max_retries} failed. Error sending full state to OpAMP server: {e}")
                pass

            if attempt < max_retries:
                time.sleep(delay)

        # If all attempts failed, set the error flag and return
        self.opamp_connection_event.error = True



    def worker(self):
        while self.running:
            with self.condition:
                try:
                    server_to_agent = self.send_heartbeat()
                    if self.update_remote_config_status(server_to_agent):
                        if server_to_agent.HasField("remote_config") and self.update_conf_cb:
                            try:
                                remote_config = self.get_remote_config(server_to_agent)
                                self.update_conf_cb(remote_config)
                            except Exception:
                                # Catch exception and don't update the config
                                # The default config is preloaded when the EBPFSpanProcessor is initialized
                                pass

                    if server_to_agent.flags & opamp_pb2.ServerToAgentFlags_ReportFullState:
                        # opamp_logger.info("Received request to report full state")

                        agent_description = self.get_agent_description()
                        agent_health = self.get_agent_health(component_health=True, status=AgentHealthStatus.HEALTHY.value)
                        agent_to_server = opamp_pb2.AgentToServer(agent_description=agent_description, health=agent_health)

                        server_to_agent = self.send_agent_to_server_message(agent_to_server)

                        if self.update_remote_config_status(server_to_agent):
                            if server_to_agent.HasField("remote_config") and self.update_conf_cb:
                                try:
                                    remote_config = self.get_remote_config(server_to_agent)
                                    self.update_conf_cb(remote_config)
                                except Exception:
                                    # Catch exception and don't update the config
                                    # The default config is preloaded when the EBPFSpanProcessor is initialized
                                    pass

                except requests_odigos.RequestException as e:
                    # opamp_logger.error(f"Error fetching data: {e}")
                    pass
                self.condition.wait(30)

    def get_remote_config(self, message) -> dict:
        """
        Given a Protobuf message with a 'remote_config' field,
        decode all bytes and base64-encoded subfields into a clean Python dict.
        """
        proto_dict = MessageToDict(message, preserving_proto_field_name=True)

        remote_config = proto_dict.get("remote_config")
        if not remote_config:
            raise ValueError("No 'remote_config' field found in the provided message.")

        config_map = remote_config.get("config", {}).get("config_map", {})
        if not config_map:
            raise ValueError("No 'config_map' found inside 'remote_config'.")

        decoded_map = {}

        for key, item in config_map.items():
            body_base64 = item.get("body")
            content_type = item.get("content_type")

            if not body_base64:
                decoded_map[key] = None
                continue

            try:
                body_bytes = base64.b64decode(body_base64)
            except Exception as e:
                raise ValueError(f"Failed to base64 decode body for key {key}: {e}")

            if content_type == "application/json":
                try:
                    body_json = json.loads(body_bytes.decode('utf-8'))
                    decoded_map[key] = body_json
                except Exception as e:
                    raise ValueError(f"Failed to JSON-decode body for key {key}: {e}")
            else:
                # If not JSON, just keep it as raw bytes
                decoded_map[key] = body_bytes

        inner = decoded_map.get("", None)
        if inner is None:
            return Config() # Return default values for config
        return from_dict(Config, inner)

    def send_heartbeat(self) -> opamp_pb2.ServerToAgent: # type: ignore
        # opamp_logger.debug("Sending heartbeat to OpAMP server...")
        try:
            agent_to_server = opamp_pb2.AgentToServer(remote_config_status=self.remote_config_status)
            return self.send_agent_to_server_message(agent_to_server)
        except requests_odigos.RequestException as e:
            # opamp_logger.error(f"Error sending heartbeat to OpAMP server: {e}")
            pass

    def get_agent_description(self) -> opamp_pb2.AgentDescription: # type: ignore
        # The "DISABLE_OPAMP_CLIENT" environment variable is defined only in our VMs environments.
        # Here we use it exclusively to distinguish between virtual machine and Kubernetes environments.
        #
        # - If "DISABLE_OPAMP_CLIENT" is set to "true", it indicates that the service is running in a VM,
        #   so we use "PROCESS_PID" for identification.
        # - Otherwise, the service is assumed to be running in a K8s environment,
        #   and we use "PROCESS_VPID" instead.
        #
        # This ensures the correct process identification mechanism is applied based on the runtime environment.

        # Add additional attributes from environment variables

        if os.getenv("DISABLE_OPAMP_CLIENT", "false").strip().lower() == "true":
            process_id_key = ResourceAttributes.PROCESS_PID
        else:
            process_id_key = PROCESS_VPID

        identifying_attributes = [
            anyvalue_pb2.KeyValue(
                key=ResourceAttributes.SERVICE_INSTANCE_ID,
                value=anyvalue_pb2.AnyValue(string_value=self.instance_uid)
            ),
            anyvalue_pb2.KeyValue(
                key=process_id_key,
                value=anyvalue_pb2.AnyValue(int_value=self.pid)
            ),
            anyvalue_pb2.KeyValue(
                key=ResourceAttributes.TELEMETRY_SDK_LANGUAGE,
                value=anyvalue_pb2.AnyValue(string_value="python")
            )
        ]

        # Add additional attributes from environment variables
        for env_var, attribute_key in env_var_mappings.items():
            value = os.environ.get(env_var)
            if value:
                identifying_attributes.append(
                    anyvalue_pb2.KeyValue(
                        key=attribute_key,
                        value=anyvalue_pb2.AnyValue(string_value=value)
                    )
                )

        return opamp_pb2.AgentDescription(
            identifying_attributes=identifying_attributes,
            non_identifying_attributes=[]
        )

    def get_agent_disconnect(self) -> opamp_pb2.AgentDisconnect: # type: ignore
        return opamp_pb2.AgentDisconnect()

    def get_agent_health(self, component_health: bool = None, last_error : str = None, status: str = None) -> opamp_pb2.ComponentHealth: # type: ignore
        health = opamp_pb2.ComponentHealth(
        )
        if component_health is not None:
            health.healthy = component_health
        if last_error is not None:
            health.last_error = last_error
        if status is not None:
            health.status = status

        return health


    def send_agent_to_server_message(self, message: opamp_pb2.AgentToServer) -> opamp_pb2.ServerToAgent: # type: ignore

        message.instance_uid = self.instance_uid.encode('utf-8')
        message.sequence_num = self.next_sequence_num
        if self.remote_config_status:
            message.remote_config_status.CopyFrom(self.remote_config_status)

        self.next_sequence_num += 1
        message_bytes = message.SerializeToString()

        headers = {
            "Content-Type": "application/x-protobuf",
        }

        try:
            agent_message = attach(set_value(_SUPPRESS_HTTP_INSTRUMENTATION_KEY, True))
            response = requests_odigos.post(self.server_url, data=message_bytes, headers=headers, timeout=5)
            response.raise_for_status()
        except requests_odigos.Timeout:
            # opamp_logger.error("Timeout sending message to OpAMP server")
            return opamp_pb2.ServerToAgent()
        except requests_odigos.ConnectionError as e:
            # opamp_logger.error(f"Error sending message to OpAMP server: {e}")
            return opamp_pb2.ServerToAgent()
        finally:
            detach(agent_message)

        server_to_agent = opamp_pb2.ServerToAgent()
        try:
            server_to_agent.ParseFromString(response.content)
        except NotImplementedError as e:
            # opamp_logger.error(f"Error parsing response from OpAMP server: {e}")
            return opamp_pb2.ServerToAgent()
        return server_to_agent

    def mandatory_env_vars_set(self):
        mandatory_env_vars = {
            "ODIGOS_OPAMP_SERVER_HOST": self.server_host,
        }

        for env_var, value in mandatory_env_vars.items():
            if not value:
                # opamp_logger.error(f"{env_var} environment variable not set")
                return False

        return True

    def shutdown(self, custom_failure_message: str = None, component_health: bool = False):
        self.running = False
        # opamp_logger.info("Sending agent disconnect message to OpAMP server...")
        if custom_failure_message:
            disconnect_message = self.get_agent_failure_disconnect_message(error_message=custom_failure_message, component_health=component_health)
        else:
            agent_health = self.get_agent_health(component_health=component_health, last_error="Python runtime is exiting", status=AgentHealthStatus.TERMINATED.value)
            disconnect_message = opamp_pb2.AgentToServer(agent_disconnect=opamp_pb2.AgentDisconnect(), health=agent_health)

        with self.condition:
            self.condition.notify_all()
        self.client_thread.join()

        self.send_agent_to_server_message(disconnect_message)

    def update_remote_config_status(self, server_to_agent: opamp_pb2.ServerToAgent) -> bool: # type: ignore
        if server_to_agent.HasField("remote_config"):
            remote_config_hash = server_to_agent.remote_config.config_hash
            remote_config_status = opamp_pb2.RemoteConfigStatus(last_remote_config_hash=remote_config_hash)
            self.remote_config_status = remote_config_status
            return True
        return False

    def register_config_update_cb(self, cb) -> None:
        self.update_conf_cb = cb


# Mock client class for non-OpAMP installations
# This class simulates the OpAMP client when the OpAMP server is not available.
# To activate it, set the environment variable DISABLE_OPAMP_CLIENT to true.
class MockOpAMPClient:
    def __init__(self, opamp_connection_event, *args, **kwargs):
        self.signals = {'traceSignal': True}
        opamp_connection_event.event.set()

    def shutdown(self, custom_failure_message=None):
        pass
