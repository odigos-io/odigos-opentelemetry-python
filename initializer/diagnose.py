import logging
import os
from typing import Any, Dict, Optional

# log level of the odigos agent itself
ODIGOS_LOG_LEVEL: str = "ODIGOS_LOG_LEVEL"
ODIGOS_LOGGER_NAME: str = "odigos"
# log level of the OpenTelemetry components
OTEL_LOG_LEVEL: str = "OTEL_LOG_LEVEL"
OPENTELEMETRY_LOGGER_NAME: str = "opentelemetry"

# Env var vocabulary: the OpenTelemetry standard log level words (case-insensitive).
_ENV_LEVEL_MAP: Dict[str, Optional[int]] = {
    "ALL": logging.NOTSET,
    "VERBOSE": logging.DEBUG,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "NONE": None,
}

# Remote config vocabulary: log level set sent by the OpAMP server.
# The key is optional so a missing config level (None) resolves to None, which silences the logger.
_CONFIG_LEVEL_MAP: Dict[Optional[str], int] = {
    "error": logging.ERROR,
    "warn": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


def _set_logger_level(logger_name: str, level: Optional[int]) -> None:
    logger = logging.getLogger(logger_name)
    if level is None:
        # No level configured for this logger, so silence it.
        logger.disabled = True
    else:
        logger.disabled = False
        logger.setLevel(level)


def apply_log_levels_from_env() -> None:
    """
    This governs the startup window before the first OpAMP remote config is received.
    An unset or unrecognized value silences the logger.
    """
    _set_logger_level(ODIGOS_LOGGER_NAME, _ENV_LEVEL_MAP.get((os.getenv(ODIGOS_LOG_LEVEL) or "").upper()))
    _set_logger_level(OPENTELEMETRY_LOGGER_NAME, _ENV_LEVEL_MAP.get((os.getenv(OTEL_LOG_LEVEL) or "").upper()))


def apply_log_levels_from_opamp(container_config: Optional[Dict[str, Any]]) -> None:
    """
    Apply the log levels from the OpAMP remote container config.
    The remote config fully overrides the environment variables: a missing level silences the logger rather than falling back to the environment.
    """
    agent_diagnostics: Dict[str, Any] = (container_config or {}).get("agentDiagnostics", {}) or {}
    _set_logger_level(ODIGOS_LOGGER_NAME, _CONFIG_LEVEL_MAP.get(agent_diagnostics.get("odigosLogLevel")))
    _set_logger_level(OPENTELEMETRY_LOGGER_NAME, _CONFIG_LEVEL_MAP.get(agent_diagnostics.get("openTelemetryComponentsLogLevel")))
