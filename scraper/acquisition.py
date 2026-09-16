from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from scraper.cache.fetch import FetchCache
from scraper.content_quality import ContentQualityClassifier
from scraper.fetcher import FetchedPage, PageFetcher


@dataclass(frozen=True)
class FetchRequest:
    url: str


@dataclass(frozen=True)
class ExternalFetchRequest:
    """Provider-neutral request contract for external acquisition services."""

    url: str
    render: bool = False
    timeout: float | None = None


class AcquisitionStrategy(Protocol):
    def fetch(self, request: FetchRequest) -> FetchedPage:
        ...


class ExternalFetcher(Protocol):
    """Provider-neutral interface implemented by external scraping adapters."""

    def fetch(self, request: ExternalFetchRequest) -> FetchedPage:
        ...


class PolicyAwareExternalFetcher:
    "Wrap an external provider with existing fetch policy checks."

    def __init__(
        self,
        provider: ExternalFetcher,
        policy: PageFetcher | None = None,
    ) -> None:
        self.provider = provider
        self.policy = policy or PageFetcher()

    def fetch(self, request: ExternalFetchRequest) -> FetchedPage:
        url = request.url.strip()

        if not url:
            return FetchedPage(url=request.url, error="empty URL")

        try:
            if not self.policy.can_fetch(url):
                return FetchedPage(
                    url=url,
                    error="blocked by robots.txt",
                )

            self.policy.wait_for_request_delay(url)
        except Exception as exc:
            return FetchedPage(
                url=url,
                error=f"fetch policy check failed: {exc}",
            )

        return self.provider.fetch(request)


class HTTPFetcherAdapter:
    def __init__(self, fetcher: PageFetcher | None = None) -> None:
        self.fetcher = fetcher or PageFetcher()

    def fetch(self, request: FetchRequest) -> FetchedPage:
        return self.fetcher.fetch(request.url)


class CachedFetcher:
    def __init__(
        self,
        acquisition: AcquisitionStrategy,
        cache: FetchCache,
        acquisition_strategy: str = "auto",
    ) -> None:
        self.acquisition = acquisition
        self.cache = cache
        self.acquisition_strategy = acquisition_strategy

    def fetch(self, request: FetchRequest) -> FetchedPage:
        cached = self.cache.get(
            url=request.url,
            acquisition_strategy=self.acquisition_strategy,
        )
        if cached is not None:
            return cached.to_fetched_page()

        page = self.acquisition.fetch(request)

        if page.ok:
            self.cache.set(
                url=request.url,
                acquisition_strategy=self.acquisition_strategy,
                status_code=page.status_code,
                content_type=page.content_type,
                html=page.html,
                final_url=page.final_url,
            )

        return page


class AutoFetcher:
    def __init__(
        self,
        http_fetcher: PageFetcher | AcquisitionStrategy | None = None,
        browser_fetcher: AcquisitionStrategy | None = None,
        content_quality: ContentQualityClassifier | None = None,
    ) -> None:
        self.http = HTTPFetcherAdapter(http_fetcher)
        if browser_fetcher is None:
            from scraper.browser_fetcher import BrowserFetcher
            browser_fetcher = BrowserFetcher()
        self.browser = browser_fetcher
        self.content_quality = content_quality or ContentQualityClassifier()

    def fetch(self, request: FetchRequest) -> FetchedPage:
        page = self.http.fetch(request)
        quality = self.content_quality.classify(page)

        if quality.needs_browser_fallback:
            return self.browser.fetch(request)

        return page
