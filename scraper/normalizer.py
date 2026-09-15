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
            profession=self.normalize_text(lead.profession),
            company_name=self.normalize_text(lead.company_name),
            category=self.normalize_text(lead.category),
            subcategory=self.normalize_text(lead.subcategory),
            designation=self.normalize_text(lead.designation),
            specialization=self.normalize_text(lead.specialization),
            services=self.normalize_text(lead.services),
            description=self.normalize_text(lead.description),
            phone=self.normalize_phone(lead.phone),
            alternate_phone=self.normalize_phone(lead.alternate_phone),
            email=self.normalize_email(lead.email),
            alternate_email=self.normalize_email(lead.alternate_email),
            website=self.normalize_url(lead.website),
            address=self.normalize_text(lead.address),
            location=self.normalize_text(lead.location),
            locality=self.normalize_text(lead.locality),
            city=self.normalize_text(lead.city),
            district=self.normalize_text(lead.district),
            state=self.normalize_text(lead.state),
            country=self.normalize_text(lead.country),
            pincode=self.normalize_text(lead.pincode),
            social_profiles={
                self.normalize_text(key): self.normalize_url(value)
                for key, value in lead.social_profiles.items()
                if self.normalize_text(key) and self.normalize_text(value)
            },
            source_url=self.normalize_url(lead.source_url),
            source_name=self.normalize_text(lead.source_name),
            source_id=self.normalize_text(lead.source_id),
            search_context=self.normalize_text(lead.search_context),
            extra=dict(lead.extra),
            raw_data=dict(lead.raw_data),
        )

    def lead_identity_keys(self, lead: Lead) -> list[str]:
        name = self.normalize_name(lead.name)
        company_name = self.normalize_name(lead.company_name)
        profession = self.normalize_name(lead.profession)

        phone = self.normalize_phone(lead.phone)
        alternate_phone = self.normalize_phone(lead.alternate_phone)

        email = self.normalize_email(lead.email)
        alternate_email = self.normalize_email(lead.alternate_email)

        website = self.normalize_url(lead.website)
        address = self.normalize_name(lead.address)

        location = self.normalize_name(
            lead.city or lead.location
        )

        keys: list[str] = []

        for value in [phone, alternate_phone]:
            if value:
                keys.append(f"phone:{value}")

        for value in [email, alternate_email]:
            if value:
                keys.append(f"email:{value}")

        if website and name:
            keys.append(f"website-name:{website}|{name}")

        if website and company_name:
            keys.append(f"website-company:{website}|{company_name}")

        if name and address:
            keys.append(f"name-address:{name}|{address}")

        if company_name and address:
            keys.append(
                f"company-address:{company_name}|{address}"
            )

        if name and profession and location:
            keys.append(
                f"name-profession-location:"
                f"{name}|{profession}|{location}"
            )

        return keys

    def merge_leads(self, primary: Lead, secondary: Lead) -> Lead:
        merged = Lead(
            name=self._prefer(primary.name, secondary.name),
            profession=self._prefer(
                primary.profession,
                secondary.profession,
            ),
            company_name=self._prefer(
                primary.company_name,
                secondary.company_name,
            ),
            category=self._prefer(
                primary.category,
                secondary.category,
            ),
            subcategory=self._prefer(
                primary.subcategory,
                secondary.subcategory,
            ),
            designation=self._prefer(
                primary.designation,
                secondary.designation,
            ),
            specialization=self._prefer(
                primary.specialization,
                secondary.specialization,
            ),
            services=self._prefer(
                primary.services,
                secondary.services,
            ),
            description=self._prefer(
                primary.description,
                secondary.description,
            ),
            phone=self._prefer(primary.phone, secondary.phone),
            alternate_phone=self._prefer(
                primary.alternate_phone,
                secondary.alternate_phone,
            ),
            email=self._prefer(primary.email, secondary.email),
            alternate_email=self._prefer(
                primary.alternate_email,
                secondary.alternate_email,
            ),
            website=self._prefer(
                primary.website,
                secondary.website,
            ),
            address=self._prefer(
                primary.address,
                secondary.address,
            ),
            location=self._prefer(
                primary.location,
                secondary.location,
            ),
            locality=self._prefer(
                primary.locality,
                secondary.locality,
            ),
            city=self._prefer(primary.city, secondary.city),
            district=self._prefer(
                primary.district,
                secondary.district,
            ),
            state=self._prefer(primary.state, secondary.state),
            country=self._prefer(
                primary.country,
                secondary.country,
            ),
            pincode=self._prefer(
                primary.pincode,
                secondary.pincode,
            ),
            social_profiles=dict(primary.social_profiles),
            source_url=self._prefer(
                primary.source_url,
                secondary.source_url,
            ),
            source_name=self._prefer(
                primary.source_name,
                secondary.source_name,
            ),
            source_id=self._prefer(
                primary.source_id,
                secondary.source_id,
            ),
            search_context=self._prefer(
                primary.search_context,
                secondary.search_context,
            ),
            extra=dict(primary.extra),
            raw_data=dict(primary.raw_data),
        )

        for key, value in secondary.social_profiles.items():
            if (
                key not in merged.social_profiles
                or not str(merged.social_profiles[key]).strip()
            ):
                merged.social_profiles[key] = value

        for key, value in secondary.extra.items():
            if key not in merged.extra or not str(merged.extra[key]).strip():
                merged.extra[key] = value

        for key, value in secondary.raw_data.items():
            if key not in merged.raw_data or not merged.raw_data[key]:
                merged.raw_data[key] = value

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
                (
                    key_to_index[key]
                    for key in keys
                    if key in key_to_index
                ),
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
            for value in [
                lead.source_url,
                str(lead.extra.get("source_urls", "")),
            ]:
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
