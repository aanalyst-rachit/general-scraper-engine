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
