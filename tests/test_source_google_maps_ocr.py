from scraper.discovery import SearchRequest
from scraper.source_google_maps_ocr import GoogleMapsOCRAdapter


def test_google_maps_ocr_adapter_has_expected_id() -> None:
    adapter = GoogleMapsOCRAdapter()

    assert adapter.id == "google_maps_ocr"


def test_google_maps_ocr_adapter_implements_source_contract() -> None:
    adapter = GoogleMapsOCRAdapter()

    assert hasattr(adapter, "id")
    assert callable(adapter.search)
    assert callable(adapter.close)


def test_google_maps_ocr_search_returns_empty_for_invalid_request() -> None:
    adapter = GoogleMapsOCRAdapter()

    request = SearchRequest(
        keyword="",
        location="Shahjahanpur",
        limit=5,
    )

    assert adapter.search(request) == []


def test_google_maps_ocr_search_returns_empty_for_zero_limit() -> None:
    adapter = GoogleMapsOCRAdapter()

    request = SearchRequest(
        keyword="shops",
        location="Shahjahanpur",
        limit=0,
    )

    assert adapter.search(request) == []


def test_google_maps_ocr_search_returns_lead_list() -> None:
    adapter = GoogleMapsOCRAdapter()

    request = SearchRequest(
        keyword="shops",
        location="Shahjahanpur",
        limit=5,
    )

    result = adapter.search(request)

    assert isinstance(result, list)
    assert all(hasattr(item, "to_dict") for item in result)
