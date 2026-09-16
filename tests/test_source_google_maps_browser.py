from scraper.discovery import SearchRequest
from scraper.models import Lead
from scraper.source_google_maps_browser import GoogleMapsBrowserAdapter


HTML = '<html><body>\n<div class="Nv2PK" role="article">\n<a class="hfpxzc" href="https://www.google.com/maps/place/Alpha+Clinic">Alpha Clinic</a>\n<div class="qBF1Pd">Alpha Clinic</div>\n<div class="W4Efsd">5.0 (10)</div>\n<div class="W4Efsd">Dental clinic · 123 Main Street, Shahjahanpur</div>\n<div class="W4Efsd">Open · Closes 8 pm · +91 98765 43210</div>\n<span class="UsdlK">+91 98765 43210</span>\n<a href="https://alpha.example.com">Website</a>\n</div>\n<div class="Nv2PK" role="article">\n<a class="hfpxzc" href="https://www.google.com/maps/place/Beta+Hospital">Beta Hospital</a>\n<div class="qBF1Pd">Beta Hospital</div>\n<div class="W4Efsd">4.8 (20)</div>\n<div class="W4Efsd">Hospital · 456 Civil Lines, Shahjahanpur</div>\n<div class="W4Efsd">Closed · Opens 9 am · +91 91234 56789</div>\n<span class="UsdlK">+91 91234 56789</span>\n</div>\n</body></html>'


class FakePage:
    def __init__(self, html=HTML):
        self.html = html
        self.url = ""
        self.goto_calls = []

    def set_default_timeout(self, timeout):
        self.timeout = timeout

    def goto(self, url, **kwargs):
        self.goto_calls.append((url, kwargs))
        self.url = url

    def wait_for_timeout(self, timeout):
        self.wait_timeout = timeout

    def content(self):
        return self.html


class FakeBrowser:
    def __init__(self, page):
        self.page = page
        self.closed = False

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self, browser):
        self.browser = browser
        self.launch_calls = []

    def launch(self, **kwargs):
        self.launch_calls.append(kwargs)
        return self.browser


class FakePlaywright:
    def __init__(self, page):
        self.browser = FakeBrowser(page)
        self.chromium = FakeChromium(self.browser)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def make_adapter(html=HTML):
    page = FakePage(html)
    playwright = FakePlaywright(page)
    adapter = GoogleMapsBrowserAdapter(
        lambda: playwright,
        wait_for_timeout=0,
    )
    return adapter, page, playwright


def test_google_maps_browser_parses_rendered_results():
    adapter, _, _ = make_adapter()

    leads = adapter.search(
        SearchRequest(
            keyword="clinics",
            location="Shahjahanpur",
            limit=2,
        )
    )

    assert len(leads) == 2
    assert all(isinstance(lead, Lead) for lead in leads)
    assert leads[0].name == "Alpha Clinic"
    assert leads[0].phone == "+91 98765 43210"
    assert leads[0].website == "https://alpha.example.com"
    assert leads[0].source_name == "google_maps_browser"


def test_google_maps_browser_builds_public_search_url():
    adapter, page, _ = make_adapter()

    adapter.search(
        SearchRequest(
            keyword="dentist",
            location="Shahjahanpur",
            limit=1,
        )
    )

    url = page.goto_calls[0][0]
    assert url.startswith(
        "https://www.google.com/maps/search/?api=1&query="
    )
    assert "dentist+Shahjahanpur" in url


def test_google_maps_browser_respects_limit():
    adapter, _, _ = make_adapter()

    leads = adapter.search(
        SearchRequest(keyword="clinic", limit=1)
    )

    assert len(leads) == 1


def test_google_maps_browser_empty_keyword_skips_browser():
    called = False

    def factory():
        nonlocal called
        called = True
        return make_adapter()[2]

    adapter = GoogleMapsBrowserAdapter(factory)

    assert adapter.search(SearchRequest(keyword="")) == []
    assert called is False


def test_google_maps_browser_zero_limit_skips_browser():
    called = False

    def factory():
        nonlocal called
        called = True
        return make_adapter()[2]

    adapter = GoogleMapsBrowserAdapter(factory)

    assert adapter.search(
        SearchRequest(keyword="clinic", limit=0)
    ) == []
    assert called is False


def test_google_maps_browser_stops_on_challenge_page():
    html = (
        "<html><body>"
        "<h1>Our systems have detected unusual traffic</h1>"
        "</body></html>"
    )

    adapter, _, _ = make_adapter(html)

    assert adapter.search(
        SearchRequest(keyword="clinic", limit=10)
    ) == []


def test_google_maps_browser_closes_browser():
    adapter, _, playwright = make_adapter()

    adapter.search(
        SearchRequest(keyword="clinic", limit=1)
    )

    assert playwright.browser.closed is True


def test_google_maps_browser_validates_options():
    import pytest

    with pytest.raises(ValueError):
        GoogleMapsBrowserAdapter(
            lambda: make_adapter()[2],
            timeout=0,
        )

    with pytest.raises(ValueError):
        GoogleMapsBrowserAdapter(
            lambda: make_adapter()[2],
            wait_for_timeout=-1,
        )
