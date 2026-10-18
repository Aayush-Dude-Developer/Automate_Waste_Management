import argparse
from datetime import datetime, timezone
from typing import Any

from ..repositories.database import db


ILLUSTRATIVE_YIELD_DEFAULTS = {
    "Chicken Leg": (-15.0, "trimmed"),
    "Chinese Noodles": (150.0, "cooked"),
    "Jasmine Rice": (100.0, "cooked"),
    "Pak Choi": (-10.0, "trimmed"),
    "Dark Soy Sauce": (0.0, "no change"),
    "Firm Tofu": (-5.0, "drained"),
    "Tiger Prawns": (-35.0, "peeled"),
    "Coconut Milk": (0.0, "no change"),
    "Thai Green Curry Paste": (0.0, "no change"),
    "Refined Sunflower Oil": (0.0, "no change"),
    "Farm Fresh Eggs": (0.0, "no change"),
    "Banana Yellow": (-35.0, "peeled"),
}


def get_yield_defaults(item: dict[str, Any]) -> tuple[float, str]:
    default_percentage, default_stage = ILLUSTRATIVE_YIELD_DEFAULTS.get(
        item.get("item_name"), (0.0, "no change")
    )
    yield_percentage = float(item.get("yield_percentage", default_percentage) or 0)
    if not item.get("yield_stages") and yield_percentage == 0 and default_percentage != 0:
        yield_percentage = default_percentage
    yield_stage = item.get("yield_stage") or (
        default_stage if yield_percentage == default_percentage else "prepared"
    )
    return yield_percentage, yield_stage


def migrate_inventory_documents(
    restaurant_id: str,
    apply: bool = False,
    restaurant_profile: dict[str, str] | None = None,
) -> int:
    collection_path = f"restaurants/{restaurant_id}/inventory_items"
    updates: list[tuple[str, str, dict[str, Any]]] = []
    for existing in db.get_collection(collection_path):
        item = dict(existing)
        ingredient_id = str(item.get("ingredient_id") or item["id"])
        base_unit = item.get("base_unit") or item.get("input_unit") or "kg"
        unit_cost = item.get("unit_cost", item.get("unit_cost_inr", 0))
        store = item.get("current_quantity_in_store", item.get("stock_in_store", 0))
        in_use = item.get("current_quantity_in_use", item.get("stock_in_use", 0))
        yield_percentage, yield_stage = get_yield_defaults(item)
        yield_stages = item.get("yield_stages") or []
        if not yield_stages and yield_percentage != 0:
            yield_stages = [{
                "stage_name": yield_stage,
                "input_stage": "raw",
                "output_stage": yield_stage,
                "input_unit": item.get("input_unit") or base_unit,
                "output_unit": item.get("output_unit") or base_unit,
                "yield_percentage": yield_percentage,
            }]
        item.update({
            "ingredient_id": ingredient_id,
            "base_unit": base_unit,
            "input_unit": item.get("input_unit") or base_unit,
            "output_unit": item.get("output_unit") or base_unit,
            "unit_cost": unit_cost,
            "unit_cost_inr": item.get("unit_cost_inr", unit_cost),
            "current_quantity_in_store": store,
            "current_quantity_in_use": in_use,
            "stock_in_store": store,
            "stock_in_use": in_use,
            "yield_percentage": yield_percentage,
            "yield_type": (
                "negative" if yield_percentage < 0 else
                "positive" if yield_percentage > 0 else
                "no change"
            ),
            "yield_stage": yield_stage,
            "yield_stages": yield_stages,
            "lead_time_days": int(item.get("lead_time_days", 0) or 0),
            "minimum_order_quantity": item.get("minimum_order_quantity"),
            "pack_size": item.get("pack_size"),
        })
        if item != existing:
            updates.append((collection_path, str(existing["id"]), item))

    if apply:
        profile = dict(restaurant_profile or {})
        profile.update({
            "id": restaurant_id,
            "name": "Straits Garden Kitchen",
            "outlet_name": "Kharadi",
            "location": "Kharadi, Pune, India",
            "address": "Kharadi, Pune, India",
            "timezone": "Asia/Kolkata",
            "currency": profile.get("currency", "INR"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        profile_path = f"restaurants/{restaurant_id}/profile"
        profile_document_id = "main"
        if (
            not db.get_document(profile_path, "main")
            and any(
                record.get("id") == restaurant_id
                for record in db.get_collection(profile_path)
            )
        ):
            profile_document_id = restaurant_id
        db.set_documents(updates + [
            (profile_path, profile_document_id, profile),
        ])
        migration_path = f"restaurants/{restaurant_id}/schema_migrations"
        migration_id = "restaurant_yield_sg_v1"
        db.add_document(migration_path, migration_id, {
            "id": migration_id,
            "version": 2,
            "name": "restaurant_yield_sg_v1",
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "documents_updated": len(updates),
        })
    return len(updates)


def main():
    parser = argparse.ArgumentParser(
        description="Add yield metadata and India restaurant identity without deleting existing fields."
    )
    parser.add_argument("--restaurant-id", required=True)
    parser.add_argument("--apply", action="store_true", help="Persist changes; default is read-only preview.")
    parser.add_argument(
        "--restaurant-profile",
        action="store_true",
        help="Also update the existing restaurant profile to Straits Garden Kitchen in Kharadi, Pune, India.",
    )
    args = parser.parse_args()
    profile_path = f"restaurants/{args.restaurant_id}/profile"
    profile = db.get_document(profile_path, "main") if args.restaurant_profile else None
    if args.restaurant_profile and profile is None:
        profile = next(
            (
                record for record in db.get_collection(profile_path)
                if record.get("id") == args.restaurant_id
            ),
            None,
        )
    collection_path = f"restaurants/{args.restaurant_id}/inventory_items"
    for item in db.get_collection(collection_path):
        percentage, stage = get_yield_defaults(item)
        print(f"Yield preview: {item.get('item_name', item.get('id'))}: {percentage:+g}% at {stage}")
    count = migrate_inventory_documents(
        args.restaurant_id,
        apply=args.apply,
        restaurant_profile=profile,
    )
    mode = "Updated" if args.apply else "Would update"
    print(f"{mode} {count} inventory documents for {args.restaurant_id}.")
    if args.restaurant_profile:
        print(f"{'Updated' if args.apply else 'Would update'} restaurant profile to Straits Garden Kitchen, Kharadi, Pune, India.")
    if not args.apply:
        print("No data was changed. Re-run with --apply to persist this additive migration.")


if __name__ == "__main__":
    main()
