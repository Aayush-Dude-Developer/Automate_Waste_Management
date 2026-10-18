"""Replace demo tokens in every table under one restaurant in Firestore."""

import argparse
import re
from typing import Any

_ID_REWRITES = (
    (re.compile(r"(?i)(?:sample|demo)_purchase_(?:sample|demo)_sg_(.+)_(\d+)$"), r"purchase_\1_\2"),
    (re.compile(r"(?i)(?:sample|demo)_line_(?:sample|demo)_sg_(.+)_(\d+)$"), r"line_\1_\2"),
    (re.compile(r"(?i)(?:sample|demo)_batch_(?:sample|demo)_sg_(.+)_(\d+)$"), r"batch_\1_\2"),
    (re.compile(r"(?i)(?:sample|demo)_receipt_(?:sample|demo)_sg_(.+)_(\d+)$"), r"movement_\1_\2"),
    (re.compile(r"(?i)(?:sample|demo)_ri_(?:sample|demo)_recipe_(.+)_(\d+)$"), r"recipe_component_\1_\2"),
    (re.compile(r"(?i)(?:sample|demo)_sale_(?:sample|demo)_recipe_(.+)_(\d{8})$"), r"sale_\1_\2"),
    (re.compile(r"(?i)(?:sample|demo)_supplier_"), "supplier_"),
    (re.compile(r"(?i)(?:sample|demo)_sg_"), "inv_"),
    (re.compile(r"(?i)(?:sample|demo)_recipe_"), "recipe_"),
)
_PLACEHOLDER_WORD = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:sample|demo|testing|dummy)(?=$|[^A-Za-z0-9])"
)


def normalize_generated_value(value: Any) -> Any:
    if isinstance(value, str):
        if value.casefold() in {"synthetic sample data", "synthetic demo data"}:
            return "Not specified"
        if value.casefold() in {"synthetic_sample", "synthetic_demo"}:
            return "system_generated"
        normalized = value.replace("purchase_recommendations_sample_v1", "purchase_recommendations_v1")
        normalized = normalized.replace("purchase_recommendations_demo_v1", "purchase_recommendations_v1")
        normalized = normalized.replace("sample:", "sales:").replace("demo:", "sales:")
        for pattern, replacement in _ID_REWRITES[:6]:
            normalized = pattern.sub(replacement, normalized)
        normalized = re.sub(
            r"(?i)(?<![A-Za-z0-9])(?:sample|demo)_sg_jasmine_rice(?=$|[^A-Za-z0-9])",
            "inv_jasmine_rice_bulk",
            normalized,
        )
        normalized = re.sub(
            r"(?i)(?<![A-Za-z0-9])(?:sample|demo)_sg_pak_choi(?=$|[^A-Za-z0-9])",
            "inv_pak_choi_baby",
            normalized,
        )
        for pattern, replacement in _ID_REWRITES[6:]:
            normalized = pattern.sub(replacement, normalized)
        normalized = re.sub(
            r"(?i)^(?:synthetic)\s+SG\s+",
            "Straits Garden ",
            normalized,
        )
        normalized = _PLACEHOLDER_WORD.sub("", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip(" _:-")
        return normalized
    if isinstance(value, dict):
        field_renames = {
            "synthetic_demo": "system_generated_data",
            "synthetic_sample": "system_generated_data",
            "synthetic_sample_data": "system_generated_data",
            "demo_dataset": "dataset_version",
            "sample_dataset": "dataset_version",
        }
        transformed = {}
        for key, item in value.items():
            new_key = (
                field_renames.get(key, normalize_generated_value(key))
                if isinstance(key, str)
                else key
            )
            new_value = normalize_generated_value(item)
            if new_key in transformed and transformed[new_key] != new_value:
                raise ValueError(f"Renaming creates a conflicting field: {new_key}")
            transformed[new_key] = new_value
        return transformed
    if isinstance(value, list):
        return [normalize_generated_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_generated_value(item) for item in value)
    return value


def normalize_generated_record(collection_id: str, record: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_generated_value(record)
    if collection_id == "inventory_items":
        locations = {
            "Dry Pantry": "Dry Store",
            "Protein": "Freezer",
            "Produce": "Chiller",
            "Sauces": "Dry Store",
        }
        if normalized.get("storage_location") in {"Store", "Sample Store", "Demo Store"}:
            normalized["storage_location"] = locations.get(
                normalized.get("category"), "Storage Area"
            )
        if normalized.get("id") == "inv_jasmine_rice_bulk":
            normalized["item_name"] = "Jasmine Rice (Bulk)"
        if normalized.get("id") == "inv_pak_choi_baby":
            normalized["item_name"] = "Baby Pak Choi"
    if collection_id == "suppliers":
        name = normalized.get("name")
        if isinstance(name, str):
            normalized["name"] = name.replace("Synthetic ", "")
    if collection_id == "purchase_invoices":
        purchase_id = normalized.get("purchase_id", "")
        match = re.fullmatch(r"purchase_(.+)_(\d+)", purchase_id)
        invoice_date = str(normalized.get("invoice_date", "")).replace("-", "")
        if match and invoice_date:
            ingredient_name, batch_number = match.groups()
            normalized["invoice_number"] = (
                f"INV-{invoice_date}-{ingredient_name.replace('_', '-').upper()}-{int(batch_number):02d}"
            )
    return normalized


def migrate_restaurant(restaurant_id: str, database: Any, apply: bool) -> int:
    restaurant_ref = database.db.collection("restaurants").document(restaurant_id)
    collection_plans = []
    changed_count = 0
    collisions = []

    collection_refs = [
        database.db.collection("global_donation_centres"),
        *restaurant_ref.collections(),
    ]
    for collection_ref in collection_refs:
        snapshots = list(collection_ref.stream())
        documents_by_id = {snapshot.id: snapshot.to_dict() or {} for snapshot in snapshots}
        plans = []
        target_ids = {}

        for snapshot in snapshots:
            new_id = normalize_generated_value(snapshot.id)
            new_data = normalize_generated_record(collection_ref.id, documents_by_id[snapshot.id])
            previous_target = target_ids.get(new_id)
            if previous_target is not None and previous_target != snapshot.id:
                previous_data = normalize_generated_record(
                    collection_ref.id, documents_by_id[previous_target]
                )
                if previous_data != new_data:
                    collisions.append(f"{collection_ref.id}/{new_id}")
            target_ids[new_id] = snapshot.id

            if new_id != snapshot.id and new_id in documents_by_id:
                existing_target = normalize_generated_record(
                    collection_ref.id, documents_by_id[new_id]
                )
                if existing_target != new_data:
                    collisions.append(f"{collection_ref.id}/{new_id}")

            if new_id != snapshot.id or new_data != documents_by_id[snapshot.id]:
                plans.append((snapshot.id, new_id, new_data))

        if plans:
            collection_plans.append((collection_ref, plans))
            changed_count += len(plans)

    if collisions:
        unique_collisions = sorted(set(collisions))
        raise ValueError(
            "Generated record IDs conflict with existing records: "
            + ", ".join(unique_collisions)
        )

    if not apply or not changed_count:
        return changed_count

    for collection_ref, plans in collection_plans:
        writes = [(old_id, new_id, data) for old_id, new_id, data in plans]
        for offset in range(0, len(writes), 450):
            batch = database.db.batch()
            for _old_id, new_id, data in writes[offset:offset + 450]:
                batch.set(collection_ref.document(new_id), data)
            batch.commit()

    for collection_ref, plans in collection_plans:
        deletes = [(old_id, new_id) for old_id, new_id, _data in plans if old_id != new_id]
        for offset in range(0, len(deletes), 450):
            batch = database.db.batch()
            for old_id, _new_id in deletes[offset:offset + 450]:
                batch.delete(collection_ref.document(old_id))
            batch.commit()

    return changed_count


def main() -> None:
    from ..config import settings
    from ..repositories.database import FirestoreDatabase

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restaurant-id", default=settings.DEFAULT_RESTAURANT_ID)
    parser.add_argument("--apply", action="store_true", help="Write the changes to Firestore.")
    args = parser.parse_args()

    if settings.DATABASE_BACKEND != "firestore":
        parser.error("This migration requires DATABASE_BACKEND=firestore.")
    if not settings.GOOGLE_CLOUD_PROJECT:
        parser.error("GOOGLE_CLOUD_PROJECT must be configured.")

    database = FirestoreDatabase()
    changed_count = migrate_restaurant(args.restaurant_id, database, args.apply)
    if args.apply:
        print(f"Updated {changed_count} record(s) in {args.restaurant_id}.")
    else:
        print(
            f"Dry run: {changed_count} generated record(s) in {args.restaurant_id} "
            "contain non-operational names or identifiers. Pass --apply to normalize them."
        )


if __name__ == "__main__":
    main()
