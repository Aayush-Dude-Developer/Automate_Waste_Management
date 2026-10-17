from backend.agents import investigation_agent, tools


class FakeDatabase:
    def __init__(self, collections):
        self.collections = collections
        self.saved = []

    def get_collection(self, path):
        return self.collections.get(path, [])

    def add_document(self, path, document_id, data):
        self.saved.append((path, document_id, data))


def test_waste_history_matches_unlinked_imports_and_inventory_linked_records(monkeypatch):
    database = FakeDatabase({
        "restaurants/restaurant/inventory_items": [
            {"id": "inv_noodles", "item_name": "Chinese Noodles"},
        ],
        "restaurants/restaurant/waste_records": [
            {"item_name": "Chinese Noodles", "quantity": 500, "unit": "g", "reason": "Over-preparation"},
            {"item_name": "Tiger Prawns", "quantity": 1, "unit": "kg", "reason": "Spoiled"},
        ],
        "restaurants/restaurant/waste_records_v2": [
            {"ingredient_id": "inv_noodles", "quantity": 0.5, "unit": "kg", "waste_reason": "Over-preparation"},
        ],
    })
    monkeypatch.setattr(tools, "db", database)

    history = tools.get_recent_waste_history("restaurant", "Chinese Noodles")

    assert len(history) == 2
    assert {record["reason"] for record in history} == {"Over-preparation"}
    assert investigation_agent._waste_totals(history) == {"kg": 1.0}
    assert investigation_agent._common_reasons(history) == ["Over-preparation (2 records)"]


def test_investigation_report_contains_frequency_totals_reasons_and_suggestions(monkeypatch):
    database = FakeDatabase({})
    monkeypatch.setattr(investigation_agent, "db", database)
    monkeypatch.setattr(investigation_agent.settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(investigation_agent, "get_inventory_status", lambda *_: {})
    monkeypatch.setattr(investigation_agent, "get_recent_waste_history", lambda *_: [
        {"quantity": 500, "unit": "g", "reason": "Over-preparation"},
        {"quantity": 0.5, "unit": "kg", "reason": "Over-preparation"},
    ])
    monkeypatch.setattr(investigation_agent, "check_donation_eligibility", lambda *_: "Not assessed.")

    report = investigation_agent.run_surplus_investigation("restaurant", "", "Chinese Noodles")

    assert report.waste_frequency_count == 2
    assert report.total_waste_by_unit == {"kg": 1.0}
    assert report.common_waste_reasons == ["Over-preparation (2 records)"]
    assert report.waste_reduction_suggestions
    assert len(database.saved) == 1
