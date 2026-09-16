from scraper.location import LocationValidator
from scraper.models import Lead


def test_requested_location_matches_city():
    lead = Lead(name="Dr. Raj Kumar", city="Shahjahanpur")
    assert LocationValidator("Shahjahanpur").is_relevant(lead)


def test_requested_location_matches_district():
    lead = Lead(name="ABC Clinic", district="Shahjahanpur")
    assert LocationValidator("Shahjahanpur").is_relevant(lead)


def test_requested_location_matches_state():
    lead = Lead(name="ABC Clinic", state="Uttar Pradesh")
    assert LocationValidator("Uttar Pradesh").is_relevant(lead)


def test_requested_location_matches_locality():
    lead = Lead(name="ABC Clinic", locality="Shahjahanpur")
    assert LocationValidator("Shahjahanpur").is_relevant(lead)


def test_requested_location_matches_location_text():
    lead = Lead(name="ABC Clinic", location="Shahjahanpur")
    assert LocationValidator("Shahjahanpur").is_relevant(lead)


def test_requested_location_matches_address_text():
    lead = Lead(name="ABC Clinic", address="Main Road, Shahjahanpur, Uttar Pradesh")
    assert LocationValidator("Shahjahanpur").is_relevant(lead)


def test_wrong_extracted_location_is_rejected():
    lead = Lead(name="ABC Clinic", city="Lucknow")
    assert not LocationValidator("Shahjahanpur").is_relevant(lead)


def test_wrong_location_in_address_is_rejected():
    lead = Lead(name="ABC Clinic", address="Hazratganj, Lucknow, Uttar Pradesh")
    assert not LocationValidator("Shahjahanpur").is_relevant(lead)


def test_missing_location_evidence_is_rejected_when_requested():
    lead = Lead(name="ABC Clinic")
    assert not LocationValidator("Shahjahanpur").is_relevant(lead)


def test_matching_is_case_insensitive():
    lead = Lead(name="ABC Clinic", city="SHAHJAHANPUR")
    assert LocationValidator("shahjahanpur").is_relevant(lead)


def test_empty_requested_location_accepts_lead():
    lead = Lead(name="ABC Clinic")
    assert LocationValidator("").is_relevant(lead)


def test_empty_requested_location_rejects_only_whitespace():
    lead = Lead(name="ABC Clinic")
    assert LocationValidator("   ").is_relevant(lead)

def test_conflicting_location_evidence_is_rejected():
    lead = Lead(
        name="ABC Clinic",
        city="Shahjahanpur",
        address="Hazratganj, Lucknow, Uttar Pradesh",
    )
    assert not LocationValidator("Shahjahanpur").is_relevant(lead)

def test_conflicting_location_text_is_rejected():
    lead = Lead(
        name="ABC Clinic",
        city="Shahjahanpur",
        location="Lucknow",
    )
    assert not LocationValidator("Shahjahanpur").is_relevant(lead)
