from scraper.acquisition import ExternalFetchRequest
from scraper.fetcher import FetchedPage
from scraper.providers.firecrawl import FirecrawlProvider


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

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_firecrawl_provider_maps_html_response():
    payload = {
        "success": True,
        "data": {
            "html": "<html><body>Firecrawl content</body></html>",
            "metadata": {
                "url": "https://example.com/final",
            },
        },
    }
    fake_client = FakeClient(FakeResponse(payload))

    provider = FirecrawlProvider(api_key="test-key", client=fake_client)
    page = provider.fetch(ExternalFetchRequest("https://example.com"))

    assert isinstance(page, FetchedPage)
    assert page.url == "https://example.com"
    assert page.final_url == "https://example.com/final"
    assert page.status_code == 200
    assert page.content_type == "text/html"
    assert page.html == "<html><body>Firecrawl content</body></html>"
    assert page.error == ""

    assert len(fake_client.calls) == 1
    url, kwargs = fake_client.calls[0]
    assert url == "https://api.firecrawl.dev/v2/scrape"
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert kwargs["headers"]["Accept"] == "application/json"
    assert kwargs["json"]["url"] == "https://example.com"
    assert kwargs["json"]["formats"] == ["html"]


def test_firecrawl_provider_maps_timeout_to_milliseconds():
    fake_client = FakeClient(
        FakeResponse(
            {
                "data": {
                    "html": "<html>ok</html>",
                }
            }
        )
    )
    provider = FirecrawlProvider(api_key="test-key", client=fake_client)

    provider.fetch(
        ExternalFetchRequest(
            "https://example.com",
            timeout=12.5,
        )
    )

    _, kwargs = fake_client.calls[0]
    assert kwargs["json"]["timeout"] == 12500


def test_firecrawl_provider_requires_api_key():
    try:
        FirecrawlProvider(api_key="")
    except ValueError as exc:
        assert str(exc) == "Firecrawl API key must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_firecrawl_provider_reads_api_key_from_environment(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "env-key")

    provider = FirecrawlProvider(client=FakeClient(None))

    assert provider.api_key == "env-key"


def test_firecrawl_provider_returns_error_for_http_failure():
    fake_client = FakeClient(FakeResponse({}, status_code=500))
    provider = FirecrawlProvider(api_key="test-key", client=fake_client)

    page = provider.fetch(ExternalFetchRequest("https://example.com"))

    assert page.url == "https://example.com"
    assert page.html == ""
    assert page.error == "HTTP 500"


def test_firecrawl_provider_returns_error_for_missing_data():
    fake_client = FakeClient(FakeResponse({"success": True}))
    provider = FirecrawlProvider(api_key="test-key", client=fake_client)

    page = provider.fetch(ExternalFetchRequest("https://example.com"))

    assert page.error == "Firecrawl response does not contain page data"


def test_firecrawl_provider_returns_error_for_empty_html():
    fake_client = FakeClient(
        FakeResponse(
            {
                "data": {
                    "html": "",
                    "metadata": {
                        "url": "https://example.com/final",
                    },
                }
            }
        )
    )
    provider = FirecrawlProvider(api_key="test-key", client=fake_client)

    page = provider.fetch(ExternalFetchRequest("https://example.com"))

    assert page.final_url == "https://example.com/final"
    assert page.error == "Firecrawl returned empty HTML"


def test_firecrawl_provider_rejects_empty_url_without_calling_api():
    fake_client = FakeClient(FakeResponse({}))
    provider = FirecrawlProvider(api_key="test-key", client=fake_client)

    page = provider.fetch(ExternalFetchRequest("   "))

    assert page.url == "   "
    assert page.error == "URL must not be empty"
    assert fake_client.calls == []


def test_firecrawl_provider_converts_unexpected_client_errors_to_fetch_error():
    class BrokenClient:
        def post(self, url, **kwargs):
            raise RuntimeError("connection failed")

    provider = FirecrawlProvider(api_key="test-key", client=BrokenClient())

    page = provider.fetch(ExternalFetchRequest("https://example.com"))

    assert page.error == "connection failed"
