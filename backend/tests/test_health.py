import asyncio
import httpx
from backend.main import app


def request(path, headers=None):
    async def send_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, headers=headers)
    return asyncio.run(send_request())


def test_health_requires_verified_user_even_with_tenant_header(monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    response = request("/api/health", headers={"X-Restaurant-Id": "other-restaurant"})

    assert response.status_code == 401


def test_health_allows_local_development_without_firebase(monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    response = request("/api/health")

    assert response.status_code == 200


def test_health_check_for_authenticated_user():
    from backend.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"email": "test@example.com", "uid": "test-user"}
    try:
        response = request("/api/health", headers={"X-Restaurant-Id": "other-restaurant"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data
    assert isinstance(data["gemini_ready"], bool)
