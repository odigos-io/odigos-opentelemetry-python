import os

static_env_dict = {
    "OTEL_PYTHON_LOG_CORRELATION": "true",
}

def set_static_otel_env():
    """
    Injects environment variables from a dictionary.
    """
    if not isinstance(static_env_dict, dict):
        raise TypeError("static_env_dict must be a dictionary")

    os.environ.update(static_env_dict)