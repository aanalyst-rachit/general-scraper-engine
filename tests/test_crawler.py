from scraper.acquisition import FetchRequest
from scraper.crawler import SiteCrawler
from scraper.fetcher import FetchedPage


class StubAcquisition:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def fetch(self, request: FetchRequest) -> FetchedPage:
        self.calls.append(request.url)
        return self.pages.get(
            request.url,
            FetchedPage(url=request.url, status_code=404, error="missing"),
        )


def page(url, html):
    return FetchedPage(
        url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        html=html,
    )


def test_canonicalize_url_removes_fragment_and_normalizes_path():
    assert SiteCrawler.canonicalize_url(
        "HTTPS://Example.COM/about/#team"
    ) == "https://example.com/about"


def test_canonicalize_url_resolves_relative_url():
    assert SiteCrawler.canonicalize_url(
        "../contact",
        "https://example.com/about/team",
    ) == "https://example.com/contact"


def test_extract_links_resolves_relative_links():
    html = """
    <a href="/about">About</a>
    <a href="contact">Contact</a>
    <a href="https://other.example/page">Other</a>
    """

    assert SiteCrawler.extract_links(
        html,
        "https://example.com/company/",
    ) == [
        "https://example.com/about",
        "https://example.com/company/contact",
        "https://other.example/page",
    ]


def test_crawl_discovers_internal_urls_and_deduplicates():
    acquisition = StubAcquisition(
        {
            "https://example.com/": page(
                "https://example.com/",
                """
                <a href="/about">About</a>
                <a href="/about#team">About again</a>
                <a href="/contact">Contact</a>
                <a href="https://other.example/outside">Outside</a>
                """,
            ),
            "https://example.com/about": page(
                "https://example.com/about",
                "<p>About</p>",
            ),
            "https://example.com/contact": page(
                "https://example.com/contact",
                "<p>Contact</p>",
            ),
        }
    )

    result = SiteCrawler(
        acquisition,
        max_pages=10,
        max_depth=1,
    ).crawl("https://example.com/")

    assert [item.url for item in result.pages] == [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/contact",
    ]
    assert acquisition.calls == [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/contact",
    ]


def test_crawl_respects_max_pages():
    acquisition = StubAcquisition(
        {
            "https://example.com/": page(
                "https://example.com/",
                '<a href="/one">One</a><a href="/two">Two</a>',
            ),
            "https://example.com/one": page(
                "https://example.com/one",
                "<p>One</p>",
            ),
            "https://example.com/two": page(
                "https://example.com/two",
                "<p>Two</p>",
            ),
        }
    )

    result = SiteCrawler(acquisition, max_pages=2, max_depth=1).crawl(
        "https://example.com/"
    )

    assert result.count == 2
    assert len(acquisition.calls) == 2


def test_crawl_respects_max_depth():
    acquisition = StubAcquisition(
        {
            "https://example.com/": page(
                "https://example.com/",
                '<a href="/one">One</a>',
            ),
            "https://example.com/one": page(
                "https://example.com/one",
                '<a href="/two">Two</a>',
            ),
            "https://example.com/two": page(
                "https://example.com/two",
                "<p>Two</p>",
            ),
        }
    )

    result = SiteCrawler(acquisition, max_pages=10, max_depth=1).crawl(
        "https://example.com/"
    )

    assert [item.url for item in result.pages] == [
        "https://example.com/",
        "https://example.com/one",
    ]


def test_crawl_supports_allowed_domains():
    acquisition = StubAcquisition(
        {
            "https://example.com/": page(
                "https://example.com/",
                '<a href="https://allowed.example/page">Allowed</a>'
                '<a href="https://other.example/page">Other</a>',
            ),
            "https://allowed.example/page": page(
                "https://allowed.example/page",
                "<p>Allowed</p>",
            ),
        }
    )

    result = SiteCrawler(
        acquisition,
        max_pages=10,
        max_depth=1,
        allowed_domains={"example.com", "allowed.example"},
    ).crawl("https://example.com/")

    assert [item.url for item in result.pages] == [
        "https://example.com/",
        "https://allowed.example/page",
    ]


def test_crawl_supports_include_and_exclude_patterns():
    acquisition = StubAcquisition(
        {
            "https://example.com/": page(
                "https://example.com/",
                '<a href="/products/a">Product</a>'
                '<a href="/products/private">Private</a>'
                '<a href="/about">About</a>',
            ),
            "https://example.com/products/a": page(
                "https://example.com/products/a",
                "<p>Product</p>",
            ),
        }
    )

    result = SiteCrawler(
        acquisition,
        max_pages=10,
        max_depth=1,
        include_patterns=("https://example.com/products/*",),
        exclude_patterns=("https://example.com/products/private*",),
    ).crawl("https://example.com/")

    assert [item.url for item in result.pages] == [
        "https://example.com/products/a",
    ]

def test_crawl_reuses_acquisition_robots_policy(monkeypatch):
    from scraper.acquisition import HTTPFetcherAdapter
    from scraper.fetcher import PageFetcher

    fetcher = PageFetcher()
    fetcher._allowed = lambda url: False

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url):
            raise AssertionError("robots-blocked request reached HTTP client")

    monkeypatch.setattr("scraper.fetcher.httpx.Client", Client)

    acquisition = HTTPFetcherAdapter(fetcher)

    result = SiteCrawler(
        acquisition,
        max_pages=10,
        max_depth=1,
    ).crawl("https://example.com/private")

    assert result.pages == []
    assert result.discovered_urls == ["https://example.com/private"]

def test_crawl_enforces_global_concurrency_limit():
    import threading
    import time

    from scraper.concurrency import ConcurrencyConfig

    active = 0
    maximum = 0
    lock = threading.Lock()

    class SlowAcquisition:
        def fetch(self, request):
            nonlocal active, maximum

            with lock:
                active += 1
                maximum = max(maximum, active)

            time.sleep(0.03)

            with lock:
                active -= 1

            return page(request.url, "<p>ok</p>")

    class SeedAcquisition:
        def fetch(self, request):
            if request.url == "https://example.com/":
                return page(
                    request.url,
                    "".join(
                        f'<a href="/page-{index}">Page {index}</a>'
                        for index in range(6)
                    ),
                )
            return SlowAcquisition().fetch(request)

    result = SiteCrawler(
        SeedAcquisition(),
        max_pages=7,
        max_depth=1,
        concurrency=ConcurrencyConfig(global_limit=2),
    ).crawl("https://example.com/")

    assert result.count == 7
    assert maximum <= 2
    assert maximum == 2


def test_crawl_enforces_per_domain_concurrency_limit():
    import threading
    import time

    from scraper.concurrency import ConcurrencyConfig

    active = 0
    maximum = 0
    lock = threading.Lock()

    class SlowAcquisition:
        def fetch(self, request):
            nonlocal active, maximum

            with lock:
                active += 1
                maximum = max(maximum, active)

            time.sleep(0.03)

            with lock:
                active -= 1

            return page(request.url, "<p>ok</p>")

    class Acquisition:
        def fetch(self, request):
            if request.url == "https://example.com/":
                return page(
                    request.url,
                    "".join(
                        f'<a href="/page-{index}">Page {index}</a>'
                        for index in range(6)
                    ),
                )
            return SlowAcquisition().fetch(request)

    result = SiteCrawler(
        Acquisition(),
        max_pages=7,
        max_depth=1,
        concurrency=ConcurrencyConfig(
            global_limit=4,
            per_domain_limit=2,
        ),
    ).crawl("https://example.com/")

    assert result.count == 7
    assert maximum <= 2
    assert maximum == 2


def test_crawl_allows_independent_domains_to_run_concurrently():
    import threading
    import time

    from scraper.concurrency import ConcurrencyConfig

    active_by_domain = {}
    maximum_by_domain = {}
    locks = threading.Lock()

    class Acquisition:
        def fetch(self, request):
            from urllib.parse import urlsplit

            domain = urlsplit(request.url).netloc

            with locks:
                active_by_domain[domain] = active_by_domain.get(domain, 0) + 1
                maximum_by_domain[domain] = max(
                    maximum_by_domain.get(domain, 0),
                    active_by_domain[domain],
                )

            time.sleep(0.03)

            with locks:
                active_by_domain[domain] -= 1

            if request.url == "https://example.com/":
                return page(
                    request.url,
                    '<a href="https://one.example/a">A</a>'
                    '<a href="https://two.example/b">B</a>',
                )

            return page(request.url, "<p>ok</p>")

    result = SiteCrawler(
        Acquisition(),
        max_pages=3,
        max_depth=1,
        allowed_domains={
            "example.com",
            "one.example",
            "two.example",
        },
        concurrency=ConcurrencyConfig(
            global_limit=2,
            per_domain_limit=1,
        ),
    ).crawl("https://example.com/")

    assert result.count == 3
    assert maximum_by_domain["one.example"] == 1
    assert maximum_by_domain["two.example"] == 1

def test_crawl_result_can_be_processed_by_existing_parser():
    from scraper.parser import PageParser

    acquisition = StubAcquisition(
        {
            "https://example.com/": page(
                "https://example.com/",
                """
                <html>
                  <head><title>Example Business</title></head>
                  <body>
                    <address>Shahjahanpur, Uttar Pradesh</address>
                    <a href="/about">About</a>
                  </body>
                </html>
                """,
            ),
            "https://example.com/about": page(
                "https://example.com/about",
                "<html><head><title>About</title></head></html>",
            ),
        }
    )

    result = SiteCrawler(
        acquisition,
        max_pages=2,
        max_depth=1,
    ).crawl("https://example.com/")

    lead = PageParser().parse(result.pages[0].page, category="business")

    assert lead is not None
    assert lead.name == "Example Business"
    assert lead.location == "Shahjahanpur, Uttar Pradesh"
    assert lead.source_url == "https://example.com/"

def test_crawler_rejects_invalid_limits():
    import pytest

    acquisition = StubAcquisition({})

    with pytest.raises(ValueError, match="max_pages"):
        SiteCrawler(acquisition, max_pages=0)

    with pytest.raises(ValueError, match="max_depth"):
        SiteCrawler(acquisition, max_depth=-1)


def test_canonicalize_url_preserves_query_and_rejects_non_http():
    assert SiteCrawler.canonicalize_url(
        "HTTPS://Example.COM/search?q=python#results"
    ) == "https://example.com/search?q=python"

    assert SiteCrawler.canonicalize_url("mailto:test@example.com") == ""
    assert SiteCrawler.canonicalize_url("javascript:void(0)") == ""

def test_crawl_never_fetches_beyond_max_pages_budget():
    from scraper.concurrency import ConcurrencyConfig

    acquisition = StubAcquisition(
        {
            "https://example.com/": page(
                "https://example.com/",
                "".join(
                    f'<a href="/products/{index}">Product {index}</a>'
                    for index in range(6)
                ),
            ),
        }
    )

    for index in range(6):
        url = f"https://example.com/products/{index}"
        acquisition.pages[url] = page(url, "<p>Product</p>")

    result = SiteCrawler(
        acquisition,
        max_pages=2,
        max_depth=1,
        include_patterns=("https://example.com/products/*",),
        concurrency=ConcurrencyConfig(global_limit=4),
    ).crawl("https://example.com/")

    assert result.count == 2
    assert acquisition.calls == [
        "https://example.com/",
        "https://example.com/products/0",
        "https://example.com/products/1",
    ]
