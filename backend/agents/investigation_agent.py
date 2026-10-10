import os
import uuid
from typing import Dict, Any
from ..schemas.ai import SurplusInvestigationResponse, InterventionProposal
from ..config import settings
from .tools import get_inventory_status, get_recent_waste_history, check_donation_eligibility
from ..repositories.database import db

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
            
            client = genai.Client(api_key=api_key)
            
            prompt = f"""
            You are the Surplus Investigation Agent for a restaurant.
            Target Item: {item_name}
            Inventory Status: {inv_status}
            Recent Waste History: {waste_history}
            Donation Rules: {donation_rule}
            
            Your job is to analyze why this item is at risk of surplus/waste and recommend interventions.
            Separate your findings strictly into verified_facts (from the data above), hypotheses, and data_gaps.
            """
            
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    # Schema matches SurplusInvestigationResponse roughly
                )
            )
            import json
            data = json.loads(response.text)
            
            # Map back to our schema (simplified for reliability here)
            investigation_id = f"inv_{uuid.uuid4().hex[:12]}"
            
            result = SurplusInvestigationResponse(
                id=investigation_id,
                target_item_name=item_name,
                investigation_summary=data.get("investigation_summary", "Agent analysis completed."),
                verified_facts=data.get("verified_facts", []),
                hypotheses=data.get("hypotheses", []),
                data_gaps=data.get("data_gaps", []),
                financial_risk_inr=float(data.get("financial_risk_inr", 0.0)),
                recommended_interventions=[InterventionProposal(**i) for i in data.get("recommended_interventions", [])]
            )
            
            db.add_document(f"restaurants/{restaurant_id}/ai_investigations", investigation_id, result.model_dump())
            return result
            
        except Exception as e:
            print(f"Gemini API failed: {e}. Falling back to deterministic heuristics.")
    
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
        investigation_summary=f"Automated risk analysis for {item_name}. High surplus detected.",
        verified_facts=facts,
        hypotheses=["Demand has dropped compared to historical averages.", "Possible over-ordering from supplier."],
        data_gaps=["No scheduled buffet cover data available for tonight."],
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
