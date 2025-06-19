import json

def get_sdk_config(config_map):
    """
    Extracts and parses the SDK configuration from the config map.
    """
    if "SDK" not in config_map:
        return {}

    try:
        return json.loads(config_map["SDK"].body)
    except json.JSONDecodeError:
        return {}



def parse_first_message_signals(sdk_config): # type: ignore
    """
    Parses the trace, logs, and metrics signals configuration from the SDK config.
    """

    return {
        "traceSignal": sdk_config.get("traceSignal", {}).get("enabled", False),
        "metricsSignal": sdk_config.get("metricsSignal", {}).get("enabled", False),
        "logsSignal": sdk_config.get("logsSignal", {}).get("enabled", False),
    }
