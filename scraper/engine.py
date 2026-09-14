from __future__ import annotations

from dataclasses import dataclass

from scraper.discovery import DiscoveredPage, SearchRequest, WebDiscovery
from scraper.fetcher import FetchedPage, PageFetcher
from scraper.models import Lead
from scraper.normalizer import LeadNormalizer
from scraper.parser import PageParser
from scraper.quality import LeadQuality
from scraper.relevance import CategoryRelevance, KeywordRelevance, LocationRelevance, RequirementsRelevance


@dataclass(frozen=True)
class FetchFailure:
    url: str
    error: str


@dataclass(frozen=True)
class ParseFailure:
    url: str
    error: str


@dataclass
class ScrapeResult:
    leads: list[Lead]
    discovered: list[DiscoveredPage]
    fetched: list[FetchedPage]
    fetch_failures: list[FetchFailure]
    parse_failures: list[ParseFailure]

    @property
    def count(self) -> int:
        return len(self.leads)


class ScraperEngine:
    def __init__(
        self,
        discovery: WebDiscovery,
        fetcher: PageFetcher,
        parser: PageParser,
        normalizer: LeadNormalizer,
        quality: LeadQuality | None = None,
        relevance: KeywordRelevance | None = None,
        location_relevance: LocationRelevance | None = None,
        category_relevance: CategoryRelevance | None = None,
        requirements_relevance: RequirementsRelevance | None = None,
    ) -> None:
        self.discovery = discovery
        self.fetcher = fetcher
        self.parser = parser
        self.normalizer = normalizer
        self.quality = quality or LeadQuality()
        self.relevance = relevance
        self.location_relevance = location_relevance
        self.category_relevance = category_relevance
        self.requirements_relevance = requirements_relevance

    def run(self, request: SearchRequest) -> ScrapeResult:
        discovered = self.discovery.discover(request)
        fetched: list[FetchedPage] = []
        fetch_failures: list[FetchFailure] = []
        parsed_leads: list[Lead] = []
        parse_failures: list[ParseFailure] = []

        for candidate in discovered:
            if self.relevance is not None and not self.relevance.is_relevant(candidate):
                continue

            if self.location_relevance is not None and not self.location_relevance.is_relevant(candidate):
                continue

            if self.category_relevance is not None and not self.category_relevance.is_relevant(candidate):
                continue

            if self.requirements_relevance is not None and not self.requirements_relevance.is_relevant(candidate):
                continue

            page = self.fetcher.fetch(candidate.url)

            if not page.ok:
                fetched.append(page)
                fetch_failures.append(
                    FetchFailure(
                        url=candidate.url,
                        error=page.error or f"HTTP {page.status_code}",
                    )
                )
                continue

            fetched.append(page)

            try:
                lead = self.parser.parse(page, category=request.keyword)
            except Exception as exc:
                parse_failures.append(
                    ParseFailure(
                        url=page.final_url or page.url,
                        error=str(exc),
                    )
                )
                continue

            if lead is None:
                parse_failures.append(
                    ParseFailure(
                        url=page.final_url or page.url,
                        error="parser returned no lead",
                    )
                )
                continue

            if not lead.source_url:
                lead.source_url = page.final_url or page.url

            if not lead.source_name:
                lead.source_name = candidate.source_name or "web"

            if not self.quality.is_valid(lead):
                continue

            parsed_leads.append(lead)

        leads = self.normalizer.deduplicate_leads(parsed_leads)

        return ScrapeResult(
            leads=leads,
            discovered=discovered,
            fetched=fetched,
            fetch_failures=fetch_failures,
            parse_failures=parse_failures,
        )


def scrape(
    request: SearchRequest,
    discovery: WebDiscovery,
    fetcher: PageFetcher | None = None,
    parser: PageParser | None = None,
    normalizer: LeadNormalizer | None = None,
    relevance: KeywordRelevance | None = None,
    location_relevance: LocationRelevance | None = None,
    category_relevance: CategoryRelevance | None = None,
    requirements_relevance: RequirementsRelevance | None = None,
) -> ScrapeResult:
    engine = ScraperEngine(
        discovery=discovery,
        fetcher=fetcher or PageFetcher(),
        parser=parser or PageParser(),
        normalizer=normalizer or LeadNormalizer(),
        relevance=relevance,
        location_relevance=location_relevance,
        category_relevance=category_relevance or (
            CategoryRelevance(request.category) if request.category.strip() else None
        ),
        requirements_relevance=requirements_relevance or (
            RequirementsRelevance(request.requirements) if request.requirements.strip() else None
        ),
    )
    return engine.run(request)
