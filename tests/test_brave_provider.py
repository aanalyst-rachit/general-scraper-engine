from scraper.providers.brave import BraveSearchProvider


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_brave_provider_maps_web_results(monkeypatch):
    payload = {
        "web": {
            "results": [
                {
                    "title": "Dr. Raj Kumar Clinic",
                    "url": "https://example.com/doctor",
                    "description": "General physician in Shahjahanpur",
                },
                {
                    "title": "City Hospital",
                    "url": "https://example.com/hospital",
                    "description": "Hospital in Shahjahanpur",
                },
            ]
        }
    }
    fake_client = FakeClient(FakeResponse(payload))

    provider = BraveSearchProvider(api_key="test-key", client=fake_client)
    results = provider.search("doctor Shahjahanpur", limit=2)

    assert len(results) == 2
    assert results[0].url == "https://example.com/doctor"
    assert results[0].title == "Dr. Raj Kumar Clinic"
    assert results[0].snippet == "General physician in Shahjahanpur"
    assert results[0].source_name == "brave"
    assert results[1].url == "https://example.com/hospital"

    assert len(fake_client.calls) == 1
    url, kwargs = fake_client.calls[0]
    assert url == "https://api.search.brave.com/res/v1/web/search"
    assert kwargs["headers"]["X-Subscription-Token"] == "test-key"
    assert kwargs["params"]["q"] == "doctor Shahjahanpur"
    assert kwargs["params"]["count"] == 2
    assert kwargs["params"]["country"] == "IN"
    assert kwargs["params"]["search_lang"] == "en"


def test_brave_provider_respects_limit_when_api_returns_more():
    payload = {
        "web": {
            "results": [
                {"title": "One", "url": "https://example.com/1"},
                {"title": "Two", "url": "https://example.com/2"},
                {"title": "Three", "url": "https://example.com/3"},
            ]
        }
    }
    fake_client = FakeClient(FakeResponse(payload))
    provider = BraveSearchProvider(api_key="test-key", client=fake_client)

    results = provider.search("doctor Shahjahanpur", limit=2)

    assert [result.url for result in results] == [
        "https://example.com/1",
        "https://example.com/2",
    ]


def test_brave_provider_ignores_invalid_results():
    payload = {
        "web": {
            "results": [
                {"title": "Missing URL"},
                {"url": ""},
                {"url": "https://example.com/valid", "title": "Valid"},
            ]
        }
    }
    fake_client = FakeClient(FakeResponse(payload))
    provider = BraveSearchProvider(api_key="test-key", client=fake_client)

    results = provider.search("doctor Shahjahanpur", limit=10)

    assert len(results) == 1
    assert results[0].url == "https://example.com/valid"


def test_brave_provider_zero_limit_does_not_call_api():
    fake_client = FakeClient(FakeResponse({}))
    provider = BraveSearchProvider(api_key="test-key", client=fake_client)

    assert provider.search("doctor Shahjahanpur", limit=0) == []
    assert fake_client.calls == []


def test_brave_provider_requires_api_key():
    try:
        BraveSearchProvider(api_key="")
    except ValueError as exc:
        assert str(exc) == "Brave Search API key must not be empty"
    else:
        raise AssertionError("expected ValueError")

def test_provider_reads_api_key_from_environment(monkeypatch):
    from scraper.providers.brave import BraveSearchProvider

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "env-key")

    provider = BraveSearchProvider(client=FakeClient(None))

    assert provider.api_key == "env-key"

def test_brave_provider_accepts_country_and_language_configuration():
    payload = {"web": {"results": []}}
    fake_client = FakeClient(FakeResponse(payload))

    provider = BraveSearchProvider(
        api_key="test-key",
        client=fake_client,
        country="US",
        search_lang="hi",
    )

    provider.search("doctor Shahjahanpur", limit=5)

    _, kwargs = fake_client.calls[0]
    assert kwargs["params"]["country"] == "US"
    assert kwargs["params"]["search_lang"] == "hi"
