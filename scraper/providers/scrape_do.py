from __future__ import annotations

import os

import httpx

from scraper.acquisition import ExternalFetchRequest, ExternalFetcher
from scraper.fetcher import FetchedPage


class ScrapeDoProvider(ExternalFetcher):
    """Optional Scrape.do scraping adapter."""

    endpoint = "https://api.scrape.do/"

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = (api_key or os.getenv("SCRAPE_DO_API_KEY", "")).strip()
        if not self.api_key:
            raise ValueError("Scrape.do API key must not be empty")

        self.client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def fetch(self, request: ExternalFetchRequest) -> FetchedPage:
        url = request.url.strip()

        if not url:
            return FetchedPage(url=request.url, error="URL must not be empty")

        params = {
            "token": self.api_key,
            "url": url,
        }

        if request.timeout is not None:
            params["timeout"] = int(request.timeout * 1000)

        if request.render:
            params["render"] = "true"

        try:
            response = self.client.get(
                self.endpoint,
                params=params,
            )
            response.raise_for_status()
        except Exception as exc:
            return FetchedPage(url=url, error=str(exc))

        html = response.text
        final_url = response.headers.get(
            "Scrape.do-Resolved-Url",
            url,
        ).strip() or url

        if not html:
            return FetchedPage(
                url=url,
                final_url=final_url,
                status_code=response.status_code,
                content_type=response.headers.get("content-type", ""),
                error="Scrape.do returned empty content",
            )

        return FetchedPage(
            url=url,
            final_url=final_url,
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            html=html,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
