from __future__ import annotations

from typing import Protocol, runtime_checkable

from scraper.models import Lead


@runtime_checkable
class LeadRepository(Protocol):
    def save(self, lead: Lead) -> Lead:
        ...

    def search(
        self,
        keyword: str = "",
        location: str = "",
        limit: int = 50,
    ) -> list[Lead]:
        ...
