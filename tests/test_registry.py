from scraper.fetcher import FetchedPage
from scraper.models import Lead
from scraper.registry import ExtractionRegistry, ParserRegistry


class StubParser:
    def parse(self, page: FetchedPage, category: str = "") -> Lead | None:
        return Lead(name="Stub")


def test_registry_registers_and_resolves_parser_by_domain():
    parser = StubParser()
    registry = ParserRegistry()

    registry.register("Example.COM", parser)

    assert registry.resolve("https://example.com/doctor") is parser


def test_registry_normalizes_trailing_dot():
    parser = StubParser()
    registry = ParserRegistry()

    registry.register("example.com.", parser)

    assert registry.resolve("https://example.com./doctor") is parser


def test_registry_returns_none_for_unknown_domain():
    registry = ParserRegistry()

    assert registry.resolve("https://unknown.example/") is None


def test_registry_rejects_empty_domain():
    registry = ParserRegistry()

    try:
        registry.register("   ", StubParser())
    except ValueError as exc:
        assert str(exc) == "domain must not be empty"
    else:
        raise AssertionError("expected ValueError")


class StubExtractor:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def extract(self, html):
        self.calls += 1
        return self.result


def test_extraction_registry_uses_first_deterministic_result():
    first = StubExtractor({"name": "First"})
    second = StubExtractor({"name": "Second"})

    registry = ExtractionRegistry()
    registry.register(first)
    registry.register(second)

    result = registry.extract("<html></html>")

    assert result == {"name": "First"}
    assert first.calls == 1
    assert second.calls == 0


def test_extraction_registry_continues_when_strategy_returns_none():
    first = StubExtractor(None)
    second = StubExtractor({"name": "Second"})

    registry = ExtractionRegistry()
    registry.register(first)
    registry.register(second)

    result = registry.extract("<html></html>")

    assert result == {"name": "Second"}
    assert first.calls == 1
    assert second.calls == 1


def test_extraction_registry_returns_none_without_match():
    extractor = StubExtractor(None)

    registry = ExtractionRegistry()
    registry.register(extractor)

    assert registry.extract("<html></html>") is None
    assert extractor.calls == 1
