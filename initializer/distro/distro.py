from opentelemetry.instrumentation.distro import BaseDistro
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from importlib.metadata import EntryPoint
from .instrumentation_registry import add_instrumented_library


# These modules are instrumented by OpenTelemetry as part of the Python standard library.
# Even if they are not explicitly imported by the user, they will appear as instrumented.
# Telemetry data will only be produced if the application actually uses them at runtime.
# We mark them with `is_standard_lib = True` to distinguish them from user-added libraries.
STANDARD_LIB_MODULES = {
    "asyncio",
    "sqlite3",
    "logging",
    "threading",
    "urllib",
}


class OdigosDistro(BaseDistro):
    def _configure(self, **kwargs):
        pass

    def load_instrumentor(self, entry_point: EntryPoint, **kwargs) -> None:
        instrumentor: BaseInstrumentor = entry_point.load()
        instance = instrumentor()
        instance.instrument(**kwargs)

        # Later we can add more details here, like the version of the library, etc.
        instrumentation_details = {
            "is_standard_lib": entry_point.name in STANDARD_LIB_MODULES
        }

        add_instrumented_library(entry_point.name, instrumentation_details)

