from scraper.discovery import SearchRequest
from scraper.source_google_maps import GoogleMapsAdapter


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, responses):
        self.responses = (
            list(responses)
            if isinstance(responses, (list, tuple))
            else [responses]
        )
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[index]


def test_google_maps_maps_places_to_leads():
    payload = {
        "places": [
            {
                "id": "ChIJ123",
                "displayName": {"text": "City Hospital"},
                "formattedAddress": "Station Road, Shahjahanpur, Uttar Pradesh",
                "googleMapsUri": "https://maps.google.com/?cid=123",
                "websiteUri": "https://example.com",
                "nationalPhoneNumber": "+91 9876543210",
                "types": ["hospital", "health"],
                "location": {
                    "latitude": 27.88,
                    "longitude": 79.91,
                },
            }
        ]
    }

    client = FakeClient(FakeResponse(payload))
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    result = adapter.search(
        SearchRequest(
            keyword="hospital",
            location="Shahjahanpur",
            limit=10,
        )
    )

    assert len(result) == 1

    lead = result[0]
    assert lead.name == "City Hospital"
    assert lead.company_name == "City Hospital"
    assert lead.address == "Station Road, Shahjahanpur, Uttar Pradesh"
    assert lead.phone == "+91 9876543210"
    assert lead.website == "https://example.com"
    assert lead.category == "hospital"
    assert lead.source_id == "ChIJ123"
    assert lead.source_name == "google_maps"
    assert lead.source_url == "https://maps.google.com/?cid=123"
    assert lead.search_context == "hospital Shahjahanpur"
    assert lead.extra["types"] == "hospital, health"
    assert lead.extra["latitude"] == "27.88"
    assert lead.extra["longitude"] == "79.91"


def test_google_maps_sends_expected_request():
    client = FakeClient(FakeResponse({"places": []}))
    adapter = GoogleMapsAdapter(
        api_key="test-key",
        client=client,
    )

    adapter.search(
        SearchRequest(
            keyword="doctor",
            location="Shahjahanpur",
            limit=5,
        )
    )

    assert len(client.calls) == 1

    url, kwargs = client.calls[0]

    assert url == (
        "https://places.googleapis.com/v1/places:searchText"
    )
    assert kwargs["headers"]["X-Goog-Api-Key"] == "test-key"
    assert "places.id" in kwargs["headers"]["X-Goog-FieldMask"]
    assert "places.displayName" in kwargs["headers"]["X-Goog-FieldMask"]
    assert kwargs["json"]["textQuery"] == "doctor Shahjahanpur"
    assert kwargs["json"]["pageSize"] == 5


def test_google_maps_respects_limit():
    payload = {
        "places": [
            {"id": "1", "displayName": {"text": "One"}},
            {"id": "2", "displayName": {"text": "Two"}},
            {"id": "3", "displayName": {"text": "Three"}},
        ]
    }

    client = FakeClient(FakeResponse(payload))
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    result = adapter.search(
        SearchRequest(keyword="doctor", limit=2)
    )

    assert [lead.source_id for lead in result] == ["1", "2"]


def test_google_maps_zero_limit_does_not_call_api():
    client = FakeClient(FakeResponse({}))
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    assert adapter.search(
        SearchRequest(keyword="doctor", limit=0)
    ) == []
    assert client.calls == []


def test_google_maps_empty_keyword_does_not_call_api():
    client = FakeClient(FakeResponse({}))
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    assert adapter.search(
        SearchRequest(keyword="   ", location="Shahjahanpur")
    ) == []
    assert client.calls == []


def test_google_maps_requires_api_key():
    try:
        GoogleMapsAdapter(api_key="")
    except ValueError as exc:
        assert str(exc) == "Google Maps API key must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_google_maps_reads_api_key_from_environment(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "env-key")

    adapter = GoogleMapsAdapter(
        client=FakeClient(FakeResponse({"places": []}))
    )

    assert adapter.api_key == "env-key"


def test_google_maps_ignores_invalid_places():
    payload = {
        "places": [
            "invalid",
            {},
            {"displayName": {"text": "Valid Place"}},
        ]
    }

    client = FakeClient(FakeResponse(payload))
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    result = adapter.search(
        SearchRequest(keyword="doctor", limit=10)
    )

    assert len(result) == 1
    assert result[0].name == "Valid Place"


def test_google_maps_does_not_store_complete_api_payload():
    payload = {
        "places": [
            {
                "id": "ChIJ123",
                "displayName": {"text": "Clinic"},
                "secretField": "should-not-be-stored",
            }
        ]
    }

    client = FakeClient(FakeResponse(payload))
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    result = adapter.search(
        SearchRequest(keyword="clinic", limit=10)
    )

    assert result[0].raw_data == {}
    assert "secretField" not in result[0].raw_data


def test_google_maps_paginates_until_requested_limit():
    first_page = {
        "places": [
            {"id": str(index), "displayName": {"text": f"Place {index}" }}
            for index in range(1, 21)
        ],
        "nextPageToken": "page-2",
    }
    second_page = {
        "places": [
            {"id": str(index), "displayName": {"text": f"Place {index}" }}
            for index in range(21, 31)
        ],
    }

    client = FakeClient([
        FakeResponse(first_page),
        FakeResponse(second_page),
    ])
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    result = adapter.search(
        SearchRequest(keyword="doctor", limit=25)
    )

    assert len(result) == 25
    assert [lead.source_id for lead in result] == [
        str(index) for index in range(1, 26)
    ]
    assert len(client.calls) == 2
    assert client.calls[0][1]["json"]["pageSize"] == 20
    assert client.calls[0][1]["json"].get("pageToken") is None
    assert client.calls[1][1]["json"]["pageSize"] == 5
    assert client.calls[1][1]["json"]["pageToken"] == "page-2"


def test_google_maps_requests_next_page_token_in_field_mask():
    client = FakeClient(FakeResponse({"places": []}))
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    adapter.search(
        SearchRequest(keyword="doctor", limit=25)
    )

    field_mask = client.calls[0][1]["headers"]["X-Goog-FieldMask"]
    assert "nextPageToken" in field_mask


def test_google_maps_does_not_paginate_when_limit_is_one_page():
    first_page = {
        "places": [
            {"id": str(index), "displayName": {"text": f"Place {index}" }}
            for index in range(1, 21)
        ],
        "nextPageToken": "page-2",
    }

    client = FakeClient(FakeResponse(first_page))
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    result = adapter.search(
        SearchRequest(keyword="doctor", limit=20)
    )

    assert len(result) == 20
    assert len(client.calls) == 1


def test_google_maps_stops_on_empty_page_even_with_next_page_token():
    first_page = {
        "places": [],
        "nextPageToken": "page-2",
    }

    client = FakeClient([
        FakeResponse(first_page),
        FakeResponse({"places": [{"id": "unexpected"}]}),
    ])
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    result = adapter.search(
        SearchRequest(keyword="doctor", limit=25)
    )

    assert result == []
    assert len(client.calls) == 1


def test_google_maps_stops_on_invalid_next_page_token():
    first_page = {
        "places": [
            {"id": "1", "displayName": {"text": "One"}},
        ],
        "nextPageToken": 12345,
    }

    client = FakeClient([
        FakeResponse(first_page),
        FakeResponse({"places": [{"id": "unexpected"}]}),
    ])
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    result = adapter.search(
        SearchRequest(keyword="doctor", limit=25)
    )

    assert [lead.source_id for lead in result] == ["1"]
    assert len(client.calls) == 1


def test_google_maps_stops_pagination_when_limit_is_reached():
    first_page = {
        "places": [
            {"id": str(index), "displayName": {"text": f"Place {index}"}}
            for index in range(1, 21)
        ],
        "nextPageToken": "page-2",
    }
    second_page = {
        "places": [
            {"id": str(index), "displayName": {"text": f"Place {index}"}}
            for index in range(21, 41)
        ],
        "nextPageToken": "page-3",
    }

    client = FakeClient([
        FakeResponse(first_page),
        FakeResponse(second_page),
        FakeResponse({"places": [{"id": "unexpected"}]}),
    ])
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    result = adapter.search(
        SearchRequest(keyword="doctor", limit=30)
    )

    assert len(result) == 30
    assert len(client.calls) == 2
    assert [lead.source_id for lead in result] == [
        str(index) for index in range(1, 31)
    ]


def test_google_maps_paginates_when_first_page_has_fewer_than_page_size():
    first_page = {
        "places": [
            {"id": "1", "displayName": {"text": "One"}},
        ],
        "nextPageToken": "page-2",
    }
    second_page = {
        "places": [
            {"id": "2", "displayName": {"text": "Two"}},
        ],
    }

    client = FakeClient([
        FakeResponse(first_page),
        FakeResponse(second_page),
    ])
    adapter = GoogleMapsAdapter(api_key="test-key", client=client)

    result = adapter.search(
        SearchRequest(keyword="doctor", limit=2)
    )

    assert [lead.source_id for lead in result] == ["1", "2"]
    assert len(client.calls) == 2
    assert client.calls[1][1]["json"]["pageToken"] == "page-2"
