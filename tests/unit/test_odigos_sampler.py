import pytest
from initializer.odigos_sampler import OdigosSampler


@pytest.fixture
def sampler():
    return OdigosSampler()


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
