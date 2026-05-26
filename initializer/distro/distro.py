from opentelemetry.instrumentation.distro import BaseDistro
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from importlib.metadata import EntryPoint
from .instrumentation_registry import add_instrumented_library
from .newrelic_compat import apply_newrelic_asgi_compat


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
        # Patch OTel's ASGI middleware so it doesn't trip on New Relic's
        # Starlette/FastAPI wrapping. No-op when NR is not present.
        # Must run before load_instrumentor() so the patched class is in
        # place by the time the FastAPI/Starlette instrumentors construct
        # OpenTelemetryMiddleware instances.
        apply_newrelic_asgi_compat()

    def load_instrumentor(self, entry_point: EntryPoint, **kwargs) -> None:
        instrumentor: BaseInstrumentor = entry_point.load()
        instance = instrumentor()
        instance.instrument(**kwargs)

        # Later we can add more details here, like the version of the library, etc.
        instrumentation_details = {
            "is_standard_lib": entry_point.name in STANDARD_LIB_MODULES
        }

        add_instrumented_library(entry_point.name, instrumentation_details)

