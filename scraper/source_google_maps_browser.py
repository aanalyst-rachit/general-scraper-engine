from __future__ import annotations

import re
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

                page.set_default_timeout(
                    self.timeout * 1000
                )

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

                cards = self._extract_cards(
                    html,
                    limit=request.limit,
                )

                leads: list[Lead] = []

                for card in cards:
                    detail_url = card["source_url"]

                    detail = self._fetch_detail(
                        browser,
                        detail_url,
                    )

                    lead = self._build_lead(
                        card=card,
                        detail=detail,
                        search_context=query,
                        location=location,
                    )

                    leads.append(lead)

                    if len(leads) >= request.limit:
                        break

                return leads

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

    def _extract_cards(
        self,
        html: str,
        *,
        limit: int,
    ) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "lxml")

        cards: list[dict[str, str]] = []
        seen_urls: set[str] = set()

        for card in soup.select(
            'div.Nv2PK[role="article"]'
        ):
            if len(cards) >= limit:
                break

            link = next(
                (
                    candidate
                    for candidate in card.find_all(
                        "a",
                        href=True,
                    )
                    if "/maps/place/" in candidate.get(
                        "href",
                        "",
                    )
                ),
                None,
            )

            name_node = card.select_one(
                ".qBF1Pd"
            )

            if link is None or name_node is None:
                continue

            name = name_node.get_text(
                " ",
                strip=True,
            )

            source_url = link.get(
                "href",
                "",
            ).strip()

            if not name or not source_url:
                continue

            if source_url in seen_urls:
                continue

            seen_urls.add(source_url)

            cards.append(
                {
                    "name": name,
                    "source_url": source_url,
                }
            )

        return cards

    def _fetch_detail(
        self,
        browser,
        url: str,
    ) -> dict[str, str]:
        page = browser.new_page()

        try:
            page.set_default_timeout(
                self.timeout * 1000
            )

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.timeout * 1000,
            )

            if self.wait_for_timeout > 0:
                page.wait_for_timeout(
                    max(
                        self.wait_for_timeout,
                        2.0,
                    )
                    * 1000
                )

            html = page.content()

            if self._looks_blocked(
                html,
                page.url,
            ):
                return {}

            return self._parse_detail(html)

        except Exception:
            return {}

        finally:
            close = getattr(page, "close", None)

            if close is not None:
                close()

    def _parse_detail(
        self,
        html: str,
    ) -> dict[str, str]:
        soup = BeautifulSoup(
            html,
            "lxml",
        )

        text = soup.get_text(
            "\n",
            strip=True,
        )

        result: dict[str, str] = {}

        name_node = soup.select_one(
            "h1.DUwDvf"
        )

        if name_node is not None:
            result["name"] = name_node.get_text(
                " ",
                strip=True,
            )

        category_node = soup.select_one(
            "button.DkEaL"
        )

        if category_node is not None:
            result["category"] = (
                category_node.get_text(
                    " ",
                    strip=True,
                )
            )

        phone = self._extract_phone(
            soup,
            text,
        )

        if phone:
            result["phone"] = phone

        address = self._extract_address(
            soup,
            text,
        )

        if address:
            result["address"] = address

        website = self._extract_website(
            soup,
        )

        if website:
            result["website"] = website

        rating, reviews = self._extract_rating(
            soup,
        )

        if rating:
            result["rating"] = rating

        if reviews:
            result["reviews"] = reviews

        return result

    def _extract_phone(
        self,
        soup: BeautifulSoup,
        text: str,
    ) -> str:
        phone_link = soup.select_one(
            'a[href^="tel:"]'
        )

        if phone_link is not None:
            href = phone_link.get(
                "href",
                "",
            ).strip()

            if href.startswith("tel:"):
                phone = href[4:].strip()

                if phone:
                    return self._clean_phone(
                        phone
                    )

        phone_button = soup.select_one(
            '[data-item-id^="phone:"]'
        )

        if phone_button is not None:
            item_id = phone_button.get(
                "data-item-id",
                "",
            )

            if ":" in item_id:
                phone = item_id.split(
                    ":",
                    1,
                )[1].strip()

                if phone:
                    return self._clean_phone(
                        phone
                    )

        lines = [
            " ".join(
                line.split()
            )
            for line in text.splitlines()
            if line.strip()
        ]

        for index, line in enumerate(lines):
            if self._looks_like_phone(line):
                return self._clean_phone(
                    line
                )

            if line.lower() in {
                "phone",
                "mobile",
                "telephone",
            }:
                if index + 1 < len(lines):
                    candidate = lines[
                        index + 1
                    ]

                    if self._looks_like_phone(
                        candidate
                    ):
                        return self._clean_phone(
                            candidate
                        )

        return ""

    def _looks_like_phone(
        self,
        value: str,
    ) -> bool:
        digits = re.sub(
            r"\D",
            "",
            value,
        )

        return (
            10 <= len(digits) <= 15
            and len(value) <= 25
        )

    def _clean_phone(
        self,
        value: str,
    ) -> str:
        value = " ".join(
            value.split()
        ).strip()

        return value

    def _extract_address(
        self,
        soup: BeautifulSoup,
        text: str,
    ) -> str:
        address_button = soup.select_one(
            'button[data-item-id^="address"]'
        )

        if address_button is not None:
            value = address_button.get_text(
                " ",
                strip=True,
            )

            if value:
                return value

        address_link = soup.select_one(
            'a[href*="google.com/maps/dir"]'
        )

        if address_link is not None:
            value = address_link.get_text(
                " ",
                strip=True,
            )

            if value:
                return value

        lines = [
            " ".join(
                line.split()
            )
            for line in text.splitlines()
            if line.strip()
        ]

        for line in lines:
            lower = line.lower()

            if (
                "shahjahanpur" in lower
                or "uttar pradesh" in lower
            ):
                if not self._looks_like_phone(
                    line
                ):
                    return line

        return ""

    def _extract_website(
        self,
        soup: BeautifulSoup,
    ) -> str:
        excluded_domains = (
            "google.com",
            "googleusercontent.com",
            "gstatic.com",
            "justdial.com",
        )

        for link in soup.select(
            'a[href^="http"]'
        ):
            href = link.get(
                "href",
                "",
            ).strip()

            if not href:
                continue

            lower = href.lower()

            if any(
                domain in lower
                for domain in excluded_domains
            ):
                continue

            text = link.get_text(
                " ",
                strip=True,
            ).lower()

            aria = (
                link.get(
                    "aria-label",
                    "",
                )
                or ""
            ).lower()

            if (
                "website" in text
                or "website" in aria
                or "site" in text
            ):
                return href

        return ""

    def _extract_rating(
        self,
        soup: BeautifulSoup,
    ) -> tuple[str, str]:
        rating_node = soup.select_one(
            '[aria-label*="stars"]'
        )

        if rating_node is None:
            return "", ""

        aria = rating_node.get(
            "aria-label",
            "",
        )

        match = re.search(
            r"([0-5](?:\.\d+)?)\s*stars?"
            r".*?"
            r"([\d,]+)\s*Reviews?",
            aria,
            re.IGNORECASE,
        )

        if match is None:
            return "", ""

        return (
            match.group(1),
            match.group(2),
        )

    def _build_lead(
        self,
        *,
        card: dict[str, str],
        detail: dict[str, str],
        search_context: str,
        location: str,
    ) -> Lead:
        name = (
            detail.get("name")
            or card.get("name")
            or ""
        )

        return Lead(
            name=name,
            company_name=name,
            category=detail.get(
                "category",
                "",
            ),
            address=detail.get(
                "address",
                "",
            ),
            phone=detail.get(
                "phone",
                "",
            ),
            website=detail.get(
                "website",
                "",
            ),
            source_url=card.get(
                "source_url",
                "",
            ),
            source_name=self.id,
            search_context=search_context,
            location=location,
        )

    def _looks_blocked(
        self,
        html: str,
        final_url: str,
    ) -> bool:
        text = BeautifulSoup(
            html,
            "lxml",
        ).get_text(
            " ",
            strip=True,
        ).lower()

        markers = (
            "unusual traffic",
            "verify you are human",
            "captcha",
            "access denied",
            "automated queries",
        )

        return any(
            marker in text
            for marker in markers
        )


def default_browser_factory():
    from playwright.sync_api import sync_playwright

    return sync_playwright()