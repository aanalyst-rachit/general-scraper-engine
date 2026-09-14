import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.fetcher import FetchedPage
from scraper.models import Lead


class PageParser:
    def parse(self, page: FetchedPage, category: str = "") -> Lead | None:
        if not page.ok:
            return None

        soup = BeautifulSoup(page.html, "lxml")
        structured = self._parse_json_ld(soup)

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

    def _parse_json_ld(self, soup: BeautifulSoup) -> dict[str, str]:
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text()
            if not raw.strip():
                continue

            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            candidates = data if isinstance(data, list) else [data]

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                if "@graph" in item and isinstance(item["@graph"], list):
                    candidates.extend(
                        node for node in item["@graph"]
                        if isinstance(node, dict)
                    )

                if self._looks_like_entity(item):
                    return self._structured_fields(item)

        return {}

    def _looks_like_entity(self, data: dict) -> bool:
        entity_type = data.get("@type", "")

        if isinstance(entity_type, list):
            entity_types = {str(value).lower() for value in entity_type}
        else:
            entity_types = {str(entity_type).lower()}

        useful_types = {
            "person",
            "organization",
            "localbusiness",
            "professionalservice",
            "medicalbusiness",
            "physician",
            "dentist",
            "restaurant",
            "store",
            "educationalorganization",
            "realestateagent",
        }

        return bool(entity_types & useful_types) and bool(data.get("name"))

    def _structured_fields(self, data: dict) -> dict[str, str]:
        address = data.get("address", "")

        if isinstance(address, dict):
            parts = [
                address.get("streetAddress", ""), 
                address.get("addressLocality", ""), 
                address.get("addressRegion", ""), 
                address.get("postalCode", ""), 
                address.get("addressCountry", ""), 
            ]
            address_text = ", ".join(
                str(part).strip() for part in parts if str(part).strip()
            )
        else:
            address_text = str(address).strip()

        category = data.get("category", "")
        if isinstance(category, list):
            category = ", ".join(str(value) for value in category)

        if not str(category).strip():
            entity_type = data.get("@type", "")
            if isinstance(entity_type, list):
                category = ", ".join(str(value) for value in entity_type)
            else:
                category = str(entity_type).strip()

        return {
            "name": str(data.get("name", "")).strip(),
            "description": str(data.get("description", "")).strip(),
            "telephone": str(data.get("telephone", "")).strip(),
            "email": str(data.get("email", "")).strip(),
            "url": str(data.get("url", "")).strip(),
            "category": str(category).strip(),
            "address": address_text,
            "address_locality": str(
                address.get("addressLocality", "") if isinstance(address, dict) else ""
            ).strip(),
            "address_region": str(
                address.get("addressRegion", "") if isinstance(address, dict) else ""
            ).strip(),
        }

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
