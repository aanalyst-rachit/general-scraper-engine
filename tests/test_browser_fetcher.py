import pytest

from scraper.acquisition import FetchRequest
from scraper.fetcher import FetchedPage


def test_browser_fetcher_is_exposed_as_acquisition_strategy():
    from scraper.browser_fetcher import BrowserFetcher

    fetcher = BrowserFetcher()

    assert hasattr(fetcher, "fetch")
    assert callable(fetcher.fetch)


def test_browser_fetcher_rejects_empty_url_without_browser():
    from scraper.browser_fetcher import BrowserFetcher

    fetcher = BrowserFetcher()

    page = fetcher.fetch(FetchRequest(""))

    assert isinstance(page, FetchedPage)
    assert page.url == ""
    assert page.ok is False
    assert page.error == "empty URL"


def test_browser_fetcher_rejects_unsupported_url_without_browser():
    from scraper.browser_fetcher import BrowserFetcher

    fetcher = BrowserFetcher()

    page = fetcher.fetch(FetchRequest("ftp://example.com"))

    assert isinstance(page, FetchedPage)
    assert page.ok is False
    assert page.error == "unsupported URL"


def test_browser_fetcher_validates_options():
    from scraper.browser_fetcher import BrowserFetcher

    with pytest.raises(ValueError):
        BrowserFetcher(timeout=0)

    with pytest.raises(ValueError):
        BrowserFetcher(wait_for_timeout=-1)

    with pytest.raises(ValueError):
        BrowserFetcher(scroll_steps=-1)

    with pytest.raises(ValueError):
        BrowserFetcher(click_selector="")

    with pytest.raises(ValueError):
        BrowserFetcher(max_concurrency=0)


def test_browser_fetcher_returns_optional_dependency_error():
    from scraper.browser_fetcher import BrowserFetcher

    fetcher = BrowserFetcher(
        playwright_factory=lambda: (_ for _ in ()).throw(
            ModuleNotFoundError("No module named 'playwright'")
        )
    )

    page = fetcher.fetch(FetchRequest("https://example.com"))

    assert isinstance(page, FetchedPage)
    assert page.ok is False
    assert "playwright" in page.error.lower()

def _browser_fixture_url():
    import urllib.request

    url = "http://127.0.0.1:8766/browser-interaction"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status != 200:
                return None
    except Exception:
        return None
    return url


@pytest.mark.integration
def test_browser_fetcher_real_navigation_and_selector_wait():
    from scraper.browser_fetcher import BrowserFetcher

    url = _browser_fixture_url()
    if url is None:
        pytest.skip("browser integration fixture is unavailable")

    page = BrowserFetcher(
        timeout=10,
        wait_for_selector="#reveal",
    ).fetch(FetchRequest(url))

    assert page.ok is True
    assert page.status_code == 200
    assert 'id="reveal"' in page.html
    assert page.final_url == url


@pytest.mark.integration
def test_browser_fetcher_real_click_changes_rendered_dom():
    from scraper.browser_fetcher import BrowserFetcher

    url = _browser_fixture_url()
    if url is None:
        pytest.skip("browser integration fixture is unavailable")

    page = BrowserFetcher(
        timeout=10,
        click_selector="#reveal",
        wait_for_timeout=0.1,
    ).fetch(FetchRequest(url))

    assert page.ok is True
    assert page.status_code == 200
    assert '<p id="revealed">Revealed after click</p>' in page.html


@pytest.mark.integration
def test_browser_fetcher_real_scroll_returns_rendered_document():
    from scraper.browser_fetcher import BrowserFetcher

    url = _browser_fixture_url()
    if url is None:
        pytest.skip("browser integration fixture is unavailable")

    page = BrowserFetcher(
        timeout=10,
        scroll_steps=2,
    ).fetch(FetchRequest(url))

    assert page.ok is True
    assert page.status_code == 200
    assert "Scrolled Content" in page.html





def test_browser_fetcher_bounds_concurrent_browser_operations():
    from threading import Event, Lock, Thread

    from scraper.browser_fetcher import BrowserFetcher

    fetcher = BrowserFetcher(max_concurrency=2)
    active = 0
    maximum_active = 0
    lock = Lock()
    first_two_active = Event()
    release = Event()

    def fake_browser_fetch(request, url):
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
            if active == 2:
                first_two_active.set()
        try:
            assert release.wait(timeout=5)
        finally:
            with lock:
                active -= 1
        return FetchedPage(
            url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            html="<html><body>ok</body></html>",
        )

    fetcher._fetch_with_browser = fake_browser_fetch

    results = []
    threads = []

    def run_fetch(index):
        results.append(
            fetcher.fetch(FetchRequest(f"https://example.com/{index}"))
        )

    for index in range(4):
        thread = Thread(target=run_fetch, args=(index,))
        threads.append(thread)
        thread.start()

    assert first_two_active.wait(timeout=5)
    with lock:
        assert active == 2
        assert maximum_active == 2

    release.set()

    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()

    assert len(results) == 4
    assert all(result.ok for result in results)
    assert maximum_active == 2
