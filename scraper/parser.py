import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.extraction import ExtractionStrategy
from scraper.registry import ExtractionRegistry
from scraper.fetcher import FetchedPage
from scraper.models import Lead
from scraper.structured_data import StructuredDataExtractor


class PageParser:
    def __init__(
        self,
        structured_data: ExtractionStrategy | None = None,
        extraction_registry: ExtractionRegistry | None = None,
    ) -> None:
        if extraction_registry is None:
            extraction_registry = ExtractionRegistry()
            extraction_registry.register(
                structured_data or StructuredDataExtractor()
            )
        self.extraction_registry = extraction_registry

    def parse(self, page: FetchedPage, category: str = "") -> Lead | None:
        if not page.ok:
            return None

        soup = BeautifulSoup(page.html, "lxml")
        structured = self.extraction_registry.extract(page.html) or {}

        name = self._first_nonempty(
            structured.get("name", ""), 
            self._meta(soup, "og:title"), 
            self._meta(soup, "twitter:title"), 
            self._text(soup.title), 
        )

        if not name:
            return None

        description = self._first_nonempty(
            structured.get("description", ""), 
            self._meta(soup, "description"), 
            self._meta(soup, "og:description"), 
        )

        address = self._first_nonempty(
            structured.get("address", ""),
            self._extract_address(soup),
        )
        phone = self._first_nonempty(
            structured.get("telephone", ""), 
            self._extract_phone(soup.get_text(" ", strip=True)), 
        )
        email = self._first_nonempty(
            structured.get("email", ""), 
            self._extract_email(soup), 
        )

        website = structured.get("url", "").strip()

        location = self._first_nonempty(
            structured.get("address_locality", ""), 
            structured.get("address_region", ""), 
            address, 
        )

        return Lead(
            name=name,
            category=self._first_nonempty(
                structured.get("category", ""), 
                category, 
            ),
            location=location,
            address=address,
            phone=phone,
            email=email,
            website=self._absolute_url(website, page.final_url or page.url),
            description=description,
            source_url=page.final_url or page.url,
            source_name="web",
            extra={"title": self._text(soup.title)},
        )

    def _meta(self, soup: BeautifulSoup, name: str) -> str:
        tag = soup.find("meta", attrs={"property": name})
        if tag is None:
            tag = soup.find("meta", attrs={"name": name})
        if tag is None:
            return ""
        return str(tag.get("content", "")).strip()

    def _text(self, tag) -> str:
        if tag is None:
            return ""
        return tag.get_text(" ", strip=True)

    def _extract_address(self, soup: BeautifulSoup) -> str:
        address_tag = soup.find("address")
        if address_tag is not None:
            value = address_tag.get_text(" ", strip=True)
            if value:
                return value

        for name in ("address", "street-address"):
            value = self._meta(soup, name)
            if value:
                return value

        for property_name in ("og:street-address", "og:address"):
            value = self._meta(soup, property_name)
            if value:
                return value

        return ""

    def _extract_email(self, soup: BeautifulSoup) -> str:
        for link in soup.find_all("a", href=True):
            href = str(link.get("href", ""))
            if href.lower().startswith("mailto:"):
                return href[7:].split("?", 1)[0].strip()

        text = soup.get_text(" ", strip=True)
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}", text)
        return match.group(0) if match else ""

    def _extract_phone(self, text: str) -> str:
        patterns = [
            r"(?<![0-9])\(\d{3,5}\)[ -]?\d{5,8}(?![0-9])",
            r"(?<![0-9])\+\d{1,3}[ -]?\d{5}[ -]?\d{5}(?![0-9])",
            r"(?<![0-9])\+\d{1,3}[ -]?\d{10}(?![0-9])",
            r"(?<![0-9])\d{10}(?![0-9])",
            r"(?<![0-9])\d{4,6}[ -]?\d{5,8}(?![0-9])",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()

        return ""

    def _absolute_url(self, url: str, base_url: str) -> str:
        if not url:
            return ""
        return urljoin(base_url, url)

    def _first_nonempty(self, *values: str) -> str:
        for value in values:
            value = str(value).strip()
            if value:
                return value
        return ""
