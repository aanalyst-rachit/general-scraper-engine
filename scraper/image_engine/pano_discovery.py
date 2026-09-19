from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True)
class PanoLocation:
    panoid: str
    latitude: float
    longitude: float
    distance_m: float | None = None


class StreetViewPanoDiscovery:
    """
    Discover the nearest Google Street View panorama for coordinates.

    This module is intentionally independent from the existing
    StreetViewBrowser.capture_panoid() implementation.
    """

    BASE_URL = (
        "https://maps.googleapis.com/maps/api/js/"
        "GeoPhotoService.SingleImageSearch"
    )

    def __init__(self, *, radius_m: int = 50, timeout: float = 15.0) -> None:
        if radius_m <= 0:
            raise ValueError("radius_m must be > 0")
        if timeout <= 0:
            raise ValueError("timeout must be > 0")

        self.radius_m = int(radius_m)
        self.timeout = float(timeout)

    def build_url(self, latitude: float, longitude: float) -> str:
        pb = (
            "!1m5!1sapiv3!5sUS!11m2!1m1!1b0"
            f"!2m4!1m2!3d{latitude}!4d{longitude}!2d{self.radius_m}"
            "!3m10!2m2!1sen!2sGB!9m1!1e2"
            "!11m4!1m3!1e2!2b1!3e2"
            "!4m10!1e1!1e2!1e3!1e4!1e8!1e6"
            "!5m1!1e2!6m1!1e2"
        )

        return f"{self.BASE_URL}?pb={quote(pb, safe='!')}&callback=callbackfunc"

    def search(
        self,
        latitude: float,
        longitude: float,
    ) -> PanoLocation | None:
        import requests

        response = requests.get(
            self.build_url(latitude, longitude),
            timeout=self.timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/153.0.0.0 Safari/537.36"
                ),
            },
        )
        response.raise_for_status()

        return self._parse_response(
            response.text,
            latitude=latitude,
            longitude=longitude,
        )

    @staticmethod
    def _parse_response(
        text: str,
        *,
        latitude: float,
        longitude: float,
    ) -> PanoLocation | None:
        """
        Extract the nearest pano ID and coordinates from Google's
        GeoPhotoService response.

        Google changes the exact response structure periodically,
        so parsing deliberately uses structural patterns rather
        than depending on one fixed JSON schema.
        """

        # Known pano-id shape used by Google Street View.
        pano_candidates = re.findall(
            r'"([A-Za-z0-9_-]{20,})"',
            text,
        )

        if not pano_candidates:
            return None

        # Prefer IDs appearing near common pano metadata markers.
        preferred: list[str] = []

        for match in re.finditer(
            r"(?:panoid|panoId|pano_id)",
            text,
            flags=re.IGNORECASE,
        ):
            start = max(0, match.start() - 300)
            end = min(len(text), match.end() + 500)
            chunk = text[start:end]

            preferred.extend(
                re.findall(
                    r"[A-Za-z0-9_-]{20,}",
                    chunk,
                )
            )

        candidates = preferred + pano_candidates

        seen: set[str] = set()

        for panoid in candidates:
            if panoid in seen:
                continue

            seen.add(panoid)

            # Filter obvious non-pano strings.
            if panoid.lower() in {
                "singleimagesearch",
                "geophotoservice",
            }:
                continue

            return PanoLocation(
                panoid=panoid,
                latitude=latitude,
                longitude=longitude,
            )

        return None


__all__ = [
    "PanoLocation",
    "StreetViewPanoDiscovery",
]
