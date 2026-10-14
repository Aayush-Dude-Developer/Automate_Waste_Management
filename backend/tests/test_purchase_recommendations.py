from datetime import date, timedelta

import pytest

from backend.schemas.purchase_recommendations import RecommendationStatusUpdate
from backend.seed_purchase_demo import build_documents
from backend.services import purchase_recommendation_service as recommendations
from backend.services import stock_service


class FakeDatabase:
    def __init__(self, collections=None):
        self.collections = collections or {}

    def get_collection(self, path):
        return self.collections.setdefault(path, [])

    def query_collection(self, path, filters=None, order_by=None, limit=None):
        rows = list(self.get_collection(path))
        for field, operator, value in filters or []:
            if operator == "==":
                rows = [row for row in rows if row.get(field) == value]
            elif operator == ">=":
                rows = [row for row in rows if row.get(field) is not None and row[field] >= value]
            elif operator == "<=":
                rows = [row for row in rows if row.get(field) is not None and row[field] <= value]
            elif operator == "in":
                rows = [row for row in rows if row.get(field) in value]
            else:
                raise ValueError(operator)
        if order_by:
            field, direction = order_by
            rows.sort(key=lambda row: row.get(field), reverse=direction == "DESCENDING")
        return rows[:limit] if limit else rows

    def get_document(self, path, document_id):
        return next((row for row in self.get_collection(path) if row.get("id") == document_id), None)

    def add_document(self, path, document_id, data):
        rows = self.get_collection(path)
        for index, row in enumerate(rows):
            if row.get("id") == document_id:
                rows[index] = data
                return
        rows.append(data)

    def query_noop(self):
        return None

    def transition_document(self, path, document_id, expected_status, data):
        current = self.get_document(path, document_id)
        if (current.get("status") if current else None) != expected_status:
            raise ValueError("Recommendation status changed; refresh and try again.")
        if current:
            self.add_document(path, document_id, data)
        else:
            self.add_document(path, document_id, data)
        return data


def rice_inventory(stock=5):
    return {
        "id": "rice",
        "ingredient_id": "rice",
        "item_name": "Jasmine Rice",
        "input_unit": "kg",
        "base_unit": "kg",
        "unit_cost": 4,
        "current_quantity_in_store": stock,
        "current_quantity_in_use": 0,
        "total_current_quantity": stock,
        "reorder_threshold": 2,
        "safety_stock": 1,
        "supplier_id": "supplier-a",
        "lead_time_days": 2,
        "minimum_order_quantity": 5,
        "pack_size": 5,
        "yield_percentage": 100,
        "yield_stage": "cooked",
    }


def base_data(as_of: date):
    sales = []
    for offset in range(1, 57):
        sold = as_of - timedelta(days=offset)
        sales.append({
            "id": f"sale-{offset}",
            "sale_date": sold.isoformat(),
            "recipe_id": "rice-bowl",
            "net_quantity_sold": 4,
        })
    return {
        "restaurants/demo/inventory_items": [rice_inventory()],
        "restaurants/demo/recipes": [{
            "id": "rice-bowl",
            "recipe_id": "rice-bowl",
            "recipe_name": "Rice Bowl",
            "is_active": True,
        }],
        "restaurants/demo/recipe_ingredients": [{
            "id": "recipe-rice",
            "recipe_id": "rice-bowl",
            "ingredient_id": "rice",
            "required_quantity": 2,
            "required_unit": "kg",
            "required_stage": "cooked",
            "yield_stage_reference": None,
            "servings_per_batch": 2,
        }],
        "restaurants/demo/daily_sales": sales,
    }


def test_weekday_sales_yield_projection_order_date_and_supplier_rounding(monkeypatch):
    as_of = date(2026, 10, 11)
    database = FakeDatabase(base_data(as_of))
    monkeypatch.setattr(recommendations, "db", database)

    result = recommendations.get_purchase_recommendations("demo", 7, as_of)
    row = result.recommendations[0]

    assert row.forecast_daily_consumption == pytest.approx(2)
    assert row.sales_basis[0].forecast_portions == pytest.approx(28)
    assert row.sales_basis[0].raw_quantity_per_portion == pytest.approx(0.5)
    assert row.sales_basis[0].trend_factor == pytest.approx(1)
    assert row.current_usable_stock == 5
    assert row.projected_stockout_date == date(2026, 10, 14)
    assert row.recommended_order_date == date(2026, 10, 11)
    assert row.recommended_purchase_quantity == 15
    assert row.estimated_purchase_cost == 60
    assert row.priority == "critical"
    assert "56 days" in row.explanation


def test_confirmed_incoming_order_reduces_purchase_requirement(monkeypatch):
    as_of = date(2026, 10, 11)
    data = base_data(as_of)
    forecast_start = as_of + timedelta(days=1)
    data["restaurants/demo/purchase_recommendations"] = [{
        "id": "order-1",
        "ingredient_id": "rice",
        "status": "ordered",
        "expected_delivery_date": (forecast_start + timedelta(days=1)).isoformat(),
        "recommended_purchase_quantity": 5,
        "order_reference": "PO-100",
    }]
    database = FakeDatabase(data)
    monkeypatch.setattr(recommendations, "db", database)

    row = recommendations.get_purchase_recommendations("demo", 7, as_of).recommendations[0]

    assert len(row.incoming_orders) == 1
    assert row.recommended_purchase_quantity == 10


def test_lot_stock_excludes_expired_quantity_and_shows_remaining_batches(monkeypatch):
    as_of = date(2026, 10, 11)
    data = base_data(as_of)
    data["restaurants/demo/inventory_items"][0].update({
        "lot_tracking_enabled": True,
        "untracked_stock_quantity": 0.5,
    })
    data["restaurants/demo/purchase_invoices"] = [
        {"id": "expired-invoice", "purchase_id": "expired-invoice", "verification_status": "verified"},
        {"id": "near-invoice", "purchase_id": "near-invoice", "verification_status": "verified"},
    ]
    data["restaurants/demo/purchase_lines"] = [
        {
            "id": "expired-line", "purchase_id": "expired-invoice", "ingredient_id": "rice",
            "expiry_date": "2026-10-10", "quantity_received": 2,
            "remaining_usable_quantity": 2, "usable_unit": "kg",
        },
        {
            "id": "near-line", "purchase_id": "near-invoice", "ingredient_id": "rice",
            "expiry_date": "2026-10-15", "quantity_received": 3,
            "remaining_usable_quantity": 3, "usable_unit": "kg",
        },
    ]
    monkeypatch.setattr(recommendations, "db", FakeDatabase(data))

    row = recommendations.get_purchase_recommendations("demo", 7, as_of).recommendations[0]

    assert row.current_usable_stock == pytest.approx(3.5)
    assert any(batch.expired and batch.remaining_usable_quantity == 2 for batch in row.expiry_batches)
    assert any(not batch.expired and batch.remaining_usable_quantity == 3 for batch in row.expiry_batches)
    assert any("Expired batch balances are excluded" in warning for warning in row.reliability_warnings)


def test_lot_depletion_uses_earliest_unexpired_batch_and_rejects_shortage(monkeypatch):
    as_of = date(2026, 10, 11)
    database = FakeDatabase({
        "restaurants/demo/purchase_invoices": [
            {"id": "expired-invoice", "purchase_id": "expired-invoice", "verification_status": "verified"},
            {"id": "near-invoice", "purchase_id": "near-invoice", "verification_status": "verified"},
            {"id": "later-invoice", "purchase_id": "later-invoice", "verification_status": "verified"},
        ],
        "restaurants/demo/purchase_lines": [
            {"id": "expired", "purchase_id": "expired-invoice", "ingredient_id": "rice", "expiry_date": "2026-10-10", "remaining_usable_quantity": 100},
            {"id": "near", "purchase_id": "near-invoice", "ingredient_id": "rice", "expiry_date": "2026-10-12", "remaining_usable_quantity": 3},
            {"id": "later", "purchase_id": "later-invoice", "ingredient_id": "rice", "expiry_date": "2026-11-12", "remaining_usable_quantity": 5},
        ],
    })
    monkeypatch.setattr(stock_service, "db", database)
    item = {"id": "rice", "ingredient_id": "rice", "item_name": "Jasmine Rice", "lot_tracking_enabled": True}

    writes, allocations, untracked_remaining = stock_service.prepare_lot_depletion("demo", item, 4, as_of)

    assert [write[1] for write in writes] == ["near", "later"]
    assert [write[2]["remaining_usable_quantity"] for write in writes] == [0, 4]
    assert allocations == [
        {"purchase_line_id": "near", "quantity": 3},
        {"purchase_line_id": "later", "quantity": 1},
    ]
    assert untracked_remaining == 0
    with pytest.raises(ValueError, match="Insufficient unexpired usable stock"):
        stock_service.prepare_lot_depletion("demo", item, 9, as_of)


def test_synthetic_demo_dataset_populates_reliable_recommendation_inputs(monkeypatch):
    as_of = date(2026, 10, 11)
    seeded = {}
    for path, _, document in build_documents(as_of):
        seeded.setdefault(path, []).append(document)
    database = FakeDatabase(seeded)
    monkeypatch.setattr(recommendations, "db", database)

    dashboard = recommendations.get_purchase_recommendations("taiken_kharadi", 7, as_of)

    assert len(seeded["restaurants/taiken_kharadi/daily_sales"]) == 56 * 3
    assert len(seeded["restaurants/taiken_kharadi/recipes"]) == 3
    assert dashboard.recommendations
    assert not any("No sales records" in warning for warning in dashboard.data_warnings)
    for recommendation in dashboard.recommendations:
        assert recommendation.supplier_lead_time_days is not None
        assert recommendation.supplier_id
        assert not any("Minimum order quantity is not configured" in warning for warning in recommendation.reliability_warnings)
        assert not any("Pack size is not configured" in warning for warning in recommendation.reliability_warnings)
        assert not any("Lot-level expiry tracking is not enabled" in warning for warning in recommendation.reliability_warnings)


def test_missing_sales_and_recipe_data_is_warned_without_fabricated_demand(monkeypatch):
    database = FakeDatabase({
        "restaurants/demo/inventory_items": [rice_inventory(stock=0)],
        "restaurants/demo/recipes": [],
        "restaurants/demo/recipe_ingredients": [],
        "restaurants/demo/daily_sales": [],
    })
    monkeypatch.setattr(recommendations, "db", database)

    result = recommendations.get_purchase_recommendations("demo", 7, date(2026, 10, 11))

    assert result.recommendations == []
    assert result.ingredients_requiring_replenishment == 0
    assert any("No sales records" in warning for warning in result.data_warnings)
    assert any("No active recipes" in warning for warning in result.data_warnings)


def test_recommendation_approval_order_and_receipt_states_are_idempotent(monkeypatch):
    as_of = date(2026, 10, 11)
    data = base_data(as_of)
    data["restaurants/demo/purchase_invoices"] = [{
        "id": "invoice-1",
        "purchase_id": "invoice-1",
        "verification_status": "verified",
    }]
    data["restaurants/demo/purchase_lines"] = [{
        "id": "line-1",
        "purchase_line_id": "line-1",
        "purchase_id": "invoice-1",
        "ingredient_id": "rice",
    }]
    database = FakeDatabase(data)
    monkeypatch.setattr(recommendations, "db", database)
    row = recommendations.get_purchase_recommendations("demo", 7, as_of).recommendations[0]
    common = {
        "ingredient_id": "rice",
        "forecast_start_date": row.forecast_start_date,
        "forecast_period_days": 7,
    }

    approved = recommendations.update_recommendation_status(
        "demo",
        row.recommendation_id,
        RecommendationStatusUpdate(status="approved", **common),
    )
    assert approved["recommended_purchase_quantity"] == pytest.approx(15)
    with pytest.raises(ValueError, match="status transition"):
        recommendations.update_recommendation_status(
            "demo",
            row.recommendation_id,
            RecommendationStatusUpdate(status="approved", **common),
        )
    recommendations.update_recommendation_status(
        "demo",
        row.recommendation_id,
        RecommendationStatusUpdate(
            status="ordered",
            order_reference="PO-100",
            expected_delivery_date=date(2026, 10, 14),
            **common,
        ),
    )
    received = recommendations.update_recommendation_status(
        "demo",
        row.recommendation_id,
        RecommendationStatusUpdate(status="received", purchase_line_id="line-1", **common),
    )
    assert received["status"] == "received"
    with pytest.raises(ValueError, match="status transition"):
        recommendations.update_recommendation_status(
            "demo",
            row.recommendation_id,
            RecommendationStatusUpdate(status="received", purchase_line_id="line-1", **common),
        )


def test_duplicate_purchase_line_cannot_be_linked_to_two_recommendations(monkeypatch):
    as_of = date(2026, 10, 11)
    data = base_data(as_of)
    data["restaurants/demo/purchase_invoices"] = [{
        "id": "invoice-1", "purchase_id": "invoice-1", "verification_status": "verified",
    }]
    data["restaurants/demo/purchase_lines"] = [{
        "id": "line-1", "purchase_line_id": "line-1", "purchase_id": "invoice-1", "ingredient_id": "rice",
    }]
    period_start = as_of + timedelta(days=1)
    duplicate_id = recommendations._recommendation_id(period_start, 14, "rice")
    data["restaurants/demo/purchase_recommendations"] = [
        {
            "id": "another-recommendation",
            "recommendation_id": "another-recommendation",
            "ingredient_id": "rice",
            "status": "received",
            "purchase_line_id": "line-1",
        },
        {
            "id": duplicate_id,
            "recommendation_id": duplicate_id,
            "ingredient_id": "rice",
            "forecast_start_date": period_start.isoformat(),
            "forecast_period_days": 14,
            "forecast_key": f"{period_start.isoformat()}:14",
            "status": "ordered",
            "order_reference": "PO-200",
            "expected_delivery_date": "2026-10-20",
        },
    ]
    database = FakeDatabase(data)
    monkeypatch.setattr(recommendations, "db", database)

    with pytest.raises(ValueError, match="already linked"):
        recommendations.update_recommendation_status(
            "demo",
            duplicate_id,
            RecommendationStatusUpdate(
                status="received",
                ingredient_id="rice",
                forecast_start_date=period_start,
                forecast_period_days=14,
                purchase_line_id="line-1",
            ),
        )
