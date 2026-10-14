import json

from fastapi import HTTPException
from google.genai import errors as genai_errors
from google.genai import types

from backend.routers.donations import get_donation_matches
from backend.schemas.donations import DonationCentre, MatchRequest
from backend.services import donation_service


def test_ai_discovery_uses_google_search_and_only_keeps_grounded_sources(monkeypatch):
    source_url = "https://example.org/donate"
    response_data = {
        "search_location": {"latitude": 18.5, "longitude": 73.9},
        "centres": [
            {
                "name": "Verified Food Bank",
                "address": "Pune",
                "latitude": 18.51,
                "longitude": 73.91,
                "phone": "1234567890",
                "opening_hours": "10:00-17:00",
                "minimum_quantity_kg": 5,
                "pickup_service_available": True,
                "accepts_vegetarian": True,
                "accepts_non_vegetarian": False,
                "accepts_cooked_food": True,
                "accepts_raw_produce": True,
                "requires_cold_chain": False,
                "website_url": source_url,
                "source_urls": [source_url, "https://not-grounded.example"],
            }
        ],
    }

    class FakeModels:
        def generate_content(self, **request):
            self.request = request
            return type(
                "Response",
                (),
                {
                    "text": json.dumps(response_data),
                    "candidates": [
                        type(
                            "Candidate",
                            (),
                            {
                                "grounding_metadata": type(
                                    "Metadata",
                                    (),
                                    {
                                        "grounding_chunks": [
                                            type(
                                                "Chunk",
                                                (),
                                                {
                                                    "web": type(
                                                        "WebSource",
                                                        (),
                                                        {"uri": source_url},
                                                    )()
                                                },
                                            )()
                                        ]
                                    },
                                )()
                            },
                        )()
                    ],
                },
            )()

    models = FakeModels()
    monkeypatch.setattr(donation_service.settings, "GEMINI_API_KEY", "configured-key")
    monkeypatch.setattr(
        donation_service.genai,
        "Client",
        lambda **_kwargs: type("Client", (), {"models": models})(),
    )

    centres, latitude, longitude = donation_service.discover_donation_centres_with_ai(
        "Kharadi, Pune, Maharashtra, India, 411014"
    )

    assert latitude == 18.5
    assert longitude == 73.9
    assert centres[0].phone == "1234567890"
    assert centres[0].source_urls == [source_url]
    assert centres[0].website_url == source_url
    assert "Search Google Maps" in models.request["contents"]
    assert any(
        isinstance(tool, types.Tool) and tool.google_search is not None
        for tool in models.request["config"].tools
    )


def test_ai_discovery_requires_gemini_instead_of_returning_demo_data(monkeypatch):
    monkeypatch.setattr(donation_service.settings, "GEMINI_API_KEY", "")

    try:
        donation_service.discover_donation_centres_with_ai("Pune, India")
    except donation_service.DonationDiscoveryUnavailable as error:
        assert "No demo results were substituted" in str(error)
    else:
        raise AssertionError("Missing AI configuration silently returned demo data.")


def test_gemini_429_is_reported_as_rate_limit(monkeypatch):
    class FakeModels:
        def generate_content(self, **_request):
            raise genai_errors.ClientError(
                429,
                {"error": {"message": "Quota exceeded.", "status": "RESOURCE_EXHAUSTED"}},
            )

    monkeypatch.setattr(donation_service.settings, "GEMINI_API_KEY", "configured-key")
    monkeypatch.setattr(
        donation_service.genai,
        "Client",
        lambda **_kwargs: type("Client", (), {"models": FakeModels()})(),
    )
    request = MatchRequest(
        item_name="Meal",
        quantity_kg=5,
        is_cooked=True,
        requires_cold_chain=False,
        city="Pune",
        country="India",
    )

    try:
        get_donation_matches(request, use_ai=True)
    except HTTPException as error:
        assert error.status_code == 429
        assert "quota has been reached (429)" in error.detail
        assert "check the Gemini API quota and billing" in error.detail
    else:
        raise AssertionError("Gemini 429 did not produce a rate-limit HTTP response.")


def test_ai_matches_rank_by_distance_and_unknown_details_are_not_invented(monkeypatch):
    farther = DonationCentre(
        id="far",
        name="Far Centre",
        latitude=18.6,
        longitude=73.9,
        accepts_cooked_food=True,
        accepts_vegetarian=True,
        opening_hours=None,
        verified=False,
    )
    nearer = DonationCentre(
        id="near",
        name="Near Centre",
        latitude=18.51,
        longitude=73.91,
        accepts_cooked_food=True,
        accepts_vegetarian=True,
        opening_hours="10:00-17:00",
        verified=False,
    )
    monkeypatch.setattr(
        donation_service,
        "discover_donation_centres_with_ai",
        lambda _location: ([farther, nearer], 18.5, 73.9),
    )
    request = MatchRequest(
        item_name="Meal",
        quantity_kg=5,
        is_cooked=True,
        requires_cold_chain=False,
        is_vegetarian=True,
        location_area="Kharadi",
        city="Pune",
        country="India",
    )

    results = donation_service.find_matches(request, use_ai_discovery=True)

    assert [result.centre.id for result in results] == ["near", "far"]
    assert results[0].distance_km < results[1].distance_km
    assert results[1].centre.phone is None
    assert results[1].centre.minimum_quantity_kg is None
    assert any("timings not found" in note for note in results[1].eligibility_notes)
