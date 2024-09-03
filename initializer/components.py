import threading
import atexit
import sys
import os
import opentelemetry.sdk._configuration as sdk_config

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.resources import ProcessResourceDetector, OTELResourceDetector
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider

from .lib_handling import reorder_python_path, reload_distro_modules
from .version import VERSION

from .odigos_sampler import OdigosSampler
from opentelemetry.sdk.trace.sampling import ParentBased

# Reorder the python sys.path to ensure that the user application's dependencies take precedence over the agent's dependencies.
# This is necessary because the user application's dependencies may be incompatible with those used by the agent.
reorder_python_path()

from opamp.http_client import OpAMPHTTPClient


MINIMUM_PYTHON_SUPPORTED_VERSION = (3, 8)
        
def initialize_components(trace_exporters = None, metric_exporters = None, log_exporters = None , span_processor = None):
    resource_attributes_event = threading.Event()
    client = None
    
    try:
        
        client = start_opamp_client(resource_attributes_event)
        resource_attributes_event.wait(timeout=30)  # Wait for the resource attributes to be received for 30 seconds

        received_value = client.resource_attributes
        
        if received_value:    

            auto_resource = {
                "telemetry.distro.name": "odigos",
                "telemetry.distro.version": VERSION,
            }
                        
            auto_resource.update(received_value)

            resource = Resource.create(auto_resource) \
                .merge(OTELResourceDetector().detect()) \
                .merge(ProcessResourceDetector().detect())

            odigos_sampler = initialize_traces_if_enabled(trace_exporters, resource, span_processor)
            
            client.sampler = odigos_sampler
            
            initialize_metrics_if_enabled(metric_exporters, resource)
            initialize_logging_if_enabled(log_exporters, resource)

        # # Reload distro modules to ensure the new path is used.
        reload_distro_modules()
        
    except Exception as e:
        if client is not None:
            client.shutdown(custom_failure_message=str(e))
        

def initialize_traces_if_enabled(trace_exporters, resource, span_processor = None):
    traces_enabled = os.getenv(sdk_config.OTEL_TRACES_EXPORTER, "none").strip().lower()
    if traces_enabled != "none":
        
        odigos_sampler = OdigosSampler()
        sampler = ParentBased(odigos_sampler)
        
        # Exporting using exporters
        if trace_exporters is not None:            
            provider = TracerProvider(resource=resource, sampler=sampler)
            id_generator_name = sdk_config._get_id_generator()
            id_generator = sdk_config._import_id_generator(id_generator_name)            
            provider.id_generator = id_generator
            
            set_tracer_provider(provider)
            
            for _, exporter_class in trace_exporters.items():
                exporter_args = {}
                provider.add_span_processor(
                    BatchSpanProcessor(exporter_class(**exporter_args))
                )
                
        # Exporting using EBPF
        else:
            provider = TracerProvider(sampler=sampler)
            set_tracer_provider(provider)
            if span_processor is not None:
                provider.add_span_processor(span_processor)
            
    return odigos_sampler

def initialize_metrics_if_enabled(metric_exporters, resource):
    metrics_enabled = os.getenv(sdk_config.OTEL_METRICS_EXPORTER, "none").strip().lower()
    if metrics_enabled != "none" and metric_exporters:
        sdk_config._init_metrics(metric_exporters, resource)

def initialize_logging_if_enabled(log_exporters, resource):
    logging_enabled = os.getenv(sdk_config.OTEL_LOGS_EXPORTER, "none").strip().lower()
    if logging_enabled != "none" and log_exporters:
        sdk_config._init_logging(log_exporters, resource)


def start_opamp_client(event):
    condition = threading.Condition(threading.Lock())
    client = OpAMPHTTPClient(event, condition)
    
    python_version_supported = is_supported_python_version()

    client.start(python_version_supported)
    
    def shutdown():
        client.shutdown()

    # Ensure that the shutdown function is called on program exit
    atexit.register(shutdown)

    return client


def is_supported_python_version():
    return sys.version_info >= MINIMUM_PYTHON_SUPPORTED_VERSION