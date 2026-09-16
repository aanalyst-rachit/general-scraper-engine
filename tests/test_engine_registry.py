from scraper.discovery import DiscoveredPage, SearchRequest
from scraper.engine import ScraperEngine
from scraper.fetcher import FetchedPage
from scraper.models import Lead
from scraper.normalizer import LeadNormalizer
from scraper.parser import PageParser
from scraper.registry import ParserRegistry


class SingleDiscovery:
    def __init__(self, url):
        self.url = url

    def discover(self, request):
        return [
            DiscoveredPage(
                url=self.url,
                title="Test",
                snippet="Test",
            )
        ]


class SingleFetcher:
    def __init__(self, page):
        self.page = page

    def fetch(self, url):
        return self.page


class StubParser:
    def __init__(self, name, result=True):
        self.name = name
        self.result = result
        self.calls = 0

    def parse(self, page, category=""):
        self.calls += 1
        if not self.result:
            return None
        return Lead(
            name=self.name,
            category=category,
            location="Shahjahanpur",
            source_url=page.final_url or page.url,
        )


def make_engine(url, site_parser, generic_parser):
    page = FetchedPage(
        url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        html="<html><body>test content</body></html>",
    )

    registry = ParserRegistry()
    registry.register("example.com", site_parser)

    return ScraperEngine(
        discovery=SingleDiscovery(url),
        fetcher=SingleFetcher(page),
        parser=generic_parser,
        parser_registry=registry,
        normalizer=LeadNormalizer(),
    )


def make_request():
    return SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=10,
    )


def test_engine_uses_registered_site_parser_before_generic_parser():
    site_parser = StubParser("Site Parser")
    generic_parser = StubParser("Generic Parser")

    engine = make_engine(
        "https://example.com/doctor",
        site_parser,
        generic_parser,
    )

    result = engine.run(make_request())

    assert result.count == 1
    assert result.leads[0].name == "Site Parser"
    assert site_parser.calls == 1
    assert generic_parser.calls == 0


def test_engine_uses_generic_parser_for_unregistered_domain():
    site_parser = StubParser("Site Parser")
    generic_parser = StubParser("Generic Parser")

    url = "https://unknown.example/doctor"
    page = FetchedPage(
        url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        html="<html><body>test content</body></html>",
    )

    registry = ParserRegistry()
    registry.register("example.com", site_parser)

    engine = ScraperEngine(
        discovery=SingleDiscovery(url),
        fetcher=SingleFetcher(page),
        parser=generic_parser,
        parser_registry=registry,
        normalizer=LeadNormalizer(),
    )

    result = engine.run(make_request())

    assert result.count == 1
    assert result.leads[0].name == "Generic Parser"
    assert site_parser.calls == 0
    assert generic_parser.calls == 1


def test_engine_falls_back_to_generic_parser_when_site_parser_returns_none():
    site_parser = StubParser("Site Parser", result=False)
    generic_parser = StubParser("Generic Parser")

    engine = make_engine(
        "https://example.com/doctor",
        site_parser,
        generic_parser,
    )

    result = engine.run(make_request())

    assert result.count == 1
    assert result.leads[0].name == "Generic Parser"
    assert site_parser.calls == 1
    assert generic_parser.calls == 1

def test_registered_site_parser_is_deterministic_and_does_not_require_ai():
    site_parser = StubParser("Deterministic Site Parser")
    generic_parser = StubParser("Generic Parser")

    engine = make_engine(
        "https://example.com/doctor",
        site_parser,
        generic_parser,
    )

    result = engine.run(make_request())

    assert result.count == 1
    assert result.leads[0].name == "Deterministic Site Parser"
    assert site_parser.calls == 1
    assert generic_parser.calls == 0
