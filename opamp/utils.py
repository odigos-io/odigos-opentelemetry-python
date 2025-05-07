import json
import logging

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


def parse_first_message_to_resource_attributes(sdk_config, logger: logging.Logger) -> dict: # type: ignore
    '''
    Parses remote resource attributes from the SDK config.
    '''

    remote_resource_attributes = sdk_config.get('remoteResourceAttributes', [])

    if not remote_resource_attributes:
        # logger.error('missing "remoteResourceAttributes" section in OpAMP server remote config on first server to agent message')
        return {}

    return {item['key']: item['value'] for item in remote_resource_attributes}

def parse_first_message_signals(sdk_config, logger: logging.Logger): # type: ignore
    """
    Parses the trace, logs, and metrics signals configuration from the SDK config.
    """

    return {
        "traceSignal": sdk_config.get("traceSignal", {}).get("enabled", False),
        "metricsSignal": sdk_config.get("metricsSignal", {}).get("enabled", False),
        "logsSignal": sdk_config.get("logsSignal", {}).get("enabled", False),
    }
