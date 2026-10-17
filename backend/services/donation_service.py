import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import ValidationError

from ..config import settings
from ..repositories.database import db
from ..schemas.donations import (
    DonationCentreSuggestion,
    HandoverRecord,
    HandoverResponse,
)

logger = logging.getLogger(__name__)
GEMINI_TIMEOUT_MS = 60_000


class DonationSearchError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def search_donation_centres(query: str) -> List[DonationCentreSuggestion]:
    """Generate centre suggestions from Gemini's existing knowledge without live grounding."""
    api_key = settings.GEMINI_API_KEY.strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        raise DonationSearchError(
            "Gemini is not configured. Set GEMINI_API_KEY on the backend and try again.",
            503,
        )

    prompt = f"""
Suggest up to 10 real food donation centres or food banks relevant to this location/search:
{query.strip()}

Use only your existing knowledge. Do not use Google Maps, Google Search, tools, or live
grounding. Accuracy is more important than returning results: never invent or guess an
organization or its location. Include a centre only when you can confidently identify
its name and a known city/area. Do not infer that a centre accepts food donations unless
you know this; do not invent street addresses, contact details, opening hours, URLs, or
current status.
If you cannot confidently identify any suitable centre, return an empty suggestions list.
Do not imply that these suggestions were checked live.

Return JSON matching the supplied schema.
"""
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=GEMINI_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "suggestions": {
                            "type": "array",
                            "maxItems": 10,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "location": {"type": "string"},
                                },
                                "required": ["name", "location"],
                            },
                        },
                    },
                    "required": ["suggestions"],
                },
                temperature=0.1,
            ),
        )
    except genai_errors.APIError as error:
        logger.warning("Gemini donation search failed with HTTP %s.", error.code)
        if error.code == 429:
            raise DonationSearchError(
                "Gemini's rate or usage limit has been reached. Please try again later.",
                429,
            ) from error
        if error.code == 503:
            raise DonationSearchError(
                "Gemini is temporarily unavailable. Please try again shortly.",
                503,
            ) from error
        raise DonationSearchError(
            f"Gemini could not complete this search (HTTP {error.code}). Please try again.",
            502,
        ) from error
    except Exception as error:
        logger.exception("Gemini donation search request failed.")
        raise DonationSearchError(
            "Gemini could not complete this search. Please try again.",
            502,
        ) from error

    try:
        payload = json.loads(response.text or "")
        suggestions = payload.get("suggestions")
        if not isinstance(suggestions, list):
            raise ValueError("Gemini returned an invalid suggestions list.")
        return [
            DonationCentreSuggestion.model_validate(suggestion)
            for suggestion in suggestions[:10]
        ]
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as error:
        logger.exception("Gemini returned invalid donation search data.")
        raise DonationSearchError(
            "Gemini returned invalid search results. Please try again.",
            502,
        ) from error


def record_handover(restaurant_id: str, handover: HandoverRecord) -> HandoverResponse:
    record_id = f"don_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    doc_data = handover.model_dump()
    doc_data.update({
        "id": record_id,
        "restaurant_id": restaurant_id,
        "status": "HANDOVER_COMPLETED",
        "timestamp": now.isoformat(),
    })

    db.add_document(f"restaurants/{restaurant_id}/donation_handovers", record_id, doc_data)
    return HandoverResponse(**doc_data)


def get_handovers(restaurant_id: str, limit: int | None = None) -> List[HandoverResponse]:
    docs = db.query_collection(
        f"restaurants/{restaurant_id}/donation_handovers",
        order_by=("timestamp", "DESCENDING") if limit else None,
        limit=limit,
    )
    return [HandoverResponse(**doc) for doc in docs]
