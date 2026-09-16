from scraper.acquisition import FetchRequest, HTTPFetcherAdapter
from scraper.fetcher import FetchedPage, PageFetcher


class StubFetcher:
    def __init__(self):
        self.urls = []

    def fetch(self, url):
        self.urls.append(url)
        return FetchedPage(
            url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            html="<html><body>ok</body></html>",
        )


def test_fetch_request_is_immutable():
    request = FetchRequest("https://example.com")

    assert request.url == "https://example.com"


def test_http_fetcher_adapter_delegates_to_existing_fetcher():
    fetcher = StubFetcher()
    adapter = HTTPFetcherAdapter(fetcher)

    page = adapter.fetch(FetchRequest("https://example.com"))

    assert fetcher.urls == ["https://example.com"]
    assert isinstance(page, FetchedPage)
    assert page.url == "https://example.com"
    assert page.status_code == 200
    assert page.html == "<html><body>ok</body></html>"


def test_http_fetcher_adapter_accepts_existing_page_fetcher():
    fetcher = PageFetcher()
    adapter = HTTPFetcherAdapter(fetcher)

    assert adapter.fetcher is fetcher


def test_auto_fetcher_returns_http_page_when_content_is_valid():
    from scraper.acquisition import AutoFetcher

    http_page = FetchedPage(
        url="https://example.com/page",
        final_url="https://example.com/page",
        status_code=200,
        content_type="text/html",
        html="<html><body><p>Useful content with enough text here.</p></body></html>",
    )

    class HTTP:
        def fetch(self, url):
            return http_page

    class Browser:
        def __init__(self):
            self.calls = []

        def fetch(self, request):
            self.calls.append(request.url)
            return FetchedPage(
                url=request.url,
                status_code=200,
                html="<html><body>browser</body></html>",
            )

    browser = Browser()
    result = AutoFetcher(
        http_fetcher=HTTP(),
        browser_fetcher=browser,
    ).fetch(FetchRequest(http_page.url))

    assert result == http_page
    assert browser.calls == []


def test_auto_fetcher_falls_back_for_js_shell():
    from scraper.acquisition import AutoFetcher

    url = "https://example.com/app"

    class HTTP:
        def fetch(self, requested_url):
            return FetchedPage(
                url=requested_url,
                final_url=requested_url,
                status_code=200,
                content_type="text/html",
                html=(
                    "<html><body><div id=\"root\"></div>"
                    "<script src=\"/app.js\"></script></body></html>"
                ),
            )

    class Browser:
        def __init__(self):
            self.calls = []

        def fetch(self, request):
            self.calls.append(request.url)
            return FetchedPage(
                url=request.url,
                final_url=request.url,
                status_code=200,
                content_type="text/html",
                html="<html><body><p>Rendered browser content.</p></body></html>",
            )

    browser = Browser()
    result = AutoFetcher(
        http_fetcher=HTTP(),
        browser_fetcher=browser,
    ).fetch(FetchRequest(url))

    assert result.html == "<html><body><p>Rendered browser content.</p></body></html>"
    assert browser.calls == [url]


def test_auto_fetcher_does_not_fallback_http_errors():
    from scraper.acquisition import AutoFetcher

    url = "https://example.com/broken"

    class HTTP:
        def fetch(self, requested_url):
            return FetchedPage(
                url=requested_url,
                status_code=500,
                content_type="text/html",
                error="HTTP 500",
            )

    class Browser:
        def __init__(self):
            self.calls = []

        def fetch(self, request):
            self.calls.append(request.url)
            raise AssertionError("browser fallback must not run for HTTP errors")

    browser = Browser()
    result = AutoFetcher(
        http_fetcher=HTTP(),
        browser_fetcher=browser,
    ).fetch(FetchRequest(url))

    assert result.status_code == 500
    assert result.error == "HTTP 500"
    assert browser.calls == []


def test_auto_fetcher_does_not_fallback_block_pages():
    from scraper.acquisition import AutoFetcher

    url = "https://example.com/blocked"

    class HTTP:
        def fetch(self, requested_url):
            return FetchedPage(
                url=requested_url,
                final_url=requested_url,
                status_code=200,
                content_type="text/html",
                html=(
                    "<html><body><h1>Access Denied</h1>"
                    "<p>Verify you are human.</p></body></html>"
                ),
            )

    class Browser:
        def fetch(self, request):
            raise AssertionError("browser fallback must not run for block pages")

    result = AutoFetcher(
        http_fetcher=HTTP(),
        browser_fetcher=Browser(),
    ).fetch(FetchRequest(url))

    assert result.status_code == 200
    assert "Access Denied" in result.html


def test_cached_fetcher_caches_successful_acquisition(tmp_path):
    from scraper.acquisition import CachedFetcher
    from scraper.cache.fetch import FetchCache

    class Acquisition:
        def __init__(self):
            self.calls = []

        def fetch(self, request):
            self.calls.append(request.url)
            return FetchedPage(
                url=request.url,
                final_url=request.url,
                status_code=200,
                content_type="text/html",
                html="<html><body>cached</body></html>",
            )

    acquisition = Acquisition()

    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        fetcher = CachedFetcher(acquisition, cache)

        first = fetcher.fetch(FetchRequest("https://example.com/page"))
        second = fetcher.fetch(FetchRequest("https://example.com/page"))

        assert first.html == "<html><body>cached</body></html>"
        assert second.html == first.html
        assert acquisition.calls == ["https://example.com/page"]


def test_cached_fetcher_does_not_cache_failed_page(tmp_path):
    from scraper.acquisition import CachedFetcher
    from scraper.cache.fetch import FetchCache

    class Acquisition:
        def __init__(self):
            self.calls = 0

        def fetch(self, request):
            self.calls += 1
            return FetchedPage(
                url=request.url,
                status_code=500,
                content_type="text/html",
                error="HTTP 500",
            )

    acquisition = Acquisition()

    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        fetcher = CachedFetcher(acquisition, cache)

        first = fetcher.fetch(FetchRequest("https://example.com/error"))
        second = fetcher.fetch(FetchRequest("https://example.com/error"))

        assert first.status_code == 500
        assert second.status_code == 500
        assert acquisition.calls == 2


def test_cached_fetcher_does_not_cache_empty_page(tmp_path):
    from scraper.acquisition import CachedFetcher
    from scraper.cache.fetch import FetchCache

    class Acquisition:
        def __init__(self):
            self.calls = 0

        def fetch(self, request):
            self.calls += 1
            return FetchedPage(
                url=request.url,
                final_url=request.url,
                status_code=200,
                content_type="text/html",
                html="",
            )

    acquisition = Acquisition()

    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        fetcher = CachedFetcher(acquisition, cache)

        fetcher.fetch(FetchRequest("https://example.com/empty"))
        fetcher.fetch(FetchRequest("https://example.com/empty"))

        assert acquisition.calls == 2


def test_cached_fetcher_separates_acquisition_strategies(tmp_path):
    from scraper.acquisition import CachedFetcher
    from scraper.cache.fetch import FetchCache

    class Acquisition:
        def __init__(self, html):
            self.html = html
            self.calls = 0

        def fetch(self, request):
            self.calls += 1
            return FetchedPage(
                url=request.url,
                final_url=request.url,
                status_code=200,
                content_type="text/html",
                html=self.html,
            )

    http = Acquisition("<html><body>http</body></html>")
    browser = Acquisition("<html><body>browser</body></html>")

    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        http_fetcher = CachedFetcher(http, cache, acquisition_strategy="http")
        browser_fetcher = CachedFetcher(
            browser,
            cache,
            acquisition_strategy="browser",
        )

        http_result = http_fetcher.fetch(FetchRequest("https://example.com/app"))
        browser_result = browser_fetcher.fetch(
            FetchRequest("https://example.com/app")
        )

        assert http_result.html == "<html><body>http</body></html>"
        assert browser_result.html == "<html><body>browser</body></html>"
        assert http.calls == 1
        assert browser.calls == 1
