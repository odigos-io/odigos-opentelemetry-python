from typing import Mapping, Optional
from urllib.parse import urlsplit

from opentelemetry.util.types import AttributeValue


def strip_port(host: str) -> str:
    parsed = urlsplit(f'//{host}')
    return parsed.hostname or host


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
