from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from scraper.content_quality import ContentQualityClassifier
from scraper.fetcher import FetchedPage, PageFetcher


@dataclass(frozen=True)
class FetchRequest:
    url: str


class AcquisitionStrategy(Protocol):
    def fetch(self, request: FetchRequest) -> FetchedPage:
        ...


class HTTPFetcherAdapter:
    def __init__(self, fetcher: PageFetcher | None = None) -> None:
        self.fetcher = fetcher or PageFetcher()

    def fetch(self, request: FetchRequest) -> FetchedPage:
        return self.fetcher.fetch(request.url)


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
