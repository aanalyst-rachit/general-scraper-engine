from scraper.acquisition import ExternalFetchRequest
from scraper.fetcher import FetchedPage
from scraper.providers.scrapingdog import ScrapingdogProvider


class FakeResponse:
    def __init__(self, text="", status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_scrapingdog_provider_maps_html_response():
    fake_client = FakeClient(
        FakeResponse(
            "<html><body>Scrapingdog content</body></html>",
            headers={"content-type": "text/html"},
        )
    )

    provider = ScrapingdogProvider(
        api_key="test-key",
        client=fake_client,
    )

    page = provider.fetch(
        ExternalFetchRequest("https://example.com")
    )

    assert isinstance(page, FetchedPage)
    assert page.url == "https://example.com"
    assert page.final_url == "https://example.com"
    assert page.status_code == 200
    assert page.content_type == "text/html"
    assert page.html == "<html><body>Scrapingdog content</body></html>"
    assert page.error == ""

    url, kwargs = fake_client.calls[0]

    assert url == "https://api.scrapingdog.com/scrape"
    assert kwargs["params"]["api_key"] == "test-key"
    assert kwargs["params"]["url"] == "https://example.com"
    assert "dynamic" not in kwargs["params"]


def test_scrapingdog_provider_maps_render_to_dynamic():
    fake_client = FakeClient(
        FakeResponse("<html><body>rendered</body></html>")
    )

    provider = ScrapingdogProvider(
        api_key="test-key",
        client=fake_client,
    )

    provider.fetch(
        ExternalFetchRequest(
            "https://example.com",
            render=True,
        )
    )

    _, kwargs = fake_client.calls[0]

    assert kwargs["params"]["dynamic"] == "true"


def test_scrapingdog_provider_does_not_invent_timeout_query_parameter():
    fake_client = FakeClient(
        FakeResponse("<html>ok</html>")
    )

    provider = ScrapingdogProvider(
        api_key="test-key",
        client=fake_client,
    )

    provider.fetch(
        ExternalFetchRequest(
            "https://example.com",
            timeout=12.5,
        )
    )

    _, kwargs = fake_client.calls[0]

    assert "timeout" not in kwargs["params"]


def test_scrapingdog_provider_requires_api_key():
    try:
        ScrapingdogProvider(api_key="")
    except ValueError as exc:
        assert str(exc) == "Scrapingdog API key must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_scrapingdog_provider_reads_api_key_from_environment(monkeypatch):
    monkeypatch.setenv("SCRAPINGDOG_API_KEY", "env-key")

    provider = ScrapingdogProvider(
        client=FakeClient(FakeResponse())
    )

    assert provider.api_key == "env-key"


def test_scrapingdog_provider_returns_error_for_http_failure():
    fake_client = FakeClient(
        FakeResponse(status_code=500)
    )

    provider = ScrapingdogProvider(
        api_key="test-key",
        client=fake_client,
    )

    page = provider.fetch(
        ExternalFetchRequest("https://example.com")
    )

    assert page.url == "https://example.com"
    assert page.html == ""
    assert page.error == "HTTP 500"


def test_scrapingdog_provider_returns_error_for_empty_content():
    fake_client = FakeClient(
        FakeResponse(
            "",
            headers={"content-type": "text/html"},
        )
    )

    provider = ScrapingdogProvider(
        api_key="test-key",
        client=fake_client,
    )

    page = provider.fetch(
        ExternalFetchRequest("https://example.com")
    )

    assert page.status_code == 200
    assert page.content_type == "text/html"
    assert page.error == "Scrapingdog returned empty content"


def test_scrapingdog_provider_rejects_empty_url_without_calling_api():
    fake_client = FakeClient(FakeResponse())

    provider = ScrapingdogProvider(
        api_key="test-key",
        client=fake_client,
    )

    page = provider.fetch(
        ExternalFetchRequest("   ")
    )

    assert page.url == "   "
    assert page.error == "URL must not be empty"
    assert fake_client.calls == []


def test_scrapingdog_provider_converts_unexpected_client_errors_to_fetch_error():
    class BrokenClient:
        def get(self, url, **kwargs):
            raise RuntimeError("connection failed")

    provider = ScrapingdogProvider(
        api_key="test-key",
        client=BrokenClient(),
    )

    page = provider.fetch(
        ExternalFetchRequest("https://example.com")
    )

    assert page.error == "connection failed"
