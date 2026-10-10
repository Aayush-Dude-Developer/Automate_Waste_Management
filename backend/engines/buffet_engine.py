import math
from typing import Dict, Any

def calculate_buffet_production(
    dish_name: str,
    expected_covers: int,
    historical_consumption_per_cover: float,
    buffer_percentage: float,
    standard_batch_yield: float,
    unit: str
) -> Dict[str, Any]:
    """
    Deterministic calculation for buffet production batching.
    Balancing shortage risk vs overproduction waste.
    """
    base_requirement = expected_covers * historical_consumption_per_cover
    safety_buffer = base_requirement * (buffer_percentage / 100.0)
    target_production = base_requirement + safety_buffer
    
    # Calculate how many full batches to cook
    recommended_batches = math.ceil(target_production / standard_batch_yield)
    actual_planned_production = recommended_batches * standard_batch_yield
    
    # Predict surplus if covers match exactly
    predicted_surplus = actual_planned_production - base_requirement
    
    reasoning = (f"Base demand for {expected_covers} covers is {base_requirement:.1f} {unit}. "
                 f"Added {buffer_percentage}% buffer ({safety_buffer:.1f} {unit}). "
                 f"Target is {target_production:.1f} {unit}. "
                 f"Cooking {recommended_batches} batch(es) yields {actual_planned_production:.1f} {unit}.")

    return {
        "dish_name": dish_name,
        "expected_covers": expected_covers,
        "base_requirement": round(base_requirement, 2),
        "target_production": round(target_production, 2),
        "recommended_batches": recommended_batches,
        "actual_planned_production": round(actual_planned_production, 2),
        "predicted_surplus_portions": round(predicted_surplus, 2),
        "unit": unit,
        "reasoning": reasoning,
        "confidence": "HIGH" if historical_consumption_per_cover > 0 else "LOW"
    }
