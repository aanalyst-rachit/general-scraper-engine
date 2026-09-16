from __future__ import annotations

from typing import Callable
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scraper.discovery import SearchRequest
from scraper.models import Lead


class JustdialBrowserAdapter:
    id = "justdial_browser"
    base_url = "https://www.justdial.com"

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

        city = location or "India"
        path = f"/{quote_plus(city)}/{quote_plus(keyword)}"
        url = f"{self.base_url}{path}"

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

                if self._looks_blocked_or_empty(html, final_url):
                    return []

                return self._parse_results(
                    html,
                    search_context=(
                        f"{keyword} {location}".strip()
                    ),
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

        cards = soup.select("div.store-details")

        if not cards:
            cards = soup.select(
                "div.resultbox, "
                "li.cntanr"
            )

        for card in cards:
            if len(leads) >= limit:
                break

            link = self._extract_listing_link(card)
            name = self._first_text(
                card,
                (
                    "h2",
                    "h3",
                    ".lng_cont_name",
                    ".store-name",
                ),
            )

            if not name or not link:
                continue

            if link in seen_urls:
                continue

            seen_urls.add(link)

            phone = self._first_text(
                card,
                (
                    ".contact-info .tel",
                    ".mobilesv",
                    ".contact-info",
                ),
            )
            address = self._first_text(
                card,
                (
                    ".cont_fl_addr",
                    ".address-info",
                    ".store-address",
                ),
            )
            category = self._first_text(
                card,
                (
                    ".catname",
                    ".store-category",
                    ".category",
                ),
            )
            website = self._extract_website(card)

            leads.append(
                Lead(
                    name=name,
                    company_name=name,
                    category=category,
                    address=address,
                    phone=phone,
                    website=website,
                    source_url=link,
                    source_name=self.id,
                    search_context=search_context,
                )
            )

        return leads

    def _extract_listing_link(self, card) -> str:
        for link in card.select("a[href]"):
            href = link.get("href", "").strip()

            if not href:
                continue

            if href.startswith("/"):
                return f"{self.base_url}{href}"

            if "justdial.com" in href.lower():
                return href

        return ""

    def _extract_website(self, container) -> str:
        for link in container.select("a[href]"):
            href = link.get("href", "").strip()

            if not href.startswith(("http://", "https://")):
                continue

            if "justdial.com" in href.lower():
                continue

            return href

        return ""

    def _first_text(self, container, selectors) -> str:
        for selector in selectors:
            node = container.select_one(selector)

            if node is None:
                continue

            value = " ".join(node.stripped_strings)
            if value:
                return value

        return ""

    def _looks_blocked_or_empty(
        self,
        html: str,
        final_url: str,
    ) -> bool:
        if not html.strip() or len(html.strip()) <= 32:
            return True

        text = BeautifulSoup(html, "lxml").get_text(
            " ", strip=True
        ).lower()

        markers = (
            "captcha",
            "verify you are human",
            "access denied",
            "unusual traffic",
            "automated queries",
            "robot check",
        )

        if any(marker in text for marker in markers):
            return True

        return (
            not text
            or final_url.lower().startswith(
                "https://www.justdial.com/login"
            )
        )


def default_browser_factory():
    from playwright.sync_api import sync_playwright

    return sync_playwright()
