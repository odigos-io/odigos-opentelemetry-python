from opamp import opamp_registry
from .distro import instrumentation_registry

def run_post_hook():
    client = opamp_registry.get_client()

    # If the client is not set for some reason, don't do anything
    if client is None:
        return

    # If the client is not connected, we don't need to report the instrumentation libraries
    if client.opamp_connection_event.error:
        return

    instrumented_libraries = instrumentation_registry.get_instrumented_libraries()

    client.report_instrumented_libraries(instrumented_libraries)
