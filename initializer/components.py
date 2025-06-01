from .lib_handling import reorder_python_path, reload_distro_modules, handle_django_instrumentation, handle_eventlet_instrumentation

handle_eventlet_instrumentation()

import threading
import atexit
import sys
import os

import opentelemetry.sdk._configuration as sdk_config
from .process_resource import OdigosProcessResourceDetector
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.resources import OTELResourceDetector
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider, get_tracer_provider

from .version import VERSION
from .exit_hook import ExitHooks
from .envs import set_static_otel_env

from .odigos_sampler import OdigosSampler
from opentelemetry.sdk.trace.sampling import ParentBased

from opamp.config import Config

# Reorder the python sys.path to ensure that the user application's dependencies take precedence over the agent's dependencies.
# This is necessary because the user application's dependencies may be incompatible with those used by the agent.
reorder_python_path()

from opamp.http_client import OpAMPHTTPClient, MockOpAMPClient

MINIMUM_PYTHON_SUPPORTED_VERSION = (3, 8)


def initialize_components(trace_exporters = False, span_processor = None):
    # In case of forking, the OpAMP client should be started in the child process.
    # e.g when using gunicorn/celery with multiple workers.
    os.register_at_fork(
    after_in_child=lambda: start_opamp_client(threading.Event()),
    )  # pylint: disable=protected-access

    handle_instrumenation_of_sub_processes()

    resource_attributes_event = threading.Event()
    client = None

    try:

        client = start_opamp_client(resource_attributes_event)
        resource_attributes_event.wait(timeout=30)  # Wait for the resource attributes to be received for 30 seconds

        supported_signals = client.signals
        received_value = client.resource_attributes

        if received_value:
            handle_django_instrumentation()

            auto_resource = {
                "telemetry.distro.name": "odigos",
                "telemetry.distro.version": VERSION,
            }

            auto_resource.update(received_value)

            resource = OdigosProcessResourceDetector(client.pid).detect() \
                .merge(OTELResourceDetector().detect()) \
                .merge(Resource.create(auto_resource))

            odigos_sampler = initialize_traces_if_enabled(trace_exporters, resource, span_processor, supported_signals)
            if odigos_sampler is not None :
                client.sampler = odigos_sampler

            initialize_metrics_if_enabled(resource, supported_signals)
            initialize_logging_if_enabled(resource, supported_signals)

        else:
            raise Exception("Did not receive resource attributes from the OpAMP server.")

    except Exception as e:
        if client is not None:
            client.shutdown(custom_failure_message=str(e))
        raise

    finally:
        # Make sure the distro modules are reloaded even if an exception is raised.
        reload_distro_modules()

def initialize_traces_if_enabled(trace_exporters, resource, span_processor = None, signals = None):
    # In case collectors signals support receiving traces, initialize the tracer provider with the exporters
    traces_enabled = signals.get("traceSignal", False)

    if traces_enabled:

        odigos_sampler = OdigosSampler()
        sampler = ParentBased(odigos_sampler)

        # Exporting using exporters
        if trace_exporters:
            provider = TracerProvider(resource=resource, sampler=sampler)
            id_generator_name = sdk_config._get_id_generator()
            id_generator = sdk_config._import_id_generator(id_generator_name)
            provider.id_generator = id_generator

            set_tracer_provider(provider)

            exporters, _, _ = sdk_config._import_exporters(["otlp_proto_http"], [], [])

            for _, exporter_class in exporters.items():
                exporter_args = {}
                provider.add_span_processor(
                    BatchSpanProcessor(exporter_class(**exporter_args))
                )

        # Exporting using EBPF
        else:
            provider = TracerProvider(resource=resource, sampler=sampler)
            set_tracer_provider(provider)
            if span_processor is not None:
                provider.add_span_processor(span_processor)

        return odigos_sampler

    return None

def initialize_metrics_if_enabled(resource, signals):
    # Currently we're not exporting metrics using the OTEL exporter.
    metrics_enabled = False

    if metrics_enabled:
        _, exporters, _ = sdk_config._import_exporters([], ["otlp_proto_http"], [])

        sdk_config._init_metrics(exporters, resource)


def initialize_logging_if_enabled(resource, signals):
    # Logs are collected using the filelog receiver; currently, there is no need to export them using the OTEL exporter.
    logging_enabled = False

    if logging_enabled:
        _, _, exporters = sdk_config._import_exporters([], [], ["otlp_proto_http"])
        sdk_config._init_logging(exporters, resource)


def start_opamp_client(event):
    if os.getenv('DISABLE_OPAMP_CLIENT', 'false').strip().lower() == 'true':
        return MockOpAMPClient(event)

    # Setting static otel envs such as log correlation and exporter protocols
    set_static_otel_env()

    condition = threading.Condition(threading.Lock())
    client = OpAMPHTTPClient(event, condition)

    # Register the configuration update callback for the processor
    client.register_config_update_cb(update_agent_config)

    python_version_supported = is_supported_python_version()

    client.start(python_version_supported)

    hooks = ExitHooks()
    hooks.hook()

    def shutdown():
        if hooks.exit_code is not None and hooks.exit_code != 0:
            client.shutdown("Program exit with code: " + str(hooks.exit_code))
        elif hooks.exception is not None:
            client.shutdown("Program exit with exception: " + str(hooks.exception))
        else:
            client.shutdown("Program finished", component_health=True)

    # Ensure that the shutdown function is called on program exit
    atexit.register(shutdown)

    return client

def update_agent_config(conf: Config):
    """
    The function `update_agent_config` checks for a tracer provider and updates its configuration using
    processors if available.
    It searches specifically for the EBPFSpanProcessor processes (Looking for the update_config attribute).

    :param conf: The `conf` parameter in the `update_agent_config` function is of type `Config`. It is
    used to update the configuration settings of the agent
    :type conf: Config
    :return: If the `provider` is `None` or if `active_proc` is `None`, then the function will return
    without performing any further actions.
    """
    provider = get_tracer_provider()
    if provider is None:
        return

    # The provider’s public API does not expose processors directly,
    # but the private _active_span_processor attribute always exists.
    active_proc = getattr(provider, "_active_span_processor", None)
    if active_proc is None:
        return

    # If you attached only one BatchSpanProcessor, _active_span_processor
    # *is* that object.  If you attached several, it is a MultiSpanProcessor
    # that wraps them in ._span_processors.
    processors = (
        active_proc._span_processors
        if hasattr(active_proc, "_span_processors")
        else [active_proc]
    )

    for proc in processors:
        if hasattr(proc, "update_config"):
            proc.update_config(conf)

def is_supported_python_version():
    return sys.version_info >= MINIMUM_PYTHON_SUPPORTED_VERSION

def handle_instrumenation_of_sub_processes():
    # Resolves a path management issue introduced by OpenTelemetry's sitecustomize implementation.
    # OpenTelemetry removed auto_instrumentation from the path to address a specific bug
    # (ref: https://github.com/open-telemetry/opentelemetry-python-contrib/issues/1050).
    # This modification does not impact our use case, as we utilize auto_instrumentation as a package
    # and do not rely on opentelemetry-instrument for running instrumentations.
    #
    # We are reintroducing the path to enable parallel execution with other agent that inject themselves via sitecustomize.
    # We've observed that agents attempt to import user-defined sitecustomize.py [OpenTelemetry one in this case] prior to their own execution
    # to prevent application logic disruption.
    #
    # Given OpenTelemetry's path removal during Distro creation, we must manually restore the path.
    # This addresses cases where applications using os.exec* are not properly instrumented.
    #
    # Note: This is a temporary solution and should be refactored when:
    # - The environment override writer is removed
    # - Webhook integration is implemented
    # - A custom distro creation mechanism is developed
    auto_instrumentation_path = "/var/odigos/python/opentelemetry/instrumentation/auto_instrumentation"
    python_path = os.getenv("PYTHONPATH", "")

    if auto_instrumentation_path not in python_path:
        new_python_path = f"{python_path}:{auto_instrumentation_path}" if python_path else auto_instrumentation_path
        os.environ["PYTHONPATH"] = new_python_path
