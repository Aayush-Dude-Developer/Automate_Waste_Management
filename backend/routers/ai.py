from fastapi import APIRouter, Header, HTTPException
from ..schemas.ai import InvestigationRequest, SurplusInvestigationResponse, ActionApprovalRequest
from ..agents.investigation_agent import run_surplus_investigation
from ..repositories.database import db
import datetime

router = APIRouter(prefix="/api/ai", tags=["Agentic AI"])

@router.post("/investigate-surplus", response_model=SurplusInvestigationResponse)
def investigate_surplus(
    request: InvestigationRequest,
    x_restaurant_id: str = Header(default="taiken_kharadi")
):
    return run_surplus_investigation(x_restaurant_id, request.target_item_id, request.target_item_name)

@router.post("/investigations/{investigation_id}/approve-action")
def approve_action(
    investigation_id: str,
    request: ActionApprovalRequest,
    x_restaurant_id: str = Header(default="taiken_kharadi")
):
    collection_path = f"restaurants/{x_restaurant_id}/ai_investigations"
    inv = db.get_document(collection_path, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
        
    inv["status"] = "APPROVED"
    inv["selected_action"] = request.selected_intervention_id
    inv["approved_by"] = "Manager (API)"
    inv["approval_notes"] = request.notes
    inv["approved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    db.add_document(collection_path, investigation_id, inv)
    
    # In a full system, this would trigger the actual backend adjustment
    
    return {"status": "success", "investigation": inv}
