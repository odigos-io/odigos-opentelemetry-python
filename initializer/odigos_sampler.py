import logging
from threading import Lock
from typing import Mapping, Optional, Sequence
from urllib.parse import urlsplit

from opentelemetry.context import Context
from opentelemetry.sdk.trace.sampling import Decision, Sampler, SamplingResult, _get_parent_trace_state
from opentelemetry.semconv.attributes import http_attributes as http_attributes_semconv
from opentelemetry.semconv.attributes import server_attributes as server_attributes_semconv
from opentelemetry.semconv.attributes import url_attributes as url_attributes_semconv
from opentelemetry.trace import Link, SpanKind, TraceState, get_current_span
from opentelemetry.util.types import Attributes, AttributeValue

from initializer.odigos_sampler_helpers import get_attribute, strip_port
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

    def _not_sampled_decision(self) -> Decision:
        if self._config and self._config.get('spanMetricsMode') == "all-spans":
            return Decision.RECORD_ONLY
        return Decision.DROP

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
            parent_span_context = get_current_span(parent_context).get_span_context()

            # Parent-based logic taken from upstream ParentBased sampler so we can
            # decide to DROP or RECORD_ONLY based on the recordMode configuration.
            # Remote/local parent distinction is removed because both paths used the
            # same not-sampled decision.
            if parent_span_context is not None and parent_span_context.is_valid:
                if parent_span_context.trace_flags.sampled:
                    return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=_get_parent_trace_state(parent_context))
                else:
                    return SamplingResult(self._not_sampled_decision(), trace_state=_get_parent_trace_state(parent_context))
            # sampler_logger.debug(f'Running Should_sample a span with the following attributes: {attributes}')

            if self._config is None:
                # sampler_logger.debug('No configuration is set, returning RECORD_AND_SAMPLE')
                return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=_get_parent_trace_state(parent_context))

            is_dry_run: bool = self._config.get('dryRun', False)
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
                    if (http_server_sample := http_operation_sample.get("httpServer")) and kind == SpanKind.SERVER:
                        matched = self._match_http_server_sample_rule(http_server_sample, attributes) or matched

                    if (http_client_sample := http_operation_sample.get("httpClient")) and kind == SpanKind.CLIENT:
                        matched = self._match_http_client_sample_rule(http_client_sample, attributes) or matched

                # sampler_logger.debug(f'Noisy operation matched: {matched}, percentage: {percentage_to_sample}')
                if matched and (winning_operation is None or percentage_to_sample < winning_operation.get("percentageAtMost", 0.0)):
                    winning_operation = noisy_operation

            if winning_operation is not None:
                # Build tracestate from the winning rule and attach it to both decisions.
                # Even on DROP the SpanContext (and its trace_state) is propagated to downstream services via the tracestate header,
                # enabling consistent head-sampling and tail-sampler decisions across the trace.
                lowest_percentage = winning_operation.get("percentageAtMost", 0.0)
                sampled = self._trace_id_based_sampling(trace_id, lowest_percentage)

                dry_run_sampled = sampled if is_dry_run else None
                trace_state = self.build_tracestate(parent_context, winning_operation, dry_run_sampled)

                # In dry-run mode, never actually drop spans
                if is_dry_run:
                    # sampler_logger.debug(f'Dry run [{trace_id}] would_be_sampled={sampled} (lowest_percentage={lowest_percentage})')
                    return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=trace_state)

                if sampled:
                    # sampler_logger.debug(f'Trace [{trace_id}] is sampled with lowest percentage {lowest_percentage}')
                    return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=trace_state)
                else:
                    # sampler_logger.debug(f'Trace [{trace_id}] is dropped with lowest percentage {lowest_percentage}')
                    return SamplingResult(self._not_sampled_decision(), trace_state=trace_state)

            # sampler_logger.debug('No noisy operation matched, sampling the trace')
            return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=_get_parent_trace_state(parent_context))

    def _match_http_server_sample_rule(
        self, http_server_rule: HeadSamplingHttpServerOperationMatcher, span_attributes: Mapping[str, AttributeValue]
    ) -> bool:
        """
        Try to match all the http server's attributes to the definitions of the noisy action
        """
        raw_route = span_attributes.get(http_attributes_semconv.HTTP_ROUTE)
        span_route: Optional[str] = raw_route if isinstance(raw_route, str) else None
        # Old semconv: "http.method" → new semconv: "http.request.method"
        span_method = get_attribute(span_attributes, http_attributes_semconv.HTTP_REQUEST_METHOD, "http.method")

        # Some instrumentations send target instead of route
        target = get_attribute(span_attributes, "http.target", "url.path")

        if http_server_rule.get("route") and http_server_rule["route"] != span_route:
            # If we have route in the span attributes, evaluate it first (use template matching
            # since param names may differ, e.g. /grml/{grml_id} vs /grml/{path_param})
            if span_route:
                return self._match_rule_route_to_span(http_server_rule["route"], span_route)
            # If we have target, try to match it with the route in the sampling rule
            if target:
                return self._match_rule_route_to_span(http_server_rule["route"], target)

        if route_prefix := http_server_rule.get("routePrefix"):
            candidate = span_route or target
            if not candidate or not self._match_rule_route_to_span(route_prefix, candidate, route_has_prefix=True):
                return False
        if http_server_rule.get("method") and http_server_rule["method"] != span_method:
            return False

        return True

    def _match_http_client_sample_rule(
        self,
        http_client_rule: HeadSamplingHttpClientOperationMatcher,
        span_attributes: Mapping[str, AttributeValue],
    ) -> bool:
        """
        Try to match all the http client's attributes to the definitions of the noisy action
        """
        # Old semconv: "http.host"/"net.peer.name" → new semconv: "server.address"
        server_address = get_attribute(span_attributes, server_attributes_semconv.SERVER_ADDRESS, "net.peer.name", "http.host")
        if server_address:
            server_address = strip_port(server_address)
        else:
            # some instrumentations (like urllib) never puts a host attribute on the span. it sets only method + url, so if we want the host we need to extract it from the full url
            # default (old) semconv mode the full URL is http.url; in stable mode url.full.
            full_url = get_attribute(span_attributes, "url.full", "http.url")
            if full_url:
                server_address = urlsplit(full_url).hostname

        # Old semconv for url is a target that we need to get the client_path from → new semconv: "url.template"/"url.path"
        client_path = get_attribute(span_attributes, "url.template", url_attributes_semconv.URL_PATH)
        if not client_path:
            # Old semconv: "http.target" is a path (may carry a query); "http.url"/"url.full" is a full URL we parse the path out of.
            target = get_attribute(span_attributes, "http.target", "url.full", "http.url")
            client_path = urlsplit(target).path if target else None

        # Old semconv: "http.method" → new semconv: "http.request.method"
        method = get_attribute(span_attributes, http_attributes_semconv.HTTP_REQUEST_METHOD, "http.method")

        if http_client_rule.get("serverAddress") and http_client_rule["serverAddress"] != server_address:
            return False
        templated_path = http_client_rule.get("templatedPath")
        if templated_path and not self._match_rule_route_to_span(templated_path, client_path or ""):
            return False
        templated_path_prefix = http_client_rule.get("templatedPathPrefix")
        if templated_path_prefix and not self._match_rule_route_to_span(templated_path_prefix, client_path or "", route_has_prefix=True):
            return False
        if http_client_rule.get("method") and http_client_rule["method"] != method:
            return False

        return True

    def _match_rule_route_to_span(self, rule_route: str, span_value: str, route_has_prefix: bool = False) -> bool:
        """
        Match a sampling rule route (e.g. /item/{id}) against a span value, which can be either
        a templated route (e.g. /item/{item_id}) or a full URL target (e.g. /item/123?param=hello).
        Wildcard segments ({...}, :name, *) in the rule match any single span segment.
        With prefix=True the span may have extra trailing segments (prefix match).
        """
        span_value = span_value.split('?')[0]
        rule_parts = [part for part in rule_route.split('/') if part]
        span_parts = [part for part in span_value.split('/') if part]

        if route_has_prefix:
            # Prefix match: span may have extra trailing segments, but not fewer.
            if len(span_parts) < len(rule_parts):
                return False
        else:
            # Exact match: segment counts must be identical.
            if len(span_parts) != len(rule_parts):
                return False

        for rule_segment, span_segment in zip(rule_parts, span_parts):
            # Wildcard segment ({text}, :name, *) matches any single span segment
            if rule_segment == '*' or (rule_segment.startswith('{') and rule_segment.endswith('}')) or rule_segment.startswith(':'):
                continue
            if rule_segment != span_segment:
                return False

        return True

    def get_description(self):
        return "OdigosSampler"

    def update_config(self, new_config):
        with self._lock:
            self._config = new_config

    def build_tracestate(
        self,
        parent_context: Optional[Context],
        noisy_operation: NoisyOperation,
        dry_run_sampled: Optional[bool] = None,
    ) -> TraceState:
        tracestate = _get_parent_trace_state(parent_context)

        if not tracestate:
            tracestate = TraceState()

        # Round percentage to 2 decimal places for byte-identical tracestate values
        percentage = round(noisy_operation.get("percentageAtMost", 0.0), 2)
        noisy_op_tracestate_value = f"c:n;dr.p:{percentage};dr.id:{noisy_operation['id']}"

        if dry_run_sampled is not None:
            noisy_op_tracestate_value += ";dry:t" if dry_run_sampled else ";dry:f"
        tracestate = tracestate.add("odigos", noisy_op_tracestate_value)

        return tracestate
