from scraper.structured_data import StructuredDataExtractor


def test_extracts_schema_org_entity_fields():
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
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
    </script>
    """

    result = StructuredDataExtractor().extract(html)

    assert result is not None
    assert result["name"] == "Dr. Test Kumar"
    assert result["category"] == "General Physician"
    assert result["address"] == (
        "Main Road, Shahjahanpur, Uttar Pradesh, 242001, IN"
    )
    assert result["address_locality"] == "Shahjahanpur"
    assert result["address_region"] == "Uttar Pradesh"


def test_extracts_entity_from_json_ld_graph():
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "WebSite",
          "name": "Example"
        },
        {
          "@type": "LocalBusiness",
          "name": "Graph Clinic",
          "telephone": "+91 98765 43210"
        }
      ]
    }
    </script>
    """

    result = StructuredDataExtractor().extract(html)

    assert result is not None
    assert result["name"] == "Graph Clinic"
    assert result["telephone"] == "+91 98765 43210"


def test_extracts_entity_from_json_ld_array():
    html = """
    <script type="application/ld+json">
    [
      {"@type": "Thing", "name": "Ignore Me"},
      {"@type": "Dentist", "name": "Array Dentist"}
    ]
    </script>
    """

    result = StructuredDataExtractor().extract(html)

    assert result is not None
    assert result["name"] == "Array Dentist"


def test_non_entity_json_ld_returns_none():
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Thing",
      "name": "Generic Thing"
    }
    </script>
    """

    assert StructuredDataExtractor().extract(html) is None


def test_malformed_json_ld_is_ignored():
    html = """
    <script type="application/ld+json">
    {"@type":"Physician","name":
    </script>
    """

    assert StructuredDataExtractor().extract(html) is None


def test_multiple_json_ld_scripts_find_first_entity():
    html = """
    <script type="application/ld+json">
    {"@type":"Thing","name":"Ignore Me"}
    </script>
    <script type="application/ld+json">
    {"@type":"Organization","name":"Useful Organization"}
    </script>
    """

    result = StructuredDataExtractor().extract(html)

    assert result is not None
    assert result["name"] == "Useful Organization"


def test_entity_type_list_is_supported():
    html = """
    <script type="application/ld+json">
    {
      "@type": ["Organization", "LocalBusiness"],
      "name": "Multi Type Business"
    }
    </script>
    """

    result = StructuredDataExtractor().extract(html)

    assert result is not None
    assert result["name"] == "Multi Type Business"
    assert result["category"] == "Organization, LocalBusiness"
