from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse


@dataclass(frozen=True)
class StreetViewFrame:
    path: Path
    panoid: str
    yaw: float
    pitch: float
    width: int
    height: int


class StreetViewBrowser:
    base_url = "https://www.google.com/maps"

    thumbnail_url = (
        "https://streetviewpixels-pa.googleapis.com/v1/thumbnail"
    )

    def __init__(
        self,
        page: object,
        *,
        timeout: float = 15.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be > 0")

        self.page = page
        self.timeout = float(timeout)

    def open_location(self, location: str) -> str:
        location = location.strip()

        if not location:
            raise ValueError("location must not be empty")

        url = (
            f"{self.base_url}/search/"
            f"?api=1&query={quote_plus(location)}"
        )

        self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=self.timeout * 1000,
        )

        return self.page.url

    def open_street_view(self, location: str) -> str:
        location = location.strip()

        if not location:
            raise ValueError("location must not be empty")

        url = (
            f"{self.base_url}/@?api=1"
            f"&map_action=pano"
            f"&viewpoint={quote_plus(location)}"
        )

        self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=self.timeout * 1000,
        )

        return self.page.url

    @classmethod
    def extract_panoid(cls, street_view_url: str) -> str:
        """
        Extract panoid from a real Google Maps Street View URL.

        Supports URLs containing:

        panoid=XXXXXXXX

        including panoid values embedded inside the thumbnail
        URL found in Google's Street View data URL.
        """
        if not street_view_url.strip():
            raise ValueError("street_view_url must not be empty")

        decoded = unquote(street_view_url)

        match = re.search(
            r"(?:[?&])panoid=([^&!]+)",
            decoded,
        )

        if match:
            return match.group(1)

        # Fallback for encoded/nested URLs.
        parsed = urlparse(decoded)

        for value in parse_qs(parsed.query).values():
            for item in value:
                nested = unquote(item)

                nested_match = re.search(
                    r"(?:[?&])panoid=([^&!]+)",
                    nested,
                )

                if nested_match:
                    return nested_match.group(1)

        raise ValueError(
            "panoid not found in Street View URL"
        )

    @classmethod
    def extract_yaw(
        cls,
        street_view_url: str,
        *,
        default: float = 0.0,
    ) -> float:
        decoded = unquote(street_view_url)

        match = re.search(
            r"(?:[?&])yaw=([-+]?\d+(?:\.\d+)?)",
            decoded,
        )

        if match:
            return float(match.group(1))

        match = re.search(
            r",([-+]?\d+(?:\.\d+)?)h,",
            decoded,
        )

        if match:
            return float(match.group(1))

        return float(default)

    @classmethod
    def extract_pitch(
        cls,
        street_view_url: str,
        *,
        default: float = 0.0,
    ) -> float:
        decoded = unquote(street_view_url)

        match = re.search(
            r"(?:[?&])pitch=([-+]?\d+(?:\.\d+)?)",
            decoded,
        )

        if match:
            return float(match.group(1))

        match = re.search(
            r",([-+]?\d+(?:\.\d+)?)t/",
            decoded,
        )

        if match:
            return float(match.group(1))

        return float(default)

    @classmethod
    def build_thumbnail_url(
        cls,
        *,
        panoid: str,
        yaw: float = 0.0,
        pitch: float = 0.0,
        width: int = 900,
        height: int = 600,
    ) -> str:
        panoid = panoid.strip()

        if not panoid:
            raise ValueError("panoid must not be empty")

        if width <= 0:
            raise ValueError("width must be > 0")

        if height <= 0:
            raise ValueError("height must be > 0")

        return (
            f"{cls.thumbnail_url}"
            f"?cb_client=maps_sv.tactile"
            f"&w={int(width)}"
            f"&h={int(height)}"
            f"&pitch={float(pitch)}"
            f"&panoid={quote_plus(panoid)}"
            f"&yaw={float(yaw)}"
        )

    @classmethod
    def frame_angles(
        cls,
        *,
        start_yaw: float = 0.0,
        step: float = 45.0,
        count: int = 8,
    ) -> list[float]:
        if count <= 0:
            raise ValueError("count must be > 0")

        if step <= 0:
            raise ValueError("step must be > 0")

        return [
            (start_yaw + (step * index)) % 360
            for index in range(count)
        ]

    def capture_panoid(
        self,
        panoid: str,
        output_dir: str | Path,
        *,
        yaws: list[float] | None = None,
        pitch: float = 0.0,
        width: int = 900,
        height: int = 600,
        prefix: str = "street_view",
    ) -> list[StreetViewFrame]:
        panoid = panoid.strip()

        if not panoid:
            raise ValueError("panoid must not be empty")

        if yaws is None:
            yaws = self.frame_angles()

        if not yaws:
            raise ValueError("yaws must not be empty")

        destination = Path(output_dir)
        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        frames: list[StreetViewFrame] = []

        for index, yaw in enumerate(yaws):
            url = (
                f"{self.base_url}/@?api=1"
                f"&map_action=pano"
                f"&pano={quote_plus(panoid)}"
                f"&heading={float(yaw)}"
                f"&pitch={float(pitch)}"
                f"&fov=90"
            )

            self.page.set_viewport_size(
                {
                    "width": width,
                    "height": height,
                }
            )

            self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.timeout * 1000,
            )

            self.page.wait_for_timeout(15000)

            path = (
                destination
                / f"{prefix}_{index:03d}.png"
            )

            self.page.screenshot(
                path=str(path),
                full_page=False,
            )

            frames.append(
                StreetViewFrame(
                    path=path,
                    panoid=panoid,
                    yaw=float(yaw),
                    pitch=float(pitch),
                    width=width,
                    height=height,
                )
            )

        return frames

    def capture_from_url(
        self,
        street_view_url: str,
        output_dir: str | Path,
        *,
        yaws: list[float] | None = None,
        pitch: float | None = None,
        width: int = 900,
        height: int = 600,
        prefix: str = "street_view",
    ) -> list[StreetViewFrame]:
        panoid = self.extract_panoid(
            street_view_url
        )

        if pitch is None:
            pitch = self.extract_pitch(
                street_view_url
            )

        if yaws is None:
            yaws = self.frame_angles(
                start_yaw=self.extract_yaw(
                    street_view_url
                )
            )

        return self.capture_panoid(
            panoid,
            output_dir,
            yaws=yaws,
            pitch=pitch,
            width=width,
            height=height,
            prefix=prefix,
        )