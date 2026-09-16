from __future__ import annotations

from typing import Protocol
from urllib.parse import urlparse

from scraper.extraction import ExtractionResult, ExtractionStrategy
from scraper.fetcher import FetchedPage
from scraper.models import Lead


class ParserStrategy(Protocol):
    def parse(self, page: FetchedPage, category: str = "") -> Lead | None:
        """Parse a fetched page into a lead."""
        ...


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, ParserStrategy] = {}

    def register(self, domain: str, parser: ParserStrategy) -> None:
        key = self._normalize_domain(domain)
        if not key:
            raise ValueError("domain must not be empty")
        self._parsers[key] = parser

    def resolve(self, url: str) -> ParserStrategy | None:
        domain = self._normalize_domain(urlparse(url).netloc)
        return self._parsers.get(domain)

    def _normalize_domain(self, value: str) -> str:
        return value.strip().lower().rstrip(".")


class ExtractionRegistry:
    def __init__(self) -> None:
        self._strategies: list[ExtractionStrategy] = []

    def register(self, strategy: ExtractionStrategy) -> None:
        self._strategies.append(strategy)

    def extract(self, html: str) -> ExtractionResult | None:
        for strategy in self._strategies:
            result = strategy.extract(html)
            if result is not None:
                return result
        return None
