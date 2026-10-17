from typing import Dict, Any, List
from ..services.inventory_service import get_inventory_item
from ..repositories.database import db

def get_inventory_status(restaurant_id: str, item_id: str) -> Dict[str, Any]:
    """Returns current inventory stock, location, and unit cost for an item."""
    if not item_id:
        return {}
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

def get_recent_waste_history(
    restaurant_id: str,
    item_name: str,
    item_id: str | None = None,
) -> List[Dict[str, Any]]:
    """Return all matching waste records, including imported rows without inventory links."""
    normalize = lambda value: " ".join(str(value or "").casefold().split())
    target_name = normalize(item_name)
    linked_ids = {item_id} if item_id else set()
    inventory = db.get_collection(f"restaurants/{restaurant_id}/inventory_items")
    linked_ids.update(
        str(item.get("id") or item.get("ingredient_id"))
        for item in inventory
        if normalize(item.get("item_name")) == target_name
        and (item.get("id") or item.get("ingredient_id"))
    )
    inventory_names = {
        str(item.get("id") or item.get("ingredient_id")): item.get("item_name")
        for item in inventory
        if item.get("id") or item.get("ingredient_id")
    }

    records = []
    for row in db.get_collection(f"restaurants/{restaurant_id}/waste_records"):
        if (
            (row.get("inventory_item_id") and row.get("inventory_item_id") in linked_ids)
            or normalize(row.get("item_name")) == target_name
        ):
            records.append({
                "date": row.get("date"),
                "quantity": row.get("quantity", 0),
                "unit": row.get("unit", ""),
                "reason": row.get("reason", ""),
                "item_name": row.get("item_name") or item_name,
            })

    for row in db.get_collection(f"restaurants/{restaurant_id}/waste_records_v2"):
        ingredient_id = str(row.get("ingredient_id") or "")
        row_name = row.get("item_name") or inventory_names.get(ingredient_id)
        if ingredient_id in linked_ids or normalize(row_name) == target_name:
            records.append({
                "date": row.get("waste_date"),
                "quantity": row.get("quantity", 0),
                "unit": row.get("unit", ""),
                "reason": row.get("waste_reason", ""),
                "item_name": row_name or item_name,
            })
    return records

def check_donation_eligibility(item_name: str, category: str) -> str:
    """Checks deterministic safety rules to see if an item can be donated."""
    if category.lower() in ["produce", "dry pantry", "dry pantry / grocery"]:
        return "Eligible if packaging is intact and not expired."
    if category.lower() in ["meat & poultry", "seafood"]:
        return "Eligible only if cold-chain is strictly maintained (<4C)."
    return "Requires manager food-safety verification before donation."
