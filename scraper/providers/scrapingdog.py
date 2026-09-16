from __future__ import annotations

import os

import httpx

from scraper.acquisition import ExternalFetchRequest, ExternalFetcher
from scraper.fetcher import FetchedPage


class ScrapingdogProvider(ExternalFetcher):
    """Optional Scrapingdog scraping adapter."""

    endpoint = "https://api.scrapingdog.com/scrape"

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = (
            api_key or os.getenv("SCRAPINGDOG_API_KEY", "")
        ).strip()

        if not self.api_key:
            raise ValueError("Scrapingdog API key must not be empty")

        self.client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def fetch(self, request: ExternalFetchRequest) -> FetchedPage:
        url = request.url.strip()

        if not url:
            return FetchedPage(
                url=request.url,
                error="URL must not be empty",
            )

        params = {
            "api_key": self.api_key,
            "url": url,
        }

        if request.render:
            params["dynamic"] = "true"

        try:
            response = self.client.get(
                self.endpoint,
                params=params,
            )
            response.raise_for_status()
        except Exception as exc:
            return FetchedPage(
                url=url,
                error=str(exc),
            )

        html = response.text
        content_type = response.headers.get("content-type", "")

        if not html:
            return FetchedPage(
                url=url,
                status_code=response.status_code,
                content_type=content_type,
                error="Scrapingdog returned empty content",
            )

        return FetchedPage(
            url=url,
            final_url=url,
            status_code=response.status_code,
            content_type=content_type,
            html=html,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
