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

def test_lead_quality_dimensions_report_present_evidence():
    lead = Lead(
        name="Dr. Raj Kumar",
        profession="Doctor",
        phone="+91 98765 43210",
        email="raj@example.com",
        website="https://example.com/doctor",
        city="Shahjahanpur",
        source_url="https://example.com/doctor",
    )

    dimensions = LeadQuality().dimensions(lead)

    assert dimensions == {
        "identity": True,
        "contact": True,
        "web_presence": True,
        "location": True,
        "business_context": True,
        "source": True,
    }

def test_lead_quality_measurement_separates_checked_and_rejected_leads():
    quality = LeadQuality()
    valid = Lead(
        name="Dr. Raj Kumar",
        phone="9876543210",
        source_url="https://example.com/doctor",
    )
    invalid = Lead(name="Incomplete Lead")

    assert quality.measure([valid, invalid]) == {
        "checked": 2,
        "accepted": 1,
        "rejected": 1,
    }

def test_lead_model_preserves_existing_location_fields_and_serialization():
    lead = Lead(
        name="ABC Clinic",
        address="Main Road",
        location="Shahjahanpur",
        locality="Civil Lines",
        city="Shahjahanpur",
        district="Shahjahanpur",
        state="Uttar Pradesh",
        country="India",
        pincode="242001",
    )

    data = lead.to_dict()

    assert data["address"] == "Main Road"
    assert data["location"] == "Shahjahanpur"
    assert data["locality"] == "Civil Lines"
    assert data["city"] == "Shahjahanpur"
    assert data["district"] == "Shahjahanpur"
    assert data["state"] == "Uttar Pradesh"
    assert data["country"] == "India"
    assert data["pincode"] == "242001"


def test_lead_model_defaults_remain_backward_compatible():
    lead = Lead(name="Existing Lead")

    assert lead.name == "Existing Lead"
    assert lead.phone == ""
    assert lead.email == ""
    assert lead.city == ""
    assert lead.state == ""
    assert lead.social_profiles == {}
    assert lead.extra == {}
    assert lead.raw_data == {}
