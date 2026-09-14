from scraper.models import Lead
from scraper.normalizer import LeadNormalizer


def test_normalize_text_collapses_whitespace():
    normalizer = LeadNormalizer()
    assert normalizer.normalize_text("  Dr.   Raj   Kumar  ") == "Dr. Raj Kumar"


def test_normalize_name_casefolds():
    normalizer = LeadNormalizer()
    assert normalizer.normalize_name("Dr. Raj Kumar") == "dr. raj kumar"


def test_normalize_phone():
    normalizer = LeadNormalizer()
    assert normalizer.normalize_phone("+91 98765-43210") == "+919876543210"
    assert normalizer.normalize_phone("0091 98765 43210") == "+919876543210"
    assert normalizer.normalize_phone("(98765) 43210") == "9876543210"


def test_normalize_email():
    normalizer = LeadNormalizer()
    assert normalizer.normalize_email("  RAJ@EXAMPLE.COM ") == "raj@example.com"


def test_normalize_url():
    normalizer = LeadNormalizer()
    assert normalizer.normalize_url("HTTPS://Example.COM/doctor/") == "https://example.com/doctor"
    assert normalizer.normalize_url("example.com/doctor/") == "https://example.com/doctor"


def test_normalize_lead():
    normalizer = LeadNormalizer()
    lead = Lead(
        name="  Dr.   Raj Kumar ", 
        category=" General Physician ", 
        location=" Shahjahanpur ", 
        address=" Main Road ", 
        phone="+91 98765-43210", 
        email=" RAJ@EXAMPLE.COM ", 
        website="HTTPS://Example.COM/doctor/", 
        description="  Experienced doctor  ", 
        source_url="HTTPS://SOURCE.COM/page/", 
        source_name=" web ", 
    )

    normalized = normalizer.normalize_lead(lead)

    assert normalized.name == "Dr. Raj Kumar"
    assert normalized.category == "General Physician"
    assert normalized.location == "Shahjahanpur"
    assert normalized.address == "Main Road"
    assert normalized.phone == "+919876543210"
    assert normalized.email == "raj@example.com"
    assert normalized.website == "https://example.com/doctor"
    assert normalized.description == "Experienced doctor"
    assert normalized.source_url == "https://source.com/page"
    assert normalized.source_name == "web"


def test_deduplicate_by_phone():
    normalizer = LeadNormalizer()
    leads = [
        Lead(name="Dr. Raj Kumar", phone="+91 98765 43210"),
        Lead(name="Raj Kumar Clinic", phone="0091-98765-43210", email="raj@example.com"),
    ]

    result = normalizer.deduplicate_leads(leads)

    assert len(result) == 1
    assert result[0].name == "Dr. Raj Kumar"
    assert result[0].email == "raj@example.com"


def test_deduplicate_by_email():
    normalizer = LeadNormalizer()
    leads = [
        Lead(name="Dr. Raj Kumar", email="RAJ@example.com"),
        Lead(name="Raj Kumar Clinic", email="raj@example.com", phone="9876543210"),
    ]

    result = normalizer.deduplicate_leads(leads)

    assert len(result) == 1
    assert result[0].phone == "9876543210"


def test_deduplicate_by_website_and_name():
    normalizer = LeadNormalizer()
    leads = [
        Lead(name="Dr. Raj Kumar", website="https://example.com/doctor/"),
        Lead(name="Dr. Raj Kumar", website="HTTPS://EXAMPLE.COM/doctor"),
    ]

    result = normalizer.deduplicate_leads(leads)

    assert len(result) == 1


def test_deduplicate_by_name_and_address():
    normalizer = LeadNormalizer()
    leads = [
        Lead(name="Dr. Raj Kumar", address="Main Road, Shahjahanpur"),
        Lead(name="DR. RAJ KUMAR", address="Main Road, Shahjahanpur", phone="9876543210"),
    ]

    result = normalizer.deduplicate_leads(leads)

    assert len(result) == 1
    assert result[0].phone == "9876543210"


def test_deduplicate_by_name_and_location_when_address_missing():
    normalizer = LeadNormalizer()
    leads = [
        Lead(name="Dr. Raj Kumar", location="Shahjahanpur"),
        Lead(name="DR. RAJ KUMAR", location="SHAHJAHANPUR", email="raj@example.com"),
    ]

    result = normalizer.deduplicate_leads(leads)

    assert len(result) == 1
    assert result[0].email == "raj@example.com"


def test_merge_preserves_missing_fields():
    normalizer = LeadNormalizer()
    primary = Lead(
        name="Dr. Raj Kumar", 
        phone="9876543210", 
        source_url="https://source-one.example/raj", 
    )
    secondary = Lead(
        name="", 
        email="raj@example.com", 
        website="https://example.com/raj", 
        source_url="https://source-two.example/raj", 
    )

    merged = normalizer.merge_leads(primary, secondary)

    assert merged.name == "Dr. Raj Kumar"
    assert merged.phone == "9876543210"
    assert merged.email == "raj@example.com"
    assert merged.website == "https://example.com/raj"
    assert "https://source-one.example/raj" in merged.extra["source_urls"]
    assert "https://source-two.example/raj" in merged.extra["source_urls"]


def test_empty_normalization_inputs():
    normalizer = LeadNormalizer()
    assert normalizer.normalize_text("") == ""
    assert normalizer.normalize_phone("") == ""
    assert normalizer.normalize_email("") == ""
    assert normalizer.normalize_url("") == ""


def test_empty_lead_list():
    normalizer = LeadNormalizer()
    assert normalizer.deduplicate_leads([]) == []
