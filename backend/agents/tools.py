from typing import Dict, Any, List
from ..services.inventory_service import get_inventory_item, get_inventory_items
from ..services.waste_service import get_waste_records, get_staff_meal_records

def get_inventory_status(restaurant_id: str, item_id: str) -> Dict[str, Any]:
    """Returns current inventory stock, location, and unit cost for an item."""
    item = get_inventory_item(restaurant_id, item_id)
    if not item:
        return {"error": f"Item {item_id} not found."}
    return {
        "item_name": item.item_name,
        "total_current_quantity": item.total_current_quantity,
        "unit": item.base_unit,
        "unit_cost_inr": item.unit_cost_inr,
        "status": item.status
    }

def get_recent_waste_history(restaurant_id: str, item_name: str, days: int = 7) -> List[Dict[str, Any]]:
    """Returns recent waste records for a specific item to identify patterns."""
    all_waste = get_waste_records(restaurant_id)
    # Simple mock filter
    filtered = [w for w in all_waste if item_name.lower() in w.item_name.lower()]
    return [{"date": w.date, "quantity": w.quantity, "reason": w.reason} for w in filtered]

def check_donation_eligibility(item_name: str, category: str) -> str:
    """Checks deterministic safety rules to see if an item can be donated."""
    if category.lower() in ["produce", "dry pantry", "dry pantry / grocery"]:
        return "Eligible if packaging is intact and not expired."
    if category.lower() in ["meat & poultry", "seafood"]:
        return "Eligible only if cold-chain is strictly maintained (<4C)."
    return "Requires manager food-safety verification before donation."
