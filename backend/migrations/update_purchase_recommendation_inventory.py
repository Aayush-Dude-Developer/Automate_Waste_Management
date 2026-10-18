"""Remove invalid inventory rows and refresh generated stock/recommendation inputs."""

import argparse
from datetime import datetime, timedelta, timezone
from typing import Any

from ..seed_purchase_demo import (
    INGREDIENTS,
    RESTAURANT_ID,
    SEED_VERSION,
    build_documents,
)

INVALID_INVENTORY_NAMES = {"testing yoo", "testng yoo", "asda"}


def _delete_unreferenced_invalid_inventory(database: Any, restaurant_id: str) -> int:
    inventory = database.db.collection(f"restaurants/{restaurant_id}/inventory_items")
    invalid_docs = [
        snapshot for snapshot in inventory.stream()
        if str((snapshot.to_dict() or {}).get("item_name", "")).strip().casefold()
        in INVALID_INVENTORY_NAMES
    ]
    invalid_ids = {snapshot.id for snapshot in invalid_docs}
    if not invalid_ids:
        return 0

    references = (
        ("stock_movements", ("item_id", "ingredient_id")),
        ("waste_records", ("inventory_item_id",)),
        ("waste_records_v2", ("ingredient_id",)),
        ("recipe_ingredients", ("ingredient_id",)),
        ("purchase_lines", ("ingredient_id",)),
        ("daily_sales", ("ingredient_id", "item_id")),
        ("staff_consumptions", ("ingredient_id",)),
    )
    linked: dict[str, list[str]] = {}
    for collection_name, fields in references:
        for record in database.db.collection(f"restaurants/{restaurant_id}/{collection_name}").stream():
            data = record.to_dict() or {}
            if any(data.get(field) in invalid_ids for field in fields):
                linked.setdefault(record.id, []).append(collection_name)

    if linked:
        raise ValueError(
            "Invalid inventory entries are referenced by other records: "
            + ", ".join(
                f"{record_id} ({', '.join(collections)})"
                for record_id, collections in sorted(linked.items())
            )
        )

    batch = database.db.batch()
    for snapshot in invalid_docs:
        batch.delete(snapshot.reference)
    batch.commit()
    return len(invalid_docs)


def _refresh_generated_documents(database: Any, restaurant_id: str) -> int:
    docs = build_documents((datetime.now(timezone.utc) + timedelta(hours=8)).date())
    writes = [
        (collection_path, document_id, record)
        for collection_path, document_id, record in docs
        if f"restaurants/{restaurant_id}/" in collection_path
    ]
    for offset in range(0, len(writes), 450):
        batch = database.db.batch()
        for collection_path, document_id, record in writes[offset:offset + 450]:
            batch.set(database.db.collection(collection_path).document(document_id), record)
        batch.commit()
    return len(writes)


def _inventory_summary(database: Any, restaurant_id: str) -> list[dict[str, Any]]:
    collection = database.db.collection(f"restaurants/{restaurant_id}/inventory_items")
    generated_ids = {ingredient["id"] for ingredient in INGREDIENTS}
    return [
        record
        for snapshot in collection.stream()
        if snapshot.id in generated_ids
        and (record := snapshot.to_dict() or {}).get("system_generated_data") is True
    ]


def migrate(database: Any, restaurant_id: str, apply: bool) -> tuple[list[dict[str, Any]], int, int]:
    as_of = (datetime.now(timezone.utc) + timedelta(hours=8)).date()
    documents = build_documents(as_of)
    planned_inventory = {
        document_id: record
        for collection_path, document_id, record in documents
        if collection_path == f"restaurants/{restaurant_id}/inventory_items"
    }
    inventory = list(database.db.collection(
        f"restaurants/{restaurant_id}/inventory_items"
    ).stream())
    invalid_count = sum(
        str((snapshot.to_dict() or {}).get("item_name", "")).strip().casefold()
        in INVALID_INVENTORY_NAMES
        for snapshot in inventory
    )
    linked_records = []
    invalid_ids = {
        snapshot.id for snapshot in inventory
        if str((snapshot.to_dict() or {}).get("item_name", "")).strip().casefold()
        in INVALID_INVENTORY_NAMES
    }
    references = (
        ("stock_movements", ("item_id", "ingredient_id")),
        ("waste_records", ("inventory_item_id",)),
        ("waste_records_v2", ("ingredient_id",)),
        ("recipe_ingredients", ("ingredient_id",)),
        ("purchase_lines", ("ingredient_id",)),
        ("daily_sales", ("ingredient_id", "item_id")),
        ("staff_consumptions", ("ingredient_id",)),
    )
    for collection_name, fields in references:
        for snapshot in database.db.collection(f"restaurants/{restaurant_id}/{collection_name}").stream():
            record = snapshot.to_dict() or {}
            if any(record.get(field) in invalid_ids for field in fields):
                linked_records.append(f"{collection_name}/{snapshot.id}")
    if linked_records:
        raise ValueError(
            "Cannot remove invalid inventory entries because records reference them: "
            + ", ".join(linked_records)
        )

    if apply:
        removed = _delete_unreferenced_invalid_inventory(database, restaurant_id)
        written = _refresh_generated_documents(database, restaurant_id)
        return _inventory_summary(database, restaurant_id), removed, written

    return [
        record for record in planned_inventory.values()
        if record.get("system_generated_data") is True
    ], invalid_count, len(documents)


def main() -> None:
    from ..config import settings
    from ..repositories.database import FirestoreDatabase

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restaurant-id", default=RESTAURANT_ID)
    parser.add_argument("--apply", action="store_true", help="Write changes to Firestore.")
    args = parser.parse_args()
    if settings.DATABASE_BACKEND != "firestore":
        parser.error("This migration requires DATABASE_BACKEND=firestore.")
    if not settings.GOOGLE_CLOUD_PROJECT:
        parser.error("GOOGLE_CLOUD_PROJECT must be configured.")

    database = FirestoreDatabase()
    inventory, removed, refreshed = migrate(database, args.restaurant_id, args.apply)
    if args.apply:
        print(f"Removed {removed} unlinked invalid inventory records; refreshed {refreshed} generated records.")
    else:
        print(f"Would remove {removed} unlinked invalid inventory records and refresh {refreshed} generated records.")
    for record in sorted(inventory, key=lambda item: str(item.get("item_name", ""))):
        print(
            f"{record.get('item_name')}: {record.get('total_current_quantity')} "
            f"{record.get('base_unit')} on hand"
        )


if __name__ == "__main__":
    main()
