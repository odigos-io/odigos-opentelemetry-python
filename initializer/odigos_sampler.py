import logging
from threading import Lock
from typing import Any, Mapping, Optional, Sequence

from opentelemetry.context import Context
from opentelemetry.sdk.trace.sampling import Decision, Sampler, SamplingResult, _get_parent_trace_state
from opentelemetry.semconv.attributes import http_attributes as http_attributes_semconv
from opentelemetry.semconv.attributes import server_attributes as server_attributes_semconv
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from initializer.schemas.sampling import (
    HeadSamplingConfig,
    HeadSamplingHttpClientOperationMatcher,
    HeadSamplingHttpServerOperationMatcher,
    HeadSamplingOperationMatcher,
    NoisyOperation,
)

# Setup the Sampler logger
sampler_logger = logging.getLogger('odigos')


class OdigosSampler(Sampler):
    # For compatibility with 64 bit trace IDs, the sampler checks the 64
    # low-order bits of the trace ID to decide whether to sample a given trace.
    TRACE_ID_LIMIT = (1 << 64) - 1

    def __init__(self):
        self._lock = Lock()
        self._config: Optional[HeadSamplingConfig] = None

    def _trace_id_based_sampling(self, trace_id: int, percentage_to_sample: float) -> bool:
        """Mimic OpenTelemetry's trace ID-based sampling logic with 64-bit range."""
        # Since percentage to sample is in percents and we need a fraction, divide by 100
        fraction = percentage_to_sample / 100

        # Calculate the bound based on the fraction using OpenTelemetry's approach
        bound = round(fraction * (self.TRACE_ID_LIMIT + 1))
        # Apply the TRACE_ID_LIMIT mask to ensure 64-bit range and compare it to the bound
        return (trace_id & self.TRACE_ID_LIMIT) < bound

    def should_sample(
        self,
        parent_context: Optional[Context],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Attributes = None,
        links: Optional[Sequence["Link"]] = None,
        trace_state: Optional[TraceState] = None,
    ) -> "SamplingResult":
        attributes = attributes or {}
        with self._lock:
            # sampler_logger.debug(f'Running Should_sample a span with the following attributes: {attributes}')

            if self._config is None:
                # sampler_logger.debug('No configuration is set, returning RECORD_AND_SAMPLE')
                return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=_get_parent_trace_state(parent_context))

            noisy_operations: list[NoisyOperation] = self._config.get('noisyOperations', [])
            # Track the rule with the lowest percentageAtMost so the tracestate entry reports the actual deciding rule's id (first-wins on ties)
            winning_operation: Optional[NoisyOperation] = None

            for noisy_operation in noisy_operations:
                if noisy_operation.get("disabled"):
                    continue

                percentage_to_sample: float = noisy_operation.get("percentageAtMost", 0.0)

                http_operation_sample: Optional[HeadSamplingOperationMatcher] = noisy_operation.get("operation")

                # sampler_logger.debug(f'Evaluating noisy operation: {noisy_operation}')

                # No operation matcher -> rule applies workload-wide (matches every span)
                # This supports Sampling rules that scope by sourceScopes (workload) without specific HTTP matcher
                if not http_operation_sample:
                    matched = True
                else:  # When we have a granular operation, check it vs the server/client rules specified in the noisy operation
                    matched = False
                    if http_server_sample := http_operation_sample.get("httpServer"):
                        matched = self._match_http_server_sample_rule(http_server_sample, attributes) or matched

                    if http_client_sample := http_operation_sample.get("httpClient"):
                        matched = self._match_http_client_sample_rule(http_client_sample, attributes) or matched

                # sampler_logger.debug(f'Noisy operation matched: {matched}, percentage: {percentage_to_sample}')
                if matched and (winning_operation is None or percentage_to_sample < winning_operation.get("percentageAtMost", 0.0)):
                    winning_operation = noisy_operation

            if winning_operation is not None:
                # Build tracestate from the winning rule and attach it to both decisions.
                # Even on DROP the SpanContext (and its trace_state) is propagated to downstream services via the tracestate header,
                # enabling consistent head-sampling and tail-sampler decisions across the trace.
                lowest_percentage = winning_operation.get("percentageAtMost", 0.0)
                trace_state = self.build_tracestate(parent_context, winning_operation)
                if self._trace_id_based_sampling(trace_id, lowest_percentage):
                    # sampler_logger.debug(f'Trace [{trace_id}] is sampled with lowest percentage {lowest_percentage}')
                    return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=trace_state)
                else:
                    # sampler_logger.debug(f'Trace [{trace_id}] is dropped with lowest percentage {lowest_percentage}')
                    return SamplingResult(Decision.DROP, trace_state=trace_state)

            # sampler_logger.debug('No noisy operation matched, sampling the trace')
            return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=_get_parent_trace_state(parent_context))

    @staticmethod
    def _get_attribute(span_attributes: Mapping[str, Any], *keys: str):
        """Return the first non-None value found for the given attribute keys."""
        for key in keys:
            value = span_attributes.get(key)
            if value is not None:
                return value
        return None

    def _match_http_server_sample_rule(self, http_server_rule: HeadSamplingHttpServerOperationMatcher, span_attributes: Mapping[str, Any]) -> bool:
        """
        Try to match all the http server's attributes to the definitions of the noisy action
        """
        span_route = span_attributes.get(http_attributes_semconv.HTTP_ROUTE)
        # Old semconv: "http.method" → new semconv: "http.request.method"
        span_method = self._get_attribute(span_attributes, http_attributes_semconv.HTTP_REQUEST_METHOD, "http.method")

        # Some instrumentations send target instead of route
        target = self._get_attribute(span_attributes, "http.target", "url.path")

        if http_server_rule.get("route") and http_server_rule["route"] != span_route:
            # If we have route in the span attributes, evaluate it first (use template matching
            # since param names may differ, e.g. /grml/{grml_id} vs /grml/{path_param})
            if span_route:
                return self._match_rule_route_to_span(http_server_rule["route"], span_route)
            # If we have target, try to match it with the route in the sampling rule
            if target:
                return self._match_rule_route_to_span(http_server_rule["route"], target)

        if http_server_rule.get("routePrefix") and not (span_route or "").startswith(http_server_rule["routePrefix"]):
            return False
        if http_server_rule.get("method") and http_server_rule["method"] != span_method:
            return False

        return True

    def _match_http_client_sample_rule(self, http_client_rule: HeadSamplingHttpClientOperationMatcher, span_attributes: Mapping[str, Any]) -> bool:
        """
        Try to match all the http client's attributes to the definitions of the noisy action
        """
        # Old semconv: "net.peer.name" / "http.host" → new semconv: "server.address"
        server_address = self._get_attribute(span_attributes, server_attributes_semconv.SERVER_ADDRESS, "net.peer.name", "http.host")
        url_template = span_attributes.get("url.template")
        # Old semconv: "http.method" → new semconv: "http.request.method"
        method = self._get_attribute(span_attributes, http_attributes_semconv.HTTP_REQUEST_METHOD, "http.method")

        if http_client_rule.get("serverAddress") and http_client_rule["serverAddress"] != server_address:
            return False
        if http_client_rule.get("templatedPath") and http_client_rule["templatedPath"] != url_template:
            return False
        if http_client_rule.get("templatedPathPrefix") and not (url_template or "").startswith(http_client_rule["templatedPathPrefix"]):
            return False
        if http_client_rule.get("method") and http_client_rule["method"] != method:
            return False

        return True

    def _match_rule_route_to_span(self, rule_route: str, span_value: str) -> bool:
        """
        Match a sampling rule route (e.g. /item/{id}) against a span value, which can be either
        a templated route (e.g. /item/{item_id}) or a full URL target (e.g. /item/123?param=hello).
        Path param segments ({...}) in the rule are treated as wildcards.
        """
        span_value = span_value.split('?')[0]
        rule_parts = [part for part in rule_route.split('/') if part]
        span_parts = [part for part in span_value.split('/') if part]

        if len(rule_parts) != len(span_parts):
            return False

        # Traverse both rule and span segments
        for i in range(len(rule_parts)):
            # If we hit a path param in the rule, it matches any span segment
            if rule_parts[i].startswith('{'):
                continue
            if rule_parts[i] != span_parts[i]:
                return False

        return True

    def get_description(self):
        return "OdigosSampler"

    def update_config(self, new_config):
        with self._lock:
            # sampler_logger.debug(f'Updating the configuration with the new configuration: {new_config}')
            self._config = new_config

    def build_tracestate(self, parent_context: Optional[Context], noisy_operation: NoisyOperation) -> TraceState:
        tracestate = _get_parent_trace_state(parent_context)

        if not tracestate:
            tracestate = TraceState()

        # Round percentage to 2 decimal places for byte-identical tracestate values
        percentage = round(noisy_operation.get("percentageAtMost", 0.0), 2)
        noisy_op_tracestate_value = f"c:n;dr.p:{percentage};dr.id:{noisy_operation['id']}"
        tracestate = tracestate.add("odigos", noisy_op_tracestate_value)

        return tracestate
