from __future__ import annotations

from typing import Callable
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scraper.discovery import SearchRequest
from scraper.models import Lead


class GoogleMapsBrowserAdapter:
    id = "google_maps_browser"
    base_url = "https://www.google.com/maps/search/"

    def __init__(
        self,
        browser_factory: Callable[[], object],
        *,
        timeout: float = 15.0,
        wait_for_timeout: float = 1.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be > 0")
        if wait_for_timeout < 0:
            raise ValueError("wait_for_timeout must be >= 0")

        self.browser_factory = browser_factory
        self.timeout = float(timeout)
        self.wait_for_timeout = float(wait_for_timeout)

    def search(self, request: SearchRequest) -> list[Lead]:
        keyword = request.keyword.strip()
        location = request.location.strip()

        if not keyword or request.limit <= 0:
            return []

        query = keyword
        if location:
            query = f"{keyword} {location}"

        url = f"{self.base_url}?api=1&query={quote_plus(query)}"

        with self.browser_factory() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            try:
                page = browser.new_page()
                page.set_default_timeout(self.timeout * 1000)
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout * 1000,
                )

                if self.wait_for_timeout > 0:
                    page.wait_for_timeout(
                        self.wait_for_timeout * 1000
                    )

                html = page.content()
                final_url = page.url

                if self._looks_blocked(html, final_url):
                    return []

                return self._parse_results(
                    html,
                    search_context=query,
                    limit=request.limit,
                )
            finally:
                browser.close()

    def _parse_results(
        self,
        html: str,
        *,
        search_context: str,
        limit: int,
    ) -> list[Lead]:
        soup = BeautifulSoup(html, "lxml")
        leads: list[Lead] = []
        seen_urls: set[str] = set()

        for card in soup.select("div.Nv2PK[role=article]"):
            if len(leads) >= limit:
                break

            link = next(
                (
                    candidate
                    for candidate in card.find_all("a", href=True)
                    if "/maps/place/" in candidate.get("href", "")
                ),
                None,
            )
            name_node = card.select_one(".qBF1Pd")

            if link is None or name_node is None:
                continue

            name = name_node.get_text(" ", strip=True)
            href = link.get("href", "").strip()

            if not name or not href or href in seen_urls:
                continue

            seen_urls.add(href)

            phone_node = card.select_one(".UsdlK")
            phone = (
                phone_node.get_text(" ", strip=True)
                if phone_node is not None
                else ""
            )

            rows = [
                " ".join(row.get_text(" ", strip=True).split())
                for row in card.select("div.W4Efsd")
            ]

            category = ""
            address = ""

            address_row = next(
                (
                    row
                    for row in rows
                    if "·" in row
                    and not any(
                        marker in row.lower()
                        for marker in ("open", "closed", "closes", "opens")
                    )
                ),
                "",
            )

            if address_row:
                parts = [
                    "".join(
                        ch
                        for ch in part
                        if not 0xE000 <= ord(ch) <= 0xF8FF
                    ).strip()
                    for part in address_row.split("·")
                    if part.strip()
                ]
                parts = [part for part in parts if part]

                if parts:
                    category = parts[0]
                if len(parts) > 1:
                    address = " · ".join(parts[1:])

            website = self._extract_website(card)

            leads.append(
                Lead(
                    name=name,
                    company_name=name,
                    category=category,
                    address=address,
                    phone=phone,
                    website=website,
                    source_url=href,
                    source_name=self.id,
                    search_context=search_context,
                )
            )

        return leads

    def _extract_website(self, container) -> str:
        excluded_domains = (
            "google.com",
            "justdial.com",
        )

        for link in container.select("a[href]"):
            href = link.get("href", "").strip()

            if not href.startswith(("http://", "https://")):
                continue

            if any(domain in href.lower() for domain in excluded_domains):
                continue

            return href

        return ""

    def _looks_blocked(self, html: str, final_url: str) -> bool:
        text = BeautifulSoup(html, "lxml").get_text(
            " ", strip=True
        ).lower()

        markers = (
            "unusual traffic",
            "verify you are human",
            "captcha",
            "access denied",
            "automated queries",
        )

        return any(marker in text for marker in markers)


def default_browser_factory():
    from playwright.sync_api import sync_playwright

    return sync_playwright()
