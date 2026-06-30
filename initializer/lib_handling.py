from __future__ import annotations

import sys
import importlib
import os
from typing import TYPE_CHECKING, Optional, Sequence

if TYPE_CHECKING:
    from opentelemetry.proto.trace.v1.trace_pb2 import Span as PB2Span
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.trace import Link


def reorder_python_path():
    # Moves '/var/odigos/' [k8s] and '/etc/odigos-vmagent/' [vmagent] paths to end of sys.path
    # to prioritize user dependencies over odigos ones
    paths_to_move = [path for path in sys.path if path.startswith(('/var/odigos/', '/etc/odigos-vmagent/'))]

    for path in paths_to_move:
        sys.path.remove(path)
        sys.path.append(path)


def reload_distro_modules() -> None:
    # Delete distro modules and their sub-modules, as they have been imported before the path was reordered.
    # The distro modules will be re-imported from the new path.
    needed_module_prefixes = [
        'requests',
        'charset_normalizer',
        'certifi',
        'asgiref',
        'idna',
        'deprecated',
        'importlib_metadata',
        'packaging',
        'psutil',
        'zipp',
        'urllib3',
        'uuid_extensions.uuid7',
        'typing_extensions',
    ]

    for module in list(sys.modules):
        if any(module.startswith(prefix) for prefix in needed_module_prefixes):
            module_file = getattr(sys.modules[module], '__file__', None)  # Safely get __file__
            if module_file and ('/etc/odigos-vmagent/' in module_file or '/var/odigos/' in module_file):
                del sys.modules[module]


### Django


# Disables Django instrumentation if DJANGO_SETTINGS_MODULE is unset and adds the current directory to sys.path for proper Django instrumentation.
# These changes address this issue: https://github.com/open-telemetry/opentelemetry-python-contrib/issues/2495.
# TODO: Remove once the bug is fixed.
def handle_django_instrumentation():
    # Get the DJANGO_SETTINGS_MODULE environment variable value.
    django_settings_module = os.getenv('DJANGO_SETTINGS_MODULE', None)

    if django_settings_module is None:
        os.environ.setdefault("OTEL_PYTHON_DJANGO_INSTRUMENT", 'False')

    else:
        cwd_path = os.getcwd()
        if cwd_path not in sys.path:
            sys.path.insert(0, cwd_path)

        # As an additional safeguard, we're ensuring that DJANGO_SETTINGS_MODULE is importable.
        # This is done to prevent instrumentation from being enabled if the Django settings module cannot be imported.
        try:
            importlib.import_module(django_settings_module)
        except Exception:
            os.environ.setdefault("OTEL_PYTHON_DJANGO_INSTRUMENT", 'False')


def patch_otlp_span_flags() -> None:
    # Backport of https://github.com/open-telemetry/opentelemetry-python/pull/4761:
    # include W3C TraceFlags (lower 8 bits, e.g. the sampled bit) in the OTLP Span.flags / Link.flags alongside the existing is-remote bits (8-9).
    # We wrap the encode helpers instead of replacing _span_flags because the PR also changed that function's signature and both of its call sites.
    try:
        from opentelemetry.exporter.otlp.proto.common._internal import trace_encoder
    except ImportError:
        return

    original_encode_span = trace_encoder._encode_span
    original_encode_links = trace_encoder._encode_links

    # W3C TraceFlags is a single byte (values 0-255), and the encoder's existing
    # flags only ever set the higher has-remote / is-remote bits.
    def encode_span(sdk_span: ReadableSpan) -> PB2Span:
        encoded_span = original_encode_span(sdk_span)
        # THE FIX: fold the W3C trace flags into Span.flags (PR #4761).
        encoded_span.flags |= int(sdk_span.get_span_context().trace_flags)
        return encoded_span

    def encode_links(links: Sequence[Link]) -> Optional[Sequence[PB2Span.Link]]:
        encoded_links = original_encode_links(links)
        if encoded_links:
            # Propagate the trace flags to links as well
            for link, encoded_link in zip(links, encoded_links):
                # THE FIX: fold the W3C trace flags into Link.flags (PR #4761).
                encoded_link.flags |= int(link.context.trace_flags)
        return encoded_links

    setattr(trace_encoder, "_encode_span", encode_span)
    setattr(trace_encoder, "_encode_links", encode_links)
    setattr(trace_encoder, "_odigos_trace_flags_patched", True)


def handle_eventlet_instrumentation():
    """Checks if eventlet is importable and applies eventlet.monkey_patch if available."""
    # Apply monkey_patch early to enable Eventlet's green threads for non-blocking I/O.
    # Per Eventlet docs, it must run before imports or class definitions that use patched modules (e.g., socket).
    # https://eventlet.readthedocs.io/en/v0.35.1/patching.html#monkey-patch

    # Currently should run only if no OPAMP client is running, as tested only for the VM agent.
    if os.getenv('DISABLE_OPAMP_CLIENT', 'false').strip().lower() == 'true':
        try:
            eventlet = importlib.import_module("eventlet")
            if not getattr(eventlet, "_opamp_patched", False):  # Avoid multiple patches
                eventlet.monkey_patch()
                setattr(eventlet, "_opamp_patched", True)
        except ImportError:
            pass
