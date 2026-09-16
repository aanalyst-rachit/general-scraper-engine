from scraper.discovery import DiscoveredPage, SearchRequest, WebDiscovery

class FakeProvider:
    def __init__(self, pages):
        self.pages = pages
        self.queries = []

    def search(self, query, limit=20):
        self.queries.append((query, limit))
        return self.pages[:limit]


def test_build_queries_with_location_and_requirements():
    discovery = WebDiscovery()
    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        requirements="female doctor",
    )

    queries = discovery.build_queries(request)

    assert "doctor Shahjahanpur" in queries
    assert "doctor in Shahjahanpur" in queries
    assert "doctor near Shahjahanpur" in queries
    assert "doctor Shahjahanpur contact" in queries
    assert "doctor Shahjahanpur phone" in queries
    assert "doctor Shahjahanpur address" in queries
    assert "doctor Shahjahanpur female doctor" in queries


def test_build_queries_rejects_empty_keyword():
    discovery = WebDiscovery()
    request = SearchRequest(keyword="")

    try:
        discovery.build_queries(request)
    except ValueError as exc:
        assert str(exc) == "keyword must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_discover_deduplicates_urls():
    pages = [
        DiscoveredPage(url="https://example.com/doctor-1"),
        DiscoveredPage(url="https://example.com/doctor-1"),
        DiscoveredPage(url="https://example.com/doctor-2"),
    ]
    provider = FakeProvider(pages)
    discovery = WebDiscovery(providers=[provider])

    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=10,
    )

    results = discovery.discover(request)

    assert [page.url for page in results] == [
        "https://example.com/doctor-1",
        "https://example.com/doctor-2",
    ]


def test_discover_respects_limit():
    pages = [
        DiscoveredPage(url="https://example.com/1"),
        DiscoveredPage(url="https://example.com/2"),
        DiscoveredPage(url="https://example.com/3"),
    ]
    provider = FakeProvider(pages)
    discovery = WebDiscovery(providers=[provider])

    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=2,
    )

    results = discovery.discover(request)

    assert len(results) == 2


def test_discover_zero_limit_returns_empty():
    provider = FakeProvider([])
    discovery = WebDiscovery(providers=[provider])

    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=0,
    )

    assert discovery.discover(request) == []


def test_discover_uses_multiple_providers():
    provider_a = FakeProvider([
        DiscoveredPage(
            url="https://a.example/doctor",
            source_name="A",
        )
    ])
    provider_b = FakeProvider([
        DiscoveredPage(
            url="https://b.example/doctor",
            source_name="B",
        )
    ])

    discovery = WebDiscovery(providers=[provider_a, provider_b])
    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=2,
    )

    results = discovery.discover(request)

    assert len(results) == 2
    assert results[0].source_name == "A"
    assert results[1].source_name == "B"

def test_discover_integrates_with_brave_provider():
    from scraper.providers.brave import BraveSearchProvider

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "web": {
                    "results": [
                        {
                            "title": "Doctor One",
                            "url": "https://example.com/doctor-1",
                            "description": "Doctor in Shahjahanpur",
                        },
                        {
                            "title": "Doctor Two",
                            "url": "https://example.com/doctor-2",
                            "description": "Doctor in Shahjahanpur",
                        },
                    ]
                }
            }

    class FakeClient:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return FakeResponse()

    client = FakeClient()
    provider = BraveSearchProvider(api_key="test-key", client=client)
    discovery = WebDiscovery(providers=[provider])

    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=3,
    )

    results = discovery.discover(request)

    assert len(results) == 2
    assert [page.url for page in results] == [
        "https://example.com/doctor-1",
        "https://example.com/doctor-2",
    ]
    assert all(page.source_name == "brave" for page in results)
    assert len(client.calls) >= 1


def test_discover_deduplicates_results_across_provider_queries():
    from scraper.providers.brave import BraveSearchProvider

    class FakeResponse:
        def __init__(self, call_number):
            self.call_number = call_number

        def raise_for_status(self):
            pass

        def json(self):
            if self.call_number == 1:
                urls = [
                    "https://example.com/shared",
                    "https://example.com/doctor-1",
                ]
            else:
                urls = [
                    "https://example.com/shared",
                    "https://example.com/doctor-2",
                ]

            return {
                "web": {
                    "results": [
                        {"title": url, "url": url}
                        for url in urls
                    ]
                }
            }

    class FakeClient:
        def __init__(self):
            self.call_number = 0

        def get(self, url, **kwargs):
            self.call_number += 1
            return FakeResponse(self.call_number)

    provider = BraveSearchProvider(
        api_key="test-key",
        client=FakeClient(),
    )
    discovery = WebDiscovery(providers=[provider])

    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=4,
    )

    results = discovery.discover(request)

    assert [page.url for page in results] == [
        "https://example.com/shared",
        "https://example.com/doctor-1",
        "https://example.com/doctor-2",
    ]

def test_discover_integrates_with_searxng_provider():
    from scraper.providers.searxng import SearXNGProvider

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return FakeResponse({
                "results": [
                    {
                        "title": "Doctor One",
                        "url": "https://example.com/doctor-1",
                        "content": "Doctor in Shahjahanpur",
                    },
                    {
                        "title": "Doctor Two",
                        "url": "https://example.com/doctor-2",
                        "content": "Doctor in Shahjahanpur",
                    },
                ]
            })

    client = FakeClient()
    provider = SearXNGProvider(
        base_url="http://127.0.0.1:8080",
        client=client,
    )
    discovery = WebDiscovery(providers=[provider])

    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=2,
    )

    results = discovery.discover(request)

    assert len(results) == 2
    assert [page.url for page in results] == [
        "https://example.com/doctor-1",
        "https://example.com/doctor-2",
    ]
    assert all(page.source_name == "searxng" for page in results)
    assert len(client.calls) >= 1
    assert client.calls[0][0] == "http://127.0.0.1:8080/search"


def test_provider_router_uses_primary_when_results_exist():
    from scraper.discovery import ProviderRouter

    primary = FakeProvider([
        DiscoveredPage(url="https://primary.example/result"),
    ])
    fallback = FakeProvider([
        DiscoveredPage(url="https://fallback.example/result"),
    ])

    router = ProviderRouter(primary, [fallback])

    result = router.search("doctor", limit=5)

    assert [page.url for page in result.pages] == [
        "https://primary.example/result"
    ]
    assert result.failure is None
    assert len(primary.queries) == 1
    assert fallback.queries == []


def test_provider_router_falls_back_on_no_results():
    from scraper.discovery import ProviderRouter

    primary = FakeProvider([])
    fallback = FakeProvider([
        DiscoveredPage(url="https://fallback.example/result"),
    ])

    router = ProviderRouter(primary, [fallback])

    result = router.search("doctor", limit=5)

    assert [page.url for page in result.pages] == [
        "https://fallback.example/result"
    ]
    assert result.failure is None
    assert len(primary.queries) == 1
    assert len(fallback.queries) == 1


def test_provider_router_falls_back_on_timeout():
    from scraper.discovery import ProviderRouter

    class TimeoutProvider:
        def search(self, query, limit=20):
            raise TimeoutError("provider timeout")

    fallback = FakeProvider([
        DiscoveredPage(url="https://fallback.example/result"),
    ])

    result = ProviderRouter(
        TimeoutProvider(),
        [fallback],
    ).search("doctor", limit=5)

    assert len(result.pages) == 1
    assert result.pages[0].source_name == ""
    assert result.failure is None


def test_provider_router_categorizes_final_failure():
    from scraper.discovery import ProviderFailureCategory, ProviderRouter

    class AuthProvider:
        def search(self, query, limit=20):
            raise PermissionError("authentication failed")

    result = ProviderRouter(AuthProvider()).search("doctor", limit=5)

    assert result.pages == []
    assert result.failure == ProviderFailureCategory.AUTH


def test_web_discovery_supports_primary_and_explicit_fallbacks():
    primary = FakeProvider([])
    fallback = FakeProvider([
        DiscoveredPage(
            url="https://fallback.example/doctor",
            source_name="fallback",
        )
    ])

    discovery = WebDiscovery(
        primary_provider=primary,
        fallback_providers=[fallback],
    )

    results = discovery.discover(
        SearchRequest(
            keyword="doctor",
            location="Shahjahanpur",
            limit=1,
        )
    )

    assert len(results) == 1
    assert results[0].source_name == "fallback"
    assert discovery.providers == [primary, fallback]


def test_provider_router_categorizes_http_timeout():
    import httpx
    from scraper.discovery import ProviderFailureCategory, ProviderRouter

    class TimeoutProvider:
        def search(self, query, limit=20):
            request = httpx.Request("GET", "https://example.com")
            raise httpx.TimeoutException("timed out", request=request)

    result = ProviderRouter(TimeoutProvider()).search("doctor")

    assert result.failure == ProviderFailureCategory.TIMEOUT


def test_provider_router_categorizes_http_auth_failure():
    import httpx
    from scraper.discovery import ProviderFailureCategory, ProviderRouter

    class AuthProvider:
        def search(self, query, limit=20):
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(401, request=request)
            raise httpx.HTTPStatusError(
                "unauthorized",
                request=request,
                response=response,
            )

    result = ProviderRouter(AuthProvider()).search("doctor")

    assert result.failure == ProviderFailureCategory.AUTH


def test_provider_router_categorizes_rate_limit():
    import httpx
    from scraper.discovery import ProviderFailureCategory, ProviderRouter

    class RateLimitedProvider:
        def search(self, query, limit=20):
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError(
                "rate limited",
                request=request,
                response=response,
            )

    result = ProviderRouter(RateLimitedProvider()).search("doctor")

    assert result.failure == ProviderFailureCategory.RATE_LIMIT


def test_provider_router_categorizes_server_error():
    import httpx
    from scraper.discovery import ProviderFailureCategory, ProviderRouter

    class ServerProvider:
        def search(self, query, limit=20):
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError(
                "server unavailable",
                request=request,
                response=response,
            )

    result = ProviderRouter(ServerProvider()).search("doctor")

    assert result.failure == ProviderFailureCategory.SERVER_ERROR


def test_provider_router_categorizes_request_error():
    import httpx
    from scraper.discovery import ProviderFailureCategory, ProviderRouter

    class RequestErrorProvider:
        def search(self, query, limit=20):
            request = httpx.Request("GET", "https://example.com")
            raise httpx.ConnectError("connection failed", request=request)

    result = ProviderRouter(RequestErrorProvider()).search("doctor")

    assert result.failure == ProviderFailureCategory.SERVER_ERROR


def test_provider_router_categorizes_invalid_response():
    from scraper.discovery import ProviderFailureCategory, ProviderRouter

    class InvalidProvider:
        def search(self, query, limit=20):
            raise ValueError("invalid JSON response")

    result = ProviderRouter(InvalidProvider()).search("doctor")

    assert result.failure == ProviderFailureCategory.INVALID_RESPONSE


def test_provider_router_falls_back_after_http_rate_limit():
    import httpx
    from scraper.discovery import ProviderRouter

    class RateLimitedProvider:
        def search(self, query, limit=20):
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError(
                "rate limited",
                request=request,
                response=response,
            )

    fallback = FakeProvider([
        DiscoveredPage(url="https://fallback.example/result"),
    ])

    result = ProviderRouter(
        RateLimitedProvider(),
        [fallback],
    ).search("doctor", limit=5)

    assert len(result.pages) == 1
    assert fallback.queries == [("doctor", 5)]
    assert result.failure is None


def test_quality_policy_accepts_relevant_results():
    from scraper.discovery import DiscoveryQualityPolicy

    policy = DiscoveryQualityPolicy(
        keyword="doctor",
        location="Shahjahanpur",
    )

    pages = [
        DiscoveredPage(
            url="https://example.com/doctor",
            title="Doctor Shahjahanpur",
            snippet="Medical doctor in Shahjahanpur",
        )
    ]

    assert policy.acceptable(pages)


def test_quality_policy_rejects_irrelevant_results():
    from scraper.discovery import DiscoveryQualityPolicy

    policy = DiscoveryQualityPolicy(
        keyword="doctor",
        location="Shahjahanpur",
    )

    pages = [
        DiscoveredPage(
            url="https://example.com/weather",
            title="Shahjahanpur Weather",
            snippet="Latest weather forecast",
        )
    ]

    assert not policy.acceptable(pages)


def test_quality_policy_respects_minimum_results():
    from scraper.discovery import DiscoveryQualityPolicy

    policy = DiscoveryQualityPolicy(
        keyword="doctor",
        minimum_results=2,
    )

    pages = [
        DiscoveredPage(
            url="https://example.com/doctor",
            title="Doctor",
        )
    ]

    assert not policy.acceptable(pages)


def test_provider_router_uses_fallback_for_low_quality_results():
    from scraper.discovery import DiscoveryQualityPolicy, ProviderRouter

    primary = FakeProvider([
        DiscoveredPage(
            url="https://primary.example/weather",
            title="Shahjahanpur Weather",
            snippet="Forecast",
        )
    ])
    fallback = FakeProvider([
        DiscoveredPage(
            url="https://fallback.example/doctor",
            title="Doctor Shahjahanpur",
            snippet="Doctor in Shahjahanpur",
        )
    ])

    policy = DiscoveryQualityPolicy(
        keyword="doctor",
        location="Shahjahanpur",
    )

    result = ProviderRouter(
        primary,
        [fallback],
    ).search(
        "doctor Shahjahanpur",
        limit=5,
        quality_policy=policy,
    )

    assert [page.url for page in result.pages] == [
        "https://fallback.example/doctor"
    ]
    assert result.failure is None
    assert len(primary.queries) == 1
    assert len(fallback.queries) == 1


def test_provider_router_quality_rejection_is_not_reported_as_failure():
    from scraper.discovery import DiscoveryQualityPolicy, ProviderRouter

    primary = FakeProvider([
        DiscoveredPage(
            url="https://primary.example/weather",
            title="Weather",
        )
    ])

    policy = DiscoveryQualityPolicy(keyword="doctor")

    result = ProviderRouter(primary).search(
        "doctor",
        quality_policy=policy,
    )

    assert result.pages == []
    assert result.failure is None


def test_web_discovery_quality_policy_uses_request_fields():
    primary = FakeProvider([
        DiscoveredPage(
            url="https://primary.example/weather",
            title="Shahjahanpur Weather",
        )
    ])
    fallback = FakeProvider([
        DiscoveredPage(
            url="https://fallback.example/doctor",
            title="Female Doctor Shahjahanpur",
            snippet="Female doctor in Shahjahanpur",
        )
    ])

    from scraper.discovery import DiscoveryQualityPolicy

    discovery = WebDiscovery(
        primary_provider=primary,
        fallback_providers=[fallback],
        quality_policy=DiscoveryQualityPolicy(
            keyword="doctor",
            location="Shahjahanpur",
            requirements="female doctor",
        ),
    )

    results = discovery.discover(
        SearchRequest(
            keyword="doctor",
            location="Shahjahanpur",
            requirements="female doctor",
            limit=1,
        )
    )

    assert [page.url for page in results] == [
        "https://fallback.example/doctor"
    ]


def test_web_discovery_router_does_not_repeat_provider_chain():
    primary = FakeProvider([])
    fallback = FakeProvider([
        DiscoveredPage(
            url="https://fallback.example/doctor",
            title="Doctor",
        )
    ])

    discovery = WebDiscovery(
        primary_provider=primary,
        fallback_providers=[fallback],
    )

    results = discovery.discover(
        SearchRequest(
            keyword="doctor",
            location="Shahjahanpur",
            limit=2,
        )
    )

    assert [page.url for page in results] == [
        "https://fallback.example/doctor",
    ]
    assert len(primary.queries) == 6
    assert len(fallback.queries) == 6


def test_provider_router_categorizes_no_results():
    from scraper.discovery import ProviderFailureCategory, ProviderRouter

    result = ProviderRouter(FakeProvider([])).search("doctor")

    assert result.pages == []
    assert result.failure == ProviderFailureCategory.NO_RESULTS


def test_provider_router_falls_back_after_timeout():
    from scraper.discovery import ProviderRouter
    class TimeoutProvider:
        def search(self, query, limit=20):
            raise TimeoutError("provider timeout")

    fallback = FakeProvider([
        DiscoveredPage(url="https://fallback.example/result"),
    ])

    result = ProviderRouter(
        TimeoutProvider(),
        [fallback],
    ).search("doctor", limit=5)

    assert len(result.pages) == 1
    assert fallback.queries == [("doctor", 5)]
    assert result.failure is None


def test_provider_router_falls_back_after_auth_failure():
    from scraper.discovery import ProviderRouter
    class AuthProvider:
        def search(self, query, limit=20):
            raise PermissionError("authentication failed")

    fallback = FakeProvider([
        DiscoveredPage(url="https://fallback.example/result"),
    ])

    result = ProviderRouter(
        AuthProvider(),
        [fallback],
    ).search("doctor", limit=5)

    assert len(result.pages) == 1
    assert fallback.queries == [("doctor", 5)]
    assert result.failure is None


def test_provider_router_falls_back_after_server_error():
    from scraper.discovery import ProviderRouter
    import httpx

    class ServerProvider:
        def search(self, query, limit=20):
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError(
                "server unavailable",
                request=request,
                response=response,
            )

    fallback = FakeProvider([
        DiscoveredPage(url="https://fallback.example/result"),
    ])

    result = ProviderRouter(
        ServerProvider(),
        [fallback],
    ).search("doctor", limit=5)

    assert len(result.pages) == 1
    assert fallback.queries == [("doctor", 5)]
    assert result.failure is None


def test_provider_router_falls_back_after_invalid_response():
    from scraper.discovery import ProviderRouter
    class InvalidProvider:
        def search(self, query, limit=20):
            raise ValueError("invalid JSON response")

    fallback = FakeProvider([
        DiscoveredPage(url="https://fallback.example/result"),
    ])

    result = ProviderRouter(
        InvalidProvider(),
        [fallback],
    ).search("doctor", limit=5)

    assert len(result.pages) == 1
    assert fallback.queries == [("doctor", 5)]
    assert result.failure is None


def test_provider_router_falls_back_after_unexpected_exception():
    from scraper.discovery import ProviderRouter
    class BrokenProvider:
        def search(self, query, limit=20):
            raise RuntimeError("unexpected provider failure")

    fallback = FakeProvider([
        DiscoveredPage(url="https://fallback.example/result"),
    ])

    result = ProviderRouter(
        BrokenProvider(),
        [fallback],
    ).search("doctor", limit=5)

    assert len(result.pages) == 1
    assert fallback.queries == [("doctor", 5)]
    assert result.failure is None
