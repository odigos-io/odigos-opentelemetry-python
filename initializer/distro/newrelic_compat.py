"""Compatibility patches for running Odigos alongside the New Relic Python agent.

Why this module exists
----------------------
When the New Relic Python agent is loaded it wraps Starlette/FastAPI ASGI apps
via ``newrelic.hooks.framework_starlette``. The result is that
``asgiref.compatibility.guarantee_single_callable`` mis-classifies the
NR-wrapped ASGI 3 application as ASGI 2 and routes it through
``asgiref.compatibility.new_application``. When OTel's
``OpenTelemetryMiddleware`` later dispatches a request, that path raises::

    TypeError: 'coroutine' object is not callable

newrelic upstream issue: https://github.com/newrelic/newrelic-python-agent/issues/1136

The patch below skips the asgiref wrapping so the original ASGI 3 app is
kept as-is, avoiding the mis-detection.

* The patch only runs when New Relic is detected.
* All upstream ``__init__`` logic still runs; we only override the final
  ``self.app`` assignment, so excluded_urls / span hooks / etc. are preserved.
* Any failure inside this module is swallowed — compatibility code must never
  crash the customer application.
"""
import os

_NR_ENV_SIGNALS = (
    "NEW_RELIC_CONFIG_FILE",
    "NEW_RELIC_LICENSE_KEY",
    "NEW_RELIC_APP_NAME",
    "NEW_RELIC_ADMIN_COMMAND",
)


def _is_newrelic_present() -> bool:
    """Return True if any signal indicates the New Relic agent is loaded."""
    if any(os.environ.get(k) for k in _NR_ENV_SIGNALS):
        return True
    if "newrelic/bootstrap" in os.environ.get("PYTHONPATH", ""):
        return True
    try:
        import newrelic  # noqa: F401
    except Exception:
        return False
    return True


def apply_newrelic_asgi_compat() -> None:
    """Install the OpenTelemetryMiddleware compatibility patch when needed.

    Safe to call multiple times; the patch is idempotent via a class flag.
    """
    try:
        if not _is_newrelic_present():
            return

        try:
            import opentelemetry.instrumentation.asgi as otel_asgi
        except ImportError:
            return

        middleware_cls = getattr(otel_asgi, "OpenTelemetryMiddleware", None)
        if middleware_cls is None:
            return

        if getattr(middleware_cls, "_odigos_nr_patched", False):
            return

        original_init = middleware_cls.__init__

        def patched_init(self, app, *args, **kwargs):
            # Let OTel build the middleware normally (tracer, hooks, etc.).
            # Internally it does: self.app = guarantee_single_callable(app)
            original_init(self, app, *args, **kwargs)

            # Then overwrite self.app with the user's original app.
            #
            # guarantee_single_callable wraps the app if it looks like
            # legacy ASGI 2. With New Relic in the chain that detection
            # gets fooled and wraps a modern ASGI 3 app — later causing:
            #     TypeError: 'coroutine' object is not callable
            #
            # Modern Starlette/FastAPI apps are ASGI 3, so just keeping
            # the original `app` is correct and avoids the bad wrapper.
            self.app = app

        middleware_cls.__init__ = patched_init
        middleware_cls._odigos_nr_patched = True
    except Exception:
        pass
