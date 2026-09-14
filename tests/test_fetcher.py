import httpx

from scraper.fetcher import FetchedPage, PageFetcher


class FakeResponse:
    def __init__(self, status_code=200, content_type="text/html", text="<html></html>", url="https://example.com/page"):
        self.status_code = status_code
        self.headers = {"content-type": content_type}
        self.text = text
        self.url = httpx.URL(url)


class FakeClient:
    def __init__(self, response=None, error=None, **kwargs):
        self.response = response
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def get(self, url):
        if self.error is not None:
            raise self.error
        return self.response


def test_fetched_page_ok_for_successful_html():
    page = FetchedPage(
        url="https://example.com",
        status_code=200,
        content_type="text/html",
        html="<html>hello</html>",
    )

    assert page.ok is True


def test_fetched_page_not_ok_without_html():
    page = FetchedPage(
        url="https://example.com",
        status_code=200,
        content_type="text/html",
        html="", 
    )

    assert page.ok is False


def test_fetch_rejects_empty_url():
    fetcher = PageFetcher()

    result = fetcher.fetch("   ")

    assert result.ok is False
    assert result.error == "empty URL"


def test_fetch_rejects_unsupported_url():
    fetcher = PageFetcher()

    result = fetcher.fetch("ftp://example.com/page")

    assert result.ok is False
    assert result.error == "unsupported URL"


def test_fetch_rejects_blocked_by_robots():
    fetcher = PageFetcher()
    fetcher._allowed = lambda url: False

    result = fetcher.fetch("https://example.com/private")

    assert result.ok is False
    assert result.error == "blocked by robots.txt"


def test_fetch_successful_html(monkeypatch):
    response = FakeResponse(
        status_code=200,
        content_type="text/html; charset=utf-8",
        text="<html><body>Hello</body></html>",
    )

    monkeypatch.setattr(
        "scraper.fetcher.httpx.Client",
        lambda **kwargs: FakeClient(response=response, **kwargs),
    )

    fetcher = PageFetcher()
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/page")

    assert result.ok is True
    assert result.status_code == 200
    assert result.content_type == "text/html; charset=utf-8"
    assert result.html == "<html><body>Hello</body></html>"
    assert result.final_url == "https://example.com/page"


def test_fetch_handles_http_error_status(monkeypatch):
    response = FakeResponse(
        status_code=404,
        content_type="text/html",
        text="<html>Not Found</html>",
    )

    monkeypatch.setattr(
        "scraper.fetcher.httpx.Client",
        lambda **kwargs: FakeClient(response=response, **kwargs),
    )

    fetcher = PageFetcher()
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/missing")

    assert result.ok is False
    assert result.status_code == 404
    assert result.error == "HTTP 404"


def test_fetch_rejects_non_html_response(monkeypatch):
    response = FakeResponse(
        status_code=200,
        content_type="application/pdf",
        text="%PDF-1.7",
    )

    monkeypatch.setattr(
        "scraper.fetcher.httpx.Client",
        lambda **kwargs: FakeClient(response=response, **kwargs),
    )

    fetcher = PageFetcher()
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/file.pdf")

    assert result.ok is False
    assert result.error == "not an HTML page"


def test_fetch_handles_timeout(monkeypatch):
    monkeypatch.setattr(
        "scraper.fetcher.httpx.Client",
        lambda **kwargs: FakeClient(error=httpx.TimeoutException("timed out"), **kwargs),
    )

    fetcher = PageFetcher()
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/slow")

    assert result.ok is False
    assert result.error == "request timeout"


def test_fetch_handles_httpx_error(monkeypatch):
    monkeypatch.setattr(
        "scraper.fetcher.httpx.Client",
        lambda **kwargs: FakeClient(error=httpx.ConnectError("connection failed"), **kwargs),
    )

    fetcher = PageFetcher()
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/down")

    assert result.ok is False
    assert result.error.startswith("HTTP error:")

def test_crawl_delay_is_read_from_robots_parser(monkeypatch):
    class FakeRobots:
        def crawl_delay(self, user_agent):
            assert user_agent == "TestBot"
            return 3

    fetcher = PageFetcher(user_agent="TestBot")
    monkeypatch.setattr(fetcher, "_robots_for", lambda url: FakeRobots())

    assert fetcher._crawl_delay_for("https://example.com/page") == 3.0


def test_crawl_delay_does_not_sleep_on_first_request(monkeypatch):
    class FakeRobots:
        def crawl_delay(self, user_agent):
            return 2

    fetcher = PageFetcher()
    monkeypatch.setattr(fetcher, "_robots_for", lambda url: FakeRobots())
    sleeps = []
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr("scraper.fetcher.time.monotonic", lambda: 100.0)

    fetcher._wait_for_crawl_delay("https://example.com/page")

    assert sleeps == []
    assert fetcher._last_request_at["https://example.com"] == 100.0


def test_crawl_delay_sleeps_between_same_origin_requests(monkeypatch):
    class FakeRobots:
        def crawl_delay(self, user_agent):
            return 3

    fetcher = PageFetcher()
    monkeypatch.setattr(fetcher, "_robots_for", lambda url: FakeRobots())
    sleeps = []
    clock = iter([100.0, 101.0, 104.0])
    monkeypatch.setattr("scraper.fetcher.time.monotonic", lambda: next(clock))
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: sleeps.append(seconds))

    fetcher._wait_for_crawl_delay("https://example.com/one")
    fetcher._wait_for_crawl_delay("https://example.com/two")

    assert sleeps == [2.0]
    assert fetcher._last_request_at["https://example.com"] == 104.0


def test_crawl_delay_is_independent_per_origin(monkeypatch):
    class FakeRobots:
        def crawl_delay(self, user_agent):
            return 5

    fetcher = PageFetcher()
    monkeypatch.setattr(fetcher, "_robots_for", lambda url: FakeRobots())
    sleeps = []
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr("scraper.fetcher.time.monotonic", lambda: 100.0)

    fetcher._wait_for_crawl_delay("https://example.com/page")
    fetcher._wait_for_crawl_delay("https://other.example/page")

    assert sleeps == []
    assert set(fetcher._last_request_at) == {"https://example.com", "https://other.example"}

def test_fetch_rejects_when_robots_txt_fails(monkeypatch):
    fetcher = PageFetcher()

    def fail_robots(url):
        raise RuntimeError("robots.txt unavailable: connection failed")

    monkeypatch.setattr(fetcher, "_robots_for", fail_robots)

    result = fetcher.fetch("https://example.com/page")

    assert result.ok is False
    assert result.error == "robots check failed: robots.txt unavailable: connection failed"


def test_robots_failure_is_cached(monkeypatch):
    fetcher = PageFetcher()
    calls = []

    class FakeParser:
        def set_url(self, url):
            self.url = url

        def read(self):
            calls.append(self.url)
            raise RuntimeError("connection failed")

    monkeypatch.setattr("scraper.fetcher.RobotFileParser", FakeParser)

    for _ in range(2):
        result = fetcher.fetch("https://example.com/page")
        assert result.ok is False

    assert calls == ["https://example.com/robots.txt"]
