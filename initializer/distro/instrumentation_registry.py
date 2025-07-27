
_instrumented = {}

def add_instrumented_library(name, instrumentation_details) -> None:
    _instrumented[name] = instrumentation_details

def get_instrumented_libraries() -> dict:
    return _instrumented
