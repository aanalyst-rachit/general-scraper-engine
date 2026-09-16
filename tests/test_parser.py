from scraper.fetcher import FetchedPage
from scraper.parser import PageParser
from scraper.registry import ExtractionRegistry


def make_page(html, url="https://example.com/page"):
    return FetchedPage(
        url=url,
        final_url=url,
        status_code=200,
        content_type="text/html; charset=utf-8",
        html=html,
    )


def test_parse_json_ld_business_entity():
    html = """
    <html><head><title>Test Clinic</title></head><body>
    <script type="application/ld+json">
    {
      "@type": "Physician",
      "name": "Dr. Test Kumar",
      "description": "General physician in Shahjahanpur",
      "telephone": "+91 98765 43210",
      "email": "doctor@example.com",
      "url": "https://example.com/doctor",
      "address": {
        "@type": "PostalAddress",
        "streetAddress": "Main Road",
        "addressLocality": "Shahjahanpur",
        "addressRegion": "Uttar Pradesh",
        "postalCode": "242001",
        "addressCountry": "IN"
      },
      "category": "General Physician"
    }
    </script></body></html>
    """

    lead = PageParser().parse(make_page(html), category="doctor")

    assert lead is not None
    assert lead.name == "Dr. Test Kumar"
    assert lead.category == "General Physician"
    assert lead.location == "Shahjahanpur"
    assert "Main Road" in lead.address
    assert lead.phone == "+91 98765 43210"
    assert lead.email == "doctor@example.com"
    assert lead.website == "https://example.com/doctor"
    assert "General physician" in lead.description


def test_parse_meta_and_title_fallback():
    html = """
    <html>
    <head>
      <title>ABC Dental Clinic</title>
      <meta name="description" content="Dentist in Shahjahanpur">
    </head>
    <body></body>
    </html>
    """

    lead = PageParser().parse(make_page(html), category="dentist")

    assert lead is not None
    assert lead.name == "ABC Dental Clinic"
    assert lead.category == "dentist"
    assert lead.description == "Dentist in Shahjahanpur"


def test_parse_open_graph_title():
    html = """
    <html><head>
      <meta property="og:title" content="ABC Coaching Institute">
    </head><body></body></html>
    """

    lead = PageParser().parse(make_page(html), category="coaching")

    assert lead is not None
    assert lead.name == "ABC Coaching Institute"


def test_parse_email_from_mailto():
    html = """
    <html><head><title>Test Business</title></head>
    <body><a href="mailto:hello@example.com?subject=Hi">Email</a></body></html>
    """

    lead = PageParser().parse(make_page(html), category="business")

    assert lead is not None
    assert lead.email == "hello@example.com"


def test_parse_email_from_page_text():
    html = """
    <html><head><title>Test Business</title></head>
    <body>Contact us at hello@example.com</body></html>
    """

    lead = PageParser().parse(make_page(html), category="business")

    assert lead is not None
    assert lead.email == "hello@example.com"


def test_parse_phone_from_page_text():
    html = """
    <html><head><title>Test Business</title></head>
    <body>Call +91 98765 43210 for appointments.</body></html>
    """

    lead = PageParser().parse(make_page(html), category="business")

    assert lead is not None
    assert lead.phone == "+91 98765 43210"


def test_parse_phone_with_indian_local_format():
    html = """
    <html><head><title>Test Business</title></head>
    <body>Phone: 09876543210</body></html>
    """

    lead = PageParser().parse(make_page(html), category="business")

    assert lead is not None
    assert lead.phone == "09876543210"


def test_parse_phone_with_hyphenated_indian_format():
    html = """
    <html><head><title>Test Business</title></head>
    <body>Call +91-98765-43210 for appointments.</body></html>
    """

    lead = PageParser().parse(make_page(html), category="business")

    assert lead is not None
    assert lead.phone == "+91-98765-43210"


def test_parse_phone_with_area_code():
    html = """
    <html><head><title>Test Business</title></head>
    <body>Office: (05842) 123456</body></html>
    """

    lead = PageParser().parse(make_page(html), category="business")

    assert lead is not None
    assert lead.phone == "(05842) 123456"


def test_parse_phone_does_not_extract_email_as_phone():
    html = """
    <html><head><title>Test Business</title></head>
    <body>Contact hello@example.com for information.</body></html>
    """

    lead = PageParser().parse(make_page(html), category="business")

    assert lead is not None
    assert lead.phone == ""


def test_parse_relative_structured_website_url():
    html = """
    <html><head><title>Test Business</title></head>
    <body>
    <script type="application/ld+json">
    {"@type": "Organization", "name": "Test Business", "url": "/about"}
    </script>
    </body></html>
    """

    lead = PageParser().parse(
        make_page(html, "https://example.com/directory/item"),
        category="business",
    )

    assert lead is not None
    assert lead.website == "https://example.com/about"


def test_parse_returns_none_for_failed_page():
    page = FetchedPage(
        url="https://example.com/error",
        status_code=500,
        error="HTTP 500",
    )

    assert PageParser().parse(page) is None


def test_parse_returns_none_without_entity_name():
    html = "<html><body><p>No useful title</p></body></html>"
    page = make_page(html)
    page = FetchedPage(
        url=page.url,
        final_url=page.final_url,
        status_code=page.status_code,
        content_type=page.content_type,
        html="<html><body></body></html>",
    )

    assert PageParser().parse(page, category="business") is None

def test_parse_address_from_address_element():
    html = "<html><head><title>Test Clinic</title></head><body><address>Main Road, Shahjahanpur, Uttar Pradesh, 242001</address></body></html>"
    lead = PageParser().parse(make_page(html), category="clinic")

    assert lead is not None
    assert lead.address == "Main Road, Shahjahanpur, Uttar Pradesh, 242001"


def test_parse_address_from_meta():
    html = "<html><head><title>Test Business</title><meta name=\"address\" content=\"Station Road, Shahjahanpur, Uttar Pradesh\"></head><body></body></html>"
    lead = PageParser().parse(make_page(html), category="business")

    assert lead is not None
    assert lead.address == "Station Road, Shahjahanpur, Uttar Pradesh"


def test_parse_address_from_open_graph_meta():
    html = "<html><head><title>Test Business</title><meta property=\"og:street-address\" content=\"Main Market, Shahjahanpur\"></head><body></body></html>"
    lead = PageParser().parse(make_page(html), category="business")

    assert lead is not None
    assert lead.address == "Main Market, Shahjahanpur"

def test_parse_location_from_address_element_fallback():
    html = "<html><head><title>Test Clinic</title></head><body><address>Main Road, Shahjahanpur, Uttar Pradesh, 242001</address></body></html>"
    lead = PageParser().parse(make_page(html), category="clinic")

    assert lead is not None
    assert lead.location == "Main Road, Shahjahanpur, Uttar Pradesh, 242001"


def test_parse_location_from_address_meta_fallback():
    html = "<html><head><title>Test Business</title><meta name=\"address\" content=\"Station Road, Shahjahanpur, Uttar Pradesh\"></head><body></body></html>"
    lead = PageParser().parse(make_page(html), category="business")

    assert lead is not None
    assert lead.location == "Station Road, Shahjahanpur, Uttar Pradesh"

def test_parse_category_from_json_ld_type():
    html = "<html><head><title>ABC Dental Clinic</title></head><body><script type=\"application/ld+json\">{\"@type\": \"Dentist\", \"name\": \"ABC Dental Clinic\"}</script></body></html>"
    lead = PageParser().parse(make_page(html))

    assert lead is not None
    assert lead.category == "Dentist"


def test_parse_category_from_json_ld_type_list():
    html = "<html><head><title>ABC Medical Center</title></head><body><script type=\"application/ld+json\">{\"@type\": [\"MedicalBusiness\", \"Hospital\"], \"name\": \"ABC Medical Center\"}</script></body></html>"
    lead = PageParser().parse(make_page(html))

    assert lead is not None
    assert lead.category == "MedicalBusiness, Hospital"

def test_parse_does_not_use_source_url_as_business_website():
    html = """
    <html><head><title>Directory Listing - ABC Clinic</title></head>
    <body><p>ABC Clinic, Shahjahanpur</p></body></html>
    """

    lead = PageParser().parse(
        make_page(html, "https://directory.example.com/abc-clinic"),
        category="clinic",
    )

    assert lead is not None
    assert lead.website == ""
    assert lead.source_url == "https://directory.example.com/abc-clinic"


def test_parse_returns_none_for_empty_html():
    page = FetchedPage(
        url="https://example.com/empty",
        final_url="https://example.com/empty",
        status_code=200,
        content_type="text/html",
        html="",
    )

    assert PageParser().parse(page) is None


def test_parse_handles_malformed_html():
    page = make_page(
        "<html><head><title>Broken Clinic</title><body><div><p>Clinic without closed tags"
    )

    lead = PageParser().parse(page)

    assert lead is not None
    assert lead.name == "Broken Clinic"


def test_parse_ignores_invalid_json_ld_and_uses_html_fallback():
    page = make_page(
        "<html><head>"
        '<script type="application/ld+json">{invalid json</script>'
        "<title>Fallback Clinic</title>"
        "</head><body>Clinic</body></html>"
    )

    lead = PageParser().parse(page)

    assert lead is not None
    assert lead.name == "Fallback Clinic"



def test_parser_uses_extraction_registry_for_deterministic_extraction():
    class StubExtractor:
        def extract(self, html):
            return {
                "name": "Registry Extracted Doctor",
                "description": "Deterministic description",
            }

    registry = ExtractionRegistry()
    registry.register(StubExtractor())

    lead = PageParser(
        extraction_registry=registry,
    ).parse(
        make_page(
            "<html><head><title>Fallback</title></head>"
            "<body>Plain content</body></html>"
        )
    )

    assert lead is not None
    assert lead.name == "Registry Extracted Doctor"
    assert lead.description == "Deterministic description"


def test_generic_parser_uses_html_as_canonical_content_representation():
    html = """
    <html>
      <head>
        <title>HTML Canonical Doctor</title>
        <meta name="description" content="Doctor profile">
      </head>
      <body>
        <h1>HTML Canonical Doctor</h1>
        <address>Shahjahanpur</address>
      </body>
    </html>
    """

    lead = PageParser().parse(
        make_page(html, url="https://example.com/doctor")
    )

    assert lead is not None
    assert lead.name == "HTML Canonical Doctor"
    assert lead.description == "Doctor profile"
    assert lead.address == "Shahjahanpur"
