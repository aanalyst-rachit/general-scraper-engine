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

    def measure(self, leads: list[Lead]) -> dict[str, int]:
        """Measure accepted and rejected leads independently of fetch results."""
        checked = len(leads)
        accepted = sum(1 for lead in leads if self.is_valid(lead))
        return {
            "checked": checked,
            "accepted": accepted,
            "rejected": checked - accepted,
        }

    def dimensions(self, lead: Lead) -> dict[str, bool]:
        """Report deterministic evidence across lead-quality dimensions."""
        return {
            "identity": bool(lead.name.strip()),
            "contact": any(
                value.strip()
                for value in (lead.phone, lead.alternate_phone, lead.email, lead.alternate_email)
            ),
            "web_presence": bool(lead.website.strip()),
            "location": any(
                value.strip()
                for value in (
                    lead.address,
                    lead.location,
                    lead.locality,
                    lead.city,
                    lead.district,
                    lead.state,
                    lead.country,
                    lead.pincode,
                )
            ),
            "business_context": any(
                value.strip()
                for value in (
                    lead.profession,
                    lead.company_name,
                    lead.category,
                    lead.subcategory,
                    lead.designation,
                    lead.specialization,
                    lead.services,
                    lead.description,
                )
            ),
            "source": self._valid_source_url(lead.source_url),
        }

    def _valid_source_url(self, value: str) -> bool:
        value = value.strip()
        if not value:
            return False

        try:
            parts = urlsplit(value)
        except ValueError:
            return False

        return parts.scheme.lower() in {"http", "https"} and bool(parts.netloc)
