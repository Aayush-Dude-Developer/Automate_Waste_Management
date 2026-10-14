"""Seed isolated, deterministic purchase-recommendation sample data."""

import argparse
from datetime import date, datetime, timedelta, timezone

from backend.config import settings
from backend.repositories.database import db

SEED_VERSION = "purchase_recommendations_demo_v1"
RESTAURANT_ID = "taiken_kharadi"

SUPPLIERS = [
    {
        "id": "demo_supplier_pantry",
        "supplier_id": "demo_supplier_pantry",
        "name": "Synthetic SG Pantry Supplier",
        "lead_time_days": 2,
        "demo_dataset": SEED_VERSION,
        "synthetic_demo": True,
    },
    {
        "id": "demo_supplier_produce",
        "supplier_id": "demo_supplier_produce",
        "name": "Synthetic SG Produce Supplier",
        "lead_time_days": 1,
        "demo_dataset": SEED_VERSION,
        "synthetic_demo": True,
    },
    {
        "id": "demo_supplier_protein",
        "supplier_id": "demo_supplier_protein",
        "name": "Synthetic SG Protein Supplier",
        "lead_time_days": 3,
        "demo_dataset": SEED_VERSION,
        "synthetic_demo": True,
    },
]

INGREDIENTS = [
    {
        "id": "demo_sg_jasmine_rice", "item_name": "DEMO Jasmine Rice", "category": "Dry Pantry",
        "supplier_id": "demo_supplier_pantry", "unit": "kg", "unit_cost": 4.20, "lead_time_days": 2,
        "reorder_threshold": 5.0, "safety_stock": 3.0, "minimum_order_quantity": 10.0, "pack_size": 5.0,
        "stock": 8.0, "lots": [(4.0, 120), (4.0, 240)],
        "yield_stages": [{"stage_name": "Cooked", "input_stage": "raw", "output_stage": "cooked", "input_unit": "kg", "output_unit": "kg", "yield_percentage": 100.0}],
    },
    {
        "id": "demo_sg_chicken", "item_name": "DEMO Chicken Thigh", "category": "Protein",
        "supplier_id": "demo_supplier_protein", "unit": "kg", "unit_cost": 8.50, "lead_time_days": 3,
        "reorder_threshold": 5.0, "safety_stock": 3.0, "minimum_order_quantity": 5.0, "pack_size": 2.0,
        "stock": 9.0, "lots": [(4.0, 2), (5.0, 8)],
        "yield_stages": [{"stage_name": "Trimmed", "input_stage": "raw", "output_stage": "cleaned", "input_unit": "kg", "output_unit": "kg", "yield_percentage": -15.0}],
    },
    {
        "id": "demo_sg_tomato", "item_name": "DEMO Tomato", "category": "Produce",
        "supplier_id": "demo_supplier_produce", "unit": "kg", "unit_cost": 2.80, "lead_time_days": 1,
        "reorder_threshold": 3.0, "safety_stock": 2.0, "minimum_order_quantity": 4.0, "pack_size": 2.0,
        "stock": 4.0, "lots": [(1.5, -2), (2.5, 3)],
        "yield_stages": [{"stage_name": "Cleaned", "input_stage": "raw", "output_stage": "cleaned", "input_unit": "kg", "output_unit": "kg", "yield_percentage": -20.0}],
    },
    {
        "id": "demo_sg_pak_choi", "item_name": "DEMO Pak Choi", "category": "Produce",
        "supplier_id": "demo_supplier_produce", "unit": "kg", "unit_cost": 3.10, "lead_time_days": 1,
        "reorder_threshold": 3.0, "safety_stock": 2.0, "minimum_order_quantity": 3.0, "pack_size": 1.0,
        "stock": 6.0, "lots": [(3.0, 1), (3.0, 5)],
        "yield_stages": [{"stage_name": "Trimmed", "input_stage": "raw", "output_stage": "cleaned", "input_unit": "kg", "output_unit": "kg", "yield_percentage": -10.0}],
    },
    {
        "id": "demo_sg_noodles", "item_name": "DEMO Wheat Noodles", "category": "Dry Pantry",
        "supplier_id": "demo_supplier_pantry", "unit": "kg", "unit_cost": 3.40, "lead_time_days": 2,
        "reorder_threshold": 5.0, "safety_stock": 3.0, "minimum_order_quantity": 6.0, "pack_size": 3.0,
        "stock": 9.0, "lots": [(4.0, 90), (5.0, 180)],
        "yield_stages": [{"stage_name": "Cooked", "input_stage": "raw", "output_stage": "cooked", "input_unit": "kg", "output_unit": "kg", "yield_percentage": 150.0}],
    },
    {
        "id": "demo_sg_soy_sauce", "item_name": "DEMO Light Soy Sauce", "category": "Sauces",
        "supplier_id": "demo_supplier_pantry", "unit": "ltr", "unit_cost": 3.20, "lead_time_days": 2,
        "reorder_threshold": 2.0, "safety_stock": 1.0, "minimum_order_quantity": 3.0, "pack_size": 1.0,
        "stock": 4.0, "lots": [(2.0, 180), (2.0, 365)], "yield_stages": [],
    },
]

RECIPES = [
    {
        "recipe_id": "demo_recipe_rice_bowl", "recipe_name": "DEMO Chicken Rice Bowl",
        "recipe_version": "1", "serving_size": 1, "serving_unit": "portion",
        "menu_category": "Main Course", "selling_price": 12.50, "is_active": True,
        "weekday_portions": [42, 44, 46, 50, 58, 72, 68],
        "ingredients": [
            ("demo_sg_jasmine_rice", 2.4, "kg", "cooked"),
            ("demo_sg_chicken", 1.8, "kg", "cleaned"),
            ("demo_sg_soy_sauce", 0.25, "ltr", "raw"),
        ],
    },
    {
        "recipe_id": "demo_recipe_tomato_curry", "recipe_name": "DEMO Tomato Chicken Curry Rice",
        "recipe_version": "1", "serving_size": 1, "serving_unit": "portion",
        "menu_category": "Main Course", "selling_price": 14.00, "is_active": True,
        "weekday_portions": [28, 30, 32, 34, 42, 54, 50],
        "ingredients": [
            ("demo_sg_jasmine_rice", 2.0, "kg", "cooked"),
            ("demo_sg_chicken", 1.6, "kg", "cleaned"),
            ("demo_sg_tomato", 0.6, "kg", "cleaned"),
            ("demo_sg_soy_sauce", 0.15, "ltr", "raw"),
        ],
    },
    {
        "recipe_id": "demo_recipe_wok_noodles", "recipe_name": "DEMO Wok Noodles",
        "recipe_version": "1", "serving_size": 1, "serving_unit": "portion",
        "menu_category": "Main Course", "selling_price": 11.00, "is_active": True,
        "weekday_portions": [24, 26, 28, 30, 40, 52, 48],
        "ingredients": [
            ("demo_sg_noodles", 2.0, "kg", "cooked"),
            ("demo_sg_pak_choi", 0.7, "kg", "cleaned"),
            ("demo_sg_soy_sauce", 0.2, "ltr", "raw"),
        ],
    },
]


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
            "brand": "Synthetic demo data",
            "storage_location": "Demo Store",
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
            "shelf_life_days": 365,
            "current_quantity_in_store": store,
            "current_quantity_in_use": in_use,
            "stock_in_store": store,
            "stock_in_use": in_use,
            "total_current_quantity": ingredient["stock"],
            "untracked_stock_quantity": 0,
            "lot_tracking_enabled": True,
            "status": "in_stock",
            "synthetic_demo": True,
            "demo_dataset": SEED_VERSION,
            "updated_at": now,
        }
        docs.append((_tenant_path("inventory_items"), ingredient["id"], item))

        balance_after = 0.0
        for batch_index, (quantity, days_until_expiry) in enumerate(ingredient["lots"], 1):
            batch_id = f"demo_batch_{ingredient['id']}_{batch_index}"
            purchase_id = f"demo_purchase_{ingredient['id']}_{batch_index}"
            line_id = f"demo_line_{ingredient['id']}_{batch_index}"
            received_date = as_of - timedelta(days=2 + batch_index)
            expiry_date = as_of + timedelta(days=days_until_expiry)
            invoice = {
                "id": purchase_id,
                "purchase_id": purchase_id,
                "restaurant_id": RESTAURANT_ID,
                "supplier_id": ingredient["supplier_id"],
                "invoice_number": f"DEMO-{ingredient['id']}-{batch_index}",
                "invoice_date": received_date.isoformat(),
                "received_date": received_date.isoformat(),
                "total_amount": round(quantity * ingredient["unit_cost"], 2),
                "bill_document_url": None,
                "verification_status": "verified",
                "verified_at": now,
                "synthetic_demo": True,
                "demo_dataset": SEED_VERSION,
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
                "synthetic_demo": True,
                "demo_dataset": SEED_VERSION,
            }
            docs.extend([
                (_tenant_path("purchase_invoices"), purchase_id, invoice),
                (_tenant_path("purchase_lines"), line_id, line),
            ])
            balance_after += quantity
            movement_id = f"demo_receipt_{ingredient['id']}_{batch_index}"
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
                "created_by": "synthetic_demo_seed",
                "synthetic_demo": True,
                "demo_dataset": SEED_VERSION,
            }))

    for recipe in RECIPES:
        recipe_doc = {key: value for key, value in recipe.items() if key not in {"weekday_portions", "ingredients"}}
        recipe_doc.update({
            "id": recipe["recipe_id"],
            "restaurant_id": RESTAURANT_ID,
            "synthetic_demo": True,
            "demo_dataset": SEED_VERSION,
        })
        docs.append((_tenant_path("recipes"), recipe["recipe_id"], recipe_doc))
        for row_index, (ingredient_id, batch_quantity, unit, stage) in enumerate(recipe["ingredients"], 1):
            row_id = f"demo_ri_{recipe['recipe_id']}_{row_index}"
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
                "synthetic_demo": True,
                "demo_dataset": SEED_VERSION,
            }))

        for days_ago in range(56, 0, -1):
            sale_day = as_of - timedelta(days=days_ago)
            weekday_base = recipe["weekday_portions"][sale_day.weekday()]
            trend_multiplier = 0.90 if days_ago > 28 else 1.10
            net_portions = round(weekday_base * trend_multiplier)
            cancelled = (sale_day.day + sale_day.weekday()) % 3
            sold = net_portions + cancelled
            sale_id = f"demo_sale_{recipe['recipe_id']}_{sale_day.strftime('%Y%m%d')}"
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
                "sales_source": "synthetic_demo",
                "source_reference": f"demo:{sale_day.isoformat()}:{recipe['recipe_id']}",
                "synthetic_demo": True,
                "demo_dataset": SEED_VERSION,
            }))

    metadata_id = SEED_VERSION
    docs.append((_tenant_path("seed_metadata"), metadata_id, {
        "id": metadata_id,
        "dataset": SEED_VERSION,
        "synthetic_demo": True,
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
    parser.add_argument("--apply", action="store_true", help="Write the synthetic dataset to Firestore.")
    args = parser.parse_args()
    if args.restaurant_id != RESTAURANT_ID:
        parser.error(f"This sample dataset is scoped to {RESTAURANT_ID}.")

    as_of = (datetime.now(timezone.utc) + timedelta(hours=8)).date()
    documents = build_documents(as_of)
    if not args.apply:
        print(f"Dry run only: {len(documents)} deterministic synthetic documents prepared for {RESTAURANT_ID}.")
        print("Pass --apply to write; existing non-demo document IDs are not touched.")
        return
    if settings.DATABASE_BACKEND != "firestore":
        parser.error("--apply requires DATABASE_BACKEND=firestore; refusing to write to local JSON.")
    if not settings.GOOGLE_CLOUD_PROJECT:
        parser.error("--apply requires GOOGLE_CLOUD_PROJECT to be configured.")

    marker_path = _tenant_path("seed_metadata")
    marker = db.get_document(marker_path, SEED_VERSION)
    if marker:
        if marker.get("history_through") == (as_of - timedelta(days=1)).isoformat():
            print("Synthetic purchase recommendation dataset is already current; no writes performed.")
            return
        print("Updating only deterministic demo document IDs; operational IDs remain untouched.")
    db.set_documents(documents)
    print(f"Wrote {len(documents)} synthetic demo documents to Firestore project {settings.GOOGLE_CLOUD_PROJECT}, tenant {RESTAURANT_ID}.")
    print("All demo records are marked synthetic_demo=true and demo_dataset=purchase_recommendations_demo_v1.")


if __name__ == "__main__":
    main()
