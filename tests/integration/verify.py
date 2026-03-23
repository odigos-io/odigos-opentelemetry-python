#!/usr/bin/env python3
"""
Verify integration test traces.

Reads the OTLP JSON lines produced by the OTel Collector file exporter and
asserts that:
  1. At least one span was received.
  2. Every expected service sent spans.
  3. No spans carry an ERROR status.
  4. Every service emitted spans from its expected instrumentation scopes.
  5. All HTTP server spans returned HTTP 200.
"""

import argparse
import json
import sys
import os


# Per-service instrumentation scopes that must appear in the traces.
# Each entry maps a service name to the list of OTel scope names we expect
# to see at least one span from.
EXPECTED_SCOPES = {
    # Original apps
    "flask-app": [
        "opentelemetry.instrumentation.flask",
        "opentelemetry.instrumentation.jinja2",
    ],
    "django-app": [
        "opentelemetry.instrumentation.django",
    ],
    "pythongunicorn": [
        "opentelemetry.instrumentation.starlette",
    ],
    "sqlalchemy-app": [
        "opentelemetry.instrumentation.starlette",
        "opentelemetry.instrumentation.sqlalchemy",
        "opentelemetry.instrumentation.sqlite3",
    ],
    # Tier 1: Web frameworks
    "fastapi-app": [
        "opentelemetry.instrumentation.fastapi",
    ],
    "tornado-app": [
        "opentelemetry.instrumentation.tornado",
    ],
    "falcon-app": [
        "opentelemetry.instrumentation.falcon",
    ],
    "pyramid-app": [
        "opentelemetry.instrumentation.pyramid.callbacks",
    ],
    "aiohttp-server-app": [
        "opentelemetry.instrumentation.aiohttp_server",
    ],
    # Tier 2: HTTP clients
    "http-clients-app": [
        "opentelemetry.instrumentation.requests",
        "opentelemetry.instrumentation.urllib",
        "opentelemetry.instrumentation.urllib3",
        "opentelemetry.instrumentation.httpx",
        "opentelemetry.instrumentation.aiohttp_client",
    ],
    # Tier 4: Database clients
    "redis-app": [
        "opentelemetry.instrumentation.redis",
    ],
    "postgres-app": [
        "opentelemetry.instrumentation.psycopg2",
        "opentelemetry.instrumentation.asyncpg",
        "opentelemetry.instrumentation.psycopg",
        "opentelemetry.instrumentation.aiopg",
    ],
    "mysql-app": [
        "opentelemetry.instrumentation.pymysql",
    ],
    "mongo-app": [
        "opentelemetry.instrumentation.pymongo",
    ],
    "memcached-app": [
        "opentelemetry.instrumentation.pymemcache",
    ],
    "elasticsearch-app": [
        "elasticsearch-api",
    ],
}

# OTLP span kind: 2 = SERVER
KIND_SERVER = 2


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_resource_spans(traces_file):
    """Parse OTLP JSON lines into a flat list of resourceSpans objects."""
    if not os.path.exists(traces_file):
        print(f"FAIL: Traces file not found: {traces_file}")
        sys.exit(1)

    resource_spans = []
    with open(traces_file) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"WARN: Skipping malformed JSON on line {lineno}: {exc}")
                continue

            for key in ("resourceSpans", "resource_spans"):
                if key in data:
                    resource_spans.extend(data[key])
                    break

    return resource_spans


def _get(obj, *keys):
    """Retrieve a value using the first matching key (camelCase or snake_case)."""
    for key in keys:
        if key in obj:
            return obj[key]
    return None


def _attr_value(attr):
    v = attr.get("value", {})
    return v.get("stringValue") or v.get("string_value") or v.get("intValue") or v.get("int_value")


def _span_attr(span, key):
    for attr in span.get("attributes", []):
        if attr.get("key") == key:
            return _attr_value(attr)
    return None


def extract_service_name(resource_span):
    resource = _get(resource_span, "resource") or {}
    for attr in (_get(resource, "attributes") or []):
        if attr.get("key") == "service.name":
            return _attr_value(attr) or "unknown"
    return "unknown"


def flatten_spans(resource_spans):
    """Return (service_name, scope_name, span) tuples for every span."""
    results = []
    for rs in resource_spans:
        svc = extract_service_name(rs)
        scope_spans_list = _get(rs, "scopeSpans", "scope_spans") or []
        for scope_spans in scope_spans_list:
            scope_name = (scope_spans.get("scope") or {}).get("name", "")
            for span in scope_spans.get("spans", []):
                results.append((svc, scope_name, span))
    return results


# ── Checks ───────────────────────────────────────────────────────────────────

def verify_spans_received(all_spans):
    if not all_spans:
        print("FAIL: No spans received at all")
        return False
    print(f"  OK: {len(all_spans)} span(s) received")
    return True


def verify_expected_services(all_spans, expected):
    seen = {svc for svc, _, _ in all_spans}
    missing = set(expected) - seen
    if missing:
        print(f"FAIL: Missing services: {missing}")
        print(f"  Seen: {seen}")
        return False
    print(f"  OK: All expected services present — {sorted(expected)}")
    if seen - set(expected):
        print(f"  INFO: Additional services seen — {sorted(seen - set(expected))}")
    return True


def verify_no_error_spans(all_spans):
    errors = []
    for svc, _, span in all_spans:
        status = span.get("status", {})
        # OTLP StatusCode 2 = ERROR
        if status.get("code", 0) == 2:
            errors.append(
                f"  - {svc} / {span.get('name', '?')}: "
                f"{status.get('message', '(no message)')}"
            )

    if errors:
        print(f"FAIL: {len(errors)} span(s) with ERROR status:")
        for line in errors[:20]:
            print(line)
        return False
    print("  OK: No error spans")
    return True


def verify_scopes(resource_spans, expected_scopes):
    """Check that each service emitted spans from its expected instrumentation scopes."""
    # Collect which scopes were actually seen per service
    seen: dict[str, set] = {}
    for rs in resource_spans:
        svc = extract_service_name(rs)
        scope_spans_list = _get(rs, "scopeSpans", "scope_spans") or []
        for ss in scope_spans_list:
            scope_name = (ss.get("scope") or {}).get("name", "")
            if scope_name:
                seen.setdefault(svc, set()).add(scope_name)

    ok = True
    for svc, scopes in expected_scopes.items():
        seen_for_svc = seen.get(svc, set())
        missing = [s for s in scopes if s not in seen_for_svc]
        if missing:
            print(f"  FAIL: {svc} — missing scopes: {missing}")
            ok = False
        else:
            print(f"  OK: {svc} — scopes present: {scopes}")
    return ok


def verify_http_success(all_spans):
    """Check that all HTTP server spans have http.status_code = 200."""
    failures = []
    for svc, _, span in all_spans:
        if span.get("kind") != KIND_SERVER:
            continue
        status_code = _span_attr(span, "http.status_code")
        if status_code is None:
            continue  # not an HTTP span
        if str(status_code) != "200":
            failures.append(f"  - {svc} / {span.get('name', '?')} — http.status_code={status_code}")

    if failures:
        print(f"  FAIL: HTTP server spans with non-200 status:")
        for line in failures:
            print(line)
        return False
    print("  OK: All HTTP server spans returned 200")
    return True


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verify integration test traces")
    parser.add_argument("--traces-file", required=True)
    parser.add_argument("--expected-services", nargs="+", required=True)
    args = parser.parse_args()

    print(f"=== Trace verification: {args.traces_file} ===\n")

    resource_spans = load_resource_spans(args.traces_file)
    all_spans = flatten_spans(resource_spans)

    checks = [
        verify_spans_received(all_spans),
        verify_expected_services(all_spans, args.expected_services),
        verify_no_error_spans(all_spans),
        verify_scopes(resource_spans, EXPECTED_SCOPES),
        verify_http_success(all_spans),
    ]

    print()
    if all(checks):
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
