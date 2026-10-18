import json

import pytest

from backend.routers.donations import search_donation_centres as search_donation_centres_endpoint
from backend.schemas.donations import DonationSearchRequest
from backend.services import donation_service


def _suggestions(count=2):
    return [
        {
            "name": f"Food Centre {index}",
            "location": f"Area {index}, Pune",
        }
        for index in range(count)
    ]


def test_search_uses_gemini_without_live_grounding_and_returns_at_most_ten(monkeypatch):
    request_details = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            request_details.update(kwargs)
            return type(
                "Response",
                (),
                {"text": json.dumps({"suggestions": _suggestions(12)})},
            )()

    class FakeClient:
        models = FakeModels()

        def __init__(self, **kwargs):
            request_details["client"] = kwargs

    monkeypatch.setattr(donation_service.settings, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(donation_service.genai, "Client", FakeClient)

    results = donation_service.search_donation_centres("food donation centres near Pune")

    assert len(results) == 10
    assert results[0].name == "Food Centre 0"
    assert request_details["model"] == donation_service.settings.GEMINI_MODEL
    assert "Do not use Google Maps, Google Search, tools, or live" in request_details["contents"]
    assert "never invent or guess" in request_details["contents"]
    assert request_details["config"].response_mime_type == "application/json"
    assert request_details["config"].tools is None
    assert request_details["client"]["api_key"] == "gemini-key"


def test_search_requires_gemini_api_key(monkeypatch):
    monkeypatch.setattr(donation_service.settings, "GEMINI_API_KEY", "")

    with pytest.raises(donation_service.DonationSearchError) as error:
        donation_service.search_donation_centres("food donation centres near Pune")

    assert error.value.status_code == 503
    assert "GEMINI_API_KEY" in str(error.value)


def test_gemini_rate_limit_is_reported_as_429(monkeypatch):
    class FakeApiError(Exception):
        code = 429

    class FakeModels:
        def generate_content(self, **_kwargs):
            raise FakeApiError("quota exceeded")

    class FakeClient:
        models = FakeModels()

        def __init__(self, **_kwargs):
            pass

    monkeypatch.setattr(donation_service.settings, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(donation_service.genai_errors, "APIError", FakeApiError)
    monkeypatch.setattr(donation_service.genai, "Client", FakeClient)

    with pytest.raises(donation_service.DonationSearchError) as error:
        donation_service.search_donation_centres("food donation centres near Pune")

    assert error.value.status_code == 429
    assert "rate or usage limit" in str(error.value)


def test_search_endpoint_returns_gemini_suggestions(monkeypatch):
    monkeypatch.setattr(
        donation_service,
        "search_donation_centres",
        lambda query: [
            donation_service.DonationCentreSuggestion(
                name=query,
                location="Pune",
            )
        ],
    )

    result = search_donation_centres_endpoint(
        DonationSearchRequest(query="food bank near Pune")
    )

    assert len(result) == 1
    assert result[0].name == "food bank near Pune"
