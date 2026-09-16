from __future__ import annotations

import os
from typing import Any

import httpx

from scraper.discovery import SearchRequest
from scraper.models import Lead


class GoogleMapsAdapter:
    id = "google_maps"
    endpoint = "https://places.googleapis.com/v1/places:searchText"

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = (
            api_key or os.getenv("GOOGLE_MAPS_API_KEY", "")
        ).strip()
        if not self.api_key:
            raise ValueError("Google Maps API key must not be empty")

        self.client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def search(self, request: SearchRequest) -> list[Lead]:
        keyword = request.keyword.strip()
        location = request.location.strip()

        if not keyword or request.limit <= 0:
            return []

        text_query = keyword
        if location:
            text_query = f"{keyword} {location}"

        leads: list[Lead] = []
        page_token = ""

        while len(leads) < request.limit:
            payload = {
                "textQuery": text_query,
                "pageSize": min(request.limit - len(leads), 20),
            }
            if page_token:
                payload["pageToken"] = page_token

            response = self.client.post(
                self.endpoint,
                headers={
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": (
                        "places.id,"
                        "places.displayName,"
                        "places.formattedAddress,"
                        "places.googleMapsUri,"
                        "places.websiteUri,"
                        "places.nationalPhoneNumber,"
                        "places.types,"
                        "places.location,"
                        "nextPageToken"
                    ),
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, dict):
                break

            places = data.get("places", [])
            if not isinstance(places, list) or not places:
                break

            for place in places:
                if not isinstance(place, dict):
                    continue

                lead = self._map_place(
                    place,
                    search_context=text_query,
                )
                if lead is not None:
                    leads.append(lead)

                if len(leads) >= request.limit:
                    break

            if len(leads) >= request.limit:
                break

            next_page_token = data.get("nextPageToken", "")
            if not isinstance(next_page_token, str):
                break

            page_token = next_page_token.strip()
            if not page_token:
                break

        return leads

    def _map_place(
        self,
        place: dict[str, Any],
        *,
        search_context: str,
    ) -> Lead | None:
        place_id = str(place.get("id", "")).strip()

        display_name = place.get("displayName", {})
        if not isinstance(display_name, dict):
            display_name = {}

        name = str(display_name.get("text", "")).strip()
        address = str(place.get("formattedAddress", "")).strip()
        website = str(place.get("websiteUri", "")).strip()
        phone = str(place.get("nationalPhoneNumber", "")).strip()
        maps_url = str(place.get("googleMapsUri", "")).strip()

        types = place.get("types", [])
        if not isinstance(types, list):
            types = []

        types = [
            str(item).strip()
            for item in types
            if str(item).strip()
        ]

        location = place.get("location", {})
        if not isinstance(location, dict):
            location = {}

        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if not any(
            [place_id, name, address, website, phone, maps_url]
        ):
            return None

        extra: dict[str, str] = {}
        if types:
            extra["types"] = ", ".join(types)

        if latitude is not None:
            extra["latitude"] = str(latitude)
        if longitude is not None:
            extra["longitude"] = str(longitude)

        return Lead(
            name=name,
            company_name=name,
            address=address,
            phone=phone,
            website=website,
            category=types[0] if types else "",
            source_url=maps_url,
            source_name=self.id,
            source_id=place_id,
            search_context=search_context,
            extra=extra,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
