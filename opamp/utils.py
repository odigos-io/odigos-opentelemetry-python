import json

def get_container_config(config_map):
    """
    Extracts and parses the container configuration from the config map.
    """
    if "container_config" not in config_map:
        return {}

    try:
        return json.loads(config_map["container_config"].body)
    except json.JSONDecodeError:
        return {}


def parse_first_message_signals(container_config): # type: ignore
    """
    Parses the trace, logs, and metrics signals from the container config.
    Signal is considered enabled if its key exists in the config.
    """

    return {
        "traceSignal": "traces" in container_config,
        "metricsSignal": "metrics" in container_config,
        "logsSignal": "logs" in container_config,
    }
