from __future__ import annotations

from urllib.parse import urljoin

import httpx

from scraper.discovery import DiscoveredPage


class SearXNGProvider:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        client: httpx.Client | None = None,
        timeout: float = 15.0,
    ) -> None:
        base_url = base_url.strip().rstrip("/")
        if not base_url:
            raise ValueError("base_url must not be empty")

        self.base_url = base_url
        self.client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def search(self, query: str, limit: int = 20) -> list[DiscoveredPage]:
        query = query.strip()
        if not query or limit <= 0:
            return []

        results: list[DiscoveredPage] = []
        seen_urls: set[str] = set()
        page_number = 1

        while len(results) < limit:
            response = self.client.get(
                urljoin(f"{self.base_url}/", "search"),
                params={
                    "q": query,
                    "format": "json",
                    "pageno": page_number,
                },
            )
            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, dict):
                break

            raw_results = payload.get("results", [])
            if not isinstance(raw_results, list) or not raw_results:
                break

            added_this_page = 0

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
                        snippet=str(item.get("content", "")).strip(),
                        source_name="searxng",
                    )
                )
                added_this_page += 1

                if len(results) >= limit:
                    break

            if len(results) >= limit:
                break

            if added_this_page == 0:
                break

            page_number += 1

        return results

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
