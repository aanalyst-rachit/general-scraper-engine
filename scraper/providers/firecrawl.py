from __future__ import annotations

import os

import httpx

from scraper.acquisition import ExternalFetchRequest, ExternalFetcher
from scraper.fetcher import FetchedPage


class FirecrawlProvider(ExternalFetcher):
    """Optional Firecrawl scraping adapter."""

    endpoint = "https://api.firecrawl.dev/v2/scrape"

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = (api_key or os.getenv("FIRECRAWL_API_KEY", "")).strip()
        if not self.api_key:
            raise ValueError("Firecrawl API key must not be empty")

        self.client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def fetch(self, request: ExternalFetchRequest) -> FetchedPage:
        url = request.url.strip()
        if not url:
            return FetchedPage(url=request.url, error="URL must not be empty")

        payload = {
            "url": url,
            "formats": ["html"],
        }

        if request.timeout is not None:
            payload["timeout"] = int(request.timeout * 1000)

        try:
            response = self.client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
        except Exception as exc:
            return FetchedPage(url=url, error=str(exc))

        if not isinstance(result, dict):
            return FetchedPage(
                url=url,
                error="Firecrawl returned an invalid response",
            )

        data = result.get("data")
        if not isinstance(data, dict):
            return FetchedPage(
                url=url,
                error="Firecrawl response does not contain page data",
            )

        html = str(data.get("html", "") or "")
        metadata = data.get("metadata")
        final_url = url

        if isinstance(metadata, dict):
            final_url = str(metadata.get("url", "") or url).strip() or url

        if not html:
            return FetchedPage(
                url=url,
                final_url=final_url,
                error="Firecrawl returned empty HTML",
            )

        return FetchedPage(
            url=url,
            final_url=final_url,
            status_code=200,
            content_type="text/html",
            html=html,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
