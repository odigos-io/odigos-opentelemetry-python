import pytest
from opentelemetry.sdk.trace.sampling import Decision
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    SpanKind,
    TraceFlags,
    TraceState,
    set_span_in_context,
)

from initializer.odigos_sampler import OdigosSampler


@pytest.fixture
def sampler():
    return OdigosSampler()


def _parent_context_with_tracestate(tracestate: TraceState):
    """Build a parent Context whose current span carries the given TraceState."""
    span_context = SpanContext(
        trace_id=0x1234567890ABCDEF1234567890ABCDEF,
        span_id=0x1234567890ABCDEF,
        is_remote=True,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
        trace_state=tracestate,
    )
    return set_span_in_context(NonRecordingSpan(span_context))


@pytest.mark.parametrize(
    "route, target, expected",
    [
        # Exact static match
        ("/buy", "/buy", True),
        ("/api/health", "/api/health", True),
        # Query params stripped from target
        ("/buy", "/buy?source=ad", True),
        ("/buy", "/buy?a=1&b=2", True),
        # Single path param
        ("/item/{id}", "/item/123", True),
        ("/item/{id}", "/item/abc", True),
        ("/item/{id}", "/item/123?q=hello", True),
        # Multiple path params
        ("/api/{version}/{id}", "/api/v1/123", True),
        ("/user/{uid}/order/{oid}", "/user/42/order/99", True),
        # Mixed static and param segments
        ("/api/v1/{id}", "/api/v1/456", True),
        ("/api/v1/{id}/details", "/api/v1/456/details", True),
        # Mismatch on static segment (same length)
        ("/buy", "/sell", False),
        ("/api/v1/{id}", "/api/v2/123", False),
        ("/api/v1/items", "/api/v1/orders", False),
        # Different number of segments — no match
        ("/buy", "/api/buy", False),
        ("/api/v1/items", "/items", False),
        ("/a/b/c", "/b/c", False),
        # Deeper nested paths
        ("/grml/{path_param}", "/grml/falcon-123", True),
        ("/grml/{path_param}", "/grml/falcon-123?grml-query-param=hello", True),
        # Root path
        ("/", "/", True),
        ("/", "/?key=val", True),
    ],
    ids=[
        "exact-single-segment",
        "exact-multi-segment",
        "query-params-single",
        "query-params-multiple",
        "single-param",
        "single-param-alpha",
        "single-param-with-query",
        "multi-param",
        "multi-param-deep",
        "mixed-static-param",
        "mixed-static-param-trailing",
        "mismatch-single-segment",
        "mismatch-version-segment",
        "mismatch-leaf-segment",
        "shorter-route-longer-target",
        "longer-route-shorter-target",
        "prefix-overlap-different-length",
        "nested-with-param",
        "nested-with-param-and-query",
        "root-exact",
        "root-with-query",
    ],
)
def test_match_rule_route_to_span(sampler, route, target, expected):
    assert sampler._match_rule_route_to_span(route, target) == expected


class TestBuildTracestate:
    """Tests for OdigosSampler.build_tracestate (lines 191-200)."""

    def test_adds_odigos_entry_when_no_parent_context(self, sampler):
        noisy_operation = {"id": "op-1", "percentageAtMost": 5.0}

        tracestate = sampler.build_tracestate(parent_context=None, noisy_operation=noisy_operation)

        assert isinstance(tracestate, TraceState)
        assert tracestate.get("odigos") == "c:n;dr.p:5.0;dr.id:op-1"

    def test_adds_odigos_entry_when_parent_has_no_tracestate(self, sampler):
        parent_context = _parent_context_with_tracestate(TraceState())
        noisy_operation = {"id": "op-2", "percentageAtMost": 10.0}

        tracestate = sampler.build_tracestate(parent_context=parent_context, noisy_operation=noisy_operation)

        assert tracestate.get("odigos") == "c:n;dr.p:10.0;dr.id:op-2"

    def test_preserves_parent_entries_and_uses_expected_value_format(self, sampler):
        parent_tracestate = TraceState([("vendor1", "val1"), ("vendor2", "val2")])
        parent_context = _parent_context_with_tracestate(parent_tracestate)
        noisy_operation = {"id": "noisy-route-abc", "percentageAtMost": 0.5}

        tracestate = sampler.build_tracestate(parent_context=parent_context, noisy_operation=noisy_operation)

        # Validates existing vendors don't get removed from the tracestate
        assert tracestate.get("vendor1") == "val1"
        assert tracestate.get("vendor2") == "val2"

        odigos_value = tracestate.get("odigos")
        assert odigos_value is not None
        assert odigos_value.startswith("c:n;")
        assert "dr.p:0.5" in odigos_value
        assert "dr.id:noisy-route-abc" in odigos_value

    def test_percentage_rounded_to_two_decimal_places(self, sampler):
        noisy_operation = {"id": "rounded", "percentageAtMost": 33.33333}

        tracestate = sampler.build_tracestate(parent_context=None, noisy_operation=noisy_operation)

        assert tracestate.get("odigos") == "c:n;dr.p:33.33;dr.id:rounded"


class TestShouldSample:
    """Tests for OdigosSampler.should_sample focused on tracestate attachment and
    winning-rule selection across multiple matching rules."""

    def test_drop_decision_still_attaches_tracestate(self, sampler):
        # percentageAtMost=0 -> _trace_id_based_sampling returns False for any trace_id,
        # so the result is always DROP.
        sampler.update_config(
            {
                "noisyOperations": [
                    {"id": "drop-everything", "percentageAtMost": 0},
                ],
            }
        )

        result = sampler.should_sample(
            parent_context=None,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.decision == Decision.DROP
        assert result.trace_state is not None
        assert result.trace_state.get("odigos") == "c:n;dr.p:0;dr.id:drop-everything"

    def test_winning_rule_is_the_lowest_percentage_when_multiple_match(self, sampler):
        # Two service-rules (no operation) both match every span. The rule with the
        # lower percentageAtMost should be the one reported in tracestate, even when
        # it is not the last entry in the config (regression test for the previous
        # bug where the loop's last noisy_operation was used regardless of the winner).
        sampler.update_config(
            {
                "noisyOperations": [
                    {"id": "winner", "percentageAtMost": 10},
                    {"id": "loser", "percentageAtMost": 50},
                ],
            }
        )

        result = sampler.should_sample(
            parent_context=None,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.trace_state is not None
        odigos_value = result.trace_state.get("odigos")
        assert odigos_value is not None
        assert "dr.id:winner" in odigos_value
        assert "dr.p:10" in odigos_value
        assert "dr.id:loser" not in odigos_value

    def test_no_matching_rule_keeps_parent_tracestate_untouched(self, sampler):
        # Rule has an httpServer matcher that the span does not satisfy (no http.route).
        sampler.update_config(
            {
                "noisyOperations": [
                    {
                        "id": "specific-route",
                        "percentageAtMost": 1,
                        "operation": {"httpServer": {"route": "/never/matches"}},
                    },
                ],
            }
        )

        parent_tracestate = TraceState([("vendor1", "val1")])
        parent_context = _parent_context_with_tracestate(parent_tracestate)

        result = sampler.should_sample(
            parent_context=parent_context,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET /something/else",
            kind=SpanKind.SERVER,
            attributes={"http.route": "/something/else"},
        )

        assert result.decision == Decision.RECORD_AND_SAMPLE
        assert result.trace_state is not None
        assert result.trace_state.get("vendor1") == "val1"
        assert result.trace_state.get("odigos") is None


class TestSpanKindGating:
    """httpServer operations must only match SERVER spans and httpClient only CLIENT
    spans. Regression test for ignoring health-probe rule."""

    # Mirrors the real head-sampling-http-client InstrumentationConfig.
    CONFIG = {
        "noisyOperations": [
            {
                "id": "health",
                "name": "kubelet health probe",
                "percentageAtMost": 0,
                "operation": {"httpServer": {"route": "/healthz", "method": "GET"}},
            },
            {
                "id": "outbound-exact",
                "percentageAtMost": 50,
                "operation": {
                    "httpClient": {
                        "serverAddress": "head-sampling-http-server",
                        "templatedPath": "/http-match/exact/target",
                    }
                },
            },
        ],
    }

    def test_health_server_rule_does_not_decide_client_span(self, sampler):
        sampler.update_config(self.CONFIG)
        # urllib client span: only http.url (no http.route / http.target / url.path).
        result = sampler.should_sample(
            parent_context=None,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET",
            kind=SpanKind.CLIENT,
            attributes={
                "http.method": "GET",
                "http.url": "http://head-sampling-http-server:8080/http-match/exact/target",
                "http.status_code": 200,
            },
        )
        odigos_value = result.trace_state.get("odigos")
        # The client exact rule (50%) must decide, not the 0% health-probe server rule.
        assert "dr.id:outbound-exact" in odigos_value
        assert "dr.p:50" in odigos_value
        assert "dr.id:health" not in odigos_value

    def test_health_server_rule_still_decides_server_probe_span(self, sampler):
        sampler.update_config(self.CONFIG)
        result = sampler.should_sample(
            parent_context=None,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET /healthz",
            kind=SpanKind.SERVER,
            attributes={"http.method": "GET", "http.route": "/healthz"},
        )
        assert "dr.id:health" in result.trace_state.get("odigos")


class TestHttpServerRoutePrefix:
    """routePrefix must match per-segment with wildcard support, not literal startswith,
    so templated routes (e.g. /http-match/tprefix/<tenant_id>/items) match a rule
    routePrefix of /http-match/tprefix/*/items."""

    RULE = {"routePrefix": "/http-match/tprefix/*/items"}

    @pytest.mark.parametrize(
        "route, expected",
        [
            pytest.param("/http-match/tprefix/<tenant_id>/items", True, id="flask-templated"),
            pytest.param("/http-match/tprefix/:tenantId/items", True, id="express-templated"),
            pytest.param("/http-match/tprefix/{tenantId}/items", True, id="spring-templated"),
            pytest.param("/http-match/tprefix/<tenant_id>/items/<item_id>", True, id="deeper-nested"),
            pytest.param("/http-match/tprefix/<tenant_id>/orders", False, id="wrong-suffix"),
            pytest.param("/http-match/exact/target", False, id="unrelated-route"),
        ],
    )
    def test_route_prefix_wildcard_match(self, sampler, route, expected):
        assert sampler._match_http_server_sample_rule(self.RULE, {"http.route": route}) is expected

    def test_literal_prefix_still_matches(self, sampler):
        # Non-wildcard routePrefix must still match deeper concrete routes.
        rule = {"routePrefix": "/http-match/prefix"}
        assert sampler._match_http_server_sample_rule(rule, {"http.route": "/http-match/prefix/segment"}) is True


class TestDryRun:
    """Tests for dry-run mode: spans must NEVER be dropped, but tracestate must
    record the would-be decision as `;dry:t` (kept) or `;dry:f` (dropped).

    Mirrors the contract documented on Go `HeadSamplingConfig.DryRun` and the
    OdigosHeadSampler in opentelemetry-node (`sampler/index.ts`).
    """

    def test_dry_run_does_not_drop_when_would_be_dropped(self, sampler):
        # percentageAtMost=0 -> _trace_id_based_sampling always returns False (would drop).
        # With dryRun=True, we must still record-and-sample, just annotate `;dry:f`.
        sampler.update_config(
            {
                "dryRun": True,
                "noisyOperations": [
                    {"id": "drop-everything", "percentageAtMost": 0},
                ],
            }
        )

        result = sampler.should_sample(
            parent_context=None,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.decision == Decision.RECORD_AND_SAMPLE
        assert result.trace_state is not None
        odigos_value = result.trace_state.get("odigos")
        assert odigos_value is not None
        assert odigos_value.endswith(";dry:f")
        assert "dr.id:drop-everything" in odigos_value

    def test_dry_run_records_dry_t_when_would_be_kept(self, sampler):
        # percentageAtMost=100 -> _trace_id_based_sampling always returns True (would keep).
        sampler.update_config(
            {
                "dryRun": True,
                "noisyOperations": [
                    {"id": "keep-everything", "percentageAtMost": 100},
                ],
            }
        )

        result = sampler.should_sample(
            parent_context=None,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.decision == Decision.RECORD_AND_SAMPLE
        assert result.trace_state is not None
        odigos_value = result.trace_state.get("odigos")
        assert odigos_value is not None
        assert odigos_value.endswith(";dry:t")
        assert "dr.id:keep-everything" in odigos_value

    def test_dry_run_false_still_drops(self, sampler):
        # Sanity check: dryRun explicitly False preserves the original drop behavior.
        sampler.update_config(
            {
                "dryRun": False,
                "noisyOperations": [
                    {"id": "drop-everything", "percentageAtMost": 0},
                ],
            }
        )

        result = sampler.should_sample(
            parent_context=None,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.decision == Decision.DROP
        assert result.trace_state is not None
        odigos_value = result.trace_state.get("odigos")
        assert odigos_value is not None
        assert ";dry:" not in odigos_value

    def test_dry_run_omitted_defaults_to_disabled(self, sampler):
        # When the OpAMP push omits `dryRun` (older servers), treat as disabled:
        # must still drop and must NOT add a `;dry:*` suffix.
        sampler.update_config(
            {
                "noisyOperations": [
                    {"id": "drop-everything", "percentageAtMost": 0},
                ],
            }
        )

        result = sampler.should_sample(
            parent_context=None,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.decision == Decision.DROP
        odigos_value = result.trace_state.get("odigos")
        assert odigos_value is not None
        assert ";dry:" not in odigos_value


class TestRecordMode:
    """Tests for record_mode controlling the not-sampled decision."""

    def test_all_spans_mode_uses_record_only_for_noisy_drop(self):
        s = OdigosSampler()
        s.update_config(
            {
                "spanMetricsMode": "all-spans",
                "noisyOperations": [
                    {"id": "drop-everything", "percentageAtMost": 0},
                ],
            }
        )

        result = s.should_sample(
            parent_context=None,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.decision == Decision.RECORD_ONLY

    def test_default_mode_uses_drop_for_noisy_drop(self):
        s = OdigosSampler()
        s.update_config(
            {
                "noisyOperations": [
                    {"id": "drop-everything", "percentageAtMost": 0},
                ],
            }
        )

        result = s.should_sample(
            parent_context=None,
            trace_id=0x0123456789ABCDEF0123456789ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.decision == Decision.DROP

    def test_parent_not_sampled_drops_by_default(self):
        s = OdigosSampler()
        span_context = SpanContext(
            trace_id=0x1234567890ABCDEF1234567890ABCDEF,
            span_id=0x1234567890ABCDEF,
            is_remote=True,
            trace_flags=TraceFlags(0),
        )
        parent_context = set_span_in_context(NonRecordingSpan(span_context))

        result = s.should_sample(
            parent_context=parent_context,
            trace_id=0x1234567890ABCDEF1234567890ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.decision == Decision.DROP

    def test_parent_not_sampled_records_with_all_spans_mode(self):
        s = OdigosSampler()
        s.update_config({"spanMetricsMode": "all-spans"})
        span_context = SpanContext(
            trace_id=0x1234567890ABCDEF1234567890ABCDEF,
            span_id=0x1234567890ABCDEF,
            is_remote=True,
            trace_flags=TraceFlags(0),
        )
        parent_context = set_span_in_context(NonRecordingSpan(span_context))

        result = s.should_sample(
            parent_context=parent_context,
            trace_id=0x1234567890ABCDEF1234567890ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.decision == Decision.RECORD_ONLY

    def test_parent_sampled_always_records_and_samples(self):
        s = OdigosSampler()
        span_context = SpanContext(
            trace_id=0x1234567890ABCDEF1234567890ABCDEF,
            span_id=0x1234567890ABCDEF,
            is_remote=True,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        parent_context = set_span_in_context(NonRecordingSpan(span_context))

        result = s.should_sample(
            parent_context=parent_context,
            trace_id=0x1234567890ABCDEF1234567890ABCDEF,
            name="GET /anything",
            kind=SpanKind.SERVER,
            attributes={},
        )

        assert result.decision == Decision.RECORD_AND_SAMPLE


class TestHttpClientSemconv:
    """_match_http_client_sample_rule must work across old and new HTTP semconv.

    New semconv: server.address, url.template, url.path, http.request.method.
    Old semconv: net.peer.name / http.host (host[:port]), http.target (path?query),
                 http.url / url.full (full URL), http.method.
    """

    @pytest.mark.parametrize(
        "attributes",
        [
            pytest.param({"server.address": "payments"}, id="new-server.address"),
            pytest.param({"net.peer.name": "payments"}, id="old-net.peer.name"),
            pytest.param({"http.host": "payments"}, id="old-http.host-no-port"),
            pytest.param({"http.host": "payments:8080"}, id="old-http.host-with-port"),
            # urllib emits no host attr; host must be derived from the full URL.
            pytest.param({"url.full": "http://payments:8080/p"}, id="urllib-new-url.full"),
            pytest.param({"http.url": "http://payments:8080/p"}, id="urllib-old-http.url"),
        ],
    )
    def test_server_address_matches_across_semconv(self, sampler, attributes):
        rule = {"serverAddress": "payments"}
        assert sampler._match_http_client_sample_rule(rule, attributes) is True

    def test_urllib_client_matches_server_address_and_path_from_full_url(self, sampler):
        # opentelemetry-instrumentation-urllib sets only the full URL (no server.address,
        # net.peer.name or http.host). Both serverAddress and templatedPath must still match.
        rule = {"serverAddress": "head-sampling-http-server", "templatedPath": "/http-match/exact/target"}
        attributes = {"http.url": "http://head-sampling-http-server:8080/http-match/exact/target"}
        assert sampler._match_http_client_sample_rule(rule, attributes) is True

    @pytest.mark.parametrize(
        "attributes",
        [
            pytest.param({"server.address": "other"}, id="new-mismatch"),
            pytest.param({"http.host": "other:8080"}, id="old-mismatch-with-port"),
            pytest.param({}, id="absent"),
        ],
    )
    def test_server_address_mismatch_across_semconv(self, sampler, attributes):
        rule = {"serverAddress": "payments"}
        assert sampler._match_http_client_sample_rule(rule, attributes) is False

    @pytest.mark.parametrize(
        "attributes",
        [
            pytest.param({"url.template": "/item/{id}"}, id="new-url.template"),
            pytest.param({"url.path": "/item/123"}, id="new-url.path-concrete"),
            pytest.param({"http.target": "/item/123?q=hello"}, id="old-http.target-with-query"),
            pytest.param({"http.url": "http://h:8080/item/123?q=1"}, id="old-http.url-full"),
            pytest.param({"url.full": "https://h/item/abc"}, id="new-url.full"),
        ],
    )
    def test_templated_path_matches_across_semconv(self, sampler, attributes):
        rule = {"templatedPath": "/item/{id}"}
        assert sampler._match_http_client_sample_rule(rule, attributes) is True

    def test_new_semconv_preferred_over_old_in_http_dup_mode(self, sampler):
        # http/dup emits both. url.template (new) must win over http.target (old):
        # the templated path disagrees with the rule, so the rule must NOT match
        # even though the concrete old-semconv path would have.
        rule = {"templatedPath": "/item/{id}"}
        attributes = {"url.template": "/wrong/{id}", "http.target": "/item/123"}
        assert sampler._match_http_client_sample_rule(rule, attributes) is False

    @pytest.mark.parametrize(
        "attributes, expected",
        [
            pytest.param({"url.path": "/api/v1/users"}, True, id="new-prefix-hit"),
            pytest.param({"http.target": "/api/v1/users?x=1"}, True, id="old-prefix-hit"),
            pytest.param({"http.url": "http://h/api/v2/users"}, False, id="old-prefix-miss"),
        ],
    )
    def test_templated_path_prefix_across_semconv(self, sampler, attributes, expected):
        rule = {"templatedPathPrefix": "/api/v1"}
        assert sampler._match_http_client_sample_rule(rule, attributes) is expected

    def test_templated_path_prefix_with_wildcard_segment(self, sampler):
        rule = {"templatedPathPrefix": "/a/*/items"}
        assert sampler._match_http_client_sample_rule(rule, {"url.path": "/a/9/items/extra"}) is True
        assert sampler._match_http_client_sample_rule(rule, {"url.path": "/a/9/orders"}) is False

    @pytest.mark.parametrize(
        "attributes",
        [
            pytest.param({"url.path": "/p", "http.request.method": "GET"}, id="new-http.request.method"),
            pytest.param({"url.path": "/p", "http.method": "GET"}, id="old-http.method"),
        ],
    )
    def test_method_matches_across_semconv(self, sampler, attributes):
        rule = {"templatedPath": "/p", "method": "GET"}
        assert sampler._match_http_client_sample_rule(rule, attributes) is True

    def test_method_mismatch_across_semconv(self, sampler):
        rule = {"templatedPath": "/p", "method": "GET"}
        assert sampler._match_http_client_sample_rule(rule, {"url.path": "/p", "http.method": "POST"}) is False
