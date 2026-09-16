from pathlib import Path

from scraper.source_google_maps_browser import GoogleMapsBrowserAdapter


def test_google_maps_browser_parses_real_captured_fixture():
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "google_maps_dentist_shahjahanpur.html"
    )
    html = fixture.read_text(encoding="utf-8")

    adapter = GoogleMapsBrowserAdapter(
        lambda: None,
        wait_for_timeout=0,
    )

    leads = adapter._parse_results(
        html,
        search_context="dentist Shahjahanpur",
        limit=8,
    )

    assert len(leads) == 8
    assert leads[0].name == "Anand Dental Clinic, shahjahanpur"
    assert leads[0].category == "Dental clinic"
    assert leads[0].address == "Opposite old hospital,, Jail Rd"
    assert leads[0].phone == "093055 83436"
    assert leads[0].website == ""

    assert leads[1].name == "Dr.Shahzeb Khan" + chr(39) + "s (Smile Makers Dental Clinic)"
    assert leads[1].category == "Dental clinic"
    assert leads[1].address == "Tel Tanki Road, near Lal Imli Chauraha"
    assert leads[1].phone == "080090 71771"
    assert leads[1].website == "http://www.dentistsmilemakers.com/"

    assert leads[7].name == "Vardan Laser Dental Clinic And Hospital"
    assert leads[7].category == "Dental clinic"
    assert leads[7].address == "Nishat Rd"
    assert leads[7].phone == "096289 99975"
    assert leads[7].website == "https://vardanlaserdentistry.com/"

    assert all(lead.source_name == "google_maps_browser" for lead in leads)
    assert all(
        lead.source_url.startswith("https://www.google.com/maps/place/")
        for lead in leads
    )
    assert all("Closes" not in lead.address for lead in leads)
    assert all("Opens" not in lead.address for lead in leads)
    assert all("Open" not in lead.address for lead in leads)
    assert all("Closed" not in lead.address for lead in leads)
    assert all(
        not any("\ue000" <= ch <= "\uf8ff" for ch in lead.address)
        for lead in leads
    )
