from google import genai

from backend.agents import investigation_agent


class FakeDatabase:
    def __init__(self):
        self.saved = []

    def add_document(self, collection_path, document_id, data):
        self.saved.append((collection_path, document_id, data))


def test_gemini_high_demand_returns_bounded_deterministic_fallback(monkeypatch):
    database = FakeDatabase()
    monkeypatch.setattr(investigation_agent, "db", database)
    monkeypatch.setattr(investigation_agent.settings, "GEMINI_API_KEY", "configured-key")
    monkeypatch.setattr(
        investigation_agent,
        "get_inventory_status",
        lambda *_: {
            "total_current_quantity": 5,
            "unit": "kg",
            "unit_cost_inr": 20,
        },
    )
    monkeypatch.setattr(investigation_agent, "get_recent_waste_history", lambda *_: [])
    monkeypatch.setattr(investigation_agent, "check_donation_eligibility", lambda *_: "Needs review.")

    client_options = []

    class FailedInteraction:
        def create(self, **_kwargs):
            raise RuntimeError("503 service unavailable")

    class FailedClient:
        def __init__(self, **kwargs):
            client_options.append(kwargs["http_options"])
            self.interactions = FailedInteraction()

    monkeypatch.setattr(genai, "Client", FailedClient)

    result = investigation_agent.run_surplus_investigation(
        "demo",
        "ingredient-1",
        "Rice",
    )

    assert result.analysis_source == "deterministic"
    assert "temporarily unavailable" in result.investigation_summary
    assert "Demand changes have not been verified." in result.hypotheses
    assert client_options[0].timeout == investigation_agent.GEMINI_TIMEOUT_MS
    assert client_options[0].retry_options.attempts == 1
    assert len(database.saved) == 1
    assert database.saved[0][0] == "restaurants/demo/ai_investigations"
