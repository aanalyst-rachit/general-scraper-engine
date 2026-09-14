from __future__ import annotations

from urllib.parse import urlsplit

from scraper.models import Lead


class LeadQuality:
    def is_valid(self, lead: Lead) -> bool:
        if not lead.name.strip():
            return False

        if not self._valid_source_url(lead.source_url):
            return False

        return any(
            value.strip()
            for value in (
                lead.phone,
                lead.email,
                lead.website,
                lead.address,
                lead.location,
            )
        )

    def _valid_source_url(self, value: str) -> bool:
        value = value.strip()
        if not value:
            return False

        try:
            parts = urlsplit(value)
        except ValueError:
            return False

        return parts.scheme.lower() in {"http", "https"} and bool(parts.netloc)
