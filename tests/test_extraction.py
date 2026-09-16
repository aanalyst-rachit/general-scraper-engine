from scraper.extraction import ExtractionStrategy
from scraper.structured_data import StructuredDataExtractor


def test_structured_data_extractor_matches_extraction_strategy_contract():
    extractor: ExtractionStrategy = StructuredDataExtractor()

    result = extractor.extract(
        """
        <script type="application/ld+json">
        {
          "@type": "Organization",
          "name": "Test Organization"
        }
        </script>
        """
    )

    assert result is not None
    assert result["name"] == "Test Organization"


def test_extraction_strategy_allows_no_result():
    extractor: ExtractionStrategy = StructuredDataExtractor()

    result = extractor.extract(
        """
        <html>
          <body>
            <h1>Plain page</h1>
          </body>
        </html>
        """
    )

    assert result is None
