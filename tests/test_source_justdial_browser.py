from scraper.discovery import SearchRequest
from scraper.models import Lead
from scraper.source_justdial_browser import JustdialBrowserAdapter


HTML = """<html><body>
<div class="store-details">
  <a href="/Shahjahanpur/Alpha-Dental-Clinic/999999">Alpha Dental Clinic</a>
  <h2>Alpha Dental Clinic</h2>
  <div class="catname">Dental Clinic</div>
  <div class="cont_fl_addr">Civil Lines, Shahjahanpur</div>
  <div class="mobilesv">+91 98765 43210</div>
  <a href="https://alpha.example.com">Website</a>
</div>
<div class="store-details">
  <a href="/Shahjahanpur/Beta-Dental-Care/888888">Beta Dental Care</a>
  <h2>Beta Dental Care</h2>
  <div class="catname">Dentist</div>
  <div class="cont_fl_addr">Sadar Bazar, Shahjahanpur</div>
  <div class="mobilesv">+91 91234 56789</div>
</div>
</body></html>"""


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

    def launch(self, **kwargs):
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
    adapter = JustdialBrowserAdapter(
        lambda: playwright,
        wait_for_timeout=0,
    )
    return adapter, page, playwright


def test_justdial_browser_parses_results():
    adapter, _, _ = make_adapter()

    leads = adapter.search(
        SearchRequest(
            keyword="Dentists",
            location="Shahjahanpur",
            limit=2,
        )
    )

    assert len(leads) == 2
    assert all(isinstance(lead, Lead) for lead in leads)
    assert leads[0].name == "Alpha Dental Clinic"
    assert leads[0].category == "Dental Clinic"
    assert leads[0].address == "Civil Lines, Shahjahanpur"
    assert leads[0].phone == "+91 98765 43210"
    assert leads[0].website == "https://alpha.example.com"
    assert leads[0].source_name == "justdial_browser"


def test_justdial_browser_builds_public_search_url():
    adapter, page, _ = make_adapter()

    adapter.search(
        SearchRequest(
            keyword="Dentists",
            location="Shahjahanpur",
            limit=1,
        )
    )

    assert page.goto_calls[0][0] == "https://www.justdial.com/Shahjahanpur/Dentists"


def test_justdial_browser_respects_limit():
    adapter, _, _ = make_adapter()

    leads = adapter.search(
        SearchRequest(
            keyword="Dentists",
            location="Shahjahanpur",
            limit=1,
        )
    )

    assert len(leads) == 1


def test_justdial_browser_handles_missing_optional_fields():
    html = """<html><body>
<div class="store-details">
  <a href="/Shahjahanpur/Minimal-Clinic/777777">Minimal Clinic</a>
  <h2>Minimal Clinic</h2>
</div>
</body></html>"""

    adapter, _, _ = make_adapter(html)

    leads = adapter.search(
        SearchRequest(
            keyword="Dentists",
            location="Shahjahanpur",
            limit=1,
        )
    )

    assert len(leads) == 1
    assert leads[0].name == "Minimal Clinic"
    assert leads[0].company_name == "Minimal Clinic"
    assert leads[0].category == ""
    assert leads[0].address == ""
    assert leads[0].phone == ""
    assert leads[0].website == ""
    assert leads[0].source_name == "justdial_browser"
    assert leads[0].source_id == ""


def test_justdial_browser_deduplicates_listing_urls():
    html = HTML.replace(
        "</body>",
        """<div class="store-details">
  <a href="/Shahjahanpur/Alpha-Dental-Clinic/999999">Alpha Dental Clinic</a>
  <h2>Alpha Dental Clinic</h2>
</div></body>""",
    )

    adapter, _, _ = make_adapter(html)

    leads = adapter.search(
        SearchRequest(
            keyword="Dentists",
            location="Shahjahanpur",
            limit=10,
        )
    )

    assert len(leads) == 2


def test_justdial_browser_negative_limit_skips_browser():
    called = False

    def factory():
        nonlocal called
        called = True
        return make_adapter()[2]

    adapter = JustdialBrowserAdapter(factory)

    assert adapter.search(SearchRequest(keyword="Dentists", limit=-1)) == []
    assert called is False


def test_justdial_browser_empty_keyword_skips_browser():
    called = False

    def factory():
        nonlocal called
        called = True
        return make_adapter()[2]

    adapter = JustdialBrowserAdapter(factory)

    assert adapter.search(SearchRequest(keyword="")) == []
    assert called is False


def test_justdial_browser_zero_limit_skips_browser():
    called = False

    def factory():
        nonlocal called
        called = True
        return make_adapter()[2]

    adapter = JustdialBrowserAdapter(factory)

    assert adapter.search(
        SearchRequest(keyword="Dentists", limit=0)
    ) == []
    assert called is False


def test_justdial_browser_stops_on_empty_document():
    adapter, _, _ = make_adapter("<html><body></body></html>")

    assert adapter.search(
        SearchRequest(keyword="Dentists", limit=10)
    ) == []


def test_justdial_browser_stops_on_challenge_page():
    html = "<html><body><h1>Verify you are human</h1></body></html>"
    adapter, _, _ = make_adapter(html)

    assert adapter.search(
        SearchRequest(keyword="Dentists", limit=10)
    ) == []


def test_justdial_browser_closes_browser_when_navigation_fails():
    page = FakePage()

    def failing_goto(url, **kwargs):
        page.goto_calls.append((url, kwargs))
        raise RuntimeError("navigation failed")

    page.goto = failing_goto
    playwright = FakePlaywright(page)
    adapter = JustdialBrowserAdapter(
        lambda: playwright,
        wait_for_timeout=0,
    )

    import pytest

    with pytest.raises(RuntimeError, match="navigation failed"):
        adapter.search(
            SearchRequest(
                keyword="Dentists",
                location="Shahjahanpur",
                limit=1,
            )
        )

    assert playwright.browser.closed is True


def test_justdial_browser_closes_browser():
    adapter, _, playwright = make_adapter()

    adapter.search(
        SearchRequest(keyword="Dentists", limit=1)
    )

    assert playwright.browser.closed is True


def test_justdial_browser_accepts_absolute_justdial_listing_url():
    html = """<html><body>
<div class="store-details">
  <h2>Absolute Listing</h2>
  <a href="https://www.justdial.com/Shahjahanpur/Absolute-Listing/123456">Listing</a>
</div>
</body></html>"""

    adapter, _, _ = make_adapter(html)

    leads = adapter.search(
        SearchRequest(
            keyword="Dentists",
            location="Shahjahanpur",
            limit=1,
        )
    )

    assert len(leads) == 1
    assert leads[0].source_url == "https://www.justdial.com/Shahjahanpur/Absolute-Listing/123456"


def test_justdial_browser_ignores_external_link_as_listing_url():
    html = """<html><body>
<div class="store-details">
  <h2>External Link First</h2>
  <a href="https://example.com/not-a-listing">External</a>
  <a href="/Shahjahanpur/Real-Listing/123456">Listing</a>
</div>
</body></html>"""

    adapter, _, _ = make_adapter(html)

    leads = adapter.search(
        SearchRequest(
            keyword="Dentists",
            location="Shahjahanpur",
            limit=1,
        )
    )

    assert len(leads) == 1
    assert leads[0].source_url == "https://www.justdial.com/Shahjahanpur/Real-Listing/123456"


def test_justdial_browser_skips_card_without_listing_link():
    html = """<html><body>
<div class="store-details">
  <h2>No Listing URL</h2>
  <div class="catname">Dentist</div>
</div>
</body></html>"""

    adapter, _, _ = make_adapter(html)

    assert adapter.search(
        SearchRequest(
            keyword="Dentists",
            location="Shahjahanpur",
            limit=1,
        )
    ) == []


def test_justdial_browser_validates_options():
    import pytest

    with pytest.raises(ValueError):
        JustdialBrowserAdapter(
            lambda: make_adapter()[2],
            timeout=0,
        )

    with pytest.raises(ValueError):
        JustdialBrowserAdapter(
            lambda: make_adapter()[2],
            wait_for_timeout=-1,
        )
