"""Seed isolated, deterministic purchase-recommendation records."""

import argparse
from datetime import date, datetime, timedelta, timezone

from backend.config import settings
from backend.repositories.database import db

SEED_VERSION = "purchase_recommendations_v2"
RESTAURANT_ID = "taiken_kharadi"

SUPPLIERS = [
    {
        "id": "supplier_pantry",
        "supplier_id": "supplier_pantry",
        "name": "Straits Garden Pantry Supplier",
        "lead_time_days": 2,
        "dataset_version": SEED_VERSION,
        "system_generated_data": True,
    },
    {
        "id": "supplier_produce",
        "supplier_id": "supplier_produce",
        "name": "Straits Garden Produce Supplier",
        "lead_time_days": 1,
        "dataset_version": SEED_VERSION,
        "system_generated_data": True,
    },
    {
        "id": "supplier_protein",
        "supplier_id": "supplier_protein",
        "name": "Straits Garden Protein Supplier",
        "lead_time_days": 3,
        "dataset_version": SEED_VERSION,
        "system_generated_data": True,
    },
]

INGREDIENTS = [
    {
        "id": "inv_jasmine_rice_bulk", "item_name": "Jasmine Rice (Bulk)", "category": "Dry Pantry",
        "supplier_id": "supplier_pantry", "unit": "kg", "unit_cost": 4.20, "lead_time_days": 2,
        "reorder_threshold": 70.0, "safety_stock": 40.0, "minimum_order_quantity": 10.0, "pack_size": 5.0,
        "stock": 200.0, "lots": [(140.0, 120), (60.0, 240)], "shelf_life_days": 365,
        "yield_stages": [{"stage_name": "Cooked", "input_stage": "raw", "output_stage": "cooked", "input_unit": "kg", "output_unit": "kg", "yield_percentage": 100.0}],
    },
    {
        "id": "inv_chicken", "item_name": "Chicken Thigh", "category": "Protein",
        "supplier_id": "supplier_protein", "unit": "kg", "unit_cost": 8.50, "lead_time_days": 3,
        "reorder_threshold": 35.0, "safety_stock": 20.0, "minimum_order_quantity": 20.0, "pack_size": 5.0,
        "stock": 75.0, "lots": [(50.0, 2), (25.0, 15)], "shelf_life_days": 7,
        "yield_stages": [{"stage_name": "Trimmed", "input_stage": "raw", "output_stage": "cleaned", "input_unit": "kg", "output_unit": "kg", "yield_percentage": -15.0}],
    },
    {
        "id": "inv_tomato", "item_name": "Tomato", "category": "Produce",
        "supplier_id": "supplier_produce", "unit": "kg", "unit_cost": 2.80, "lead_time_days": 1,
        "reorder_threshold": 8.0, "safety_stock": 4.0, "minimum_order_quantity": 4.0, "pack_size": 2.0,
        "stock": 16.0, "lots": [(8.0, 2), (8.0, 7)], "shelf_life_days": 5,
        "yield_stages": [{"stage_name": "Cleaned", "input_stage": "raw", "output_stage": "cleaned", "input_unit": "kg", "output_unit": "kg", "yield_percentage": -20.0}],
    },
    {
        "id": "inv_pak_choi_baby", "item_name": "Baby Pak Choi", "category": "Produce",
        "supplier_id": "supplier_produce", "unit": "kg", "unit_cost": 3.10, "lead_time_days": 1,
        "reorder_threshold": 5.0, "safety_stock": 3.0, "minimum_order_quantity": 3.0, "pack_size": 1.0,
        "stock": 8.0, "lots": [(7.0, 2), (1.0, 6)], "shelf_life_days": 5,
        "yield_stages": [{"stage_name": "Trimmed", "input_stage": "raw", "output_stage": "cleaned", "input_unit": "kg", "output_unit": "kg", "yield_percentage": -10.0}],
    },
    {
        "id": "inv_noodles", "item_name": "Wheat Noodles", "category": "Dry Pantry",
        "supplier_id": "supplier_pantry", "unit": "kg", "unit_cost": 3.40, "lead_time_days": 2,
        "reorder_threshold": 20.0, "safety_stock": 10.0, "minimum_order_quantity": 6.0, "pack_size": 3.0,
        "stock": 40.0, "lots": [(20.0, 90), (20.0, 180)], "shelf_life_days": 180,
        "yield_stages": [{"stage_name": "Cooked", "input_stage": "raw", "output_stage": "cooked", "input_unit": "kg", "output_unit": "kg", "yield_percentage": 150.0}],
    },
    {
        "id": "inv_soy_sauce", "item_name": "Light Soy Sauce", "category": "Sauces",
        "supplier_id": "supplier_pantry", "unit": "ltr", "unit_cost": 3.20, "lead_time_days": 2,
        "reorder_threshold": 10.0, "safety_stock": 5.0, "minimum_order_quantity": 4.0, "pack_size": 2.0,
        "stock": 18.0, "lots": [(8.0, 180), (10.0, 365)], "shelf_life_days": 365,
        "yield_stages": [],
    },
]

RECIPES = [
    {
        "recipe_id": "recipe_rice_bowl", "recipe_name": "Chicken Rice Bowl",
        "recipe_version": "1", "serving_size": 1, "serving_unit": "portion",
        "menu_category": "Main Course", "selling_price": 12.50, "is_active": True,
        "weekday_portions": [42, 44, 46, 50, 58, 72, 68],
        "ingredients": [
            ("inv_jasmine_rice_bulk", 2.4, "kg", "cooked"),
            ("inv_chicken", 1.8, "kg", "cleaned"),
            ("inv_soy_sauce", 0.25, "ltr", "raw"),
        ],
    },
    {
        "recipe_id": "recipe_tomato_curry", "recipe_name": "Tomato Chicken Curry Rice",
        "recipe_version": "1", "serving_size": 1, "serving_unit": "portion",
        "menu_category": "Main Course", "selling_price": 14.00, "is_active": True,
        "weekday_portions": [28, 30, 32, 34, 42, 54, 50],
        "ingredients": [
            ("inv_jasmine_rice_bulk", 2.0, "kg", "cooked"),
            ("inv_chicken", 1.6, "kg", "cleaned"),
            ("inv_tomato", 0.6, "kg", "cleaned"),
            ("inv_soy_sauce", 0.15, "ltr", "raw"),
        ],
    },
    {
        "recipe_id": "recipe_wok_noodles", "recipe_name": "Wok Noodles",
        "recipe_version": "1", "serving_size": 1, "serving_unit": "portion",
        "menu_category": "Main Course", "selling_price": 11.00, "is_active": True,
        "weekday_portions": [24, 26, 28, 30, 40, 52, 48],
        "ingredients": [
            ("inv_noodles", 2.0, "kg", "cooked"),
            ("inv_pak_choi_baby", 0.7, "kg", "cleaned"),
            ("inv_soy_sauce", 0.2, "ltr", "raw"),
        ],
    },
]

RECORD_SLUGS = {
    "inv_jasmine_rice_bulk": "jasmine_rice",
    "inv_chicken": "chicken",
    "inv_tomato": "tomato",
    "inv_pak_choi_baby": "pak_choi",
    "inv_noodles": "noodles",
    "inv_soy_sauce": "soy_sauce",
}


def _tenant_path(collection: str) -> str:
    return f"restaurants/{RESTAURANT_ID}/{collection}"


def build_documents(as_of: date) -> list[tuple[str, str, dict]]:
    now = datetime.now(timezone.utc).isoformat()
    docs: list[tuple[str, str, dict]] = []

    for supplier in SUPPLIERS:
        docs.append((_tenant_path("suppliers"), supplier["id"], supplier))

    for ingredient in INGREDIENTS:
        store = round(ingredient["stock"] * 0.8, 4)
        in_use = round(ingredient["stock"] - store, 4)
        unit = ingredient["unit"]
        item = {
            "id": ingredient["id"],
            "ingredient_id": ingredient["id"],
            "restaurant_id": RESTAURANT_ID,
            "item_name": ingredient["item_name"],
            "category": ingredient["category"],
            "brand": None,
            "storage_location": (
                "Walk-in Chiller" if ingredient["category"] == "Protein"
                else "Produce Chiller" if ingredient["category"] == "Produce"
                else "Dry Store"
            ),
            "base_unit": unit,
            "input_unit": unit,
            "output_unit": unit,
            "unit_cost": ingredient["unit_cost"],
            "unit_cost_inr": ingredient["unit_cost"],
            "yield_percentage": ingredient["yield_stages"][0]["yield_percentage"] if ingredient["yield_stages"] else 0,
            "yield_type": "negative" if ingredient["yield_stages"] and ingredient["yield_stages"][0]["yield_percentage"] < 0 else "positive" if ingredient["yield_stages"] and ingredient["yield_stages"][0]["yield_percentage"] > 0 else "no change",
            "yield_stage": ingredient["yield_stages"][-1]["output_stage"] if ingredient["yield_stages"] else None,
            "yield_stages": ingredient["yield_stages"],
            "reorder_threshold": ingredient["reorder_threshold"],
            "safety_stock": ingredient["safety_stock"],
            "supplier_id": ingredient["supplier_id"],
            "lead_time_days": ingredient["lead_time_days"],
            "minimum_order_quantity": ingredient["minimum_order_quantity"],
            "pack_size": ingredient["pack_size"],
            "shelf_life_days": ingredient["shelf_life_days"],
            "current_quantity_in_store": store,
            "current_quantity_in_use": in_use,
            "stock_in_store": store,
            "stock_in_use": in_use,
            "total_current_quantity": ingredient["stock"],
            "untracked_stock_quantity": 0,
            "lot_tracking_enabled": True,
            "status": "in_stock",
            "system_generated_data": True,
            "dataset_version": SEED_VERSION,
            "updated_at": now,
        }
        docs.append((_tenant_path("inventory_items"), ingredient["id"], item))

        balance_after = 0.0
        slug = RECORD_SLUGS[ingredient["id"]]
        for batch_index, (quantity, days_until_expiry) in enumerate(ingredient["lots"], 1):
            batch_id = f"batch_{slug}_{batch_index}"
            purchase_id = f"purchase_{slug}_{batch_index}"
            line_id = f"line_{slug}_{batch_index}"
            received_date = as_of - timedelta(days=2 + batch_index)
            expiry_date = as_of + timedelta(days=days_until_expiry)
            invoice = {
                "id": purchase_id,
                "purchase_id": purchase_id,
                "restaurant_id": RESTAURANT_ID,
                "supplier_id": ingredient["supplier_id"],
                "invoice_number": f"INV-{as_of:%Y%m%d}-{slug.replace('_', '-').upper()}-{batch_index:02d}",
                "invoice_date": received_date.isoformat(),
                "received_date": received_date.isoformat(),
                "total_amount": round(quantity * ingredient["unit_cost"], 2),
                "bill_document_url": None,
                "verification_status": "verified",
                "verified_at": now,
                "system_generated_data": True,
                "dataset_version": SEED_VERSION,
            }
            line = {
                "id": line_id,
                "purchase_line_id": line_id,
                "purchase_id": purchase_id,
                "restaurant_id": RESTAURANT_ID,
                "ingredient_id": ingredient["id"],
                "quantity_purchased": quantity,
                "purchase_unit": unit,
                "unit_price": ingredient["unit_cost"],
                "quantity_received": quantity,
                "ingredient_quantity_received": quantity,
                "usable_quantity": quantity,
                "usable_unit": unit,
                "remaining_usable_quantity": quantity,
                "expiry_date": expiry_date.isoformat(),
                "batch_number": batch_id,
                "system_generated_data": True,
                "dataset_version": SEED_VERSION,
            }
            docs.extend([
                (_tenant_path("purchase_invoices"), purchase_id, invoice),
                (_tenant_path("purchase_lines"), line_id, line),
            ])
            balance_after += quantity
            movement_id = f"movement_{slug}_{batch_index}"
            docs.append((_tenant_path("stock_movements"), movement_id, {
                "id": movement_id,
                "item_id": ingredient["id"],
                "ingredient_id": ingredient["id"],
                "movement_type": "RECEIPT_PURCHASE",
                "quantity_delta": quantity,
                "unit": unit,
                "reference_id": line_id,
                "purchase_id": purchase_id,
                "timestamp": received_date.isoformat() + "T12:00:00+08:00",
                "balance_after": balance_after,
                "created_by": "system_generated",
                "system_generated_data": True,
                "dataset_version": SEED_VERSION,
            }))

    for recipe in RECIPES:
        recipe_doc = {key: value for key, value in recipe.items() if key not in {"weekday_portions", "ingredients"}}
        recipe_doc.update({
            "id": recipe["recipe_id"],
            "restaurant_id": RESTAURANT_ID,
            "system_generated_data": True,
            "dataset_version": SEED_VERSION,
        })
        docs.append((_tenant_path("recipes"), recipe["recipe_id"], recipe_doc))
        recipe_slug = recipe["recipe_id"].removeprefix("recipe_")
        for row_index, (ingredient_id, batch_quantity, unit, stage) in enumerate(recipe["ingredients"], 1):
            row_id = f"recipe_component_{recipe_slug}_{row_index}"
            docs.append((_tenant_path("recipe_ingredients"), row_id, {
                "id": row_id,
                "restaurant_id": RESTAURANT_ID,
                "recipe_id": recipe["recipe_id"],
                "ingredient_id": ingredient_id,
                "required_quantity": batch_quantity,
                "required_unit": unit,
                "required_stage": stage,
                "yield_stage_reference": None,
                "servings_per_batch": 10,
                "system_generated_data": True,
                "dataset_version": SEED_VERSION,
            }))

        for days_ago in range(56, 0, -1):
            sale_day = as_of - timedelta(days=days_ago)
            weekday_base = recipe["weekday_portions"][sale_day.weekday()]
            trend_multiplier = 0.90 if days_ago > 28 else 1.10
            net_portions = round(weekday_base * trend_multiplier)
            cancelled = (sale_day.day + sale_day.weekday()) % 3
            sold = net_portions + cancelled
            sale_id = f"sale_{recipe_slug}_{sale_day.strftime('%Y%m%d')}"
            docs.append((_tenant_path("daily_sales"), sale_id, {
                "id": sale_id,
                "sale_record_id": sale_id,
                "restaurant_id": RESTAURANT_ID,
                "sale_date": sale_day.isoformat(),
                "recipe_id": recipe["recipe_id"],
                "quantity_sold": sold,
                "quantity_cancelled": cancelled,
                "net_quantity_sold": net_portions,
                "quantity_prepared": None,
                "net_sales_amount": round(net_portions * recipe["selling_price"], 2),
                "sales_source": "system_generated",
                "source_reference": f"daily_sales:{sale_day.isoformat()}:{recipe['recipe_id']}",
                "system_generated_data": True,
                "dataset_version": SEED_VERSION,
            }))

    metadata_id = SEED_VERSION
    docs.append((_tenant_path("seed_metadata"), metadata_id, {
        "id": metadata_id,
        "dataset": SEED_VERSION,
        "system_generated_data": True,
        "history_start": (as_of - timedelta(days=56)).isoformat(),
        "history_through": (as_of - timedelta(days=1)).isoformat(),
        "ingredient_count": len(INGREDIENTS),
        "supplier_count": len(SUPPLIERS),
        "recipe_count": len(RECIPES),
        "sales_record_count": len(RECIPES) * 56,
        "generated_at": now,
    }))
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restaurant-id", default=RESTAURANT_ID)
    parser.add_argument("--apply", action="store_true", help="Write generated records to Firestore.")
    args = parser.parse_args()
    if args.restaurant_id != RESTAURANT_ID:
        parser.error(f"This generated dataset is scoped to {RESTAURANT_ID}.")

    as_of = (datetime.now(timezone.utc) + timedelta(hours=8)).date()
    documents = build_documents(as_of)
    if not args.apply:
        print(f"Dry run only: {len(documents)} deterministic documents prepared for {RESTAURANT_ID}.")
        print("Pass --apply to write; existing operational document IDs are not touched.")
        return
    if settings.DATABASE_BACKEND != "firestore":
        parser.error("--apply requires DATABASE_BACKEND=firestore; refusing to write to local JSON.")
    if not settings.GOOGLE_CLOUD_PROJECT:
        parser.error("--apply requires GOOGLE_CLOUD_PROJECT to be configured.")

    marker_path = _tenant_path("seed_metadata")
    marker = db.get_document(marker_path, SEED_VERSION)
    if marker:
        if marker.get("history_through") == (as_of - timedelta(days=1)).isoformat():
            print("Purchase recommendation records are already current; no writes performed.")
            return
        print("Updating only deterministic generated document IDs; operational IDs remain untouched.")
    db.set_documents(documents)
    print(f"Wrote {len(documents)} purchase recommendation records to Firestore project {settings.GOOGLE_CLOUD_PROJECT}, tenant {RESTAURANT_ID}.")


if __name__ == "__main__":
    main()
