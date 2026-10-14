import uuid
from datetime import datetime, timezone
from typing import List, Optional
from ..repositories.database import db
from ..schemas.inventory import InventoryItemCreate, InventoryItemResponse, StockMovementCreate, StockMovementResponse
from .stock_service import convert_quantity, prepare_lot_depletion

def create_inventory_item(restaurant_id: str, item: InventoryItemCreate) -> InventoryItemResponse:
    item_id = f"inv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    doc_data = item.model_dump(mode="json")
    doc_data.update({
        "id": item_id,
        "ingredient_id": item_id,
        "restaurant_id": restaurant_id,
        "total_current_quantity": item.current_quantity_in_store + item.current_quantity_in_use,
        "status": "reorder_recommended" if item.current_quantity_in_store + item.current_quantity_in_use <= item.reorder_threshold else "in_stock",
        "updated_at": now.isoformat()
    })
    doc_data["stock_in_store"] = item.current_quantity_in_store
    doc_data["stock_in_use"] = item.current_quantity_in_use
    
    collection_path = f"restaurants/{restaurant_id}/inventory_items"
    db.add_document(collection_path, item_id, doc_data)
    
    return InventoryItemResponse(**doc_data)

def get_inventory_items(restaurant_id: str) -> List[InventoryItemResponse]:
    collection_path = f"restaurants/{restaurant_id}/inventory_items"
    docs = db.get_collection(collection_path)
    return [InventoryItemResponse(**doc) for doc in docs]

def get_inventory_item(restaurant_id: str, item_id: str) -> Optional[InventoryItemResponse]:
    collection_path = f"restaurants/{restaurant_id}/inventory_items"
    doc = db.get_document(collection_path, item_id)
    if doc:
        return InventoryItemResponse(**doc)
    return None

def record_stock_movement(restaurant_id: str, movement: StockMovementCreate, user: str) -> StockMovementResponse:
    movement_id = f"mov_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Fetch current item to update balance
    item = get_inventory_item(restaurant_id, movement.item_id)
    if not item:
        raise ValueError(f"Inventory item {movement.item_id} not found")
        
    stock_unit = item.input_unit or item.base_unit
    quantity_delta = convert_quantity(movement.quantity_delta, movement.unit, stock_unit)
    balance_after = item.total_current_quantity + quantity_delta
    if balance_after < 0:
        raise ValueError("Stock movement would make inventory quantity negative.")
    
    doc_data = movement.model_dump(mode="json")
    doc_data["quantity_delta"] = quantity_delta
    doc_data["unit"] = stock_unit
    doc_data.update({
        "id": movement_id,
        "ingredient_id": item.id,
        "restaurant_id": restaurant_id,
        "timestamp": now.isoformat(),
        "balance_after": balance_after,
        "created_by": user
    })
    
    mov_collection_path = f"restaurants/{restaurant_id}/stock_movements"
    store = item.current_quantity_in_store
    in_use = item.current_quantity_in_use
    if quantity_delta >= 0:
        store += quantity_delta
    else:
        remaining = abs(quantity_delta)
        used_from_in_use = min(in_use, remaining)
        in_use -= used_from_in_use
        store -= remaining - used_from_in_use

    updated_item_data = item.model_dump(mode="json")
    updated_item_data["updated_at"] = now.isoformat()
    updated_item_data["current_quantity_in_store"] = store
    updated_item_data["stock_in_store"] = store
    updated_item_data["current_quantity_in_use"] = in_use
    updated_item_data["stock_in_use"] = in_use
    updated_item_data["total_current_quantity"] = balance_after
    item_data = item.model_dump(mode="json")
    lot_writes = []
    if item_data.get("lot_tracking_enabled"):
        if quantity_delta < 0:
            lot_writes, allocations, remaining_untracked = prepare_lot_depletion(
                restaurant_id, item_data, abs(quantity_delta),
            )
            updated_item_data["untracked_stock_quantity"] = remaining_untracked
            doc_data["lot_allocations"] = allocations
        else:
            updated_item_data["untracked_stock_quantity"] = (
                float(item_data.get("untracked_stock_quantity", 0) or 0) + quantity_delta
            )
    
    if balance_after <= item.reorder_threshold:
        updated_item_data["status"] = "reorder_recommended"
    else:
        updated_item_data["status"] = "in_stock"
        
    inv_collection_path = f"restaurants/{restaurant_id}/inventory_items"
    db.set_documents([
        *lot_writes,
        (mov_collection_path, movement_id, doc_data),
        (inv_collection_path, item.id, updated_item_data),
    ])
    
    return StockMovementResponse(**doc_data)
