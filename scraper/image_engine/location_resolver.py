from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class ResolvedLocation:
    query: str
    latitude: float
    longitude: float
    url: str


class GoogleMapsLocationResolver:
    def __init__(self, page: object, *, timeout: float = 30.0) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be > 0")
        self.page = page
        self.timeout = float(timeout)

    def resolve(self, location: str) -> ResolvedLocation:
        location = location.strip()
        if not location:
            raise ValueError("location must not be empty")

        url = (
            "https://www.google.com/maps/search/?api=1&query="
            + quote_plus(location)
        )

        self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=int(self.timeout * 1000),
        )
        self.page.wait_for_timeout(7000)

        resolved_url = self.page.url

        place_match = re.search(
            r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)",
            resolved_url,
        )

        if place_match:
            latitude = float(place_match.group(1))
            longitude = float(place_match.group(2))
        else:
            viewport_match = re.search(
                r"/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)",
                resolved_url,
            )

            if not viewport_match:
                raise ValueError(
                    f"could not extract coordinates from Google Maps URL: {resolved_url}"
                )

            latitude = float(viewport_match.group(1))
            longitude = float(viewport_match.group(2))

        return ResolvedLocation(
            query=location,
            latitude=latitude,
            longitude=longitude,
            url=resolved_url,
        )
