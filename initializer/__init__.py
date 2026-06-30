import logging


# This is the main odigos-opentelemetry-python logger setup function.
# It is used by all modules within this package to ensure that all logs are captured by the same logger.
def setup_logging():
    odigos_logger = logging.getLogger('odigos')
    odigos_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    odigos_logger.addHandler(handler)

    odigos_logger.propagate = False  # Prevent logs from reaching the root logger
    odigos_logger.disabled = True  # Comment to enable the logger


setup_logging()
