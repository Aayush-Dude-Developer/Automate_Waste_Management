import json
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from urllib.parse import quote_plus

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from ..schemas.donations import DonationCentre, MatchRequest, MatchResult, HandoverRecord, HandoverResponse
from ..repositories.database import db
from ..config import settings

logger = logging.getLogger(__name__)


class DonationDiscoveryError(Exception):
    pass


class DonationDiscoveryUnavailable(DonationDiscoveryError):
    pass


class DonationDiscoveryRateLimited(DonationDiscoveryUnavailable):
    pass

# Fixed sample centres used only when AI discovery is turned off.
DEMO_CENTRES = [
    DonationCentre(
        id="dc_001", name="Pune Food Bank", contact_person="Amit Deshmukh", phone="9876543210", 
        address="Shivaji Nagar, Pune", latitude=18.5308, longitude=73.8475,
        accepts_cooked_food=True, accepts_raw_produce=True, requires_cold_chain=False,
        minimum_quantity_kg=5.0, pickup_service_available=True, verified=True
    ),
    DonationCentre(
        id="dc_002", name="Robin Hood Army - Kharadi", contact_person="Priya Sharma", phone="9876543211", 
        address="Kharadi, Pune", latitude=18.5515, longitude=73.9348,
        accepts_cooked_food=True, accepts_raw_produce=False, requires_cold_chain=True,
        minimum_quantity_kg=2.0, pickup_service_available=False, verified=True
    )
]

def _grounding_source_urls(response: Any) -> set[str]:
    urls: set[str] = set()
    for candidate in getattr(response, "candidates", None) or []:
        metadata = getattr(candidate, "grounding_metadata", None)
        for chunk in getattr(metadata, "grounding_chunks", None) or []:
            web_source = getattr(chunk, "web", None)
            url = getattr(web_source, "uri", None)
            if isinstance(url, str) and url.startswith("https://"):
                urls.add(url)
    return urls


def discover_donation_centres_with_ai(location_name: str) -> tuple[List[DonationCentre], Optional[float], Optional[float]]:
    """Search Google Maps and centre websites, returning only sourced details."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        raise DonationDiscoveryUnavailable(
            "AI donation-centre discovery requires GEMINI_API_KEY. No demo results were substituted."
        )

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=60_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        prompt = f"""
Search Google Maps for real food donation centres, food banks, and NGOs near:
{location_name}

Explicitly check Google Maps listings for candidate names, addresses, and coordinates.
Then visit/search each centre's own official website for phone number, donation
timings, minimum accepted weight, pickup availability, and vegetarian/non-vegetarian
acceptance constraints. Prefer primary sources; use third-party sources only when
there is no official website. Return only details explicitly found in Google Maps
or a cited source. Do not use general knowledge, infer, estimate, or fabricate.
For every unavailable field return null. Do not output placeholder phone numbers,
hours, minimum weights, or guessed dietary policies. Convert a minimum weight to
kilograms only when its stated unit allows an exact conversion; otherwise return null.

Return only valid JSON with this shape:
{{
  "search_location": {{"latitude": number|null, "longitude": number|null}},
  "centres": [
    {{
      "name": "string",
      "address": "string|null",
      "latitude": number|null,
      "longitude": number|null,
      "phone": "string|null",
      "opening_hours": "string|null",
      "minimum_quantity_kg": number|null,
      "pickup_service_available": boolean|null,
      "accepts_vegetarian": boolean|null,
      "accepts_non_vegetarian": boolean|null,
      "accepts_cooked_food": boolean|null,
      "accepts_raw_produce": boolean|null,
      "requires_cold_chain": boolean|null,
      "google_maps_link": "string|null",
      "website_url": "string|null",
      "source_urls": ["URLs from the search results supporting this centre"]
    }}
  ]
}}

Coordinates must come from a Google Maps result. Include the search location
coordinates only if Google Maps identifies that location. Return at most 8 centres.
"""
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        result = json.loads(response.text or "")
        if not isinstance(result, dict) or not isinstance(result.get("centres"), list):
            raise ValueError("Gemini returned an invalid donation-centre response.")
        grounding_urls = _grounding_source_urls(response)
        centres = []
        for candidate in result["centres"][:8]:
            if not isinstance(candidate, dict) or not isinstance(candidate.get("name"), str):
                continue
            values = {
                key: candidate.get(key)
                for key in DonationCentre.model_fields
                if key not in {"id", "verified", "contact_person"}
            }
            cited_urls = candidate.get("source_urls")
            values["source_urls"] = [
                url for url in cited_urls
                if isinstance(url, str) and url in grounding_urls
            ] if isinstance(cited_urls, list) else []
            if values.get("website_url") not in values["source_urls"]:
                values["website_url"] = None
            query = " ".join(filter(None, [values.get("name"), values.get("address")]))
            values["google_maps_link"] = (
                f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
                if query else None
            )
            values["id"] = f"dc_ai_{uuid.uuid4().hex[:8]}"
            values["verified"] = False
            values["contact_person"] = None
            centres.append(DonationCentre(**values))

        location = result.get("search_location") or {}
        latitude = location.get("latitude") if isinstance(location, dict) else None
        longitude = location.get("longitude") if isinstance(location, dict) else None
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            latitude = longitude = None
        return centres, latitude, longitude
    except genai_errors.APIError as error:
        logger.warning("Gemini donation discovery failed with HTTP %s.", error.code)
        if error.code == 429:
            raise DonationDiscoveryRateLimited(
                "Gemini's donation search rate or usage quota has been reached (429). "
                "Wait before retrying; if this continues, check the Gemini API quota and billing for the configured project."
            ) from error
        if error.code == 503:
            raise DonationDiscoveryUnavailable(
                "Gemini is temporarily unavailable (503). Please try donation-centre discovery again shortly."
            ) from error
        raise DonationDiscoveryError(
            f"Gemini could not search for donation centres (HTTP {error.code})."
        ) from error
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        logger.exception("Gemini returned invalid donation-centre data.")
        raise DonationDiscoveryError(
            "Gemini returned invalid donation-centre data. Please try again."
        ) from error
    except Exception as error:
        logger.exception("AI donation-centre discovery failed.")
        raise DonationDiscoveryError(
            "Could not search for donation centres. Please try again."
        ) from error

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_matches(
    request: MatchRequest,
    restaurant_lat: Optional[float] = None,
    restaurant_lon: Optional[float] = None,
    use_ai_discovery: bool = False,
    location_name: Optional[str] = None,
) -> List[MatchResult]:
    
    # Decide source of centres
    if use_ai_discovery:
        location_parts = [
            request.location_area,
            request.city,
            request.state,
            request.pincode,
            request.country,
        ]
        search_location = ", ".join(part.strip() for part in location_parts if part and part.strip())
        if not search_location:
            search_location = location_name or ""
        if not search_location:
            raise ValueError("Enter an area or city and country before AI discovery.")
        available_centres, discovered_lat, discovered_lon = discover_donation_centres_with_ai(search_location)
        restaurant_lat = restaurant_lat if restaurant_lat is not None else discovered_lat
        restaurant_lon = restaurant_lon if restaurant_lon is not None else discovered_lon
    else:
        available_centres = DEMO_CENTRES
        restaurant_lat = restaurant_lat if restaurant_lat is not None else 18.5515
        restaurant_lon = restaurant_lon if restaurant_lon is not None else 73.9348
        
    results = []
    
    for centre in available_centres:
        notes = []
        is_eligible = True
        score = 100
        
        dist = (
            haversine_distance(restaurant_lat, restaurant_lon, centre.latitude, centre.longitude)
            if restaurant_lat is not None and restaurant_lon is not None
            and centre.latitude is not None and centre.longitude is not None
            else None
        )
        
        if dist is not None and dist > 15.0:
            notes.append(f"Centre is too far ({dist:.1f} km).")
            is_eligible = False
            score -= 50
            
        if centre.minimum_quantity_kg is not None and request.quantity_kg < centre.minimum_quantity_kg:
            notes.append(f"Quantity ({request.quantity_kg}kg) is below minimum ({centre.minimum_quantity_kg}kg).")
            is_eligible = False
            score -= 40
        elif centre.minimum_quantity_kg is None and use_ai_discovery:
            notes.append("Minimum accepted weight not found; verify with the centre.")
            
        if request.is_cooked and centre.accepts_cooked_food is False:
            notes.append("Does not accept cooked food.")
            is_eligible = False
            score -= 100
        elif request.is_cooked and centre.accepts_cooked_food is None and use_ai_discovery:
            notes.append("Cooked-food acceptance not found; verify with the centre.")
            is_eligible = False

        if not request.is_cooked and centre.accepts_raw_produce is False:
            notes.append("Accepts meals only.")
            is_eligible = False
            score -= 100
        elif not request.is_cooked and centre.accepts_raw_produce is None and use_ai_discovery:
            notes.append("Raw-produce acceptance not found; verify with the centre.")
            is_eligible = False

        if request.requires_cold_chain and centre.requires_cold_chain is False:
            notes.append("Lacks cold-chain support.")
            is_eligible = False
            score -= 100
        elif request.requires_cold_chain and centre.requires_cold_chain is None and use_ai_discovery:
            notes.append("Cold-chain capability not found; verify with the centre.")
            is_eligible = False

        if request.is_vegetarian is not None:
            dietary_acceptance = (
                centre.accepts_vegetarian
                if request.is_vegetarian
                else centre.accepts_non_vegetarian
            )
            if dietary_acceptance is False:
                notes.append(
                    "Does not accept "
                    + ("vegetarian" if request.is_vegetarian else "non-vegetarian")
                    + " food."
                )
                is_eligible = False
                score -= 100
            elif dietary_acceptance is None and use_ai_discovery:
                notes.append("Dietary acceptance not found; verify with the centre.")
                is_eligible = False

        if use_ai_discovery and dist is None:
            notes.append("Distance could not be verified from Google Maps.")
        if use_ai_discovery and centre.opening_hours is None:
            notes.append("Donation timings not found; verify with the centre.")

        if not centre.verified:
            notes.append("AI-sourced centre; independently verify details and food-safety requirements.")
            
        if is_eligible:
            if centre.pickup_service_available is True:
                score += 10
            if dist is not None:
                score -= int(dist)
        
        results.append(MatchResult(
            centre=centre,
            match_score=max(0, score),
            distance_km=round(dist, 1) if dist is not None else None,
            eligibility_notes=notes,
            is_eligible=is_eligible
        ))
        
    if use_ai_discovery:
        results.sort(key=lambda result: (
            result.distance_km is None,
            result.distance_km if result.distance_km is not None else math.inf,
        ))
    else:
        results.sort(key=lambda x: (not x.is_eligible, -x.match_score))
    return results

def record_handover(restaurant_id: str, handover: HandoverRecord) -> HandoverResponse:
    record_id = f"don_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    doc_data = handover.model_dump()
    doc_data.update({
        "id": record_id,
        "restaurant_id": restaurant_id,
        "status": "HANDOVER_COMPLETED",
        "timestamp": now.isoformat()
    })
    
    db.add_document(f"restaurants/{restaurant_id}/donation_handovers", record_id, doc_data)
    
    return HandoverResponse(**doc_data)

def get_handovers(
    restaurant_id: str,
    limit: int | None = None,
) -> List[HandoverResponse]:
    docs = db.query_collection(
        f"restaurants/{restaurant_id}/donation_handovers",
        order_by=("timestamp", "DESCENDING") if limit else None,
        limit=limit,
    )
    return [HandoverResponse(**doc) for doc in docs]
