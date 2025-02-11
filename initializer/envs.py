import os


# Configuration Constants
ENV_OTEL_TRACES_EXPORTER = "OTEL_TRACES_EXPORTER"
ENV_OTEL_METRICS_EXPORTER = "OTEL_METRICS_EXPORTER"
ENV_OTEL_LOGS_EXPORTER = "OTEL_LOGS_EXPORTER"

HTTP_PROTOBUF_PROTOCOL = "http/protobuf"
static_env_dict = {
    "OTEL_PYTHON_LOG_CORRELATION": "true",
    "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL": HTTP_PROTOBUF_PROTOCOL,
    "OTEL_EXPORTER_OTLP_METRICS_PROTOCOL": HTTP_PROTOBUF_PROTOCOL,
}

def set_static_otel_env():
    """
    Injects environment variables from a dictionary.
    """
    if not isinstance(static_env_dict, dict):
        raise TypeError("static_env_dict must be a dictionary")

    os.environ.update(static_env_dict)
    
    
def set_otel_exporter_env_vars(signals: dict):
    """
    Sets the OTEL environment variables based on the signal configuration.
    """
    os.environ[ENV_OTEL_TRACES_EXPORTER] = "otlp" if signals.get("traceSignal", False) else "none"
    os.environ[ENV_OTEL_METRICS_EXPORTER] = "otlp" if signals.get("metricsSignal", False) else "none"
    os.environ[ENV_OTEL_LOGS_EXPORTER] = "otlp" if signals.get("logsSignal", False) else "none"
    