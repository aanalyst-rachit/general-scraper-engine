from __future__ import annotations

import httpx
import pytest

from scraper.providers.searxng import SearXNGProvider


class FakeClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, "kwargs": kwargs})
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request, json=self.payload)


def test_search_maps_results():
    payload = {
        "results": [
            {
                "url": "https://example.com/doctor",
                "title": "Dr. Example",
                "content": "Doctor in Shahjahanpur",
            },
            {
                "url": "https://example.org/clinic",
                "title": "Example Clinic",
                "content": "Medical clinic",
            },
        ]
    }
    client = FakeClient(payload)
    provider = SearXNGProvider(base_url="http://127.0.0.1:8080", client=client)

    results = provider.search("doctor Shahjahanpur", limit=10)

    assert len(results) == 2
    assert results[0].url == "https://example.com/doctor"
    assert results[0].title == "Dr. Example"
    assert results[0].snippet == "Doctor in Shahjahanpur"
    assert results[0].source_name == "searxng"

    assert client.calls[0]["url"] == "http://127.0.0.1:8080/search"
    assert client.calls[0]["kwargs"]["params"]["q"] == "doctor Shahjahanpur"
    assert client.calls[0]["kwargs"]["params"]["format"] == "json"


def test_search_respects_limit():
    payload = {
        "results": [
            {"url": f"https://example.com/{index}"}
            for index in range(5)
        ]
    }
    client = FakeClient(payload)
    provider = SearXNGProvider(client=client)

    results = provider.search("doctor", limit=2)

    assert len(results) == 2
    assert client.calls[0]["kwargs"]["params"]["pageno"] == 1


def test_search_ignores_duplicate_urls():
    payload = {
        "results": [
            {"url": "https://example.com/a"},
            {"url": "https://example.com/a"},
            {"url": "https://example.com/b"},
        ]
    }
    client = FakeClient(payload)
    provider = SearXNGProvider(client=client)

    results = provider.search("doctor", limit=10)

    assert [result.url for result in results] == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_search_empty_query_returns_empty():
    client = FakeClient({"results": []})
    provider = SearXNGProvider(client=client)

    assert provider.search("   ", limit=10) == []
    assert client.calls == []


def test_search_non_positive_limit_returns_empty():
    client = FakeClient({"results": []})
    provider = SearXNGProvider(client=client)

    assert provider.search("doctor", limit=0) == []
    assert client.calls == []


def test_provider_requires_base_url():
    with pytest.raises(ValueError, match="base_url"):
        SearXNGProvider(base_url="")


def test_provider_normalizes_base_url():
    client = FakeClient({"results": []})
    provider = SearXNGProvider(base_url="http://127.0.0.1:8080/", client=client)

    provider.search("doctor", limit=1)

    assert client.calls[0]["url"] == "http://127.0.0.1:8080/search"
