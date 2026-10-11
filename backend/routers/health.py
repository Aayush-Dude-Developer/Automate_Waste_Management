from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..auth import get_current_user
from ..config import settings
from ..repositories.database import db

router = APIRouter(prefix="/api/health", tags=["Health"])

class HealthResponse(BaseModel):
    status: str
    database: str
    gemini_ready: bool

@router.get("", response_model=HealthResponse)
def check_health(user: dict[str, str] = Depends(get_current_user)):
    return HealthResponse(
        status="ok",
        database="firestore" if settings.DATABASE_BACKEND == "firestore" and type(db).__name__ == "FirestoreDatabase" else "local",
        gemini_ready=bool(settings.GEMINI_API_KEY)
    )
