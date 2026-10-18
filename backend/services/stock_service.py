import hashlib
import uuid
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Any

from ..repositories.database import db
from ..schemas.inventory import InventoryItemResponse
from ..schemas.stock import (
    MonthlyStockBalance,
    PhysicalStocktake,
    PurchaseInvoiceCreate,
    PurchaseInvoiceResponse,
    PurchaseLineResponse,
    RecipeCreate,
    RecipeIngredientResponse,
    RecipeResponse,
    SaleCreate,
    SaleResponse,
    StaffConsumptionCreate,
    StaffConsumptionResponse,
    TheoreticalConsumption,
    WasteRecordCreateV2,
    WasteRecordResponseV2,
)

_UNSET = object()


def _path(restaurant_id: str, collection: str) -> str:
    return f"restaurants/{restaurant_id}/{collection}"


def _get_item(restaurant_id: str, ingredient_id: str) -> dict[str, Any]:
    item = db.get_document(_path(restaurant_id, "inventory_items"), ingredient_id)
    if not item:
        raise ValueError(f"Inventory ingredient {ingredient_id} was not found.")
    return item


def _stock_quantity(item: dict[str, Any]) -> float:
    return float(item.get("current_quantity_in_store", item.get("stock_in_store", 0))) + float(
        item.get("current_quantity_in_use", item.get("stock_in_use", 0))
    )


def _apply_stock_delta(item: dict[str, Any], delta: float, now: str) -> dict[str, Any]:
    store = float(item.get("current_quantity_in_store", item.get("stock_in_store", 0)))
    use = float(item.get("current_quantity_in_use", item.get("stock_in_use", 0)))
    if store + use + delta < -1e-9:
        raise ValueError(f"Insufficient stock for {item.get('item_name', item.get('id'))}.")
    if delta >= 0:
        store += delta
    else:
        remaining = abs(delta)
        from_use = min(use, remaining)
        use -= from_use
        store -= remaining - from_use
    updated = dict(item)
    updated["current_quantity_in_store"] = store
    updated["stock_in_store"] = store
    updated["current_quantity_in_use"] = use
    updated["stock_in_use"] = use
    updated["total_current_quantity"] = store + use
    updated["status"] = (
        "reorder_recommended"
        if updated["total_current_quantity"] <= float(item.get("reorder_threshold", 0))
        else "in_stock"
    )
    updated["updated_at"] = now
    return updated


_UNIT_FACTORS = {
    "kg": ("mass", 1.0),
    "kilogram": ("mass", 1.0),
    "kilograms": ("mass", 1.0),
    "g": ("mass", 0.001),
    "gm": ("mass", 0.001),
    "gram": ("mass", 0.001),
    "grams": ("mass", 0.001),
    "mg": ("mass", 0.000001),
    "l": ("volume", 1.0),
    "ltr": ("volume", 1.0),
    "liter": ("volume", 1.0),
    "litre": ("volume", 1.0),
    "ml": ("volume", 0.001),
    "milliliter": ("volume", 0.001),
    "millilitre": ("volume", 0.001),
    "piece": ("count", 1.0),
    "pieces": ("count", 1.0),
    "pc": ("count", 1.0),
    "pcs": ("count", 1.0),
    "each": ("count", 1.0),
}


def convert_quantity(quantity: float, source_unit: str, target_unit: str) -> float:
    source = source_unit.strip().lower()
    target = target_unit.strip().lower()
    if source == target:
        return float(quantity)
    source_info = _UNIT_FACTORS.get(source)
    target_info = _UNIT_FACTORS.get(target)
    if not source_info or not target_info or source_info[0] != target_info[0]:
        raise ValueError(f"Cannot convert {source_unit!r} to {target_unit!r}.")
    return float(quantity) * source_info[1] / target_info[1]


def prepare_lot_depletion(
    restaurant_id: str,
    item: dict[str, Any],
    quantity: float,
    today: date | None = None,
) -> tuple[list[tuple[str, str, dict[str, Any]]], list[dict[str, Any]], float]:
    """Allocate a stock deduction to verified, unexpired batches before untracked stock."""
    if not item.get("lot_tracking_enabled") or quantity <= 0:
        return [], [], float(item.get("untracked_stock_quantity", 0) or 0)

    item_id = str(item.get("ingredient_id") or item.get("id"))
    lines = db.query_collection(
        _path(restaurant_id, "purchase_lines"),
        [("ingredient_id", "==", item_id)],
    )
    invoice_ids = list(dict.fromkeys(
        str(line.get("purchase_id")) for line in lines if line.get("purchase_id")
    ))
    verified_invoices: set[str] = set()
    for offset in range(0, len(invoice_ids), 30):
        invoices = db.query_collection(
            _path(restaurant_id, "purchase_invoices"),
            [("purchase_id", "in", invoice_ids[offset:offset + 30])],
        )
        verified_invoices.update(
            str(invoice.get("purchase_id"))
            for invoice in invoices
            if invoice.get("verification_status") == "verified"
        )

    as_of = today or datetime.now(timezone.utc).date()
    eligible = []
    for line in lines:
        if str(line.get("purchase_id")) not in verified_invoices:
            continue
        expiry = line.get("expiry_date")
        expiry_day = date.fromisoformat(str(expiry)[:10]) if expiry else None
        remaining = float(line.get("remaining_usable_quantity", 0) or 0)
        if remaining > 0 and (expiry_day is None or expiry_day >= as_of):
            eligible.append((expiry_day, line))
    eligible.sort(key=lambda row: (row[0] is None, row[0] or date.max, str(row[1].get("id", ""))))

    untracked = max(0.0, float(item.get("untracked_stock_quantity", 0) or 0))
    available = sum(float(line.get("remaining_usable_quantity", 0) or 0) for _, line in eligible) + untracked
    if available + 1e-9 < quantity:
        raise ValueError(
            f"Insufficient unexpired usable stock for {item.get('item_name', item_id)}: "
            f"{available:g} available, {quantity:g} requested."
        )

    writes: list[tuple[str, str, dict[str, Any]]] = []
    allocations: list[dict[str, Any]] = []
    remaining_to_allocate = quantity
    lines_path = _path(restaurant_id, "purchase_lines")
    for _, line in eligible:
        if remaining_to_allocate <= 1e-9:
            break
        old_quantity = float(line.get("remaining_usable_quantity", 0) or 0)
        allocated = min(old_quantity, remaining_to_allocate)
        updated_line = {**line, "remaining_usable_quantity": round(old_quantity - allocated, 6)}
        writes.append((lines_path, str(line["id"]), updated_line))
        allocations.append({
            "purchase_line_id": str(line.get("purchase_line_id") or line["id"]),
            "quantity": round(allocated, 6),
        })
        remaining_to_allocate -= allocated

    untracked_used = min(untracked, remaining_to_allocate)
    if untracked_used > 0:
        allocations.append({"untracked_quantity": round(untracked_used, 6)})
    return writes, allocations, round(untracked - untracked_used, 6)


def raw_ingredient_quantity(
    item: dict[str, Any],
    required_quantity: float,
    required_unit: str,
    required_stage: str,
    yield_stage_reference: str | None = None,
) -> tuple[float, str]:
    stock_unit = str(item.get("input_unit") or item.get("base_unit") or "kg")
    stages = item.get("yield_stages") or []
    if not stages and (float(item.get("yield_percentage", 0) or 0) != 0 or item.get("yield_stage")):
        target_stage = item.get("yield_stage") or "prepared"
        stages = [{
            "stage_name": target_stage,
            "input_stage": "raw",
            "output_stage": target_stage,
            "input_unit": item.get("input_unit") or stock_unit,
            "output_unit": item.get("output_unit") or stock_unit,
            "yield_percentage": item["yield_percentage"],
        }]

    target_stage = required_stage.strip().lower()
    quantity = float(required_quantity)
    if not stages:
        if target_stage not in {"raw", "input", "stock"}:
            raise ValueError(
                f"Configured yield stages do not convert {item.get('item_name')} "
                f"from stock stage to {required_stage}."
            )
        return convert_quantity(quantity, required_unit, stock_unit), stock_unit

    normalized = []
    for stage in stages:
        stage = dict(stage)
        percentage = float(stage.get("yield_percentage", 0))
        if percentage <= -100:
            raise ValueError(f"Invalid yield for {item.get('item_name')}: must be greater than -100.")
        normalized.append(stage)

    if target_stage in {"raw", "input", "stock"}:
        return convert_quantity(quantity, required_unit, stock_unit), stock_unit

    applicable = []
    current_stage = "raw"
    for stage in normalized:
        input_stage = str(stage.get("input_stage", current_stage)).lower()
        output_stage = str(stage.get("output_stage") or stage.get("stage_name", "")).lower()
        if input_stage != current_stage:
            continue
        applicable.append(stage)
        current_stage = output_stage
        if current_stage == target_stage:
            break

    if not applicable or current_stage != target_stage:
        raise ValueError(
            f"Yield stages for {item.get('item_name')} do not convert stock stage to {required_stage}."
        )
    referenced_stage = next(
        (stage for stage in normalized if stage.get("stage_name") == yield_stage_reference),
        None,
    ) if yield_stage_reference else None
    if yield_stage_reference and not referenced_stage:
        raise ValueError(f"Yield stage {yield_stage_reference!r} is not configured for {item.get('item_name')}.")
    if referenced_stage and str(referenced_stage.get("output_stage", "")).lower() != target_stage:
        raise ValueError("Yield stage reference does not match the recipe's required stage.")

    quantity = convert_quantity(
        quantity,
        required_unit,
        str(applicable[-1].get("output_unit") or stock_unit),
    )
    for stage in reversed(applicable):
        factor = 1 + float(stage.get("yield_percentage", 0)) / 100
        if factor <= 0:
            raise ValueError("Yield conversion denominator must be positive.")
        quantity = convert_quantity(
            quantity,
            str(stage.get("output_unit") or stock_unit),
            str(stage.get("input_unit") or stock_unit),
        ) / factor
    input_unit = str(applicable[0].get("input_unit") or stock_unit)
    return convert_quantity(quantity, input_unit, stock_unit), stock_unit


def _recipe(restaurant_id: str, recipe_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    recipe = db.get_document(_path(restaurant_id, "recipes"), recipe_id)
    if not recipe:
        raise ValueError(f"Recipe {recipe_id} was not found.")
    ingredients = db.query_collection(
        _path(restaurant_id, "recipe_ingredients"),
        [("recipe_id", "==", recipe_id)],
    )
    if not ingredients:
        raise ValueError(f"Recipe {recipe_id} has no ingredients.")
    return recipe, ingredients


def _ingredient_requirements(
    restaurant_id: str,
    recipe_id: str,
    portions: float,
) -> dict[str, tuple[dict[str, Any], float, str]]:
    _, recipe_ingredients = _recipe(restaurant_id, recipe_id)
    result: dict[str, tuple[dict[str, Any], float, str]] = {}
    for row in recipe_ingredients:
        item = _get_item(restaurant_id, row["ingredient_id"])
        quantity_per_portion = float(row["required_quantity"]) / float(row["servings_per_batch"])
        raw_per_portion, stock_unit = raw_ingredient_quantity(
            item,
            quantity_per_portion,
            row["required_unit"],
            row["required_stage"],
            row.get("yield_stage_reference"),
        )
        total = raw_per_portion * portions
        existing = result.get(row["ingredient_id"])
        result[row["ingredient_id"]] = (item, total + (existing[1] if existing else 0), stock_unit)
    return result


def create_purchase(restaurant_id: str, purchase: PurchaseInvoiceCreate) -> PurchaseInvoiceResponse:
    invoice_key = f"{purchase.supplier_id.strip().lower()}:{purchase.invoice_number.strip().lower()}"
    purchase_id = "pur_" + hashlib.sha256(invoice_key.encode("utf-8")).hexdigest()[:20]
    invoice_path = _path(restaurant_id, "purchase_invoices")
    if db.get_document(invoice_path, purchase_id):
        raise ValueError("This supplier invoice has already been recorded.")

    now = datetime.now(timezone.utc).isoformat()
    invoice = purchase.model_dump(mode="json", exclude={"line_items"})
    invoice.update({"purchase_id": purchase_id, "id": purchase_id, "restaurant_id": restaurant_id, "created_at": now})
    writes = [(invoice_path, purchase_id, invoice)]
    lines = []
    for line in purchase.line_items:
        item = _get_item(restaurant_id, line.ingredient_id)
        stock_unit = str(item.get("input_unit") or item.get("base_unit") or "kg")
        received = convert_quantity(line.quantity_received, line.purchase_unit, stock_unit)
        usable_input = line.usable_quantity if line.usable_quantity is not None else line.quantity_received
        usable = convert_quantity(usable_input, line.purchase_unit, stock_unit)
        line_id = f"pl_{uuid.uuid4().hex[:16]}"
        line_data = line.model_dump(mode="json")
        line_data.update({
            "id": line_id,
            "purchase_line_id": line_id,
            "purchase_id": purchase_id,
            "restaurant_id": restaurant_id,
            "ingredient_quantity_received": received,
            "usable_quantity": usable,
            "usable_unit": stock_unit,
        })
        writes.append((_path(restaurant_id, "purchase_lines"), line_id, line_data))
        lines.append(PurchaseLineResponse(**line_data))
    db.create_documents(writes)
    return PurchaseInvoiceResponse(**invoice, line_items=lines)


def get_purchases(
    restaurant_id: str,
    limit: int | None = None,
) -> list[PurchaseInvoiceResponse]:
    invoices = db.query_collection(
        _path(restaurant_id, "purchase_invoices"),
        order_by=("invoice_date", "DESCENDING") if limit else None,
        limit=limit,
    )
    invoice_ids = [invoice.get("purchase_id") for invoice in invoices if invoice.get("purchase_id")]
    lines_by_invoice: dict[str, list[dict[str, Any]]] = {}
    for offset in range(0, len(invoice_ids), 30):
        lines = db.query_collection(
            _path(restaurant_id, "purchase_lines"),
            [("purchase_id", "in", invoice_ids[offset:offset + 30])],
        )
        for line in lines:
            lines_by_invoice.setdefault(str(line.get("purchase_id")), []).append(line)
    return [
        PurchaseInvoiceResponse(
            **{key: value for key, value in invoice.items() if key in PurchaseInvoiceResponse.model_fields and key != "line_items"},
            line_items=[
                PurchaseLineResponse(**line)
                for line in lines_by_invoice.get(str(invoice.get("purchase_id")), [])
            ],
        )
        for invoice in invoices
    ]


def verify_purchase(restaurant_id: str, purchase_id: str) -> PurchaseInvoiceResponse:
    invoice_path = _path(restaurant_id, "purchase_invoices")
    invoice = db.get_document(invoice_path, purchase_id)
    if not invoice:
        raise ValueError(f"Purchase invoice {purchase_id} was not found.")
    lines_path = _path(restaurant_id, "purchase_lines")
    lines = db.query_collection(lines_path, [("purchase_id", "==", purchase_id)])
    if invoice.get("verification_status") == "verified":
        return PurchaseInvoiceResponse(**invoice, line_items=[PurchaseLineResponse(**line) for line in lines])
    if not invoice.get("received_date"):
        raise ValueError("Set a received date before verifying the invoice.")

    now = datetime.now(timezone.utc).isoformat()
    writes = []
    movements_path = _path(restaurant_id, "stock_movements")
    quantity_by_item: dict[str, float] = {}
    item_documents: dict[str, dict[str, Any]] = {}
    for line in lines:
        quantity = float(line.get("ingredient_quantity_received", 0))
        if quantity <= 0:
            continue
        item_id = line["ingredient_id"]
        writes.append((
            lines_path,
            str(line["id"]),
            {
                **line,
                "remaining_usable_quantity": float(
                    quantity if line.get("remaining_usable_quantity") is None
                    else line["remaining_usable_quantity"]
                ),
            },
        ))
        movement_id = f"purchase_{purchase_id}_{line['purchase_line_id']}"
        if db.get_document(movements_path, movement_id):
            continue
        existing_item_total = _stock_quantity(_get_item(restaurant_id, item_id))
        running_total = existing_item_total + quantity_by_item.get(item_id, 0.0) + quantity
        quantity_by_item[item_id] = quantity_by_item.get(item_id, 0.0) + quantity
        if item_id not in item_documents:
            item_documents[item_id] = _get_item(restaurant_id, item_id)
        movement = {
            "id": movement_id,
            "item_id": item_id,
            "ingredient_id": item_id,
            "movement_type": "RECEIPT_PURCHASE",
            "quantity_delta": quantity,
            "unit": item_documents[item_id].get("input_unit") or item_documents[item_id].get("base_unit") or "kg",
            "reference_id": line["purchase_line_id"],
            "purchase_id": purchase_id,
            "timestamp": now,
            "balance_after": running_total,
            "created_by": "purchase_verification",
        }
        writes.append((movements_path, movement_id, movement))
    for item_id, quantity in quantity_by_item.items():
        writes.append((
            _path(restaurant_id, "inventory_items"),
            item_id,
            _apply_stock_delta(item_documents[item_id], quantity, now),
        ))
    invoice.update({"verification_status": "verified", "verified_at": now})
    writes.append((invoice_path, purchase_id, invoice))
    db.set_documents(writes)
    return PurchaseInvoiceResponse(**invoice, line_items=[PurchaseLineResponse(**line) for line in lines])


def create_recipe(restaurant_id: str, recipe: RecipeCreate) -> RecipeResponse:
    recipe_id = f"rec_{uuid.uuid4().hex[:16]}"
    recipe_path = _path(restaurant_id, "recipes")
    recipe_data = recipe.model_dump(mode="json", exclude={"ingredients"})
    recipe_data.update({"recipe_id": recipe_id, "id": recipe_id, "restaurant_id": restaurant_id})
    writes = [(recipe_path, recipe_id, recipe_data)]
    ingredient_responses = []
    for ingredient in recipe.ingredients:
        item = _get_item(restaurant_id, ingredient.ingredient_id)
        raw_ingredient_quantity(
            item,
            ingredient.required_quantity,
            ingredient.required_unit,
            ingredient.required_stage,
            ingredient.yield_stage_reference,
        )
        row_id = f"{recipe_id}_{uuid.uuid4().hex[:10]}"
        row = ingredient.model_dump(mode="json")
        row.update({"id": row_id, "recipe_id": recipe_id, "restaurant_id": restaurant_id})
        writes.append((_path(restaurant_id, "recipe_ingredients"), row_id, row))
        ingredient_responses.append(RecipeIngredientResponse(**row))
    db.set_documents(writes)
    return RecipeResponse(**recipe_data, ingredients=ingredient_responses)


def get_recipes(restaurant_id: str) -> list[RecipeResponse]:
    recipes = db.get_collection(_path(restaurant_id, "recipes"))
    recipe_ids = [recipe.get("recipe_id") for recipe in recipes if recipe.get("recipe_id")]
    rows_by_recipe: dict[str, list[dict[str, Any]]] = {}
    for offset in range(0, len(recipe_ids), 30):
        rows = db.query_collection(
            _path(restaurant_id, "recipe_ingredients"),
            [("recipe_id", "in", recipe_ids[offset:offset + 30])],
        )
        for row in rows:
            rows_by_recipe.setdefault(str(row.get("recipe_id")), []).append(row)
    return [
        RecipeResponse(
            **{key: value for key, value in recipe.items() if key in RecipeResponse.model_fields and key != "ingredients"},
            ingredients=[RecipeIngredientResponse(**row) for row in rows_by_recipe.get(str(recipe.get("recipe_id")), [])],
        )
        for recipe in recipes
    ]


def create_sale(restaurant_id: str, sale: SaleCreate) -> SaleResponse:
    if sale.source_reference:
        reference = sale.source_reference.strip()
        for collection in ("daily_sales", "staff_consumptions"):
            if db.query_collection(
                _path(restaurant_id, collection),
                [("source_reference", "==", reference)],
            ):
                raise ValueError(
                    "This source reference is already recorded as a sale or staff consumption."
                )
    recipe, _ = _recipe(restaurant_id, sale.recipe_id)
    consumed_portions = sale.quantity_prepared if sale.quantity_prepared is not None else sale.net_quantity_sold
    requirements = _ingredient_requirements(restaurant_id, sale.recipe_id, float(consumed_portions or 0))
    sale_id = f"sale_{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc).isoformat()
    sale_data = sale.model_dump(mode="json")
    if sale_data.get("source_reference"):
        sale_data["source_reference"] = sale_data["source_reference"].strip()
    sale_data.update({"sale_record_id": sale_id, "id": sale_id, "restaurant_id": restaurant_id})
    writes = [(_path(restaurant_id, "daily_sales"), sale_id, sale_data)]
    for ingredient_id, (item, quantity, unit) in requirements.items():
        updated = _apply_stock_delta(item, -quantity, now)
        lot_writes, lot_allocations, remaining_untracked = prepare_lot_depletion(
            restaurant_id, item, quantity,
        )
        if item.get("lot_tracking_enabled"):
            updated["untracked_stock_quantity"] = remaining_untracked
        movement_id = f"{sale_id}_{ingredient_id}"
        movement = {
            "id": movement_id,
            "item_id": ingredient_id,
            "ingredient_id": ingredient_id,
            "movement_type": "USAGE_SALES_RECIPE",
            "quantity_delta": -quantity,
            "unit": unit,
            "reference_id": sale_id,
            "recipe_id": recipe["recipe_id"],
            "timestamp": now,
            "balance_after": updated["total_current_quantity"],
            "created_by": "sales_entry",
        }
        if item.get("lot_tracking_enabled"):
            movement["lot_allocations"] = lot_allocations
        writes.extend([
            *lot_writes,
            (_path(restaurant_id, "inventory_items"), ingredient_id, updated),
            (_path(restaurant_id, "stock_movements"), movement_id, movement),
        ])
    db.set_documents(writes)
    return SaleResponse(**sale_data)


def create_staff_consumption(
    restaurant_id: str, consumption: StaffConsumptionCreate
) -> StaffConsumptionResponse:
    if consumption.source_reference:
        reference = consumption.source_reference.strip()
        for collection in ("daily_sales", "staff_consumptions"):
            if db.query_collection(
                _path(restaurant_id, collection),
                [("source_reference", "==", reference)],
            ):
                raise ValueError(
                    "This source reference is already recorded as a sale or staff consumption."
                )
    consumption_id = f"stf_{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc).isoformat()
    data = consumption.model_dump(mode="json")
    if data.get("source_reference"):
        data["source_reference"] = data["source_reference"].strip()
    data.update({"consumption_id": consumption_id, "id": consumption_id, "restaurant_id": restaurant_id})
    if consumption.recipe_id:
        requirements = _ingredient_requirements(
            restaurant_id,
            consumption.recipe_id,
            float(consumption.portions),
        )
    else:
        ingredient_id = str(consumption.ingredient_id)
        item = _get_item(restaurant_id, ingredient_id)
        unit = str(item.get("input_unit") or item.get("base_unit") or "kg")
        requirements = {
            ingredient_id: (
                item,
                convert_quantity(float(consumption.quantity), str(consumption.unit), unit),
                unit,
            )
        }
    writes = [(_path(restaurant_id, "staff_consumptions"), consumption_id, data)]
    for ingredient_id, (item, quantity, unit) in requirements.items():
        updated = _apply_stock_delta(item, -quantity, now)
        lot_writes, lot_allocations, remaining_untracked = prepare_lot_depletion(
            restaurant_id, item, quantity,
        )
        if item.get("lot_tracking_enabled"):
            updated["untracked_stock_quantity"] = remaining_untracked
        movement_id = f"{consumption_id}_{ingredient_id}"
        movement = {
            "id": movement_id,
            "item_id": ingredient_id,
            "ingredient_id": ingredient_id,
            "movement_type": "USAGE_STAFF_MEAL",
            "quantity_delta": -quantity,
            "unit": unit,
            "reference_id": consumption_id,
            "timestamp": now,
            "balance_after": updated["total_current_quantity"],
            "created_by": consumption.recorded_by,
        }
        if item.get("lot_tracking_enabled"):
            movement["lot_allocations"] = lot_allocations
        writes.extend([
            *lot_writes,
            (_path(restaurant_id, "inventory_items"), ingredient_id, updated),
            (_path(restaurant_id, "stock_movements"), movement_id, movement),
        ])
    db.set_documents(writes)
    return StaffConsumptionResponse(**data)


def create_waste_record_v2(
    restaurant_id: str, waste: WasteRecordCreateV2
) -> WasteRecordResponseV2:
    item = _get_item(restaurant_id, waste.ingredient_id)
    stock_unit = str(item.get("input_unit") or item.get("base_unit") or "kg")
    quantity = convert_quantity(waste.quantity, waste.unit, stock_unit)
    cost = waste.estimated_cost
    if cost is None:
        cost = quantity * float(item.get("unit_cost", item.get("unit_cost_inr", 0)))
    waste_id = f"wst_{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc).isoformat()
    data = waste.model_dump(mode="json")
    data.update({
        "waste_record_id": waste_id,
        "id": waste_id,
        "restaurant_id": restaurant_id,
        "estimated_cost": cost,
    })
    writes = [(_path(restaurant_id, "waste_records_v2"), waste_id, data)]
    if waste.waste_type == "raw_ingredient":
        updated = _apply_stock_delta(item, -quantity, now)
        lot_writes, lot_allocations, remaining_untracked = prepare_lot_depletion(
            restaurant_id, item, quantity,
        )
        if item.get("lot_tracking_enabled"):
            updated["untracked_stock_quantity"] = remaining_untracked
        movement_id = f"{waste_id}_{waste.ingredient_id}"
        movement = {
            "id": movement_id,
            "item_id": waste.ingredient_id,
            "ingredient_id": waste.ingredient_id,
            "movement_type": "WASTE_RECORDED",
            "quantity_delta": -quantity,
            "unit": stock_unit,
            "reference_id": waste_id,
            "timestamp": now,
            "balance_after": updated["total_current_quantity"],
            "created_by": waste.recorded_by,
        }
        if item.get("lot_tracking_enabled"):
            movement["lot_allocations"] = lot_allocations
        writes.extend([
            *lot_writes,
            (_path(restaurant_id, "inventory_items"), waste.ingredient_id, updated),
            (_path(restaurant_id, "stock_movements"), movement_id, movement),
        ])
    db.set_documents(writes)
    return WasteRecordResponseV2(**data)


def _month_start(month: str) -> date:
    return date.fromisoformat(f"{month}-01")


def _previous_month(month: str) -> str:
    start = _month_start(month)
    return f"{start.year - (start.month == 1):04d}-{12 if start.month == 1 else start.month - 1:02d}"


def _movement_date(movement: dict[str, Any]) -> date | None:
    raw = movement.get("timestamp") or movement.get("date") or movement.get("sale_date")
    if not raw:
        return None
    try:
        if isinstance(raw, datetime):
            return raw.date()
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _calculate_month(
    restaurant_id: str,
    ingredient_id: str,
    month: str,
    opening_override: float | None = None,
    item: dict[str, Any] | None = None,
    existing: Any = _UNSET,
    previous: Any = _UNSET,
    movements: list[dict[str, Any]] | None = None,
) -> MonthlyStockBalance:
    if existing is _UNSET:
        existing = db.get_document(_path(restaurant_id, "monthly_stock_balances"), f"{ingredient_id}_{month}")
    if previous is _UNSET:
        previous = db.get_document(
            _path(restaurant_id, "monthly_stock_balances"),
            f"{ingredient_id}_{_previous_month(month)}",
        )
    if opening_override is not None:
        opening = opening_override
        provisional_opening = False
    elif previous:
        if previous.get("physical_count_verified") and previous.get("actual_closing_stock") is not None:
            opening = float(previous["actual_closing_stock"])
            provisional_opening = False
        else:
            opening = float(previous.get("calculated_closing_stock", 0))
            provisional_opening = True
    else:
        opening = float(existing.get("opening_stock", 0)) if existing else 0.0
        provisional_opening = True

    totals = {
        "total_purchased_stock": 0.0,
        "total_recipe_consumption": 0.0,
        "total_staff_consumption": 0.0,
        "total_wasted_stock": 0.0,
        "other_stock_inflows": 0.0,
        "other_stock_outflows": 0.0,
    }
    start = _month_start(month)
    end = date(start.year, start.month, monthrange(start.year, start.month)[1])
    item = item or _get_item(restaurant_id, ingredient_id)
    stock_unit = str(item.get("input_unit") or item.get("base_unit") or "kg")
    if movements is None:
        next_month = date(end.year + (end.month == 12), 1 if end.month == 12 else end.month + 1, 1)
        movements = db.query_collection(
            _path(restaurant_id, "stock_movements"),
            [
                ("timestamp", ">=", f"{start.isoformat()}T00:00:00+00:00"),
                ("timestamp", "<", f"{next_month.isoformat()}T00:00:00+00:00"),
            ],
        )
    for movement in movements:
        movement_item_id = movement.get("ingredient_id") or movement.get("item_id")
        movement_date = _movement_date(movement)
        if movement_item_id != ingredient_id or movement_date is None or not start <= movement_date <= end:
            continue
        quantity = convert_quantity(
            abs(float(movement.get("quantity_delta", 0))),
            str(movement.get("unit", stock_unit)),
            stock_unit,
        )
        movement_type = str(movement.get("movement_type", "")).upper()
        if movement_type == "RECEIPT_PURCHASE":
            totals["total_purchased_stock"] += quantity
        elif movement_type == "USAGE_SALES_RECIPE":
            totals["total_recipe_consumption"] += quantity
        elif movement_type == "USAGE_STAFF_MEAL":
            totals["total_staff_consumption"] += quantity
        elif movement_type == "WASTE_RECORDED":
            totals["total_wasted_stock"] += quantity
        elif float(movement.get("quantity_delta", 0)) >= 0:
            totals["other_stock_inflows"] += quantity
        else:
            totals["other_stock_outflows"] += quantity

    calculated = (
        opening + totals["total_purchased_stock"] + totals["other_stock_inflows"]
        - totals["total_recipe_consumption"] - totals["total_staff_consumption"]
        - totals["total_wasted_stock"] - totals["other_stock_outflows"]
    )
    actual = existing.get("actual_closing_stock") if existing else None
    verified = bool(existing and existing.get("physical_count_verified") and actual is not None)
    return MonthlyStockBalance(
        ingredient_id=ingredient_id,
        month=month,
        opening_stock=opening,
        **totals,
        calculated_closing_stock=calculated,
        actual_closing_stock=actual,
        stock_variance=(float(actual) - calculated) if actual is not None else None,
        physical_count_verified=verified,
        provisional=provisional_opening or not verified,
    )


def get_monthly_balances(restaurant_id: str, month: str) -> list[MonthlyStockBalance]:
    inventory = db.get_collection(_path(restaurant_id, "inventory_items"))
    balance_path = _path(restaurant_id, "monthly_stock_balances")
    current_balances = {
        str(balance.get("ingredient_id")): balance
        for balance in db.query_collection(balance_path, [("month", "==", month)])
    }
    previous_balances = {
        str(balance.get("ingredient_id")): balance
        for balance in db.query_collection(balance_path, [("month", "==", _previous_month(month))])
    }
    start = _month_start(month)
    end = date(start.year, start.month, monthrange(start.year, start.month)[1])
    next_month = date(end.year + (end.month == 12), 1 if end.month == 12 else end.month + 1, 1)
    movements = db.query_collection(
        _path(restaurant_id, "stock_movements"),
        [
            ("timestamp", ">=", f"{start.isoformat()}T00:00:00+00:00"),
            ("timestamp", "<", f"{next_month.isoformat()}T00:00:00+00:00"),
        ],
    )
    balances = []
    for item in inventory:
        ingredient_id = str(item.get("ingredient_id") or item["id"])
        balance = _calculate_month(
            restaurant_id,
            ingredient_id,
            month,
            item=item,
            existing=current_balances.get(ingredient_id),
            previous=previous_balances.get(ingredient_id),
            movements=movements,
        )
        balances.append(balance)
    return balances


def record_stocktake(
    restaurant_id: str,
    ingredient_id: str,
    month: str,
    stocktake: PhysicalStocktake,
) -> MonthlyStockBalance:
    current = _calculate_month(restaurant_id, ingredient_id, month)
    data = current.model_dump(mode="json")
    data.update({
        "id": f"{ingredient_id}_{month}",
        "restaurant_id": restaurant_id,
        "actual_closing_stock": stocktake.actual_closing_stock,
        "stock_variance": stocktake.actual_closing_stock - current.calculated_closing_stock,
        "physical_count_verified": True,
        "provisional": False,
        "verified_by": stocktake.verified_by,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    })
    db.add_document(_path(restaurant_id, "monthly_stock_balances"), data["id"], data)
    return MonthlyStockBalance(**data)


def get_theoretical_consumption(
    restaurant_id: str,
    month: str,
) -> list[TheoreticalConsumption]:
    start = _month_start(month)
    end = date(start.year, start.month, monthrange(start.year, start.month)[1])
    totals: dict[str, tuple[dict[str, Any], float, str]] = {}
    sales = db.query_collection(
        _path(restaurant_id, "daily_sales"),
        [
            ("sale_date", ">=", start.isoformat()),
            ("sale_date", "<=", end.isoformat()),
        ],
    )
    for sale in sales:
        portions = float(sale.get("net_quantity_sold", 0))
        for ingredient_id, (item, quantity, unit) in _ingredient_requirements(
            restaurant_id, sale["recipe_id"], portions
        ).items():
            old = totals.get(ingredient_id)
            totals[ingredient_id] = (item, quantity + (old[1] if old else 0), unit)
    return [
        TheoreticalConsumption(
            ingredient_id=ingredient_id,
            item_name=str(item.get("item_name", ingredient_id)),
            month=month,
            unit=unit,
            theoretical_raw_consumption=quantity,
        )
        for ingredient_id, (item, quantity, unit) in totals.items()
    ]
