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
