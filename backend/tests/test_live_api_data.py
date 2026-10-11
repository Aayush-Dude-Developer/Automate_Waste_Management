from datetime import datetime, timedelta, timezone

from backend.routers import analytics
from backend.services import document_service
from backend.repositories import database


class FakeDatabase:
    def __init__(self, collections):
        self.collections = collections
        self.saved = {}

    def get_collection(self, path):
        return self.collections.get(path, [])

    def add_document(self, path, document_id, data):
        self.saved[(path, document_id)] = data


def test_dashboard_aggregates_restaurant_records(monkeypatch):
    today = datetime.now(timezone.utc).date()
    collections = {
        "restaurants/demo/waste_records": [
            {"date": today.isoformat(), "quantity": 500, "unit": "gm", "financial_loss_inr": 120},
            {"date": (today - timedelta(days=8)).isoformat(), "quantity": 1, "unit": "kg", "financial_loss_inr": 20},
        ],
        "restaurants/demo/inventory_items": [{"status": "reorder_recommended"}],
        "restaurants/demo/ai_investigations": [{"status": "PENDING_MANAGER_APPROVAL"}],
        "restaurants/demo/donation_handovers": [{"id": "donation-1"}],
    }
    monkeypatch.setattr(analytics, "db", FakeDatabase(collections))

    result = analytics.get_dashboard_metrics("demo")

    assert result.total_waste_week_kg == 0.5
    assert result.financial_loss_week_inr == 120
    assert result.inventory_risk_items == 1
    assert result.pending_interventions == 1
    assert result.donation_handovers == 1


def test_waste_trend_has_no_hardcoded_sample_data(monkeypatch):
    today = datetime.now(timezone.utc).date()
    monkeypatch.setattr(
        analytics,
        "db",
        FakeDatabase({
            "restaurants/demo/waste_records": [
                {"date": today.isoformat(), "quantity": 250, "unit": "gm"},
            ],
        }),
    )

    result = analytics.get_waste_trend("demo")

    assert len(result) == 7
    assert result[-1].waste == 0.25
    assert sum(point.waste for point in result) == 0.25


def test_document_upload_does_not_return_fabricated_ocr(monkeypatch):
    database = FakeDatabase({})
    monkeypatch.setattr(document_service, "db", database)

    result = document_service.process_document_upload(
        b"file contents",
        "waste.jpg",
        "waste",
        "demo",
    )

    assert result.extracted_records == []
    assert result.confidence_score == 0
    assert "OCR is not available" in result.message
    assert ("restaurants/demo/documents", result.document_id) in database.saved


def test_firestore_initialization_failure_does_not_silently_use_local_database(monkeypatch):
    monkeypatch.setattr(database.settings, "DATABASE_BACKEND", "firestore")

    def fail_initialization():
        raise OSError("Firestore credentials unavailable")

    monkeypatch.setattr(database, "FirestoreDatabase", fail_initialization)

    try:
        database.get_db()
    except RuntimeError as error:
        assert "Firestore is configured" in str(error)
    else:
        raise AssertionError("Firestore initialization failure must not use local storage.")
