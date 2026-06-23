import logging

from .diagnose import ODIGOS_LOGGER_NAME, OPENTELEMETRY_LOGGER_NAME, apply_log_levels_from_env


# This is the main odigos-opentelemetry-python logger setup function.
# It is used by all modules within this package to ensure that all logs are captured by the same logger.
#
# Each controlled logger gets its own console handler and does not propagate to the root logger.
def setup_logging():
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    for logger_name in (ODIGOS_LOGGER_NAME, OPENTELEMETRY_LOGGER_NAME):
        logger = logging.getLogger(logger_name)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False  # Prevent logs from reaching the root logger
        logger.disabled = True

    # Apply the diagnostics log levels from environment variables for the startup window, before the first OpAMP remote config.
    apply_log_levels_from_env()


setup_logging()
