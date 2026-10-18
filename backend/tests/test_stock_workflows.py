from datetime import date, datetime, timezone

import pytest

from backend.schemas.inventory import InventoryItemCreate, StockMovementCreate, YieldStage
from backend.schemas.stock import (
    PhysicalStocktake,
    PurchaseInvoiceCreate,
    RecipeCreate,
    SaleCreate,
    StaffConsumptionCreate,
    WasteRecordCreateV2,
)
from backend.services import inventory_service, stock_service
from backend.migrations import migrate_stock_schema


class FakeDatabase:
    def __init__(self, collections=None):
        self.collections = collections or {}

    def get_collection(self, path):
        return self.collections.setdefault(path, [])

    def query_collection(self, path, filters=None, order_by=None, limit=None):
        records = list(self.get_collection(path))
        for field, operator, value in filters or []:
            if operator == "==":
                records = [record for record in records if record.get(field) == value]
            elif operator == ">=":
                records = [record for record in records if record.get(field) is not None and record[field] >= value]
            elif operator == "<":
                records = [record for record in records if record.get(field) is not None and record[field] < value]
            elif operator == "<=":
                records = [record for record in records if record.get(field) is not None and record[field] <= value]
            elif operator == "in":
                records = [record for record in records if record.get(field) in value]
            else:
                raise ValueError(f"Unsupported query operator: {operator}")
        if order_by:
            field, direction = order_by
            records.sort(key=lambda record: record.get(field), reverse=direction.upper() == "DESCENDING")
        if limit is not None:
            records = records[:limit]
        return records

    def count_collection(self, path, filters=None):
        return len(self.query_collection(path, filters))

    def get_document(self, path, document_id):
        return next((doc for doc in self.get_collection(path) if doc.get("id") == document_id), None)

    def add_document(self, path, document_id, data):
        self.set_documents([(path, document_id, data)])

    def set_documents(self, writes):
        for path, document_id, data in writes:
            collection = self.get_collection(path)
            for index, current in enumerate(collection):
                if current.get("id") == document_id:
                    collection[index] = data
                    break
            else:
                collection.append(data)

    def create_documents(self, writes):
        path, document_id, _ = writes[0]
        if self.get_document(path, document_id):
            raise ValueError(f"Document {document_id} already exists.")
        self.set_documents(writes)

    def transition_document(self, path, document_id, expected_status, data):
        current = self.get_document(path, document_id)
        if (current.get("status") if current else None) != expected_status:
            raise ValueError("Recommendation status changed; refresh and try again.")
        if current:
            self.add_document(path, document_id, data)
        else:
            self.create_documents([(path, document_id, data)])
        return data


def item(item_id, name, unit="kg", **extra):
    return {
        "id": item_id,
        "ingredient_id": item_id,
        "item_name": name,
        "base_unit": unit,
        "input_unit": unit,
        "output_unit": unit,
        "current_quantity_in_store": 100.0,
        "current_quantity_in_use": 0.0,
        "total_current_quantity": 100.0,
        "reorder_threshold": 5,
        "unit_cost_inr": 40.0,
        **extra,
    }


def test_inventory_accepts_new_names_and_validates_negative_yield():
    created = InventoryItemCreate(
        item_name="Tomatoes",
        category="Produce",
        storage_location="Chiller",
        input_unit="kg",
        unit_cost=40,
        stock_in_store=8,
        stock_in_use=1,
        yield_percentage=-20,
        lead_time_days=2,
    )
    assert created.base_unit == "kg"
    assert created.current_quantity_in_store == 8
    assert created.current_quantity_in_use == 1
    assert created.yield_type == "negative"

    with pytest.raises(ValueError):
        YieldStage(
            stage_name="cleaning", input_stage="raw", output_stage="cleaned",
            input_unit="kg", output_unit="kg", yield_percentage=-100,
        )


@pytest.mark.parametrize(
    ("ingredient", "quantity", "unit", "stage", "expected"),
    [
        (item("tomato", "Tomatoes", yield_percentage=-20, yield_stage="cleaned"), 4, "kg", "cleaned", 5),
        (item("rice", "Rice", yield_percentage=100, yield_stage="cooked"), 2, "kg", "cooked", 1),
        (item("tomato", "Tomatoes", yield_percentage=-20, yield_stage="cleaned"), 4000, "g", "cleaned", 5),
    ],
)
def test_yield_conversion_to_raw_stock_units(ingredient, quantity, unit, stage, expected):
    raw, stock_unit = stock_service.raw_ingredient_quantity(ingredient, quantity, unit, stage)
    assert raw == pytest.approx(expected)
    assert stock_unit == "kg"


def test_multiple_yield_stages_are_applied_once_in_reverse():
    ingredient = item("chicken", "Chicken", yield_stages=[
        {"stage_name": "trim", "input_stage": "raw", "output_stage": "trimmed", "input_unit": "kg", "output_unit": "kg", "yield_percentage": -10},
        {"stage_name": "cook", "input_stage": "trimmed", "output_stage": "cooked", "input_unit": "kg", "output_unit": "kg", "yield_percentage": -20},
    ])
    raw, _ = stock_service.raw_ingredient_quantity(ingredient, 0.72, "kg", "cooked", "cook")
    assert raw == pytest.approx(1.0)


def test_yield_conversion_rejects_missing_stages_and_incompatible_units():
    with pytest.raises(ValueError, match="do not convert"):
        stock_service.raw_ingredient_quantity(item("rice", "Rice"), 2, "kg", "cooked")
    with pytest.raises(ValueError, match="Cannot convert"):
        stock_service.convert_quantity(2, "kg", "piece")


def test_purchase_verification_updates_received_stock_only_once_and_rejects_duplicate_invoice(monkeypatch):
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [item("rice", "Rice")],
    })
    monkeypatch.setattr(stock_service, "db", database)
    purchase = PurchaseInvoiceCreate(
        supplier_id="supplier-1",
        invoice_number="INV-100",
        invoice_date=date(2026, 10, 1),
        received_date=date(2026, 10, 2),
        total_amount=500,
        line_items=[{
            "ingredient_id": "rice",
            "quantity_purchased": 10,
            "purchase_unit": "kg",
            "unit_price": 50,
            "quantity_received": 8,
            "expiry_date": "2026-12-01",
            "batch_number": "B-1",
        }],
    )
    invoice = stock_service.create_purchase("demo", purchase)
    assert database.get_collection("restaurants/demo/inventory_items")[0]["total_current_quantity"] == 100
    with pytest.raises(ValueError, match="already been recorded"):
        stock_service.create_purchase("demo", purchase)

    stock_service.verify_purchase("demo", invoice.purchase_id)
    stock_service.verify_purchase("demo", invoice.purchase_id)
    assert database.get_collection("restaurants/demo/inventory_items")[0]["total_current_quantity"] == 108
    movements = database.get_collection("restaurants/demo/stock_movements")
    assert len(movements) == 1
    assert movements[0]["quantity_delta"] == 8
    assert database.get_collection("restaurants/demo/purchase_lines")[0]["remaining_usable_quantity"] == 8


def test_purchase_with_multiple_batches_updates_same_ingredient_for_total_received(monkeypatch):
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [item("rice", "Rice")],
    })
    monkeypatch.setattr(stock_service, "db", database)
    purchase = PurchaseInvoiceCreate(
        supplier_id="supplier-1",
        invoice_number="INV-BATCH",
        invoice_date=date(2026, 10, 1),
        received_date=date(2026, 10, 2),
        total_amount=700,
        line_items=[
            {"ingredient_id": "rice", "quantity_purchased": 5, "purchase_unit": "kg", "unit_price": 50, "quantity_received": 5, "batch_number": "A"},
            {"ingredient_id": "rice", "quantity_purchased": 5, "purchase_unit": "kg", "unit_price": 50, "quantity_received": 2, "batch_number": "B"},
        ],
    )
    invoice = stock_service.create_purchase("demo", purchase)
    stock_service.verify_purchase("demo", invoice.purchase_id)
    assert database.get_collection("restaurants/demo/inventory_items")[0]["total_current_quantity"] == 107
    assert sorted(movement["balance_after"] for movement in database.get_collection("restaurants/demo/stock_movements")) == [105, 107]


def test_manual_stock_deduction_updates_lot_balance_and_audit_allocation(monkeypatch):
    rice = item(
        "rice", "Rice", lot_tracking_enabled=True, untracked_stock_quantity=0,
        current_quantity_in_store=10, total_current_quantity=10,
    )
    rice["restaurant_id"] = "demo"
    rice["status"] = "in_stock"
    rice["updated_at"] = datetime.now(timezone.utc).isoformat()
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [rice],
        "restaurants/demo/purchase_invoices": [
            {"id": "invoice-a", "purchase_id": "invoice-a", "verification_status": "verified"},
            {"id": "invoice-b", "purchase_id": "invoice-b", "verification_status": "verified"},
        ],
        "restaurants/demo/purchase_lines": [
            {"id": "line-a", "purchase_line_id": "line-a", "purchase_id": "invoice-a", "ingredient_id": "rice", "expiry_date": "2027-01-01", "remaining_usable_quantity": 4},
            {"id": "line-b", "purchase_line_id": "line-b", "purchase_id": "invoice-b", "ingredient_id": "rice", "expiry_date": "2027-02-01", "remaining_usable_quantity": 6},
        ],
    })
    monkeypatch.setattr(inventory_service, "db", database)
    monkeypatch.setattr(stock_service, "db", database)

    inventory_service.record_stock_movement(
        "demo",
        StockMovementCreate(item_id="rice", movement_type="ADJUSTMENT_AUDIT", quantity_delta=-5, unit="kg"),
        user="test",
    )

    lines = database.get_collection("restaurants/demo/purchase_lines")
    movement = database.get_collection("restaurants/demo/stock_movements")[0]
    assert [line["remaining_usable_quantity"] for line in lines] == [0, 5]
    assert movement["lot_allocations"] == [
        {"purchase_line_id": "line-a", "quantity": 4},
        {"purchase_line_id": "line-b", "quantity": 1},
    ]


def test_schema_migration_is_additive_and_idempotent(monkeypatch):
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [{
            "id": "old-rice", "item_name": "Unlisted Rice", "base_unit": "kg",
            "unit_cost_inr": 80, "current_quantity_in_store": 6,
            "current_quantity_in_use": 1, "reorder_threshold": 2,
        }],
    })
    monkeypatch.setattr(migrate_stock_schema, "db", database)
    assert migrate_stock_schema.migrate_inventory_documents("demo") == 1
    assert "unit_cost" not in database.get_collection("restaurants/demo/inventory_items")[0]
    assert migrate_stock_schema.migrate_inventory_documents("demo", apply=True) == 1
    migrated = database.get_collection("restaurants/demo/inventory_items")[0]
    assert migrated["ingredient_id"] == "old-rice"
    assert migrated["unit_cost"] == 80
    assert migrated["stock_in_store"] == 6
    assert migrated["yield_percentage"] == 0
    assert migrated["yield_stage"] == "no change"
    assert migrate_stock_schema.migrate_inventory_documents("demo", apply=True) == 0


def test_singapore_migration_adds_yields_and_updates_profile_without_changing_stock(monkeypatch):
    chicken = item(
        "chicken", "Chicken Leg", yield_percentage=0, yield_stages=[],
        yield_stage=None, current_quantity_in_store=12, current_quantity_in_use=3,
    )
    unknown = item(
        "other", "Unlisted Ingredient", yield_percentage=0, yield_stages=[],
        yield_stage=None,
    )
    profile = {
        "id": "demo",
        "name": "Old Restaurant",
        "company_name": "Keep this company",
        "timezone": "Asia/Kolkata",
        "currency": "INR",
    }
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [chicken, unknown],
        "restaurants/demo/profile": [{"id": "main", **profile}],
    })
    monkeypatch.setattr(migrate_stock_schema, "db", database)
    count = migrate_stock_schema.migrate_inventory_documents(
        "demo", apply=True, restaurant_profile=profile,
    )

    migrated_chicken, migrated_unknown = database.get_collection("restaurants/demo/inventory_items")
    assert count == 2
    assert migrated_chicken["yield_percentage"] == -15
    assert migrated_chicken["yield_type"] == "negative"
    assert migrated_chicken["yield_stage"] == "trimmed"
    assert migrated_chicken["total_current_quantity"] == 100
    assert migrated_chicken["current_quantity_in_store"] == 12
    assert migrated_unknown["yield_percentage"] == 0
    assert migrated_unknown["yield_stage"] == "no change"

    updated_profile = next(
        record for record in database.get_collection("restaurants/demo/profile")
        if record.get("name") == "Straits Garden Kitchen"
    )
    assert updated_profile["name"] == "Straits Garden Kitchen"
    assert updated_profile["location"] == "Kharadi, Pune, India"
    assert updated_profile["timezone"] == "Asia/Kolkata"
    assert updated_profile["company_name"] == "Keep this company"
    assert updated_profile["currency"] == "INR"


def test_sales_convert_recipe_yield_and_exclude_cancelled_portions(monkeypatch):
    rice = item("rice", "Rice", yield_percentage=100, yield_stage="cooked")
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [rice],
        "restaurants/demo/recipes": [{
            "id": "recipe-1", "recipe_id": "recipe-1", "recipe_name": "Rice bowl",
            "is_active": True,
        }],
        "restaurants/demo/recipe_ingredients": [{
            "id": "row-1", "recipe_id": "recipe-1", "ingredient_id": "rice",
            "required_quantity": 2, "required_unit": "kg", "required_stage": "cooked",
            "yield_stage_reference": None, "servings_per_batch": 4,
        }],
    })
    monkeypatch.setattr(stock_service, "db", database)
    sale = SaleCreate(
        sale_date=date(2026, 10, 4), recipe_id="recipe-1", quantity_sold=3,
        quantity_cancelled=1, net_sales_amount=200, sales_source="POS",
    )
    saved = stock_service.create_sale("demo", sale)
    assert saved.net_quantity_sold == 2
    assert database.get_collection("restaurants/demo/inventory_items")[0]["total_current_quantity"] == pytest.approx(99.5)
    theory = stock_service.get_theoretical_consumption("demo", "2026-10")
    assert theory[0].theoretical_raw_consumption == pytest.approx(0.5)


def test_prepared_sale_uses_actual_prepared_quantity_for_stock(monkeypatch):
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [item("tomato", "Tomato")],
        "restaurants/demo/recipes": [{"id": "r", "recipe_id": "r", "recipe_name": "Salad"}],
        "restaurants/demo/recipe_ingredients": [{
            "id": "ri", "recipe_id": "r", "ingredient_id": "tomato",
            "required_quantity": 0.5, "required_unit": "kg", "required_stage": "raw",
            "servings_per_batch": 1,
        }],
    })
    monkeypatch.setattr(stock_service, "db", database)
    stock_service.create_sale("demo", SaleCreate(
        sale_date=date(2026, 10, 4), recipe_id="r", quantity_sold=3,
        quantity_cancelled=1, quantity_prepared=3, net_sales_amount=100, sales_source="POS",
    ))
    assert database.get_collection("restaurants/demo/inventory_items")[0]["total_current_quantity"] == pytest.approx(98.5)


def test_monthly_stock_balance_and_stocktake_keep_calculated_and_actual_values_separate(monkeypatch):
    month = "2026-10"
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [item("rice", "Rice")],
        "restaurants/demo/monthly_stock_balances": [{
            "id": "rice_2026-09", "ingredient_id": "rice", "month": "2026-09",
            "opening_stock": 5, "calculated_closing_stock": 10,
            "actual_closing_stock": 8, "physical_count_verified": True,
        }],
        "restaurants/demo/stock_movements": [
            {"id": "p", "item_id": "rice", "movement_type": "RECEIPT_PURCHASE", "quantity_delta": 10, "unit": "kg", "timestamp": "2026-10-02T10:00:00+00:00"},
            {"id": "s", "item_id": "rice", "movement_type": "USAGE_SALES_RECIPE", "quantity_delta": -2, "unit": "kg", "timestamp": "2026-10-03T10:00:00+00:00"},
            {"id": "m", "item_id": "rice", "movement_type": "USAGE_STAFF_MEAL", "quantity_delta": -1, "unit": "kg", "timestamp": "2026-10-04T10:00:00+00:00"},
            {"id": "w", "item_id": "rice", "movement_type": "WASTE_RECORDED", "quantity_delta": -1, "unit": "kg", "timestamp": "2026-10-05T10:00:00+00:00"},
            {"id": "i", "item_id": "rice", "movement_type": "ADJUSTMENT_AUDIT", "quantity_delta": 3, "unit": "kg", "timestamp": "2026-10-06T10:00:00+00:00"},
            {"id": "o", "item_id": "rice", "movement_type": "ADJUSTMENT_AUDIT", "quantity_delta": -1, "unit": "kg", "timestamp": "2026-10-07T10:00:00+00:00"},
        ],
    })
    monkeypatch.setattr(stock_service, "db", database)
    balance = stock_service.get_monthly_balances("demo", month)[0]
    assert balance.opening_stock == 8
    assert balance.calculated_closing_stock == 16
    assert balance.actual_closing_stock is None
    assert balance.provisional is True
    assert not any(
        row.get("id") == "rice_2026-10"
        for row in database.get_collection("restaurants/demo/monthly_stock_balances")
    )

    counted = stock_service.record_stocktake("demo", "rice", month, PhysicalStocktake(actual_closing_stock=15, verified_by="Manager"))
    assert counted.calculated_closing_stock == 16
    assert counted.actual_closing_stock == 15
    assert counted.stock_variance == -1
    assert counted.physical_count_verified is True


def test_unverified_previous_month_carries_calculated_balance_provisionally(monkeypatch):
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [item("rice", "Rice")],
        "restaurants/demo/monthly_stock_balances": [{
            "id": "rice_2026-09", "ingredient_id": "rice", "month": "2026-09",
            "opening_stock": 5, "calculated_closing_stock": 7,
            "actual_closing_stock": None, "physical_count_verified": False,
        }],
    })
    monkeypatch.setattr(stock_service, "db", database)
    balance = stock_service.get_monthly_balances("demo", "2026-10")[0]
    assert balance.opening_stock == 7
    assert balance.provisional is True


def test_recipe_based_staff_consumption_uses_recipe_portions_once(monkeypatch):
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [item("rice", "Rice")],
        "restaurants/demo/recipes": [{"id": "r", "recipe_id": "r", "recipe_name": "Staff rice"}],
        "restaurants/demo/recipe_ingredients": [{
            "id": "ri", "recipe_id": "r", "ingredient_id": "rice",
            "required_quantity": 1, "required_unit": "kg", "required_stage": "raw",
            "servings_per_batch": 4,
        }],
    })
    monkeypatch.setattr(stock_service, "db", database)
    stock_service.create_staff_consumption("demo", StaffConsumptionCreate(
        consumption_date=date(2026, 10, 4), recipe_id="r", portions=4,
        staff_count=4, recorded_by="Manager",
    ))
    assert database.get_collection("restaurants/demo/inventory_items")[0]["total_current_quantity"] == 99
    assert len(database.get_collection("restaurants/demo/stock_movements")) == 1


def test_sale_and_staff_consumption_cannot_share_source_reference(monkeypatch):
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [item("rice", "Rice")],
        "restaurants/demo/recipes": [{"id": "r", "recipe_id": "r", "recipe_name": "Rice"}],
        "restaurants/demo/recipe_ingredients": [{
            "id": "ri", "recipe_id": "r", "ingredient_id": "rice",
            "required_quantity": 1, "required_unit": "kg", "required_stage": "raw",
            "servings_per_batch": 1,
        }],
    })
    monkeypatch.setattr(stock_service, "db", database)
    stock_service.create_sale("demo", SaleCreate(
        sale_date=date(2026, 10, 4), recipe_id="r", quantity_sold=1,
        net_sales_amount=10, sales_source="POS", source_reference="shift-meal-1",
    ))
    with pytest.raises(ValueError, match="already recorded"):
        stock_service.create_staff_consumption("demo", StaffConsumptionCreate(
            consumption_date=date(2026, 10, 4), ingredient_id="rice", quantity=1,
            unit="kg", recorded_by="Manager", source_reference=" shift-meal-1 ",
        ))


def test_prepared_food_waste_does_not_deduct_raw_ingredient_again(monkeypatch):
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [item("rice", "Rice")],
    })
    monkeypatch.setattr(stock_service, "db", database)
    stock_service.create_waste_record_v2("demo", WasteRecordCreateV2(
        waste_date=date(2026, 10, 4), ingredient_id="rice", quantity=2, unit="kg",
        waste_reason="Unsold", stage="cooked", waste_type="prepared_food",
        recorded_by="Chef",
    ))
    assert database.get_collection("restaurants/demo/inventory_items")[0]["total_current_quantity"] == 100
    assert database.get_collection("restaurants/demo/stock_movements") == []
