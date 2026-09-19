from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
import csv
import json
import re
from pathlib import Path
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import httpx


@dataclass(frozen=True)
class OSMStreet:
    osm_way_id: int
    name: str
    highway: str
    geometry: tuple[tuple[float, float], ...]


class OSMStreetDiscovery:
    GOOGLE_MAP_SEARCH_URL = "https://www.google.com/search"
    OSM_MAP_URL = "https://api.openstreetmap.org/api/0.6/map"

    DEFAULT_MAX_GAP_M = 20.0

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        radius_km: float = 1.5,
        max_gap_m: float = DEFAULT_MAX_GAP_M,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be > 0")

        if radius_km <= 0:
            raise ValueError("radius_km must be > 0")

        if max_gap_m <= 0:
            raise ValueError("max_gap_m must be > 0")

        self.timeout = float(timeout)
        self.radius_km = float(radius_km)
        self.max_gap_m = float(max_gap_m)

    def search_area(self, area_name: str) -> list[OSMStreet]:
        area_name = area_name.strip()

        if not area_name:
            raise ValueError("area_name must not be empty")

        latitude, longitude = self._resolve_location(area_name)

        bbox = self._build_bbox(
            latitude,
            longitude,
            self.radius_km,
        )

        streets = self._fetch_streets(
            bbox,
            latitude=latitude,
            longitude=longitude,
        )

        return [
            OSMStreet(
                osm_way_id=street.osm_way_id,
                name=street.name,
                highway=street.highway,
                geometry=tuple(
                    self.sample_geometry(
                        street.geometry,
                        spacing_m=self.max_gap_m,
                    )
                ),
            )
            for street in streets
        ]

    def _resolve_location(
        self,
        location: str,
    ) -> tuple[float, float]:
        query = quote_plus(location)

        url = (
            f"{self.GOOGLE_MAP_SEARCH_URL}"
            f"?tbm=map"
            f"&authuser=0"
            f"&hl=en"
            f"&gl=in"
            f"&q={query}"
        )

        response = httpx.get(
            url,
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

        text = response.text

        # Google Maps map-search response is JSON prefixed with )]}'
        if text.startswith(")]}'"):
            text = text[4:]

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Google Maps response was not valid JSON: {exc}"
            ) from exc

        coordinates = self._find_google_coordinates(
            payload,
            location,
        )

        if coordinates is None:
            raise RuntimeError(
                f"Google Maps coordinates not found: {location}"
            )

        return coordinates

    @classmethod
    def _find_google_coordinates(
        cls,
        payload: object,
        location: str,
    ) -> tuple[float, float] | None:
        """
        Find the coordinate pair associated with the requested
        Google Maps map-search result.

        Google's internal response format is undocumented, so this
        intentionally searches nested JSON structures rather than
        depending on one fixed response index.
        """

        candidates: list[tuple[float, float]] = []

        def walk(value: object) -> None:
            if isinstance(value, list):
                if len(value) >= 4:
                    try:
                        lat = value[2]
                        lon = value[3]

                        if (
                            isinstance(lat, (int, float))
                            and isinstance(lon, (int, float))
                            and -90 <= lat <= 90
                            and -180 <= lon <= 180
                            and lat is not None
                            and lon is not None
                        ):
                            candidates.append(
                                (float(lat), float(lon))
                            )
                    except (TypeError, ValueError):
                        pass

                for item in value:
                    walk(item)

            elif isinstance(value, dict):
                for item in value.values():
                    walk(item)

        walk(payload)

        if not candidates:
            return None

        # Prefer the first valid Google map coordinate.
        return candidates[0]

    @staticmethod
    def _build_bbox(
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> tuple[float, float, float, float]:
        lat_delta = radius_km / 111.0

        lon_delta = radius_km / (
            111.0 * cos(radians(latitude))
        )

        return (
            longitude - lon_delta,
            latitude - lat_delta,
            longitude + lon_delta,
            latitude + lat_delta,
        )

    def _fetch_streets(
        self,
        bbox: tuple[float, float, float, float],
        *,
        latitude: float,
        longitude: float,
    ) -> list[OSMStreet]:
        left, bottom, right, top = bbox

        response = httpx.get(
            self.OSM_MAP_URL,
            params={
                "bbox": (
                    f"{left},{bottom},"
                    f"{right},{top}"
                ),
            },
            timeout=self.timeout,
            headers={
                "User-Agent": "general-scraper-engine/1.0",
            },
        )

        response.raise_for_status()

        root = ET.fromstring(response.text)

        nodes: dict[int, tuple[float, float]] = {}

        for node in root.findall("node"):
            nodes[int(node.attrib["id"])] = (
                float(node.attrib["lat"]),
                float(node.attrib["lon"]),
            )

        nearest_node_id = self._nearest_node_id(
            nodes,
            latitude,
            longitude,
        )

        if nearest_node_id is None:
            return []

        streets: list[OSMStreet] = []

        for way in root.findall("way"):
            tags = {
                tag.attrib["k"]: tag.attrib["v"]
                for tag in way.findall("tag")
            }

            highway = tags.get("highway", "").strip()

            if not highway:
                continue

            node_refs = [
                int(nd.attrib["ref"])
                for nd in way.findall("nd")
            ]

            if nearest_node_id not in node_refs:
                continue

            geometry = tuple(
                nodes[node_id]
                for node_id in node_refs
                if node_id in nodes
            )

            if len(geometry) < 2:
                continue

            streets.append(
                OSMStreet(
                    osm_way_id=int(way.attrib["id"]),
                    name=tags.get("name", "").strip(),
                    highway=highway,
                    geometry=geometry,
                )
            )

        return streets

    @classmethod
    def _nearest_node_id(
        cls,
        nodes: dict[int, tuple[float, float]],
        latitude: float,
        longitude: float,
    ) -> int | None:
        if not nodes:
            return None

        return min(
            nodes,
            key=lambda node_id: cls._distance_m(
                (latitude, longitude),
                nodes[node_id],
            ),
        )

    @classmethod
    def sample_geometry(
        cls,
        geometry: tuple[tuple[float, float], ...],
        *,
        spacing_m: float = DEFAULT_MAX_GAP_M,
    ) -> list[tuple[float, float]]:
        if spacing_m <= 0:
            raise ValueError("spacing_m must be > 0")

        if len(geometry) < 2:
            return list(geometry)

        points: list[tuple[float, float]] = [
            geometry[0]
        ]

        for index in range(1, len(geometry)):
            start = geometry[index - 1]
            end = geometry[index]

            distance = cls._distance_m(start, end)

            if distance <= spacing_m:
                points.append(end)
                continue

            parts = max(
                1,
                int(__import__("math").ceil(
                    distance / spacing_m
                )),
            )

            for part in range(1, parts):
                ratio = part / parts

                lat = (
                    start[0]
                    + (end[0] - start[0]) * ratio
                )

                lon = (
                    start[1]
                    + (end[1] - start[1]) * ratio
                )

                points.append((lat, lon))

            points.append(end)

        return points

    @classmethod
    def validate_spacing(
        cls,
        geometry: tuple[tuple[float, float], ...]
        | list[tuple[float, float]],
        *,
        max_gap_m: float = DEFAULT_MAX_GAP_M,
    ) -> bool:
        if max_gap_m <= 0:
            raise ValueError("max_gap_m must be > 0")

        for index in range(1, len(geometry)):
            if (
                cls._distance_m(
                    geometry[index - 1],
                    geometry[index],
                )
                > max_gap_m
            ):
                return False

        return True

    @staticmethod
    def _distance_m(
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        lat1, lon1 = map(radians, first)
        lat2, lon2 = map(radians, second)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        value = (
            sin(dlat / 2) ** 2
            + cos(lat1)
            * cos(lat2)
            * sin(dlon / 2) ** 2
        )

        return 6371000 * 2 * asin(sqrt(value))

    @classmethod
    def save_result(
        cls,
        streets: list[OSMStreet],
        output_json: str | Path,
        output_csv: str | Path,
        *,
        max_gap_m: float = DEFAULT_MAX_GAP_M,
    ) -> None:
        output_json = Path(output_json)
        output_csv = Path(output_csv)

        output_json.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output_csv.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        json_data = {
            "max_gap_m": max_gap_m,
            "ways": [
                {
                    "way_id": street.osm_way_id,
                    "name": street.name,
                    "highway": street.highway,
                    "points": [
                        {
                            "lat": lat,
                            "lon": lon,
                        }
                        for lat, lon in street.geometry
                    ],
                }
                for street in streets
            ],
        }

        with output_json.open("w") as file:
            json.dump(
                json_data,
                file,
                indent=2,
            )

        with output_csv.open(
            "w",
            newline="",
        ) as file:
            writer = csv.writer(file)

            writer.writerow([
                "way_id",
                "name",
                "highway",
                "point_index",
                "lat",
                "lon",
            ])

            for street in streets:
                for index, (lat, lon) in enumerate(
                    street.geometry,
                    start=1,
                ):
                    writer.writerow([
                        street.osm_way_id,
                        street.name,
                        street.highway,
                        index,
                        f"{lat:.7f}",
                        f"{lon:.7f}",
                    ])
