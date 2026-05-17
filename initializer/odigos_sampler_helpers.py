from typing import Mapping, Optional

from opentelemetry.util.types import AttributeValue


def strip_port(host: str) -> str:
    """Remove a trailing :port from a host, leaving bare IPv6 literals untouched."""
    if host.startswith('['):  # bracketed IPv6, optionally followed by :port — "[::1]:8080"
        return host[1:].split(']')[0]
    if host.count(':') == 1:  # "host:port" (hostname or IPv4); bare IPv6 has multiple colons
        return host.split(':')[0]
    return host


def get_attribute(span_attributes: Mapping[str, AttributeValue], *keys: str) -> Optional[str]:
        """Return the first string value found for the given attribute keys.

        Span attribute values can be str/bool/int/float or sequences of those; the HTTP
        semconv keys we look up are always strings, so non-str values are ignored.
        """
        for key in keys:
            value = span_attributes.get(key)
            if isinstance(value, str):
                return value
        return None