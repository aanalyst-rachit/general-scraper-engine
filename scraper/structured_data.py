from __future__ import annotations

import json

from bs4 import BeautifulSoup


class StructuredDataExtractor:
    _USEFUL_TYPES = {
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

    def extract(self, html: str) -> dict[str, str] | None:
        soup = BeautifulSoup(html, "lxml")

        for script in soup.find_all(
            "script",
            attrs={"type": "application/ld+json"},
        ):
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
                        node
                        for node in item["@graph"]
                        if isinstance(node, dict)
                    )

                if self._is_entity(item):
                    return self._fields(item)

        return None

    def _is_entity(self, data: dict) -> bool:
        entity_type = data.get("@type", "")

        if isinstance(entity_type, list):
            types = {str(value).lower() for value in entity_type}
        else:
            types = {str(entity_type).lower()}

        return bool(types & self._USEFUL_TYPES) and bool(data.get("name"))

    def _fields(self, data: dict) -> dict[str, str]:
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
                str(part).strip()
                for part in parts
                if str(part).strip()
            )
            locality = str(
                address.get("addressLocality", "")
            ).strip()
            region = str(
                address.get("addressRegion", "")
            ).strip()
        else:
            address_text = str(address).strip()
            locality = ""
            region = ""

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
            "address_locality": locality,
            "address_region": region,
        }
