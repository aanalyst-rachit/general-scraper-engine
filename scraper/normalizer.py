from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from scraper.models import Lead


class LeadNormalizer:
    def normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def normalize_name(self, value: str) -> str:
        return self.normalize_text(value).casefold()

    def normalize_phone(self, value: str) -> str:
        value = self.normalize_text(value)
        if not value:
            return ""

        digits = re.sub(r"[^0-9+]", "", value)
        if digits.startswith("00"):
            digits = "+" + digits[2:]

        if digits.startswith("+"):
            return "+" + re.sub(r"[^0-9]", "", digits[1:])

        return re.sub(r"[^0-9]", "", digits)

    def normalize_email(self, value: str) -> str:
        return self.normalize_text(value).casefold()

    def normalize_url(self, value: str) -> str:
        value = self.normalize_text(value)
        if not value:
            return ""

        if not re.match(r"^[a-z][a-z0-9+.-]*://", value, re.IGNORECASE):
            value = "https://" + value

        try:
            parts = urlsplit(value)
        except ValueError:
            return value.casefold().rstrip("/")

        scheme = parts.scheme.casefold()
        netloc = parts.netloc.casefold()
        path = parts.path.rstrip("/")
        return urlunsplit((scheme, netloc, path, parts.query, ""))

    def normalize_lead(self, lead: Lead) -> Lead:
        return Lead(
            name=self.normalize_text(lead.name),
            category=self.normalize_text(lead.category),
            location=self.normalize_text(lead.location),
            address=self.normalize_text(lead.address),
            phone=self.normalize_phone(lead.phone),
            email=self.normalize_email(lead.email),
            website=self.normalize_url(lead.website),
            description=self.normalize_text(lead.description),
            source_url=self.normalize_url(lead.source_url),
            source_name=self.normalize_text(lead.source_name),
            extra=dict(lead.extra),
        )

    def lead_identity_keys(self, lead: Lead) -> list[str]:
        name = self.normalize_name(lead.name)
        phone = self.normalize_phone(lead.phone)
        email = self.normalize_email(lead.email)
        website = self.normalize_url(lead.website)
        address = self.normalize_name(lead.address)
        location = self.normalize_name(lead.location)

        keys: list[str] = []

        if phone:
            keys.append(f"phone:{phone}")

        if email:
            keys.append(f"email:{email}")

        if website and name:
            keys.append(f"website-name:{website}|{name}")

        if name and address:
            keys.append(f"name-address:{name}|{address}")
        elif name and location:
            keys.append(f"name-location:{name}|{location}")

        return keys

    def merge_leads(self, primary: Lead, secondary: Lead) -> Lead:
        merged = Lead(
            name=self._prefer(primary.name, secondary.name),
            category=self._prefer(primary.category, secondary.category),
            location=self._prefer(primary.location, secondary.location),
            address=self._prefer(primary.address, secondary.address),
            phone=self._prefer(primary.phone, secondary.phone),
            email=self._prefer(primary.email, secondary.email),
            website=self._prefer(primary.website, secondary.website),
            description=self._prefer(primary.description, secondary.description),
            source_url=self._prefer(primary.source_url, secondary.source_url),
            source_name=self._prefer(primary.source_name, secondary.source_name),
            extra=dict(primary.extra),
        )

        for key, value in secondary.extra.items():
            if key not in merged.extra or not str(merged.extra[key]).strip():
                merged.extra[key] = value

        sources = self._source_values(primary, secondary)
        if sources:
            merged.extra["source_urls"] = " | ".join(sources)

        return merged

    def deduplicate_leads(self, leads: list[Lead]) -> list[Lead]:
        unique: list[Lead] = []
        key_to_index: dict[str, int] = {}

        for raw_lead in leads:
            lead = self.normalize_lead(raw_lead)
            keys = self.lead_identity_keys(lead)

            matching_index = next(
                (key_to_index[key] for key in keys if key in key_to_index),
                None,
            )

            if matching_index is None:
                unique.append(lead)
                index = len(unique) - 1
            else:
                unique[matching_index] = self.merge_leads(
                    unique[matching_index],
                    lead,
                )
                index = matching_index

            for key in keys:
                key_to_index[key] = index

        return unique

    def _prefer(self, first: str, second: str) -> str:
        first = self.normalize_text(first)
        second = self.normalize_text(second)
        return first or second

    def _source_values(self, *leads: Lead) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()

        for lead in leads:
            for value in [lead.source_url, str(lead.extra.get("source_urls", ""))]:
                for source in value.split(" | "):
                    source = self.normalize_url(source)
                    if source and source not in seen:
                        seen.add(source)
                        values.append(source)

        return values


def normalize_lead(lead: Lead) -> Lead:
    return LeadNormalizer().normalize_lead(lead)


def deduplicate_leads(leads: list[Lead]) -> list[Lead]:
    return LeadNormalizer().deduplicate_leads(leads)
