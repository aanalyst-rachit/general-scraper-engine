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


def test_concurrent_fetches_enforce_robots_policy(monkeypatch):
    import threading

    fetcher = PageFetcher()
    calls = []
    lock = threading.Lock()

    def blocked(url):
        return False

    fetcher._allowed = blocked

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url):
            with lock:
                calls.append(url)
            raise AssertionError("blocked request reached HTTP client")

    monkeypatch.setattr("scraper.fetcher.httpx.Client", Client)

    results = []

    def fetch(index):
        results.append(fetcher.fetch(f"https://example.com/private-{index}"))

    threads = [threading.Thread(target=fetch, args=(index,)) for index in range(4)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert len(results) == 4
    assert all(result.error == "blocked by robots.txt" for result in results)
    assert calls == []


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

def test_request_delay_does_not_sleep_on_first_request(monkeypatch):
    fetcher = PageFetcher(request_delay=2)
    monkeypatch.setattr(fetcher, "_crawl_delay_for", lambda url: None)
    sleeps = []
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr("scraper.fetcher.time.monotonic", lambda: 100.0)

    fetcher._wait_for_request_delay("https://example.com/page")

    assert sleeps == []
    assert fetcher._last_request_at["https://example.com"] == 100.0


def test_request_delay_sleeps_between_same_origin_requests(monkeypatch):
    fetcher = PageFetcher(request_delay=3)
    monkeypatch.setattr(fetcher, "_crawl_delay_for", lambda url: None)
    sleeps = []
    clock = iter([100.0, 101.0, 103.0])
    monkeypatch.setattr("scraper.fetcher.time.monotonic", lambda: next(clock))
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: sleeps.append(seconds))

    fetcher._wait_for_request_delay("https://example.com/one")
    fetcher._wait_for_request_delay("https://example.com/two")

    assert sleeps == [2.0]
    assert fetcher._last_request_at["https://example.com"] == 103.0


def test_request_delay_is_independent_per_origin(monkeypatch):
    fetcher = PageFetcher(request_delay=4)
    monkeypatch.setattr(fetcher, "_crawl_delay_for", lambda url: None)
    sleeps = []
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr("scraper.fetcher.time.monotonic", lambda: 100.0)

    fetcher._wait_for_request_delay("https://example.com/page")
    fetcher._wait_for_request_delay("https://other.example/page")

    assert sleeps == []
    assert set(fetcher._last_request_at) == {"https://example.com", "https://other.example"}


def test_request_delay_uses_larger_of_configured_and_crawl_delay(monkeypatch):
    fetcher = PageFetcher(request_delay=5)
    monkeypatch.setattr(fetcher, "_crawl_delay_for", lambda url: 2.0)
    sleeps = []
    clock = iter([100.0, 101.0, 105.0])
    monkeypatch.setattr("scraper.fetcher.time.monotonic", lambda: next(clock))
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: sleeps.append(seconds))

    fetcher._wait_for_request_delay("https://example.com/one")
    fetcher._wait_for_request_delay("https://example.com/two")

    assert sleeps == [4.0]

def test_per_domain_limit_allows_requests_until_limit(monkeypatch):
    response = FakeResponse()
    monkeypatch.setattr(
        "scraper.fetcher.httpx.Client",
        lambda **kwargs: FakeClient(response=response, **kwargs),
    )

    fetcher = PageFetcher(max_requests_per_domain=2)
    fetcher._allowed = lambda url: True

    first = fetcher.fetch("https://example.com/one")
    second = fetcher.fetch("https://example.com/two")

    assert first.ok is True
    assert second.ok is True
    assert fetcher._domain_request_counts["example.com"] == 2


def test_per_domain_limit_blocks_request_after_limit(monkeypatch):
    response = FakeResponse()
    calls = []

    monkeypatch.setattr(
        "scraper.fetcher.httpx.Client",
        lambda **kwargs: FakeClient(response=response, **kwargs),
    )

    fetcher = PageFetcher(max_requests_per_domain=1)
    fetcher._allowed = lambda url: True

    first = fetcher.fetch("https://example.com/one")
    calls.append(first)
    second = fetcher.fetch("https://example.com/two")
    calls.append(second)

    assert calls[0].ok is True
    assert calls[1].ok is False
    assert calls[1].error == "per-domain request limit reached"
    assert fetcher._domain_request_counts["example.com"] == 1


def test_per_domain_limit_is_independent_per_domain(monkeypatch):
    response = FakeResponse()
    monkeypatch.setattr(
        "scraper.fetcher.httpx.Client",
        lambda **kwargs: FakeClient(response=response, **kwargs),
    )

    fetcher = PageFetcher(max_requests_per_domain=1)
    fetcher._allowed = lambda url: True
    fetcher._crawl_delay_for = lambda url: None

    example = fetcher.fetch("https://example.com/one")
    other = fetcher.fetch("https://other.example/one")

    assert example.ok is True
    assert other.ok is True
    assert fetcher._domain_request_counts == {
        "example.com": 1,
        "other.example": 1,
    }


def test_per_domain_request_limit_is_atomic_across_concurrent_fetches(monkeypatch):
    import threading

    fetcher = PageFetcher(max_requests_per_domain=2)
    fetcher._allowed = lambda url: True

    class Response:
        status_code = 200
        url = "https://example.com/page"
        text = "<html><body>ok</body></html>"

        class Headers:
            def get(self, name, default=""):
                return "text/html"

        headers = Headers()

    started = threading.Event()
    release = threading.Event()

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url):
            started.set()
            release.wait(timeout=2)
            return Response()

    monkeypatch.setattr("scraper.fetcher.httpx.Client", Client)

    results = []

    def fetch():
        results.append(fetcher.fetch("https://example.com/page"))

    threads = [threading.Thread(target=fetch) for _ in range(4)]

    for thread in threads:
        thread.start()

    assert started.wait(timeout=2)
    release.set()

    for thread in threads:
        thread.join()

    assert fetcher._domain_request_counts["example.com"] == 2
    assert sum(result.ok for result in results) == 2
    assert sum(result.error == "per-domain request limit reached" for result in results) == 2


def test_per_domain_limit_does_not_count_robots_block(monkeypatch):
    fetcher = PageFetcher(max_requests_per_domain=1)
    fetcher._allowed = lambda url: False

    result = fetcher.fetch("https://example.com/private")

    assert result.error == "blocked by robots.txt"
    assert fetcher._domain_request_counts == {}


def test_per_domain_limit_does_not_count_invalid_url():
    fetcher = PageFetcher(max_requests_per_domain=1)

    result = fetcher.fetch("ftp://example.com/page")

    assert result.error == "unsupported URL"
    assert fetcher._domain_request_counts == {}


def test_per_domain_limit_zero_blocks_all_requests(monkeypatch):
    fetcher = PageFetcher(max_requests_per_domain=0)
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/page")

    assert result.ok is False
    assert result.error == "per-domain request limit reached"
    assert fetcher._domain_request_counts == {}

def test_retry_recovers_from_timeout(monkeypatch):
    responses = iter([
        httpx.TimeoutException("timed out"),
        FakeResponse(status_code=200, content_type="text/html", text="<html>ok</html>"),
    ])

    class RetryClient(FakeClient):
        def get(self, url):
            response = next(responses)
            if isinstance(response, Exception):
                raise response
            return response

    monkeypatch.setattr("scraper.fetcher.httpx.Client", lambda **kwargs: RetryClient(**kwargs))
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: None)

    fetcher = PageFetcher(max_retries=1, retry_backoff=2)
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/slow")

    assert result.ok is True
    assert result.html == "<html>ok</html>"


def test_retry_retries_http_5xx(monkeypatch):
    responses = iter([
        FakeResponse(status_code=503, content_type="text/html", text="<html>busy</html>"),
        FakeResponse(status_code=200, content_type="text/html", text="<html>ok</html>"),
    ])

    class RetryClient(FakeClient):
        def get(self, url):
            return next(responses)

    monkeypatch.setattr("scraper.fetcher.httpx.Client", lambda **kwargs: RetryClient(**kwargs))
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: None)

    fetcher = PageFetcher(max_retries=1, retry_backoff=1)
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/busy")

    assert result.ok is True
    assert result.status_code == 200


def test_retry_does_not_retry_http_4xx(monkeypatch):
    calls = []
    response = FakeResponse(status_code=404, content_type="text/html", text="<html>missing</html>")

    class NoRetryClient(FakeClient):
        def get(self, url):
            calls.append(url)
            return response

    monkeypatch.setattr("scraper.fetcher.httpx.Client", lambda **kwargs: NoRetryClient(**kwargs))
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: (_ for _ in ()).throw(AssertionError("unexpected retry sleep")))

    fetcher = PageFetcher(max_retries=3, retry_backoff=1)
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/missing")

    assert result.error == "HTTP 404"
    assert calls == ["https://example.com/missing"]


def test_retry_exhaustion_returns_last_error(monkeypatch):
    calls = []

    class FailingClient(FakeClient):
        def get(self, url):
            calls.append(url)
            raise httpx.ConnectError("connection failed")

    monkeypatch.setattr("scraper.fetcher.httpx.Client", lambda **kwargs: FailingClient(**kwargs))
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: None)

    fetcher = PageFetcher(max_retries=2, retry_backoff=1)
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/down")

    assert result.ok is False
    assert result.error.startswith("HTTP error:")
    assert len(calls) == 3


def test_retry_attempts_count_against_domain_limit(monkeypatch):
    calls = []

    class FailingClient(FakeClient):
        def get(self, url):
            calls.append(url)
            raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("scraper.fetcher.httpx.Client", lambda **kwargs: FailingClient(**kwargs))
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda seconds: None)

    fetcher = PageFetcher(max_retries=2, retry_backoff=1, max_requests_per_domain=2)
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/slow")

    assert result.ok is False
    assert result.error == "request timeout"
    assert len(calls) == 2
    assert fetcher._domain_request_counts["example.com"] == 2


def test_fetch_handles_forbidden_403(monkeypatch):
    response = FakeResponse(status_code=403, content_type="text/html", text="<html>Forbidden</html>")

    monkeypatch.setattr(
        "scraper.fetcher.httpx.Client",
        lambda **kwargs: FakeClient(response=response, **kwargs),
    )

    fetcher = PageFetcher(max_retries=3)
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/forbidden")

    assert result.ok is False
    assert result.status_code == 403
    assert result.error == "HTTP 403"


def test_fetch_handles_rate_limited_429(monkeypatch):
    response = FakeResponse(status_code=429, content_type="text/html", text="<html>Too Many Requests</html>")

    monkeypatch.setattr(
        "scraper.fetcher.httpx.Client",
        lambda **kwargs: FakeClient(response=response, **kwargs),
    )

    fetcher = PageFetcher(max_retries=3)
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/rate-limited")

    assert result.ok is False
    assert result.status_code == 429
    assert result.error == "HTTP 429"


def test_fetch_follows_redirect_and_records_final_url(monkeypatch):
    response = FakeResponse(
        status_code=200,
        content_type="text/html",
        text="<html><body>Redirected Page</body></html>",
        url="https://example.com/final",
    )

    captured = {}

    def make_client(**kwargs):
        captured.update(kwargs)
        return FakeClient(response=response, **kwargs)

    monkeypatch.setattr("scraper.fetcher.httpx.Client", make_client)

    fetcher = PageFetcher()
    fetcher._allowed = lambda url: True

    result = fetcher.fetch("https://example.com/start")

    assert captured["follow_redirects"] is True
    assert result.ok is True
    assert result.final_url == "https://example.com/final"


def test_request_delay_is_enforced_across_concurrent_fetches(monkeypatch):
    import threading
    import time

    fetcher = PageFetcher(request_delay=0.05)

    monkeypatch.setattr(
        fetcher,
        "_allowed",
        lambda url: True,
    )

    class Response:
        status_code = 200
        url = "https://example.com/page"
        text = "<html><body>ok</body></html>"

        class Headers:
            def get(self, name, default=""):
                return "text/html"

        headers = Headers()

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url):
            return Response()

    monkeypatch.setattr("scraper.fetcher.httpx.Client", Client)

    request_times = []
    lock = threading.Lock()

    original_wait = fetcher._wait_for_request_delay

    def tracked_wait(url):
        original_wait(url)
        with lock:
            request_times.append(time.monotonic())

    monkeypatch.setattr(fetcher, "_wait_for_request_delay", tracked_wait)

    threads = [
        threading.Thread(
            target=fetcher.fetch,
            args=(f"https://example.com/page-{index}",),
        )
        for index in range(4)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert len(request_times) == 4

    request_times.sort()
    intervals = [
        later - earlier
        for earlier, later in zip(request_times, request_times[1:])
    ]

    assert min(intervals) >= 0.045
