import math
import uuid
import json
from datetime import datetime, timezone
from typing import List
from ..schemas.donations import DonationCentre, MatchRequest, MatchResult, HandoverRecord, HandoverResponse
from ..repositories.database import db
from ..config import settings

# Hardcoded demo centres fallback
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

def discover_donation_centres_with_ai(location_name: str) -> List[DonationCentre]:
    """Uses Gemini to search and extract real NGOs/Food Banks in the area."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        print("Warning: Gemini API Key missing, falling back to static demo centres.")
        return DEMO_CENTRES

    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Find 3 to 4 REAL food donation centres, food banks, or NGOs operating in or near {location_name} that accept surplus restaurant food.
        Use your general knowledge or search grounding to find real organizations (e.g. Robin Hood Army, Feeding India, local orphanages).
        
        Return a JSON array of objects. Each object must have these exact keys and types:
        - name (string): Organization name
        - contact_person (string): Name of contact or "Admin"
        - phone (string): A real or placeholder phone number
        - address (string): Their operating location
        - latitude (float): Approximate latitude
        - longitude (float): Approximate longitude
        - accepts_cooked_food (boolean): True if they accept prepared meals
        - accepts_raw_produce (boolean): True if they accept raw ingredients
        - requires_cold_chain (boolean): True if they require strict temperature control
        - minimum_quantity_kg (float): Estimated minimum pickup amount (e.g. 5.0)
        - pickup_service_available (boolean): True if they offer pickup trucks
        """
        
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        extracted_data = json.loads(response.text)
        centres = []
        for c in extracted_data:
            c["id"] = f"dc_ai_{uuid.uuid4().hex[:8]}"
            c["verified"] = False  # AI-sourced centres need manual verification for safety
            centres.append(DonationCentre(**c))
            
        return centres
        
    except Exception as e:
        print(f"AI Discovery failed: {e}. Falling back to demo centres.")
        return DEMO_CENTRES

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_matches(request: MatchRequest, restaurant_lat: float, restaurant_lon: float, use_ai_discovery: bool = False, location_name: str = "Pune") -> List[MatchResult]:
    
    # Decide source of centres
    if use_ai_discovery:
        available_centres = discover_donation_centres_with_ai(location_name)
    else:
        available_centres = DEMO_CENTRES
        
    results = []
    
    for centre in available_centres:
        notes = []
        is_eligible = True
        score = 100
        
        dist = haversine_distance(restaurant_lat, restaurant_lon, centre.latitude, centre.longitude)
        
        if dist > 15.0:
            notes.append(f"Centre is too far ({dist:.1f} km).")
            is_eligible = False
            score -= 50
            
        if request.quantity_kg < centre.minimum_quantity_kg:
            notes.append(f"Quantity ({request.quantity_kg}kg) is below minimum ({centre.minimum_quantity_kg}kg).")
            is_eligible = False
            score -= 40
            
        if request.is_cooked and not centre.accepts_cooked_food:
            notes.append("Does not accept cooked food.")
            is_eligible = False
            score -= 100
            
        if not request.is_cooked and not centre.accepts_raw_produce:
            notes.append("Accepts meals only.")
            is_eligible = False
            score -= 100
            
        if request.requires_cold_chain and not centre.requires_cold_chain:
            notes.append("Lacks cold-chain support.")
            is_eligible = False
            score -= 100
            
        if not centre.verified:
            notes.append("⚠️ AI-Sourced: Manager must verify food safety protocols manually.")
            
        if is_eligible:
            if centre.pickup_service_available:
                score += 10
            score -= int(dist)
            
        results.append(MatchResult(
            centre=centre,
            match_score=max(0, score),
            distance_km=round(dist, 1),
            eligibility_notes=notes,
            is_eligible=is_eligible
        ))
        
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

def get_handovers(restaurant_id: str) -> List[HandoverResponse]:
    docs = db.get_collection(f"restaurants/{restaurant_id}/donation_handovers")
    return [HandoverResponse(**doc) for doc in docs]
