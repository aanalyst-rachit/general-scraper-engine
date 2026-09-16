from __future__ import annotations

import re

from scraper.models import Lead


class LocationValidator:
    """Validate extracted lead location against the requested location."""

    _LOCATION_FIELDS = (
        "locality",
        "city",
        "district",
        "state",
        "country",
        "location",
        "address",
    )

    def __init__(self, requested_location: str) -> None:
        self.requested_location = requested_location.strip()
        self.tokens = self._tokenize(self.requested_location)

    def is_relevant(self, lead: Lead) -> bool:
        if not self.tokens:
            return True

        evidence = {
            field: self._tokenize(getattr(lead, field, ""))
            for field in self._LOCATION_FIELDS
        }
        evidence_tokens = set().union(*evidence.values())

        if not evidence_tokens:
            return False

        requested_matches = any(
            self._matches_requested(tokens)
            for tokens in evidence.values()
            if tokens
        )
        if not requested_matches:
            return False

        for field in ("location", "address"):
            tokens = evidence[field]
            if tokens and not self._matches_requested(tokens):
                return False

        return True

    def _matches_requested(self, evidence_tokens: set[str]) -> bool:
        return all(
            token in evidence_tokens
            or f"{token}s" in evidence_tokens
            for token in self.tokens
        )

    @staticmethod
    def _tokenize(value: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", str(value or "").casefold()))
