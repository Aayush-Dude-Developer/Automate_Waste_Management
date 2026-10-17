from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

class InterventionProposal(BaseModel):
    intervention_id: str
    action_type: str # TRIM_PRODUCTION, REDUCE_PURCHASE_ORDER, PROMOTIONAL_DISCOUNT, RECIPE_AUDIT, DONATION
    title: str
    details: str
    expected_impact_inr: float
    feasibility_rating: str # High, Medium, Low
    requires_manager_approval: bool = True

class SurplusInvestigationResponse(BaseModel):
    id: str
    target_item_name: str
    analysis_source: Literal["gemini", "deterministic"] = "deterministic"
    investigation_summary: str
    waste_frequency_count: int = 0
    total_waste_by_unit: Dict[str, float] = Field(default_factory=dict)
    common_waste_reasons: List[str] = Field(default_factory=list)
    waste_reduction_suggestions: List[str] = Field(default_factory=list)
    verified_facts: List[str]
    hypotheses: List[str]
    data_gaps: List[str]
    financial_risk_inr: float
    recommended_interventions: List[InterventionProposal]
    status: str = "PENDING_MANAGER_APPROVAL"

class InvestigationRequest(BaseModel):
    target_item_id: str
    target_item_name: str
    service_date: str

class ActionApprovalRequest(BaseModel):
    selected_intervention_id: str
    notes: Optional[str] = None
