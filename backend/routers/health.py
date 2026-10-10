from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/health", tags=["Health"])

class HealthResponse(BaseModel):
    status: str
    database: str
    gemini_ready: bool

@router.get("", response_model=HealthResponse)
def check_health():
    # In Phase 2, we return a simple mock status.
    # In future phases, this will check actual Firestore and Gemini connectivity.
    return HealthResponse(
        status="ok",
        database="local_fallback",
        gemini_ready=False
    )
