from typing import Any

from fastapi import APIRouter, Depends

from ..auth import get_restaurant_id
from ..config import settings
from ..repositories.database import db

router = APIRouter(prefix="/api/restaurant", tags=["Restaurant"])


@router.get("/profile")
def get_restaurant_profile(
    restaurant_id: str = Depends(get_restaurant_id),
) -> dict[str, Any]:
    profile = db.get_document(f"restaurants/{restaurant_id}/profile", "main") or {}
    return {
        **profile,
        "id": restaurant_id,
        "name": profile.get("name", "Straits Garden Kitchen"),
        "outlet_name": profile.get("outlet_name", "Kharadi"),
        "location": profile.get("location", "Kharadi, Pune, India"),
        "address": profile.get("address", "Kharadi, Pune, India"),
        "timezone": profile.get("timezone", "Asia/Kolkata"),
    }
