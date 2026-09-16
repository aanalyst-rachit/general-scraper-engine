from __future__ import annotations

from typing import Protocol


ExtractionResult = dict[str, str]


class ExtractionStrategy(Protocol):
    def extract(self, html: str) -> ExtractionResult | None:
        """Extract structured lead fields from page HTML."""
        ...
