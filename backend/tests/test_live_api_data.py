from datetime import datetime, timedelta, timezone

from google.genai import errors as genai_errors

from backend.routers import analytics
from backend.schemas.documents import AmendRecordsRequest
from backend.services import document_service
from backend.repositories import database


class FakeDatabase:
    def __init__(self, collections):
        self.collections = collections
        self.saved = {}

    def get_collection(self, path):
        return self.collections.get(path, [])

    def query_collection(self, path, filters=None, order_by=None, limit=None):
        records = list(self.get_collection(path))
        for field, operator, value in filters or []:
            if operator == "==":
                records = [record for record in records if record.get(field) == value]
            elif operator == ">=":
                records = [record for record in records if record.get(field) is not None and record[field] >= value]
            elif operator == "<=":
                records = [record for record in records if record.get(field) is not None and record[field] <= value]
            elif operator == "<":
                records = [record for record in records if record.get(field) is not None and record[field] < value]
            elif operator == "in":
                records = [record for record in records if record.get(field) in value]
        if order_by:
            field, direction = order_by
            records.sort(key=lambda record: record.get(field), reverse=direction.upper() == "DESCENDING")
        if limit is not None:
            records = records[:limit]
        return records

    def count_collection(self, path, filters=None):
        return len(self.query_collection(path, filters))

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
    assert result.waste_trend[-1].waste == 0.5


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


def test_document_upload_reports_missing_extraction_configuration(monkeypatch):
    database = FakeDatabase({})
    monkeypatch.setattr(document_service, "db", database)
    monkeypatch.setattr(document_service.settings, "GEMINI_API_KEY", "")

    try:
        document_service.process_document_upload(b"file contents", "waste.jpg", "waste", "demo")
    except document_service.DocumentExtractionUnavailable as error:
        assert "GEMINI_API_KEY" in str(error)
    else:
        raise AssertionError("Upload succeeded without document extraction configuration.")

    saved_document = next(
        data for (path, _document_id), data in database.saved.items()
        if path == "restaurants/demo/documents"
    )
    assert saved_document["status"] == "extraction_failed"


def test_document_upload_returns_gemini_extracted_records(monkeypatch):
    database = FakeDatabase({})
    monkeypatch.setattr(document_service, "db", database)
    monkeypatch.setattr(document_service.settings, "GEMINI_API_KEY", "configured-key")
    records = [{"date": "2026-10-14", "item_name": "Tomatoes", "quantity": 2, "unit": "kg"}]
    monkeypatch.setattr(
        document_service,
        "extract_document_records",
        lambda *_: (records, 0.92, ["checked_by"]),
    )

    result = document_service.process_document_upload(b"file contents", "waste.jpg", "waste", "demo")

    assert result.extracted_records == records
    assert result.confidence_score == 0.92
    assert result.ambiguous_fields == ["checked_by"]
    assert "date" in result.available_fields
    assert "checked_by" in result.available_fields
    saved_document = next(
        data for (path, _document_id), data in database.saved.items()
        if path == "restaurants/demo/documents"
    )
    assert saved_document["status"] == "extracted"


def test_document_extraction_sends_uploaded_image_to_gemini(monkeypatch):
    records = [{"item_name": "Tomatoes", "unit_cost_inr": 42}]

    class FakeModel:
        def generate_content(self, **request):
            self.request = request
            return type(
                "Response",
                (),
                {"text": '{"extracted_records": [{"item_name": "Tomatoes", "unit_cost_inr": 42}], "confidence_score": 0.9, "ambiguous_fields": []}'},
            )()

    model = FakeModel()
    monkeypatch.setattr(document_service.settings, "GEMINI_API_KEY", "configured-key")
    monkeypatch.setattr(
        document_service.genai, "Client", lambda **_kwargs: type("Client", (), {"models": model})()
    )

    extracted, confidence, ambiguous_fields = document_service.extract_document_records(
        b"image data", "inventory.jpg", "inventory_items"
    )

    assert extracted == records
    assert confidence == 0.9
    assert ambiguous_fields == []
    image_part = model.request["contents"][1]
    assert "closest matching canonical field names" in model.request["contents"][0]
    assert "Source documents can use different names" in model.request["contents"][0]
    assert image_part.inline_data.mime_type == "image/jpeg"
    assert image_part.inline_data.data == b"image data"


def test_document_extraction_reports_gemini_503_as_temporary_unavailability(monkeypatch):
    class FakeModel:
        def generate_content(self, **_request):
            raise genai_errors.ServerError(
                503,
                {"error": {"message": "Model temporarily unavailable."}},
            )

    monkeypatch.setattr(document_service.settings, "GEMINI_API_KEY", "configured-key")
    monkeypatch.setattr(
        document_service.genai,
        "Client",
        lambda **_kwargs: type("Client", (), {"models": FakeModel()})(),
    )

    try:
        document_service.extract_document_records(b"image data", "waste.jpg", "waste")
    except document_service.DocumentExtractionUnavailable as error:
        assert "temporarily unavailable (503)" in str(error)
        assert "try again shortly" in str(error)
    else:
        raise AssertionError("Gemini 503 was not reported as temporary unavailability.")


def test_document_amendment_applies_customer_instruction(monkeypatch):
    current_records = [{"item_name": "Tomatoes", "quantity": 2, "unit": "kg"}]
    updated_records = [{"item_name": "Tomatoes", "quantity": 4, "unit": "kg"}]
    captured = {}

    def fake_generate(prompt, contents):
        captured["prompt"] = prompt
        captured["contents"] = contents
        return {"updated_records": updated_records, "message": "Changed row 1 quantity to 4."}

    monkeypatch.setattr(document_service, "_generate_json", fake_generate)
    request = AmendRecordsRequest(
        target_entity="waste_records",
        current_records=current_records,
        amendment="Change the quantity in row 1 to 4.",
    )

    result = document_service.amend_document_records(request)

    assert result.updated_records == updated_records
    assert "Change the quantity in row 1 to 4." in captured["prompt"]
    assert "current_records" not in captured["prompt"]
    assert current_records[0]["quantity"] == 2


def test_document_amendment_rejects_empty_records():
    request = AmendRecordsRequest(
        target_entity="waste_records",
        current_records=[],
        amendment="Make a change",
    )
    try:
        document_service.amend_document_records(request)
    except ValueError:
        pass
    else:
        raise AssertionError("Empty amendment record set should fail before Gemini is called.")


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
