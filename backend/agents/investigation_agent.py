import json
import logging
import uuid
from ..schemas.ai import SurplusInvestigationResponse, InterventionProposal
from ..config import settings
from .tools import get_inventory_status, get_recent_waste_history, check_donation_eligibility
from ..repositories.database import db

logger = logging.getLogger(__name__)
GEMINI_TIMEOUT_MS = 60_000


def run_surplus_investigation(restaurant_id: str, item_id: str, item_name: str) -> SurplusInvestigationResponse:
    # This acts as the agent orchestrator
    
    # 1. Gather context using tools
    inv_status = get_inventory_status(restaurant_id, item_id)
    waste_history = get_recent_waste_history(restaurant_id, item_name)
    donation_rule = check_donation_eligibility(item_name, inv_status.get("category", "Unknown"))
    
    # 2. Check if Gemini is enabled and available
    api_key = settings.GEMINI_API_KEY
    if api_key and api_key != "your_gemini_api_key_here":
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=GEMINI_TIMEOUT_MS,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
            
            prompt = f"""
            You are the Surplus Investigation Agent for a restaurant.
            Target Item: {item_name}
            Inventory Status: {inv_status}
            Recent Waste History: {waste_history}
            Donation Rules: {donation_rule}
            
            Your job is to analyze why this item is at risk of surplus/waste and recommend interventions.
            Use only the supplied data for verified_facts. Do not invent inventory, waste,
            demand, or donation facts. Return a concise analysis with these JSON fields:
            investigation_summary, verified_facts, hypotheses, data_gaps, and
            recommended_interventions. Each intervention must include intervention_id,
            action_type, title, details, expected_impact_inr, feasibility_rating, and
            requires_manager_approval.
            """
            
            response = client.interactions.create(
                model=settings.GEMINI_MODEL,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "investigation_summary": {"type": "string"},
                            "verified_facts": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "hypotheses": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "data_gaps": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "recommended_interventions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "intervention_id": {"type": "string"},
                                        "action_type": {"type": "string"},
                                        "title": {"type": "string"},
                                        "details": {"type": "string"},
                                        "expected_impact_inr": {"type": "number"},
                                        "feasibility_rating": {"type": "string"},
                                        "requires_manager_approval": {
                                            "type": "boolean"
                                        },
                                    },
                                    "required": [
                                        "intervention_id",
                                        "action_type",
                                        "title",
                                        "details",
                                        "expected_impact_inr",
                                        "feasibility_rating",
                                        "requires_manager_approval",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": [
                            "investigation_summary",
                            "verified_facts",
                            "hypotheses",
                            "data_gaps",
                            "recommended_interventions",
                        ],
                        "additionalProperties": False,
                    },
                },
            )
            data = json.loads(response.output_text)
            
            investigation_id = f"inv_{uuid.uuid4().hex[:12]}"
            current_qty = inv_status.get("total_current_quantity", 0)
            cost = inv_status.get("unit_cost_inr", 0)
            
            result = SurplusInvestigationResponse(
                id=investigation_id,
                target_item_name=item_name,
                analysis_source="gemini",
                investigation_summary=data["investigation_summary"],
                verified_facts=data["verified_facts"],
                hypotheses=data["hypotheses"],
                data_gaps=data["data_gaps"],
                financial_risk_inr=float(current_qty * cost),
                recommended_interventions=[InterventionProposal(**i) for i in data.get("recommended_interventions", [])]
            )
            
            db.add_document(f"restaurants/{restaurant_id}/ai_investigations", investigation_id, result.model_dump())
            return result
            
        except Exception as e:
            logger.warning(
                "Gemini API failed; using deterministic investigation fallback: %s",
                e,
            )
    
    # 3. Fallback Deterministic Logic (if API key missing or error)
    investigation_id = f"inv_{uuid.uuid4().hex[:12]}"
    
    current_qty = inv_status.get("total_current_quantity", 0)
    cost = inv_status.get("unit_cost_inr", 0)
    fin_risk = current_qty * cost
    
    facts = [f"Current inventory is {current_qty} {inv_status.get('unit', '')}"]
    if waste_history:
        facts.append(f"Item has been wasted {len(waste_history)} times recently.")
        
    result = SurplusInvestigationResponse(
        id=investigation_id,
        target_item_name=item_name,
        analysis_source="deterministic",
        investigation_summary=(
            f"Deterministic risk assessment for {item_name}. "
            "Gemini analysis is temporarily unavailable."
        ),
        verified_facts=facts,
        hypotheses=[
            "Demand changes have not been verified.",
            "Order quantities have not been compared with forecast demand.",
        ],
        data_gaps=[
            "Gemini analysis is unavailable.",
            "No scheduled buffet cover data is available.",
        ],
        financial_risk_inr=fin_risk,
        recommended_interventions=[
            InterventionProposal(
                intervention_id="act_trim_1",
                action_type="TRIM_PRODUCTION",
                title="Reduce prep batch by 20%",
                details="Trim the daily prep amount to align with lowered demand.",
                expected_impact_inr=fin_risk * 0.2,
                feasibility_rating="High"
            ),
            InterventionProposal(
                intervention_id="act_donate_1",
                action_type="DONATION",
                title="Route to verified charity",
                details=f"Eligibility: {donation_rule}",
                expected_impact_inr=fin_risk * 0.8,
                feasibility_rating="Medium"
            )
        ]
    )
    
    db.add_document(f"restaurants/{restaurant_id}/ai_investigations", investigation_id, result.model_dump())
    return result
