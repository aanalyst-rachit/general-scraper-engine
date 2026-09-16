from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from scraper.database.repository import LeadRepository
from scraper.concurrency import BoundedExecutor, ConcurrencyConfig, DomainConcurrencyLimiter
from scraper.discovery import DiscoveredPage, SearchRequest, WebDiscovery
from scraper.acquisition import (
    AutoFetcher,
    CachedFetcher,
    FetchRequest,
    HTTPFetcherAdapter,
)
from scraper.cache.fetch import FetchCache
from scraper.fetcher import FetchedPage, PageFetcher
from scraper.models import Lead
from scraper.normalizer import LeadNormalizer
from scraper.parser import PageParser
from scraper.registry import ParserRegistry
from scraper.quality import LeadQuality
from scraper.location import LocationValidator
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
    existing_leads: list[Lead] = field(default_factory=list)
    quality_checked_count: int = 0
    quality_accepted_count: int = 0
    quality_rejected_count: int = 0

    @property
    def count(self) -> int:
        return len(self.leads)


class ScraperEngine:
    def __init__(
        self,
        discovery: WebDiscovery,
        parser: PageParser,
        normalizer: LeadNormalizer,
        parser_registry: ParserRegistry | None = None,
        fetcher: PageFetcher | None = None,
        fetch_cache: FetchCache | None = None,
        quality: LeadQuality | None = None,
        relevance: KeywordRelevance | None = None,
        location_relevance: LocationRelevance | None = None,
        category_relevance: CategoryRelevance | None = None,
        requirements_relevance: RequirementsRelevance | None = None,
        repository: LeadRepository | None = None,
        max_concurrency: int | ConcurrencyConfig = 4,
    ) -> None:
        self.discovery = discovery
        self.fetcher = fetcher
        acquisition = (
            AutoFetcher()
            if fetcher is None
            else HTTPFetcherAdapter(fetcher)
        )

        if fetch_cache is not None:
            acquisition = CachedFetcher(
                acquisition,
                fetch_cache,
                acquisition_strategy="auto" if fetcher is None else "http",
            )

        self.acquisition = acquisition
        self.parser = parser
        self.parser_registry = parser_registry or ParserRegistry()
        self.normalizer = normalizer
        self.quality = quality or LeadQuality()
        self.relevance = relevance
        self.location_relevance = location_relevance
        self.category_relevance = category_relevance
        self.requirements_relevance = requirements_relevance
        self.repository = repository

        if isinstance(max_concurrency, ConcurrencyConfig):
            self.concurrency = max_concurrency
        else:
            self.concurrency = ConcurrencyConfig(global_limit=max_concurrency)

        # Backward-compatible alias
        self.max_concurrency = self.concurrency.global_limit

    def _fetch_candidate(
        self,
        candidate: DiscoveredPage,
        domain_limiter: DomainConcurrencyLimiter | None = None,
    ) -> FetchedPage:
        semaphore = None

        try:
            if domain_limiter is not None:
                domain = urlparse(candidate.url).netloc.lower()
                semaphore = domain_limiter.acquire(domain)

            return self.acquisition.fetch(FetchRequest(candidate.url))
        except Exception as exc:
            return FetchedPage(
                url=candidate.url,
                error=str(exc),
            )
        finally:
            if semaphore is not None:
                semaphore.release()

    def run(self, request: SearchRequest) -> ScrapeResult:
        existing_leads: list[Lead] = []

        if self.repository is not None:
            existing_leads = self.repository.search(
                keyword=request.keyword,
                location=request.location,
                limit=request.limit,
            )

        discovered = self.discovery.discover(request)
        fetched: list[FetchedPage] = []
        fetch_failures: list[FetchFailure] = []
        parsed_leads: list[Lead] = []
        parse_failures: list[ParseFailure] = []
        quality_checked_count = 0
        quality_accepted_count = 0
        quality_rejected_count = 0

        candidates: list[DiscoveredPage] = []

        for candidate in discovered:
            if self.relevance is not None and not self.relevance.is_relevant(candidate):
                continue

            if self.location_relevance is not None and not self.location_relevance.is_relevant(candidate):
                continue

            if self.category_relevance is not None and not self.category_relevance.is_relevant(candidate):
                continue

            if self.requirements_relevance is not None and not self.requirements_relevance.is_relevant(candidate):
                continue

            candidates.append(candidate)

        domain_limiter = (
            DomainConcurrencyLimiter(self.concurrency.per_domain_limit)
            if self.concurrency.per_domain_limit is not None
            else None
        )

        with BoundedExecutor(self.concurrency.global_limit) as executor:
            pages = executor.map(
                lambda candidate: self._fetch_candidate(candidate, domain_limiter),
                candidates,
            )

        for candidate, page in zip(candidates, pages):
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
                parser = self.parser_registry.resolve(
                    page.final_url or page.url
                )
                if parser is None:
                    parser = self.parser

                lead = parser.parse(page, category=request.keyword)

                if parser is not self.parser and lead is None:
                    lead = self.parser.parse(
                        page,
                        category=request.keyword,
                    )
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

            if not LocationValidator(request.location).is_relevant(lead):
                continue

            quality_checked_count += 1
            if not self.quality.is_valid(lead):
                quality_rejected_count += 1
                continue

            quality_accepted_count += 1
            parsed_leads.append(lead)

        leads = self.normalizer.deduplicate_leads(parsed_leads)

        if self.repository is not None:
            for lead in leads:
                self.repository.save(lead)

        return ScrapeResult(
            leads=leads,
            discovered=discovered,
            fetched=fetched,
            fetch_failures=fetch_failures,
            parse_failures=parse_failures,
            existing_leads=existing_leads,
            quality_checked_count=quality_checked_count,
            quality_accepted_count=quality_accepted_count,
            quality_rejected_count=quality_rejected_count,
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
    repository: LeadRepository | None = None,
) -> ScrapeResult:
    engine = ScraperEngine(
        discovery=discovery,
        fetcher=fetcher,
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
        repository=repository,
    )
    return engine.run(request)
