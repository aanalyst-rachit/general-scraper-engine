from __future__ import annotations

import math

import httpx
import pytest

from scraper.osm.street_discovery import OSMStreetDiscovery


def test_sample_geometry_subdivides_large_gaps():
    geometry = (
        (27.8800, 79.9100),
        (27.8810, 79.9110),
    )

    points = OSMStreetDiscovery.sample_geometry(
        geometry,
        spacing_m=20.0,
    )

    assert points[0] == geometry[0]
    assert points[-1] == geometry[-1]
    assert len(points) > 2

    assert OSMStreetDiscovery.validate_spacing(
        points,
        max_gap_m=20.0,
    )


def test_sample_geometry_keeps_small_gaps():
    geometry = (
        (27.8800, 79.9100),
        (27.88005, 79.91005),
    )

    points = OSMStreetDiscovery.sample_geometry(
        geometry,
        spacing_m=20.0,
    )

    assert points == list(geometry)


def test_sample_geometry_rejects_invalid_spacing():
    with pytest.raises(
        ValueError,
        match="spacing_m must be > 0",
    ):
        OSMStreetDiscovery.sample_geometry(
            (
                (27.8800, 79.9100),
                (27.8810, 79.9110),
            ),
            spacing_m=0,
        )


def test_validate_spacing_rejects_large_gap():
    geometry = (
        (27.8800, 79.9100),
        (27.8810, 79.9110),
    )

    assert not OSMStreetDiscovery.validate_spacing(
        geometry,
        max_gap_m=20.0,
    )


def test_timeout_must_be_positive():
    with pytest.raises(
        ValueError,
        match="timeout must be > 0",
    ):
        OSMStreetDiscovery(timeout=0)


def test_radius_must_be_positive():
    with pytest.raises(
        ValueError,
        match="radius_km must be > 0",
    ):
        OSMStreetDiscovery(radius_km=0)


def test_max_gap_must_be_positive():
    with pytest.raises(
        ValueError,
        match="max_gap_m must be > 0",
    ):
        OSMStreetDiscovery(max_gap_m=0)


def test_search_area_rejects_empty_name():
    discovery = OSMStreetDiscovery()

    with pytest.raises(
        ValueError,
        match="area_name must not be empty",
    ):
        discovery.search_area("   ")


def test_google_coordinates_parser():
    payload = [
        [
            "Sadar Bazar",
            None,
            [
                None,
                None,
                27.8827709,
                79.9137236,
            ],
        ]
    ]

    coordinates = OSMStreetDiscovery._find_google_coordinates(
        payload,
        "Sadar Bazar",
    )

    assert coordinates == (
        27.8827709,
        79.9137236,
    )


def test_google_coordinates_parser_returns_none():
    assert (
        OSMStreetDiscovery._find_google_coordinates(
            {"nothing": "here"},
            "Sadar Bazar",
        )
        is None
    )


def test_distance_is_reasonable():
    distance = OSMStreetDiscovery._distance_m(
        (27.8800, 79.9100),
        (27.8801, 79.9101),
    )

    assert math.isclose(
        distance,
        14.8,
        rel_tol=0.15,
    )
