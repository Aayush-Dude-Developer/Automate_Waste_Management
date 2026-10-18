from fastapi import APIRouter, Depends

from ..auth import get_current_user, get_restaurant_id

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/me")
def get_current_user_profile(
    user: dict[str, str] = Depends(get_current_user),
    restaurant_id: str = Depends(get_restaurant_id),
):
    return {"email": user["email"], "restaurant_id": restaurant_id}
