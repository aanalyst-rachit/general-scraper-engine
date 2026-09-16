from scraper.discovery import SearchRequest
from scraper.models import Lead
from scraper.source_adapter import SourceAdapterRegistry


class StubSourceAdapter:
    id = "google_maps"

    def __init__(self, leads=None):
        self.leads = leads or []
        self.requests = []

    def search(self, request):
        self.requests.append(request)
        return list(self.leads)


def test_registry_registers_and_resolves_source_adapter():
    adapter = StubSourceAdapter()
    registry = SourceAdapterRegistry()

    registry.register(adapter)

    assert registry.resolve("google_maps") is adapter


def test_registry_normalizes_source_id():
    adapter = StubSourceAdapter()
    adapter.id = " Google_Maps "
    registry = SourceAdapterRegistry()

    registry.register(adapter)

    assert registry.resolve("google_maps") is adapter


def test_registry_returns_none_for_unknown_source():
    registry = SourceAdapterRegistry()

    assert registry.resolve("unknown") is None


def test_registry_rejects_empty_source_id():
    registry = SourceAdapterRegistry()

    adapter = StubSourceAdapter()
    adapter.id = "   "

    try:
        registry.register(adapter)
    except ValueError as exc:
        assert str(exc) == "source adapter id must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_adapter_search_uses_canonical_search_request():
    lead = Lead(name="Test Lead", source_name="google_maps")
    adapter = StubSourceAdapter([lead])
    registry = SourceAdapterRegistry()
    registry.register(adapter)
    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        requirements="general physician",
        category="medical",
        limit=10,
    )

    resolved = registry.resolve("google_maps")
    result = resolved.search(request)

    assert result == [lead]
    assert adapter.requests == [request]

def test_registry_replaces_existing_adapter_with_same_source_id():
    first = StubSourceAdapter([Lead(name="First")])
    second = StubSourceAdapter([Lead(name="Second")])

    registry = SourceAdapterRegistry()
    registry.register(first)
    registry.register(second)

    assert registry.resolve("google_maps") is second


def test_registry_resolves_case_and_whitespace_insensitively():
    adapter = StubSourceAdapter()
    registry = SourceAdapterRegistry()

    registry.register(adapter)

    assert registry.resolve("  GOOGLE_MAPS  ") is adapter
