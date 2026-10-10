import math
from typing import Dict, Any, List

def calculate_reorder_quantity(
    item_name: str,
    current_stock: float,
    incoming_stock: float,
    daily_demand_forecast: float,
    lead_time_days: int,
    safety_stock: float,
    pack_size: float = 1.0
) -> Dict[str, Any]:
    """
    Deterministic calculation for inventory replenishment.
    Formula: Net Reorder = (Lead Time Demand + Safety Stock) - (On Hand + Incoming)
    """
    lead_time_demand = daily_demand_forecast * lead_time_days
    target_stock_level = lead_time_demand + safety_stock
    
    net_requirement = target_stock_level - (current_stock + incoming_stock)
    
    # If we have enough stock, requirement is 0
    if net_requirement <= 0:
        recommended_purchase_qty = 0.0
        reasoning = f"Current stock ({current_stock}) + incoming ({incoming_stock}) covers the lead time demand ({lead_time_demand}) and safety stock ({safety_stock})."
    else:
        # Round up to the nearest whole pack size
        packs_required = math.ceil(net_requirement / pack_size)
        recommended_purchase_qty = packs_required * pack_size
        reasoning = (f"Target stock is {target_stock_level}. We have {current_stock + incoming_stock}. "
                     f"Need {net_requirement}. Ordering {packs_required} pack(s) of {pack_size} provides {recommended_purchase_qty}.")

    return {
        "item_name": item_name,
        "current_stock": current_stock,
        "expected_lead_time_demand": lead_time_demand,
        "target_stock_level": target_stock_level,
        "recommended_purchase_quantity": recommended_purchase_qty,
        "recommended_packs": recommended_purchase_qty / pack_size if pack_size else 0,
        "reasoning": reasoning,
        "data_quality_status": "HIGH" if daily_demand_forecast > 0 else "FALLBACK_ESTIMATE"
    }

def estimate_daily_demand(historical_consumption: List[float]) -> float:
    """
    Simple Moving Average fallback when complex statistical models lack data.
    """
    if not historical_consumption:
        return 0.0
    # Exclude negative anomalies
    valid_data = [x for x in historical_consumption if x >= 0]
    if not valid_data:
        return 0.0
    return sum(valid_data) / len(valid_data)
