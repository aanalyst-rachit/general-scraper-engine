from pathlib import Path

from scraper.source_justdial_browser import JustdialBrowserAdapter


def test_justdial_browser_parses_synthetic_fixture():
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "justdial_dentists_shahjahanpur.html"
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

    assert len(leads) == 3

    assert leads[0].name == "Anand Dental Clinic"
    assert leads[0].category == "Dental Clinic"
    assert leads[0].address == "Jail Road, Shahjahanpur"
    assert leads[0].phone == "093055 83436"
    assert leads[0].website == "https://ananddental.example.com"

    assert leads[1].name == "Smile Makers Dental Clinic"
    assert leads[1].category == "Dentist"
    assert leads[1].address == "Tel Tanki Road, Shahjahanpur"
    assert leads[1].phone == "080090 71771"
    assert leads[1].website == ""

    assert leads[2].name == "Vardan Laser Dental Clinic"
    assert leads[2].category == "Dental Clinic"
    assert leads[2].address == "Nishat Road, Shahjahanpur"
    assert leads[2].phone == "096289 99975"
    assert leads[2].website == "https://vardandental.example.com"

    assert all(
        lead.source_name == "justdial_browser"
        for lead in leads
    )
    assert all(
        lead.source_url.startswith(
            "https://www.justdial.com/Shahjahanpur/"
        )
        for lead in leads
    )
    assert len({lead.source_url for lead in leads}) == 3
    assert all(
        "justdial.com" not in lead.website.lower()
        for lead in leads
        if lead.website
    )


def test_justdial_browser_fixture_respects_limit():
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "justdial_dentists_shahjahanpur.html"
    )
    html = fixture.read_text(encoding="utf-8")

    adapter = JustdialBrowserAdapter(
        lambda: None,
        wait_for_timeout=0,
    )

    leads = adapter._parse_results(
        html,
        search_context="Dentists Shahjahanpur",
        limit=2,
    )

    assert len(leads) == 2
