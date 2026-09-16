from pathlib import Path

from scraper.source_justdial_browser import JustdialBrowserAdapter


def test_justdial_browser_stops_on_observed_empty_live_response():
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "justdial_empty_live_response.html"
    )
    html = fixture.read_text(encoding="utf-8")

    adapter = JustdialBrowserAdapter(
        lambda: None,
        wait_for_timeout=0,
    )

    assert adapter._looks_blocked_or_empty(
        html,
        "https://www.justdial.com/Shahjahanpur/Dentists",
    )


def test_justdial_browser_empty_live_response_produces_no_leads():
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "justdial_empty_live_response.html"
    )
    html = fixture.read_text(encoding="utf-8")

    adapter = JustdialBrowserAdapter(
        lambda: None,
        wait_for_timeout=0,
    )

    leads = adapter._parse_results(
        html,
        search_context="Dentists Shahjahanpur",
        limit=10,
    )

    assert leads == []
