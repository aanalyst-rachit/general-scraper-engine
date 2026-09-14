from __future__ import annotations

import os

import httpx

from scraper.discovery import DiscoveredPage


class BraveSearchProvider:
    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 15.0,
        country: str = "IN",
        search_lang: str = "en",
    ) -> None:
        self.api_key = (api_key or os.getenv("BRAVE_SEARCH_API_KEY", "")).strip()
        if not self.api_key:
            raise ValueError("Brave Search API key must not be empty")

        self.country = country.strip().upper()
        self.search_lang = search_lang.strip().lower()
        if not self.country:
            raise ValueError("Brave Search country must not be empty")
        if not self.search_lang:
            raise ValueError("Brave Search language must not be empty")

        self.client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def search(self, query: str, limit: int = 20) -> list[DiscoveredPage]:
        query = query.strip()
        if not query or limit <= 0:
            return []

        response = self.client.get(
            self.endpoint,
            headers={
                "X-Subscription-Token": self.api_key,
                "Accept": "application/json",
            },
            params={
                "q": query,
                "count": min(limit, 20),
                "country": self.country,
                "search_lang": self.search_lang,
            },
        )
        response.raise_for_status()
        payload = response.json()

        web = payload.get("web", {})
        if not isinstance(web, dict):
            return []

        raw_results = web.get("results", [])
        if not isinstance(raw_results, list):
            return []

        results: list[DiscoveredPage] = []
        seen_urls: set[str] = set()

        for item in raw_results:
            if not isinstance(item, dict):
                continue

            url = str(item.get("url", "")).strip()
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)
            results.append(
                DiscoveredPage(
                    url=url,
                    title=str(item.get("title", "")).strip(),
                    snippet=str(item.get("description", "")).strip(),
                    source_name="brave",
                )
            )

            if len(results) >= limit:
                break

        return results

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
