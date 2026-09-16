from __future__ import annotations

from typing import Protocol

from scraper.discovery import SearchRequest
from scraper.models import Lead


class SourceAdapter(Protocol):
    id: str

    def search(self, request: SearchRequest) -> list[Lead]:
        """Search a specialized source and return normalized leads."""
        ...


class SourceAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        key = self._normalize_source_id(adapter.id)
        if not key:
            raise ValueError("source adapter id must not be empty")
        self._adapters[key] = adapter

    def resolve(self, source_id: str) -> SourceAdapter | None:
        return self._adapters.get(self._normalize_source_id(source_id))

    def _normalize_source_id(self, value: str) -> str:
        return value.strip().lower()
