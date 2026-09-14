from scraper.models import Lead
from scraper.quality import LeadQuality


def test_valid_lead_passes_quality_check():
    lead = Lead(
        name="Dr. Raj Kumar",
        location="Shahjahanpur",
        phone="+91 98765 43210",
        source_url="https://example.com/doctor",
    )

    assert LeadQuality().is_valid(lead)


def test_lead_without_name_fails_quality_check():
    lead = Lead(
        phone="+91 98765 43210",
        source_url="https://example.com/doctor",
    )

    assert not LeadQuality().is_valid(lead)


def test_lead_without_source_url_fails_quality_check():
    lead = Lead(
        name="Dr. Raj Kumar",
        phone="+91 98765 43210",
    )

    assert not LeadQuality().is_valid(lead)


def test_lead_without_business_signal_fails_quality_check():
    lead = Lead(
        name="Dr. Raj Kumar",
        source_url="https://example.com/doctor",
    )

    assert not LeadQuality().is_valid(lead)


def test_lead_with_only_location_passes_quality_check():
    lead = Lead(
        name="ABC Clinic",
        location="Shahjahanpur",
        source_url="https://example.com/clinic",
    )

    assert LeadQuality().is_valid(lead)


def test_invalid_source_url_fails_quality_check():
    lead = Lead(
        name="ABC Clinic",
        phone="9876543210",
        source_url="not-a-url",
    )

    assert not LeadQuality().is_valid(lead)
