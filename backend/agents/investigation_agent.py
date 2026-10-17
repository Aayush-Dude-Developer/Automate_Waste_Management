import json
import logging
import uuid
from collections import Counter
from ..schemas.ai import SurplusInvestigationResponse, InterventionProposal
from ..config import settings
from .tools import get_inventory_status, get_recent_waste_history, check_donation_eligibility
from ..repositories.database import db

logger = logging.getLogger(__name__)
GEMINI_TIMEOUT_MS = 60_000


_WASTE_UNIT_FACTORS = {
    "kg": ("kg", 1.0), "kilogram": ("kg", 1.0), "kilograms": ("kg", 1.0),
    "g": ("kg", 0.001), "gm": ("kg", 0.001), "gram": ("kg", 0.001), "grams": ("kg", 0.001),
    "l": ("ltr", 1.0), "ltr": ("ltr", 1.0), "liter": ("ltr", 1.0), "litre": ("ltr", 1.0),
    "ml": ("ltr", 0.001), "milliliter": ("ltr", 0.001), "millilitre": ("ltr", 0.001),
    "piece": ("piece", 1.0), "pieces": ("piece", 1.0), "pc": ("piece", 1.0),
    "pcs": ("piece", 1.0), "each": ("piece", 1.0),
}


def _waste_totals(history: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for record in history:
        try:
            quantity = float(record.get("quantity") or 0)
        except (TypeError, ValueError):
            continue
        if quantity <= 0:
            continue
        raw_unit = str(record.get("unit") or "unit").strip()
        canonical = _WASTE_UNIT_FACTORS.get(raw_unit.casefold())
        unit, factor = canonical if canonical else (raw_unit, 1.0)
        totals[unit] = totals.get(unit, 0.0) + quantity * factor
    return {unit: round(quantity, 3) for unit, quantity in sorted(totals.items())}


def _common_reasons(history: list[dict], limit: int = 3) -> list[str]:
    reason_names: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for record in history:
        reason = " ".join(str(record.get("reason") or "").split()) or "Reason not recorded"
        key = reason.casefold()
        reason_names.setdefault(key, reason)
        counts[key] += 1
    return [
        f"{reason_names[key]} ({count} {'record' if count == 1 else 'records'})"
        for key, count in sorted(counts.items(), key=lambda entry: (-entry[1], entry[0]))[:limit]
    ]


def _fallback_suggestions(common_reasons: list[str]) -> list[str]:
    if not common_reasons:
        return [
            "Record the reason and quantity for each waste event to identify repeat causes.",
            "Review preparation and storage practices for this item during each shift.",
            "Adjust purchasing and preparation to match recent usage.",
        ]
    reasons = ", ".join(reason.split(" (", 1)[0] for reason in common_reasons[:2])
    return [
        f"Review the handling and preparation steps associated with {reasons}.",
        "Track this item's daily usage and adjust order and prep quantities to match demand.",
        "Check storage conditions and use older stock first to prevent avoidable spoilage.",
    ]


def run_surplus_investigation(
    restaurant_id: str,
    item_id: str,
    item_name: str,
) -> SurplusInvestigationResponse:
    # This acts as the agent orchestrator
    
    # 1. Gather context using tools
    inv_status = get_inventory_status(restaurant_id, item_id)
    waste_history = get_recent_waste_history(restaurant_id, item_name, item_id or None)
    total_waste_by_unit = _waste_totals(waste_history)
    common_waste_reasons = _common_reasons(waste_history)
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
            Complete Waste History: {waste_history}
            Verified waste frequency: {len(waste_history)} records
            Verified total waste by unit: {total_waste_by_unit}
            Most common recorded reasons: {common_waste_reasons}
            Donation Rules: {donation_rule}
            
            Analyze the complete history, not only the latest week. Provide three concise,
            practical waste_reduction_suggestions grounded in the recorded reasons. Preserve
            the supplied verified waste frequency, totals, and reason counts exactly; do not
            invent facts. Return the remaining required JSON fields as requested by the schema.
            Each intervention must include intervention_id, action_type, title, details,
            expected_impact_inr, feasibility_rating, and requires_manager_approval.
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
                            "waste_reduction_suggestions": {
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
                            "waste_reduction_suggestions",
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
                waste_frequency_count=len(waste_history),
                total_waste_by_unit=total_waste_by_unit,
                common_waste_reasons=common_waste_reasons,
                waste_reduction_suggestions=data["waste_reduction_suggestions"],
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
    if not waste_history:
        facts.append("No matching waste records were found.")
        
    result = SurplusInvestigationResponse(
        id=investigation_id,
        target_item_name=item_name,
        analysis_source="deterministic",
        waste_frequency_count=len(waste_history),
        total_waste_by_unit=total_waste_by_unit,
        common_waste_reasons=common_waste_reasons,
        waste_reduction_suggestions=_fallback_suggestions(common_waste_reasons),
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
