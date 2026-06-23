from typing import Union
from .lib_handling import (
    reorder_python_path,
    reload_distro_modules,
    handle_django_instrumentation,
    handle_eventlet_instrumentation,
    patch_otlp_span_flags,
)

handle_eventlet_instrumentation()

import threading
import atexit
import sys
import os


# opentelemetry is a namespace package — Python merges all opentelemetry/
# directories from sys.path into opentelemetry.__path__.  If the user app
# bundles a different opentelemetry-api version, the user's copy can end up
# first and break agent imports (e.g. ImportError on std_to_otel).
# Fix: reorder opentelemetry.__path__ so agent paths are always searched first.
import opentelemetry

_agent_prefix = ('/var/odigos/', '/etc/odigos-vmagent/')
_agent_otel = [p for p in opentelemetry.__path__ if any(p.startswith(pfx) for pfx in _agent_prefix)]
_other_otel = [p for p in opentelemetry.__path__ if not any(p.startswith(pfx) for pfx in _agent_prefix)]
opentelemetry.__path__[:] = _agent_otel + _other_otel

import opentelemetry.sdk._configuration as sdk_config
from .process_resource import OdigosProcessResourceDetector
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.resources import OTELResourceDetector
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider, get_tracer_provider


# Move Odigos agent paths to the end of sys.path so the application's packages are
# imported first. User and agent stacks often pin different versions of the same libs
# (e.g. protobuf); without this, the wrong copy can win and break either side.
#
# Do this after the OpenTelemetry SDK imports above (load our SDK from the agent path
# before reshuffling) and before opamp below (it imports protobuf—the app should own that).
reorder_python_path()

# Backport OTLP Span.flags trace-flags encoding
# (upstream PR #4761: https://github.com/open-telemetry/opentelemetry-python/pull/4761)
# onto the canonical exporter module now that sys.path prefers the agent's copy.
patch_otlp_span_flags()

from .version import VERSION
from .exit_hook import ExitHooks
from .envs import set_static_otel_env

from .odigos_sampler import OdigosSampler
from .diagnose import apply_log_levels_from_opamp

from opamp.config import Config
from opamp import opamp_registry
from .distro import instrumentation_registry

from opamp.http_client import OpAMPHTTPClient, MockOpAMPClient
from opamp.utils import parse_first_message_signals

MINIMUM_PYTHON_SUPPORTED_VERSION = (3, 9)

_odigos_sampler = None


def initialize_components(trace_exporters=False, span_processor=None):
    # Ensure each child process after fork gets a fresh OpAMP client
    # and correct process.* resource attributes.
    os.register_at_fork(
        after_in_child=_after_in_child,
    )  # pylint: disable=protected-access

    handle_instrumenation_of_sub_processes()

    opamp_connection_event = OpampConnectionEvent()
    client = None

    try:
        client = start_opamp_client(opamp_connection_event)

        ## In case of error, e.g during the first connection to the OpAMP server,
        # we will use the default value which is enable traces only.
        if opamp_connection_event.error:
            container_config = None
            supported_signals: dict[str, Union[str, bool]] = {"traceSignal": True}
            initial_sampler_config = None
            initial_remote_config = None
        else:
            container_config = client.container_config
            supported_signals = parse_first_message_signals(container_config)

            # Get initial configs directly from client (only when connection is successful)
            try:
                initial_sampler_config = client.get_initial_sampler_config()
            except AttributeError:
                initial_sampler_config = None

            try:
                initial_remote_config = client.get_initial_remote_config()
            except AttributeError:
                initial_remote_config = None

        # Let the remote config take over the diagnostics log levels from the environment variables.
        # On the OpAMP error path container_config is None, which silences the loggers.
        apply_log_levels_from_opamp(container_config)

        handle_django_instrumentation()

        auto_resource = {
            "telemetry.distro.name": "odigos",
            "telemetry.distro.version": VERSION,
        }

        base_resource = (
            OdigosProcessResourceDetector(client.pid).detect().merge(OTELResourceDetector().detect()).merge(Resource.create(auto_resource))
        )

        # Wrap in proxy so child processes can refresh automatically
        resource = ProxyResource(base_resource, OdigosProcessResourceDetector)

        odigos_sampler = initialize_traces_if_enabled(
            trace_exporters,
            resource,
            supported_signals,
            span_processor,
            initial_sampler_config,
            initial_remote_config,
        )
        if odigos_sampler is not None:
            client.sampler = odigos_sampler

        initialize_metrics_if_enabled(resource, supported_signals)
        initialize_logging_if_enabled(resource, supported_signals)

    except Exception as e:
        if client is not None:
            client.shutdown(custom_failure_message=str(e))

    finally:
        # Make sure the distro modules are reloaded even if an exception is raised.
        reload_distro_modules()


def initialize_traces_if_enabled(
    trace_exporters,
    resource,
    signals: dict[str, Union[str, bool]],
    span_processor=None,
    initial_sampler_config=None,
    initial_remote_config=None,
):
    global _odigos_sampler
    # In case collectors signals support receiving traces, initialize the tracer provider with the exporters
    traces_enabled = signals.get("traceSignal", False)

    if traces_enabled:
        odigos_sampler = OdigosSampler()
        _odigos_sampler = odigos_sampler

        # Apply initial sampler config if provided (from OpAMP first message)
        if initial_sampler_config is not None:
            odigos_sampler.update_config(initial_sampler_config)

        # Exporting using exporters
        if trace_exporters:
            provider = TracerProvider(resource=resource, sampler=odigos_sampler)
            id_generator_name = sdk_config._get_id_generator()
            id_generator = sdk_config._import_id_generator(id_generator_name)
            provider.id_generator = id_generator

            set_tracer_provider(provider)

            exporters, _, _ = sdk_config._import_exporters(["otlp_proto_http"], [], [])

            for _, exporter_class in exporters.items():
                exporter_args = {}
                provider.add_span_processor(BatchSpanProcessor(exporter_class(**exporter_args)))

        # Exporting using EBPF
        else:
            provider = TracerProvider(resource=resource, sampler=odigos_sampler)
            set_tracer_provider(provider)
            if span_processor is not None:
                provider.add_span_processor(span_processor)

            # Bootstrap processor config from the first OpAMP message.
            # The update_conf_cb fires before the TracerProvider exists,
            # so the processor misses the initial config; apply it now.
            if initial_remote_config is not None and span_processor is not None and hasattr(span_processor, 'update_config'):
                span_processor.update_config(initial_remote_config)

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

    opamp_registry.set_client(client)

    # Register the configuration update callback for the processor
    client.register_config_update_cb(update_agent_config)

    python_version_supported = is_supported_python_version()

    client.start(python_version_supported)

    # Wait for the opamp first message to be received
    # Timeout based on maximum time for first message retry sequence to fail completely:
    # 2 attempts × (5s HTTP timeout + 2s delay) - 2s (no delay after last attempt) + last message timeout + 1s buffer = 18s
    event.event.wait(timeout=18)

    # Report the instrumentation libraries
    libraries = instrumentation_registry.get_instrumented_libraries()
    if libraries:
        client.report_instrumented_libraries(libraries)

    hooks = ExitHooks()
    hooks.hook()

    def shutdown():
        if hooks.exit_code is not None and hooks.exit_code != 0:
            if hooks.exception is not None:
                client.shutdown("Program exit with code: " + str(hooks.exit_code) + " and exception: " + str(hooks.exception))
            else:
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
    It also updates the sampler configuration if relevant config is present.

    :param conf: The `conf` parameter in the `update_agent_config` function is of type `Config`. It is
    used to update the configuration settings of the agent
    :type conf: Config
    :return: If the `provider` is `None` or if `active_proc` is `None`, then the function will return
    without performing any further actions.
    """
    # Update the diagnostics log levels on every remote config, even before the tracer provider exists.
    if hasattr(conf, 'container_config'):
        apply_log_levels_from_opamp(conf.container_config)

    provider = get_tracer_provider()
    if provider is None:
        return

    # Update sampler configuration if container_config is present
    if hasattr(conf, 'container_config') and conf.container_config:
        head_sampling_config = None
        if 'traces' in conf.container_config and 'headSampling' in conf.container_config['traces']:
            head_sampling_config = conf.container_config['traces']['headSampling']

        # Apply config to sampler - sampler will always exist when this callback is called
        # because update_agent_config is only called from OpAMP worker thread after sampler creation
        from opamp import opamp_registry

        client = opamp_registry.get_client()

        if client and hasattr(client, 'sampler') and client.sampler:
            client.sampler.update_config(head_sampling_config)
        else:
            # This should not happen in normal operation
            pass

    # The provider's public API does not expose processors directly,
    # but the private _active_span_processor attribute always exists.
    active_proc = getattr(provider, "_active_span_processor", None)
    if active_proc is None:
        return

    # If you attached only one BatchSpanProcessor, _active_span_processor
    # *is* that object.  If you attached several, it is a MultiSpanProcessor
    # that wraps them in ._span_processors.
    processors = active_proc._span_processors if hasattr(active_proc, "_span_processors") else [active_proc]

    for proc in processors:
        if hasattr(proc, "update_config"):
            proc.update_config(conf)


def is_supported_python_version() -> bool:
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


class OpampConnectionEvent:
    def __init__(self):
        self.event = threading.Event()
        self.error = False


class ProxyResource(Resource):
    """
    Resource wrapper to fix forked processes.

    Problem:
    - After fork, the child inherits the parent's Resource.
    - Attributes like process.pid are now wrong in the child.
    - We cannot rebuild the whole TracerProvider in the fork hook (unsafe).

    Solution:
    - ProxyResource delays ("lazy") the recomputation of process attributes
      until the child actually uses them (first access after fork).
    - This avoids doing heavy work directly in the fork hook.
    """

    def __init__(self, base: Resource, detector_cls):
        super().__init__(attributes=base.attributes)
        self._base = base
        self._detector_cls = detector_cls
        self._lock = threading.Lock()
        self._child_refreshed = False
        self._cached = None

    def _refresh_if_needed(self):
        # Ensure process attributes are recomputed only once per child.
        # The lock avoids race conditions if multiple threads access the
        # resource at the same time after fork.
        if not self._child_refreshed:
            with self._lock:
                if not self._child_refreshed:
                    proc_res = self._detector_cls(os.getpid()).detect()
                    self._cached = self._base.merge(proc_res)
                    self._child_refreshed = True

    @property
    def attributes(self):
        self._refresh_if_needed()
        return self._cached.attributes if self._cached else None

    def merge(self, other: Resource):
        self._refresh_if_needed()
        return self._cached.merge(other) if self._cached else None


def _after_in_child():
    # This hook runs in every child process after fork().
    # It does three things:
    # 1. Marks ProxyResource as "dirty" so process.* attributes are recomputed.
    # 2. Restarts the OpAMP client (threads/sockets do not survive fork).
    # 3. Propagates the sampler to the new client so config updates reach it.
    #    Without this, the forked client's sampler is None and config updates
    #    from OpAMP heartbeats are silently dropped.
    provider = get_tracer_provider()
    if isinstance(provider, TracerProvider) and isinstance(provider.resource, ProxyResource):
        provider.resource._child_refreshed = False
    client = start_opamp_client(OpampConnectionEvent())

    if _odigos_sampler is not None:
        client.sampler = _odigos_sampler
        initial_config = client.get_initial_sampler_config()
        if initial_config is not None:
            _odigos_sampler.update_config(initial_config)
