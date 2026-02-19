#!/usr/bin/env python3
"""
Verify integration test traces.

Reads the OTLP JSON lines produced by the OTel Collector file exporter and
asserts that:
  1. At least one span was received.
  2. Every expected service sent spans.
  3. No spans carry an ERROR status.
"""

import argparse
import json
import sys
import os


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


def extract_service_name(resource_span):
    resource = _get(resource_span, "resource") or {}
    attributes = _get(resource, "attributes") or []
    for attr in attributes:
        if attr.get("key") == "service.name":
            value = attr.get("value", {})
            return (
                value.get("stringValue")
                or value.get("string_value")
                or "unknown"
            )
    return "unknown"


def flatten_spans(resource_spans):
    """Return (service_name, span) tuples for every span in the dataset."""
    results = []
    for rs in resource_spans:
        svc = extract_service_name(rs)
        scope_spans_list = _get(rs, "scopeSpans", "scope_spans") or []
        for scope_spans in scope_spans_list:
            for span in scope_spans.get("spans", []):
                results.append((svc, span))
    return results


def verify_spans_received(all_spans):
    if not all_spans:
        print("FAIL: No spans received at all")
        return False
    print(f"  OK: {len(all_spans)} span(s) received")
    return True


def verify_expected_services(all_spans, expected):
    seen = {svc for svc, _ in all_spans}
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
    for svc, span in all_spans:
        status = span.get("status", {})
        code = status.get("code", 0)
        # OTLP StatusCode 2 = ERROR
        if code == 2:
            errors.append(
                f"  - {svc} / {span.get('name', '?')}: "
                f"{status.get('message', '(no message)')}"
            )

    if errors:
        print(f"FAIL: {len(errors)} span(s) with ERROR status:")
        for line in errors[:20]:
            print(line)
        return False
    print(f"  OK: No error spans")
    return True


def main():
    parser = argparse.ArgumentParser(description="Verify integration test traces")
    parser.add_argument(
        "--traces-file",
        required=True,
        help="Path to the collector's file-exporter output (JSON lines)",
    )
    parser.add_argument(
        "--expected-services",
        nargs="+",
        required=True,
        help="Service names that must appear in traces",
    )
    args = parser.parse_args()

    print(f"=== Trace verification: {args.traces_file} ===\n")

    resource_spans = load_resource_spans(args.traces_file)
    all_spans = flatten_spans(resource_spans)

    checks = [
        verify_spans_received(all_spans),
        verify_expected_services(all_spans, args.expected_services),
        verify_no_error_spans(all_spans),
    ]

    print()
    if all(checks):
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
